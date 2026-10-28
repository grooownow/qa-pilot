"""Release helper: CHANGELOG notes and the forgotten-version check."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release import ROOT, changelog_section, plugin_files, plugin_version  # noqa: E402

CHANGELOG = """# Changelog

## [1.1.0] — 2026-11-01

### Added
- New thing.

## [1.0.0] — 2026-10-28

- Old thing.
"""


class ReleaseTest(unittest.TestCase):
    def test_section_is_the_body_up_to_the_next_version(self):
        self.assertEqual(changelog_section(CHANGELOG, "1.1.0"), "### Added\n- New thing.")
        self.assertEqual(changelog_section(CHANGELOG, "1.0.0"), "- Old thing.")

    def test_missing_or_prefix_version_has_no_section(self):
        self.assertIsNone(changelog_section(CHANGELOG, "2.0.0"))
        self.assertIsNone(changelog_section(CHANGELOG, "1.0"))

    def test_only_plugin_files_need_a_new_version(self):
        changed = ["skills/test/SKILL.md", "knowledge/qa-pilot/rules/auth.md", ".claude-plugin/plugin.json",
                   "LICENSE", "README.md", "docs/qa/x.md", "scripts/kb/render_rules.py",
                   ".github/workflows/release.yml", "CHANGELOG.md"]
        self.assertEqual(plugin_files(changed), ["skills/test/SKILL.md", "knowledge/qa-pilot/rules/auth.md",
                                                 ".claude-plugin/plugin.json", "LICENSE"])

    def test_current_version_has_release_notes(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertTrue(changelog_section(text, plugin_version()))


if __name__ == "__main__":
    unittest.main()
