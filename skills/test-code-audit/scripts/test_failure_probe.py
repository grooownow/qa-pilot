import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("failure_probe.py")
SOURCE = b"def limit():\r\n    return 10\r\n\r\ndef ok(n):\r\n    return n <= limit()\r\n"
CHECK_OK = "import calc, sys; sys.exit(0 if calc.ok(10) and not calc.ok(11) else 1)"
CHECK_WEAK = "import calc, sys; sys.exit(0 if calc.ok(5) else 1)"


class FailureProbeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.src = self.dir / "calc.py"
        self.src.write_bytes(SOURCE)

    def tearDown(self):
        self.tmp.cleanup()

    def probe(self, line, find, replace, check, *extra):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--file", "calc.py", "--line", str(line), "--find", find,
             "--replace", replace, *extra, "--", sys.executable, "-c", check],
            cwd=self.dir, capture_output=True, text=True, env=env)
        return proc.returncode, json.loads(proc.stdout)

    def test_strong_test_kills_the_mutation(self):
        code, out = self.probe(5, "<=", "<", CHECK_OK)
        self.assertEqual((code, out["verdict"], out["restored"]), (0, "killed", True))
        self.assertEqual(self.src.read_bytes(), SOURCE)

    def test_weak_test_survives(self):
        code, out = self.probe(5, "<=", "<", CHECK_WEAK)
        self.assertEqual((code, out["verdict"]), (1, "survived"))
        self.assertEqual(self.src.read_bytes(), SOURCE)

    def test_red_baseline_proves_nothing(self):
        code, out = self.probe(5, "<=", "<", "import sys; sys.exit(1)")
        self.assertEqual((code, out["verdict"]), (3, "baseline-red"))
        self.assertEqual(self.src.read_bytes(), SOURCE)

    def test_find_must_be_on_the_line_exactly_once(self):
        for line, find in ((4, "<="), (5, "x"), (99, "<=")):
            code, out = self.probe(line, find, "<", CHECK_OK)
            self.assertEqual((code, out["verdict"]), (2, "error"))
        self.assertEqual(self.src.read_bytes(), SOURCE)

    def test_missing_command_is_an_error_not_survived(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--file", "calc.py", "--line", "5", "--find", "<=", "--replace", "<",
             "--no-baseline", "--", "no-such-command-qa-probe"],
            cwd=self.dir, capture_output=True, text=True)
        self.assertEqual((proc.returncode, json.loads(proc.stdout)["verdict"]), (2, "error"))
        self.assertEqual(self.src.read_bytes(), SOURCE)
        self.assertFalse((self.dir / "calc.py.qa-probe-orig").exists())

    def test_leftover_backup_blocks_the_probe(self):
        (self.dir / "calc.py.qa-probe-orig").write_bytes(SOURCE)
        code, out = self.probe(5, "<=", "<", CHECK_OK)
        self.assertEqual((code, out["verdict"]), (2, "error"))
        self.assertIn("mv ", out["error"])

    def test_signal_restores_the_file_and_stops_the_runner(self):
        for sig in (signal.SIGTERM, signal.SIGHUP):
            marker = self.dir / "runner.pid"
            hang = (f"import calc, os, time; open({str(marker)!r}, 'w').write(str(os.getpid())); "
                    "time.sleep(30) if calc.limit() == 9 else None")
            proc = subprocess.Popen(
                [sys.executable, str(SCRIPT), "--file", "calc.py", "--line", "2", "--find", "10", "--replace", "9",
                 "--no-baseline", "--", sys.executable, "-c", hang],
                cwd=self.dir, stdout=subprocess.PIPE, text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            deadline = time.time() + 10
            while not marker.exists() and time.time() < deadline:
                time.sleep(0.05)
            time.sleep(0.2)
            proc.send_signal(sig)
            out, _ = proc.communicate(timeout=10)
            self.assertEqual((proc.returncode, json.loads(out)["verdict"]), (5, "interrupted"))
            self.assertEqual(self.src.read_bytes(), SOURCE)
            self.assertFalse((self.dir / "calc.py.qa-probe-orig").exists())
            runner = int(marker.read_text())
            time.sleep(0.2)
            with self.assertRaises(ProcessLookupError):
                os.kill(runner, 0)
            marker.unlink()

    def test_each_write_lands_in_a_later_second(self):
        # Bytecode caches compare whole-second mtime + size; a same-length edit in the same
        # second would run stale code, in the mutated run or after the restore.
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import failure_probe
        finally:
            sys.path.pop(0)
        now = time.time_ns()
        os.utime(self.src, ns=(now, now))
        mutated_ns = failure_probe.write_after(self.src, SOURCE.replace(b"<=", b">="), now)
        restored_ns = failure_probe.write_after(self.src, SOURCE, mutated_ns)
        self.assertGreater(mutated_ns // 10**9, now // 10**9)
        self.assertGreater(restored_ns // 10**9, mutated_ns // 10**9)
        self.assertEqual(self.src.read_bytes(), SOURCE)

    def test_timeout_restores_the_file(self):
        hang = "import calc, sys, time; time.sleep(5) if calc.limit() == 9 else sys.exit(0)"
        code, out = self.probe(2, "10", "9", hang, "--timeout", "1")
        self.assertEqual((code, out["verdict"]), (4, "timeout"))
        self.assertEqual(self.src.read_bytes(), SOURCE)


if __name__ == "__main__":
    unittest.main()
