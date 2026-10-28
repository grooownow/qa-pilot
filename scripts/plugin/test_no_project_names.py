"""The repo never names the owner's real projects (owner rule, 1.0.1).

The names are stored only as SHA-256 hashes of their lowercase form, so this file does not
name them either. Every tracked path and text file is split into lowercase word tokens
(runs of [a-z0-9-]); each token, and each part of a hyphen-joined token, is hashed and
compared with the list. Ticket ids of one project are caught by a pattern built from parts.
"""
import hashlib
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# SHA-256 of the lowercase names. To add one: printf %s 'name' | shasum -a 256
FORBIDDEN = {
    "daf79813ecfbe95e289ecd0934b952d535625a480764e5616a6636817789aea8",
    "b3f6a67e041389bbd013b30a3c4587df567a5e77315214ac3b539b7ddba76331",
    "cef3d18dd2cecceff40fee2293619d5a3de3cd9a27b5bff37a8e55930f7ae2af",
    "6b442bc71e3024def8536680ef0d0f0c5a7e2bfce3054e16f5ae2c8af8d2ea0b",
    "7e42a22bcebc5dc6ed293568800a24b87f517cfb85f62c732cd8bc7c135565f4",
    "d5d7971ef642fb91d9c1839de923973383b42bcad7de4b9099c3b0ebad0a406d",
    "0bd7c14c4319c170b6c780d4b507872883b07d8594d815a47cef0da4eb145988",
    "8fdf56e707459e831f806e1202a1d79e24ef53316b226f25ef48954918ce5f62",
    "9d7b45b1cd7f171b920aa21c068e32972ecb288664c467e72dab8d32e88bc775",
    "dee7ffa505ec16ec7d279b42377db2ef2536a0fc6fc275f5f42536e36b5feb33",
}

TOKEN = re.compile(r"[a-z0-9-]+")
# Built from parts so this file does not match itself: a ticket id like <prefix>-123 or <prefix>-N.
TICKET = re.compile(r"\b" + "G" + "OV" + r"-(?:\d+|N\b|<)")


def tracked_files():
    names = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    for name in filter(None, names.decode().split("\0")):
        path = ROOT / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
        yield name, text


def words(text):
    found = set()
    for token in TOKEN.findall(text.lower()):
        found.add(token)
        found.update(part for part in token.split("-") if part)
    return found


def named(text):
    return any(hashlib.sha256(w.encode()).hexdigest() in FORBIDDEN for w in words(text))


class NoProjectNamesTest(unittest.TestCase):
    def test_no_project_names_in_paths_or_text(self):
        hits = [name for name, text in tracked_files() if named(name) or named(text)]
        self.assertEqual(hits, [])

    def test_no_project_ticket_ids(self):
        hits = [name for name, text in tracked_files() if TICKET.search(text)]
        self.assertEqual(hits, [])

    def test_matcher_catches_hyphen_parts_and_case(self):
        # Self-check with a harmless word: the matcher must see it inside paths, hyphens and mixed case.
        probe = hashlib.sha256(b"probeword").hexdigest()
        FORBIDDEN.add(probe)
        try:
            self.assertTrue(named("docs/x-ProbeWord-notes.md"))
            self.assertTrue(named("see ProbeWord's spec"))
            self.assertFalse(named("probewords"))
        finally:
            FORBIDDEN.discard(probe)
        self.assertTrue(TICKET.search("G" + "OV-617"))
        self.assertFalse(TICKET.search("PROJ-123"))


if __name__ == "__main__":
    unittest.main()
