import json
import tempfile
import unittest
from pathlib import Path

from score import agreement, score, validate_actions


def action(aid, bucket="should", kind="test", **extra):
    return {"id": aid, "bucket": bucket, "kind": kind, "title": f"Action {aid}", "expected": "x",
            "source": "spec:1", "level": "e2e", "target": "src/a.ts:1", **extra}


def doc(actions=(), cells=(), suppressed=()):
    return {"feature": "f", "depth": "standard", "actions": list(actions),
            "suppressed": list(suppressed), "cells": list(cells)}


class ValidateTest(unittest.TestCase):
    def test_valid_document_has_no_errors(self):
        errors, warnings = validate_actions(doc([action("A1")], [{"entity": "wf", "pattern": "QAP-WEB-001",
                                                                   "verdict": "OK"}]))
        self.assertEqual((errors, warnings), ([], []))

    def test_validate_missing_bucket(self):
        bad = action("A1")
        del bad["bucket"]
        errors, _ = validate_actions(doc([bad]))
        self.assertTrue(any("A1: bucket" in e for e in errors), errors)

    def test_question_bucket_matches_kind(self):
        errors, _ = validate_actions(doc([action("Q1", "should", "question")]))
        self.assertTrue(any("bucket 'question'" in e for e in errors), errors)
        errors, _ = validate_actions(doc([action("A1", "question", "test")]))
        self.assertTrue(any("bucket 'question'" in e for e in errors), errors)

    def test_test_and_bug_need_prescription_fields(self):
        bad = action("A1", "must", "bug")
        del bad["source"]
        errors, _ = validate_actions(doc([bad]))
        self.assertTrue(any("A1: source is required" in e for e in errors), errors)
        question = {"id": "Q1", "bucket": "question", "kind": "question", "title": "Which?"}
        self.assertEqual(validate_actions(doc([question]))[0], [])

    def test_na_cell_needs_evidence_and_bug_outside_must_warns(self):
        errors, _ = validate_actions(doc(cells=[{"entity": "wf", "pattern": "QAP-WEB-001", "verdict": "N/A"}]))
        self.assertTrue(any("N/A needs evidence" in e for e in errors), errors)
        _, warnings = validate_actions(doc([action("B1", "should", "bug")]))
        self.assertIn("B1: a bug belongs in must", warnings)

    def test_bad_verdict_and_not_a_list(self):
        errors, _ = validate_actions(doc(cells=[{"entity": "wf", "pattern": "QAP-WEB-001", "verdict": "MAYBE"}]))
        self.assertTrue(any("verdict" in e for e in errors), errors)
        errors, _ = validate_actions({"actions": "nope"})
        self.assertTrue(any("actions must be a list" in e for e in errors), errors)

    def test_should_cap_warning(self):
        _, warnings = validate_actions(doc([action(f"S{i}") for i in range(9)]))
        self.assertIn("should>8", warnings)

    def test_must_warning_over_10(self):
        _, warnings = validate_actions(doc([action(f"M{i}", bucket="must") for i in range(11)]))
        self.assertIn("must>10", warnings)

    def test_empty_cells_reported(self):
        _, warnings = validate_actions(doc(cells=[{"entity": "wf", "pattern": "QAP-WEB-001", "verdict": ""}]))
        self.assertTrue(any("empty cell" in w for w in warnings), warnings)


class ScoreTest(unittest.TestCase):
    def test_score_counts(self):
        actions = doc([action("A1", "must", "bug"), action("A2"), action("A3", "highlight"),
                       action("Q1", "question", "question")])
        rubric = [{"id": "G1"}, {"id": "G2"}, {"id": "G3"}]
        mapping = {"G1": {"verdict": "pass"}, "G2": {"verdict": "partial"}}
        result = score(actions, mapping, rubric)
        self.assertEqual((result["pass"], result["partial"], result["fail"]), (1, 1, 1))
        self.assertEqual(result["buckets"], {"must": 1, "should": 1, "highlight": 1, "question": 1})
        self.assertEqual(result["questions"], 1)
        self.assertAlmostEqual(result["question_share"], 0.25)
        self.assertIn("G3: not mapped, counted as fail", result["warnings"])


class AgreementTest(unittest.TestCase):
    def test_agreement_union(self):
        a = doc(cells=[{"entity": "e", "pattern": "a", "verdict": "OK"}, {"entity": "e", "pattern": "b", "verdict": "GAP"}])
        b = doc(cells=[{"entity": "e", "pattern": "a", "verdict": "OK"}, {"entity": "e", "pattern": "c", "verdict": "OK"}])
        result = agreement(a, b)
        self.assertEqual((result["cells_union"], result["agree"]), (3, 1))
        self.assertAlmostEqual(result["ratio"], 0.333, places=3)

    def test_agreement_ignores_cells_without_keys(self):
        a = doc(cells=[{"verdict": "OK"}, {"entity": "e", "pattern": "a", "verdict": "OK"}])
        self.assertEqual(agreement(a, a)["cells_union"], 1)

    def test_agreement_no_cells(self):
        self.assertEqual(agreement(doc(), doc())["ratio"], 0.0)


class CliTest(unittest.TestCase):
    def test_validate_cli_exit_code(self):
        from score import main
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.json"
            path.write_text(json.dumps({"actions": [{"id": "A1"}]}))
            self.assertEqual(main(["score.py", "validate", str(path)]), 1)
            path.write_text(json.dumps(doc([action("A1")])))
            self.assertEqual(main(["score.py", "validate", str(path)]), 0)
            self.assertEqual(main(["score.py", "agreement", str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
