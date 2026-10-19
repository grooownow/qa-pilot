import unittest

from render_web_patterns import render


def pattern(rid, tier, title="Паттерн"):
    return {"id": rid, "kind": "rule", "severity": "must", "title": f"{title} {rid}",
            "statement": "s", "applies_to": ["requirements"],
            "check": {"mode": "heuristic", "how": "Вопрос к сущности."},
            "source": {"origin": "RFC 9110 §15.5.10"}, "authority": "normative",
            "pattern": {"tier": tier, "triggers": ["useMutation(", "rg -n 'onError'"], "level": "e2e",
                        "book_refs": ["SRK-API-001"]}}


def invariant(rid):
    return {"id": rid, "kind": "rule", "severity": "should", "title": f"Инвариант {rid}", "statement": "inv",
            "applies_to": ["requirements"], "check": {"mode": "heuristic", "how": "h"},
            "source": {"origin": "GOV.UK"}, "authority": "industry-practice"}


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
        self.assertEqual(md, render(list(reversed(patterns)), [invariant("QAP-WINV-001"), invariant("QAP-WINV-002")]))


if __name__ == "__main__":
    unittest.main()
