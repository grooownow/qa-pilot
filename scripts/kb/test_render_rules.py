import copy
import unittest

from render_rules import render_topic, validate_all

VALID = {
    "id": "SRK-FORM-001",
    "kind": "rule",
    "severity": "must",
    "title": "Проверять пробелы в начале и конце ввода",
    "statement": "Каждое текстовое поле нужно проверить с пробелами по краям значения.",
    "applies_to": ["test-plan", "live-product"],
    "check": {"mode": "heuristic", "how": "Ищем в плане сценарий с пробелами по краям."},
    "source": {"chunk_id": "s1-c07-01", "printed_pages": [41, 42]},
    "tags": ["forms"],
}
CHUNKS = {"s1-c07-01": {"id": "s1-c07-01", "printed_pages": [40, 44]}}


def with_change(**changes):
    r = copy.deepcopy(VALID)
    for key, value in changes.items():
        if value is None:
            r.pop(key)
        else:
            r[key] = value
    return r


class ValidateTest(unittest.TestCase):
    def assert_error(self, record, fragment, chunks=CHUNKS):
        errors = validate_all({"forms": [record]}, chunks)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_valid_record_passes_with_and_without_chunks(self):
        self.assertEqual(validate_all({"forms": [VALID]}, CHUNKS), [])
        self.assertEqual(validate_all({"forms": [VALID]}, None), [])

    def test_bad_enums(self):
        self.assert_error(with_change(kind="law"), "kind must be")
        self.assert_error(with_change(severity="high"), "severity must be")
        self.assert_error(with_change(applies_to=["everything"]), "applies_to")
        self.assert_error(with_change(applies_to=[]), "applies_to")
        self.assert_error(with_change(check={"mode": "auto", "how": "x"}), "check must be")
        self.assert_error(with_change(verification="maybe"), "verification")
        self.assert_error(with_change(decision=["не очищать"]), "'decision' must be a string")

    def test_missing_and_unknown_fields(self):
        self.assert_error(with_change(statement=None), "missing or empty 'statement'")
        self.assert_error(with_change(title="  "), "missing or empty 'title'")
        self.assert_error(with_change(quote="дословно"), "unknown fields")
        self.assert_error(with_change(id="FORM-1"), "id must look like")

    def test_duplicate_id_across_files(self):
        errors = validate_all({"forms": [VALID], "gui": [copy.deepcopy(VALID)]}, CHUNKS)
        self.assertTrue(any("duplicate id SRK-FORM-001" in e for e in errors), errors)

    def test_source_checked_against_chunks(self):
        self.assert_error(with_change(source={"chunk_id": "s9-c99-99"}), "unknown chunk_id")
        self.assert_error(with_change(source={"chunk_id": "s1-c07-01", "printed_pages": [90]}), "outside chunk")
        self.assertEqual(validate_all({"forms": [with_change(source={"chunk_id": "s9-c99-99"})]}, None), [])


class RenderTest(unittest.TestCase):
    def test_groups_by_kind_and_shows_check(self):
        tip = with_change(id="SRK-FORM-002", kind="tip", verification="doubtful")
        md = render_topic("forms", [tip, VALID])
        self.assertLess(md.index("## Жёсткие правила"), md.index("## Практические советы"))
        self.assertIn("**Как проверить:** Ищем в плане", md)
        self.assertIn("SRK-FORM-002 · Проверять пробелы в начале и конце ввода ⚠️ сомнительно", md)
        self.assertIn("с. 41–42", md)

    def test_renders_team_decision(self):
        md = render_topic("forms", [with_change(decision="Пароль при ошибке не очищать.")])
        self.assertIn("**Решение команды (приоритетнее книги):** Пароль при ошибке не очищать.", md)


if __name__ == "__main__":
    unittest.main()
