import unittest

from render_web_patterns import render


def pattern(rid, tier, title="Паттерн"):
    return {"id": rid, "kind": "rule", "severity": "must", "title": f"{title} {rid}",
            "statement": "s", "applies_to": ["requirements"],
            "check": {"mode": "heuristic", "how": "Вопрос к сущности."},
            "source": {"origin": "RFC 9110 §15.5.10"}, "authority": "normative",
            "pattern": {"tier": tier, "triggers": ["useMutation(", "rg -n 'onError'"], "level": "e2e",
                        "book_refs": ["QAC-API-001"]}}


def invariant(rid):
    return {"id": rid, "kind": "rule", "severity": "should", "title": f"Инвариант {rid}", "statement": "inv",
            "applies_to": ["requirements"], "check": {"mode": "heuristic", "how": "h"},
            "source": {"origin": "GOV.UK"}, "authority": "industry-practice"}


class NotApplicableTest(unittest.TestCase):
    def test_lists_patterns_by_project_kind(self):
        ui = {**pattern("QAP-WEB-002", "must-check"), "tags": ["needs-ui"]}
        back = {**pattern("QAP-WEB-001", "must-check"), "tags": ["needs-backend"]}
        text = render([ui, back], [invariant("QAP-WINV-001")])
        self.assertIn("- `has_ui: false`: QAP-WEB-002.", text)
        self.assertIn("- `has_backend: false`: QAP-WEB-001.", text)
        self.assertLess(text.index("## Not applicable by project kind"), text.index("## Must-check patterns"))


class RenderWebPatternsTest(unittest.TestCase):
    def test_render_web_patterns_sections_and_order(self):
        patterns = [pattern("QAP-WEB-003", "highlight"), pattern("QAP-WEB-002", "must-check"),
                    pattern("QAP-WEB-001", "must-check")]
        md = render(patterns, [invariant("QAP-WINV-002"), invariant("QAP-WINV-001")])
        order = ["## Entity card", "## Must-check patterns", "## Highlight-only patterns",
                 "## Web invariants"]
        positions = [md.index(h) for h in order]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(md.index("### QAP-WEB-001"), md.index("### QAP-WEB-002"))
        self.assertLess(md.index("### QAP-WEB-002"), md.index("## Highlight-only patterns"))
        self.assertGreater(md.index("QAP-WEB-003"), md.index("## Highlight-only patterns"))
        self.assertLess(md.index("QAP-WINV-001"), md.index("QAP-WINV-002"))
        self.assertIn("`useMutation(`", md)
        self.assertIn("| QAP-WEB-001 |", md)
        self.assertNotIn("| QAP-WEB-003 |", md)
        self.assertTrue(md.rstrip().endswith("ref qp-l4-7f3a9c -->"))
        self.assertEqual(md, render(list(reversed(patterns)), [invariant("QAP-WINV-001"), invariant("QAP-WINV-002")]))


if __name__ == "__main__":
    unittest.main()
