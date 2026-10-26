"""The repo never names the author of the book the rule catalog comes from (owner rule, 0.8.1)."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Built from parts so this file does not match itself.
NAME = re.compile("|".join(["sur" + "kov", "сур" + "ков"]), re.IGNORECASE)
OLD_PREFIX = re.compile(r"\b" + "S" + "RK" + r"\b")
# The only place allowed to know the old id prefix: reading override files written before 0.8.1.
OLD_PREFIX_ALLOWED = {"skills/spec-audit/scripts/rules_pack.py", "skills/spec-audit/scripts/test_rules_pack.py"}


def tracked_texts():
    names = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    for name in filter(None, names.decode().split("\0")):
        path = ROOT / name
        if not path.is_file():
            continue
        try:
            yield name, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


class NoAuthorNameTest(unittest.TestCase):
    def test_no_author_name_in_paths_or_text(self):
        hits = [name for name, text in tracked_texts() if NAME.search(name) or NAME.search(text)]
        self.assertEqual(hits, [])

    def test_old_id_prefix_only_in_compat_layer(self):
        hits = [name for name, text in tracked_texts()
                if OLD_PREFIX.search(text) and name not in OLD_PREFIX_ALLOWED]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
