"""Licence and ownership marker stay in place (owner rule, 2026-10-27)."""
import json
import unittest
from pathlib import Path

from find_copies import MARKER_REF, search_links

ROOT = Path(__file__).resolve().parents[2]
MARKED = ["skills/*/SKILL.md", "references/*.md", "agents/*.md", "knowledge/qa-pilot/README.md"]


class LicenseTest(unittest.TestCase):
    def test_license_file_is_polyform_noncommercial_with_notice(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("Required Notice: Copyright 2026 Ludvik4"))
        self.assertIn("# PolyForm Noncommercial License 1.0.0", text)
        self.assertIn("COMMERCIAL.md", text)

    def test_manifest_and_readme_name_the_licence(self):
        manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["license"], "PolyForm-Noncommercial-1.0.0")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("PolyForm Noncommercial", readme)
        self.assertIn("COMMERCIAL.md", readme)
        self.assertTrue((ROOT / "COMMERCIAL.md").is_file())

    def test_every_skill_reference_and_agent_carries_the_marker(self):
        files = [p for pattern in MARKED for p in ROOT.glob(pattern)]
        self.assertGreater(len(files), 30)
        missing = [str(p.relative_to(ROOT)) for p in files if MARKER_REF not in p.read_text(encoding="utf-8")]
        self.assertEqual(missing, [])

    def test_search_links_quote_the_needle_and_skip_the_own_repo(self):
        github, google = search_links("test delta")
        self.assertIn("%22test%20delta%22", github)
        self.assertIn("NOT+repo%3Agrooownow%2Fqa-pilot", github)
        self.assertIn("%22test%20delta%22", google)


if __name__ == "__main__":
    unittest.main()
