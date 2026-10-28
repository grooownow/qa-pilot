"""Licence and ownership marker stay in place (owner rule, 2026-10-27)."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_copies import MARKER_REF, search_links  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
# SHA-256 of the official PolyForm-Noncommercial-1.0.0.md (polyformproject/polyform-licenses, tag 1.0.0).
POLYFORM_NC_SHA256 = "c0ea4a896d2c8c394b29f9427589996db826cd501c512279ff0ed3ef48fabbe5"
FULL_MARKER = ("<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · "
               "PolyForm-Noncommercial-1.0.0 · ref " + MARKER_REF + " -->")
MARKED = ["skills/*/SKILL.md", "references/*.md", "agents/*.md", "knowledge/qa-pilot/README.md",
          "knowledge/qa-pilot/rules/*.md"]
NO_MIT = ["README.md", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "COMMERCIAL.md"]


class LicenseTest(unittest.TestCase):
    def test_license_is_the_official_polyform_text_with_notice(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("Required Notice: Copyright 2026 Ekaterina Pustovaia (Ludvik4"))
        body = text[text.index("# PolyForm Noncommercial License 1.0.0"):]
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), POLYFORM_NC_SHA256)
        self.assertIn("not part of the licence", text)

    def test_manifest_readme_and_commercial_terms(self):
        manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["license"], "PolyForm-Noncommercial-1.0.0")
        for name in ["README.md", "COMMERCIAL.md"]:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("PolyForm Noncommercial", text, name)
            self.assertIn("knowledge/catalog/", text, name)

    def test_mit_only_named_as_the_licence_of_earlier_versions(self):
        for name in NO_MIT:
            for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
                if "MIT" in line:
                    self.assertIn("0.9.0", line, f"{name}: {line}")

    def test_every_own_file_carries_the_marker(self):
        files = [p for pattern in MARKED for p in ROOT.glob(pattern)]
        self.assertGreater(len(files), 40)
        missing = [str(p.relative_to(ROOT)) for p in files
                   if p.read_text(encoding="utf-8").rstrip().splitlines()[-1] != FULL_MARKER]
        self.assertEqual(missing, [])

    def test_book_catalog_carries_no_ownership_marker(self):
        hits = [p.name for p in (ROOT / "knowledge/catalog").rglob("*.md") if MARKER_REF in p.read_text(encoding="utf-8")]
        self.assertEqual(hits, [])

    def test_search_links_quote_the_needle_and_skip_the_own_repo(self):
        github, google = search_links("QAP-WEB-001")
        self.assertIn("%22QAP-WEB-001%22", github)
        self.assertIn("-repo%3Agrooownow%2Fqa-pilot", github)
        self.assertTrue(google.endswith("%22QAP-WEB-001%22"))


if __name__ == "__main__":
    unittest.main()
