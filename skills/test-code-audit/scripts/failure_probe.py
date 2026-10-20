#!/usr/bin/env python3
"""Prove that a test can fail: break one line of the code under test, run the test, restore.

Usage:
  python3 failure_probe.py --file <path> --line <n> --find <text> --replace <text> \
      [--timeout 240] [--no-baseline] -- <test command…>

1. Baseline: runs the test command on the untouched code; it must pass.
2. Mutation: replaces <find> with <replace> on line <n> (must occur exactly once there).
   A backup is written to <path>.qa-probe-orig first.
3. Runs the test command again; the test must now fail.
4. Restores the file byte for byte (also on timeout, Ctrl-C, SIGTERM or SIGHUP), checks the
   hash and removes the backup. Both writes move the mtime to a later whole second, so
   bytecode caches see each change. If the probe itself is killed (SIGKILL), the backup stays: the next
   probe on that file refuses to start until it is restored with `mv <path>.qa-probe-orig <path>`.

Run it with a shell timeout of at least 2 × --timeout plus a minute.

Prints one JSON object. Exit codes:
  0 killed       — the test failed on the broken code: it can fail
  1 survived     — the test passed on the broken code: false green
  2 error        — bad arguments, <find> not on the line, command not found, a backup left
                   by an earlier probe, or the file was not restored
  3 baseline-red — the test fails (or times out) on the untouched code; the probe proves nothing
  4 timeout      — the mutated run did not finish (counts as no proof)
  5 interrupted  — the probe was stopped; the file was restored
"""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

TAIL_LINES = 15
BACKUP_SUFFIX = ".qa-probe-orig"


class Interrupted(Exception):
    pass


def on_signal(signum, _frame):
    raise Interrupted(signal.Signals(signum).name)


def run(cmd, timeout):
    """Return (exit code, last output lines); exit code None on timeout. Raises OSError if cmd can't start."""
    # Own process group, so a timeout or an interrupt also stops the runner's workers (npm → node → browsers).
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, ""
    except BaseException:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    lines = out.rstrip().splitlines()
    return proc.returncode, "\n".join(lines[-TAIL_LINES:])


def mutate(data, line, find, replace):
    """Return the mutated bytes, or raise ValueError when <find> is not exactly once on <line>."""
    lines = data.split(b"\n")
    if not 1 <= line <= len(lines):
        raise ValueError(f"line {line} is out of range (1–{len(lines)})")
    target, f, r = lines[line - 1], find.encode(), replace.encode()
    if target.count(f) != 1:
        raise ValueError(f"--find occurs {target.count(f)} times on line {line}, expected exactly 1")
    lines[line - 1] = target.replace(f, r)
    return b"\n".join(lines)


def write_after(path, data, previous_ns):
    """Write data and keep the mtime in a later whole second than previous_ns.

    Bytecode caches (CPython .pyc) compare mtime in whole seconds plus size, so a same-length
    edit within one second would run the cached old code. Returns the new mtime in ns."""
    path.write_bytes(data)
    if path.stat().st_mtime_ns // 10**9 <= previous_ns // 10**9:
        later = (previous_ns // 10**9 + 1) * 10**9
        os.utime(path, ns=(later, later))
    return path.stat().st_mtime_ns


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", required=True)
    ap.add_argument("--line", type=int, required=True)
    ap.add_argument("--find", required=True)
    ap.add_argument("--replace", required=True)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--no-baseline", action="store_true")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    report = {"file": args.file, "line": args.line, "find": args.find, "replace": args.replace, "cmd": cmd}

    def done(verdict, code, **extra):
        print(json.dumps({**report, "verdict": verdict, **extra}, ensure_ascii=False, indent=1))
        return code

    if not cmd:
        return done("error", 2, error="no test command after --")
    path = Path(args.file)
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if not path.is_file():
        return done("error", 2, error="file not found")
    if backup.exists():
        return done("error", 2, error=f"{backup} exists: an earlier probe was killed; restore with `mv {backup} {path}`")
    original = path.read_bytes()
    try:
        mutated = mutate(original, args.line, args.find, args.replace)
    except ValueError as e:
        return done("error", 2, error=str(e))

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, on_signal)
    try:
        if not args.no_baseline:
            code, tail = run(cmd, args.timeout)
            if code != 0:
                return done("baseline-red", 3, baseline_tail=tail if code is not None else "timeout")
    except OSError as e:
        return done("error", 2, error=f"cannot run the test command: {e}")
    except Interrupted as e:
        return done("interrupted", 5, signal=str(e), restored=True)

    digest = hashlib.sha256(original).hexdigest()
    backup.write_bytes(original)
    outcome = None
    mutated_ns = original_ns = path.stat().st_mtime_ns
    try:
        mutated_ns = write_after(path, mutated, original_ns)
        outcome = run(cmd, args.timeout)
    except (OSError, Interrupted) as e:
        outcome = e
    finally:
        # A second signal must not cut the restore short.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        write_after(path, original, mutated_ns)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        return done("error", 2, error=f"file was not restored — the original is in {backup}")
    backup.unlink()
    if isinstance(outcome, OSError):
        return done("error", 2, error=f"cannot run the test command: {outcome}", restored=True)
    if isinstance(outcome, Interrupted):
        return done("interrupted", 5, signal=str(outcome), restored=True)
    code, tail = outcome
    if code is None:
        return done("timeout", 4, restored=True)
    if code == 0:
        return done("survived", 1, restored=True, mutated_tail=tail)
    return done("killed", 0, restored=True, mutated_tail=tail)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
