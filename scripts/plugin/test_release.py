"""Release helper: CHANGELOG notes and the forgotten-version check."""
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release import ROOT, changelog_section, main, plugin_files, plugin_version  # noqa: E402

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
                   "LICENSE", "hooks/hooks.json", "skills/a b/ä.md", "README.md", "docs/qa/x.md",
                   "scripts/kb/render_rules.py", ".github/workflows/release.yml", "CHANGELOG.md",
                   ".claude-plugin/marketplace.json", ""]
        self.assertEqual(plugin_files(changed), ["skills/test/SKILL.md", "knowledge/qa-pilot/rules/auth.md",
                                                 ".claude-plugin/plugin.json", "LICENSE", "hooks/hooks.json",
                                                 "skills/a b/ä.md"])

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["release.py", *args])
        return code, out.getvalue(), err.getvalue()

    def test_cli_notes_and_usage(self):
        code, out, _ = self.run_main("notes")
        self.assertEqual(code, 0)
        self.assertTrue(out.strip())
        self.assertEqual(self.run_main()[0], 2)

    def test_cli_stale_with_an_unknown_tag_says_so(self):
        code, _, err = self.run_main("stale", "v0.0.0-missing")
        self.assertEqual(code, 1)
        self.assertIn("not in this checkout", err)

    def test_current_version_has_release_notes(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertTrue(changelog_section(text, plugin_version()))


if __name__ == "__main__":
    unittest.main()
