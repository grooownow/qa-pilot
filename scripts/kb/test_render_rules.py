import copy
import unittest

from render_rules import dangling_refs, render_topic, validate_all

VALID = {
    "id": "QAC-FORM-001",
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
        self.assertTrue(any("duplicate id QAC-FORM-001" in e for e in errors), errors)

    def test_source_checked_against_chunks(self):
        self.assert_error(with_change(source={"chunk_id": "s9-c99-99"}), "unknown chunk_id")
        self.assert_error(with_change(source={"chunk_id": "s1-c07-01", "printed_pages": [90]}), "outside chunk")
        self.assertEqual(validate_all({"forms": [with_change(source={"chunk_id": "s9-c99-99"})]}, None), [])


class NonBookRulesTest(unittest.TestCase):
    QAP = {**copy.deepcopy(VALID), "id": "QAP-INFRA-001", "source": {"origin": "pilot pawfile 2026-10-12"}}

    def test_qap_with_origin_passes_and_renders_origin(self):
        self.assertEqual(validate_all({"pilot": [self.QAP]}, CHUNKS), [])
        md = render_topic("pilot", [self.QAP])
        self.assertIn("источник: pilot pawfile 2026-10-12", md)
        self.assertIn("Собственные правила qa-pilot", md)

    def test_qap_without_origin_fails(self):
        bad = {**self.QAP, "source": {"chunk_id": "s1-c07-01"}}
        self.assertTrue(any("source.origin is required" in e for e in validate_all({"pilot": [bad]}, CHUNKS)))

    def test_book_rule_needs_chunk_id(self):
        bad = with_change(source={"origin": "somewhere"})
        self.assertTrue(any("source.chunk_id is required" in e for e in validate_all({"forms": [bad]}, CHUNKS)))


class AuthorityAndPatternTest(unittest.TestCase):
    WEB = {**copy.deepcopy(VALID), "id": "QAP-WEB-001", "source": {"origin": "RFC 9110 §15.5.10"},
           "pattern": {"tier": "must-check", "triggers": ["useMutation("], "level": "e2e", "book_refs": ["QAC-API-001"]}}

    def test_authority_values_validated(self):
        self.assertEqual(validate_all({"forms": [with_change(authority="normative", external_check="aligned")]}, CHUNKS), [])
        errors = validate_all({"forms": [with_change(authority="gospel")]}, CHUNKS)
        self.assertTrue(any("authority must be one of" in e for e in errors), errors)
        errors = validate_all({"forms": [with_change(external_check="maybe")]}, CHUNKS)
        self.assertTrue(any("external_check must be one of" in e for e in errors), errors)

    def test_pattern_only_on_web_ids(self):
        self.assertEqual(validate_all({"web-patterns": [self.WEB]}, CHUNKS), [])
        errors = validate_all({"forms": [with_change(pattern=self.WEB["pattern"])]}, CHUNKS)
        self.assertTrue(any("pattern is only allowed on QAP-WEB" in e for e in errors), errors)

    def test_pattern_shape(self):
        bad = copy.deepcopy(self.WEB)
        del bad["pattern"]["tier"]
        errors = validate_all({"web-patterns": [bad]}, CHUNKS)
        self.assertTrue(any("pattern.tier" in e for e in errors), errors)
        bad = copy.deepcopy(self.WEB)
        bad["pattern"]["level"] = "smoke"
        errors = validate_all({"web-patterns": [bad]}, CHUNKS)
        self.assertTrue(any("pattern.level" in e for e in errors), errors)

    def test_render_shows_authority(self):
        md = render_topic("forms", [with_change(authority="author-opinion", external_check="conflict")])
        self.assertIn("авторитет: author-opinion", md)
        self.assertIn("сверка со стандартом: conflict", md)
        self.assertNotIn("авторитет:", render_topic("forms", [VALID]))


class DanglingRefsTest(unittest.TestCase):
    def test_unknown_ids_in_text_and_book_refs_are_reported(self):
        r = with_change(rationale="Уточняет QAC-FORM-001 и QAP-TC-016.")
        web = {**copy.deepcopy(AuthorityAndPatternTest.WEB), "pattern": {**AuthorityAndPatternTest.WEB["pattern"],
                                                                          "book_refs": ["QAC-API-404"]}}
        errors = dangling_refs({"forms": [r], "web-patterns": [web]}, {"QAC-FORM-001", "QAP-WEB-001"})
        self.assertEqual(sorted(errors), ["QAC-FORM-001: refers to unknown QAP-TC-016",
                                          "QAP-WEB-001: refers to unknown QAC-API-404"])


class RenderTest(unittest.TestCase):
    def test_groups_by_kind_and_shows_check(self):
        tip = with_change(id="QAC-FORM-002", kind="tip", verification="doubtful")
        md = render_topic("forms", [tip, VALID])
        self.assertLess(md.index("## Жёсткие правила"), md.index("## Практические советы"))
        self.assertIn("**Как проверить:** Ищем в плане", md)
        self.assertIn("QAC-FORM-002 · Проверять пробелы в начале и конце ввода ⚠️ сомнительно", md)
        self.assertIn("с. 41–42", md)

    def test_renders_team_decision(self):
        md = render_topic("forms", [with_change(decision="Пароль при ошибке не очищать.")])
        self.assertIn("**Решение команды (приоритетнее книги):** Пароль при ошибке не очищать.", md)


if __name__ == "__main__":
    unittest.main()
