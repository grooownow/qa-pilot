import tempfile
import unittest
from pathlib import Path

from check_skills import check


def skill(root, name, description=None, body="", extra=""):
    description = description or f"Does things. Not for z (use qa-pilot:{name})."
    d = root / "skills" / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n{extra}---\n\n{body}\n")


class CheckSkillsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "references").mkdir()
        (self.root / "references" / "a.md").write_text("x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_skills_pass(self):
        skill(self.root, "test", body="Invoke `qa-pilot:explore`; read `../../references/a.md`.")
        skill(self.root, "explore", extra="user-invocable: false\n")
        self.assertEqual(check(self.root), [])

    def test_long_description_and_wrong_name(self):
        skill(self.root, "task-qa", description="x" * 1025)
        (self.root / "skills" / "other").mkdir()
        (self.root / "skills" / "other" / "SKILL.md").write_text("---\nname: renamed\ndescription: d\n---\n")
        errors = check(self.root)
        self.assertTrue(any("1025 chars, max 1024" in e for e in errors), errors)
        self.assertTrue(any("must equal the directory 'other'" in e for e in errors), errors)

    def test_unknown_skill_and_missing_file(self):
        skill(self.root, "audit", body="Run `qa-pilot:spec-audit` with `../../references/missing.md`.",
              extra="user-invocable: maybe\n")
        errors = check(self.root)
        self.assertTrue(any("unknown skill qa-pilot:spec-audit" in e for e in errors), errors)
        self.assertTrue(any("missing file references/missing.md" in e for e in errors), errors)
        self.assertTrue(any("user-invocable must be" in e for e in errors), errors)

    def test_script_references(self):
        skill(self.root, "onboard", body='Run `python3 "$SKILL_DIR/scripts/drift.py"`.')
        skill(self.root, "test", body='Run `python3 "$SKILL_DIR/../onboard/scripts/drift.py"` and `$SKILL_DIR/scripts/x.py`.')
        errors = check(self.root)
        self.assertEqual(sorted(errors), ["skills/onboard/SKILL.md: missing script scripts/drift.py",
                                          "skills/test/SKILL.md: missing script ../onboard/scripts/drift.py",
                                          "skills/test/SKILL.md: missing script scripts/x.py"])
        (self.root / "skills" / "onboard" / "scripts").mkdir()
        (self.root / "skills" / "onboard" / "scripts" / "drift.py").write_text("")
        self.assertEqual(check(self.root), ["skills/test/SKILL.md: missing script scripts/x.py"])

    def test_quoted_description_is_unquoted(self):
        skill(self.root, "test", description='"Says \\"hi\\": fine. Not for z (use qa-pilot:test)."')
        self.assertEqual(check(self.root), [])

    def test_description_needs_not_for(self):
        skill(self.root, "test", description="Does things.")
        self.assertEqual(check(self.root), ["skills/test/SKILL.md: description has no 'Not for' clause naming a qa-pilot:<skill>"])

    def test_not_for_must_name_a_sibling(self):
        skill(self.root, "test", description="Does things. Not for z.")
        self.assertEqual(check(self.root), ["skills/test/SKILL.md: description has no 'Not for' clause naming a qa-pilot:<skill>"])

    def test_not_for_in_quoted_description(self):
        skill(self.root, "test", description='"Does \\"x\\". Not for y (use qa-pilot:test)."')
        self.assertEqual(check(self.root), [])

    def test_missing_example(self):
        skill(self.root, "test", body="See `examples/report.md`.")
        self.assertEqual(check(self.root), ["skills/test/SKILL.md: missing example examples/report.md"])
        (self.root / "skills" / "test" / "examples").mkdir()
        (self.root / "skills" / "test" / "examples" / "report.md").write_text("x")
        self.assertEqual(check(self.root), [])


if __name__ == "__main__":
    unittest.main()
