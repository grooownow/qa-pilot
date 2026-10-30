import json
import tempfile
import unittest
from pathlib import Path

from rules_pack import NEEDS, build, effective_severity, parse_traits, rule_line


def record(rid, tags=(), applies=("requirements",), how="Проверить."):
    return {"id": rid, "kind": "rule", "severity": "must", "title": f"Правило {rid}", "statement": "s",
            "applies_to": list(applies), "check": {"mode": "heuristic", "how": how},
            "source": {"chunk_id": "s1-c01-01"}, "tags": list(tags)}


PROFILE = """# Profile

## Product traits

```yaml
platform: [web, pwa]   # web | pwa
api_style: [server-actions]
has_payments: false
has_auth: true
i18n: yes
```

## Commands
platform: [ios]
"""


class TraitsTest(unittest.TestCase):
    def test_parses_section_only_with_defaults(self):
        traits, found, _ = parse_traits(PROFILE)
        self.assertTrue(found)
        self.assertEqual(traits["platform"], ["web", "pwa"])
        self.assertEqual(traits["api_style"], ["server-actions"])
        self.assertIs(traits["has_auth"], True)
        self.assertIs(traits["i18n"], True)
        self.assertIs(traits["rtl"], False)

    def test_missing_section_gives_defaults(self):
        traits, found, _ = parse_traits("# no traits here")
        self.assertFalse(found)
        self.assertEqual(traits["platform"], ["web"])


class TraitFormsTest(unittest.TestCase):
    def test_comma_quoted_and_block_forms(self):
        text = ("## Product traits\nplatform: web, ios\nhas_payments: \"false\"\napi_style:\n  - rest\n  - graphql\n"
                "i18n: maybe\ncolour: blue\n")
        traits, _, warnings = parse_traits(text)
        self.assertEqual(traits["platform"], ["web", "ios"])
        self.assertIs(traits["has_payments"], False)
        self.assertEqual(traits["api_style"], ["rest", "graphql"])
        self.assertIs(traits["i18n"], False)
        self.assertEqual(len(warnings), 2)


class ProjectKindTest(unittest.TestCase):
    def needs(self, profile, tag):
        traits, _, warnings = parse_traits(profile)
        self.assertEqual(warnings, [])
        return NEEDS[tag](traits)

    def test_old_profile_keeps_ui_and_backend(self):
        self.assertTrue(self.needs("## Product traits\nplatform: [web]\n", "needs-ui"))
        self.assertTrue(self.needs("## Product traits\nplatform: [web]\n", "needs-backend"))

    def test_no_ui_and_no_backend(self):
        profile = "## Product traits\nplatform: [cli, library]\nhas_ui: false\nhas_backend: false\n"
        self.assertFalse(self.needs(profile, "needs-ui"))
        self.assertFalse(self.needs(profile, "needs-backend"))

    def test_app_rules_need_a_ui_or_a_backend(self):
        self.assertTrue(self.needs("## Product traits\nhas_ui: false\n", "needs-app"))
        self.assertFalse(self.needs("## Product traits\nhas_ui: false\nhas_backend: false\n", "needs-app"))

    def test_web_and_installed_platforms(self):
        self.assertTrue(self.needs("## Product traits\nplatform: [pwa]\n", "needs-web"))
        self.assertFalse(self.needs("## Product traits\nplatform: [cli]\n", "needs-web"))
        self.assertTrue(self.needs("## Product traits\nplatform: [cli]\n", "needs-installed"))
        self.assertFalse(self.needs("## Product traits\nplatform: [web]\n", "needs-installed"))


class RealCatalogTagsTest(unittest.TestCase):
    """The shipped knowledge base: the kind filter must really drop what it promises."""
    KB = Path(__file__).resolve().parents[3] / "knowledge"
    NO_UI = "## Product traits\nplatform: [cli]\napi_style: [rest]\nhas_ui: false\n"
    NO_BACKEND = "## Product traits\nplatform: [web]\nhas_backend: false\n"
    WEB = "## Product traits\nplatform: [web]\n"

    def titles(self, profile):
        packs, manifest = build(self.KB, profile, {}, ["requirements", "test-plan"])
        self.assertEqual(manifest["unknown_needs_tags"], [])
        return {r["id"] for rs in packs.values() for r in rs}

    def test_no_ui_drops_ui_topics(self):
        kept = self.titles(self.NO_UI)
        for prefix in ("QAC-GUI-", "QAC-HIG-", "QAP-UI-"):
            self.assertEqual([i for i in kept if i.startswith(prefix)], [])
        self.assertIn("QAC-FORM-014", kept)  # injection safety is a server concern too

    def test_no_backend_drops_server_topics(self):
        kept = self.titles(self.NO_BACKEND)
        self.assertEqual([i for i in kept if i.startswith(("QAC-DB-", "QAP-API-"))], [])

    def test_web_project_gets_no_native_only_rules(self):
        kept = self.titles(self.WEB)
        self.assertNotIn("QAC-INST-028", kept)  # uninstall
        self.assertIn("QAC-INST-037", kept)     # browser matrix


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        kb = Path(self.tmp.name)
        (kb / "catalog" / "rules").mkdir(parents=True)
        (kb / "qa-pilot" / "rules").mkdir(parents=True)
        (kb / "catalog" / "rules" / "mobile-hig.json").write_text(json.dumps([
            record("QAC-HIG-001", ["ios", "needs-ios"]),
            record("QAC-HIG-002", ["web"]),
        ]))
        (kb / "catalog" / "rules" / "requirements.json").write_text(json.dumps([
            record("QAC-REQ-001"),
            record("QAC-REQ-002", ["needs-payments"]),
            record("QAC-REQ-003", applies=("live-product",)),
            record("QAC-REQ-004", ["needs-teleport"]),
        ]))
        (kb / "qa-pilot" / "rules" / "pilot.json").write_text(json.dumps([record("QAP-AUTH-001", ["needs-auth"])]))
        self.kb = kb

    def tearDown(self):
        self.tmp.cleanup()

    def ids(self, packs):
        return {r["id"] for rs in packs.values() for r in rs}

    def test_trait_filtering(self):
        packs, manifest = build(self.kb, PROFILE, {}, ["requirements", "test-plan"])
        self.assertEqual(self.ids(packs), {"QAC-HIG-002", "QAC-REQ-001", "QAP-AUTH-001", "QAC-REQ-004"})
        self.assertIn("needs-ios", manifest["excluded"]["QAC-HIG-001"])
        self.assertIn("needs-payments", manifest["excluded"]["QAC-REQ-002"])
        self.assertEqual(manifest["unknown_needs_tags"], ["needs-teleport"])
        self.assertEqual(packs["platform"][0]["id"], "QAC-HIG-002")
        self.assertEqual(packs["core"][-1]["id"], "QAP-AUTH-001")

    def test_commercial_use_skips_the_book_catalog(self):
        commercial = PROFILE + "\n## Licence\n\n```yaml\nuse: commercial\n```\n"
        packs, manifest = build(self.kb, commercial, {}, ["requirements", "test-plan"])
        self.assertEqual(self.ids(packs), {"QAP-AUTH-001"})
        self.assertFalse(manifest["catalog"])
        self.assertTrue(any("book catalog skipped" in w for w in manifest["warnings"]))
        packs, manifest = build(self.kb, PROFILE + "\n## Licence\nuse: noncommercial\n", {}, ["requirements"])
        self.assertTrue(manifest["catalog"])
        self.assertIn("QAC-REQ-001", self.ids(packs))

    def test_no_catalog_flag_skips_the_book_catalog(self):
        packs, manifest = build(self.kb, PROFILE, {}, ["requirements", "test-plan"], catalog=False)
        self.assertEqual(self.ids(packs), {"QAP-AUTH-001"})
        self.assertFalse(manifest["catalog"])

    def test_untagged_rule_kept_even_without_profile(self):
        packs, manifest = build(self.kb, "", {}, ["requirements"])
        self.assertIn("QAC-REQ-001", self.ids(packs))
        self.assertNotIn("QAP-AUTH-001", self.ids(packs))
        self.assertFalse(manifest["traits_section_found"])

    def test_overrides_disable_decide_and_add_project_rules(self):
        overrides = {"disabled": ["QAC-REQ-001"], "decisions": {"QAC-HIG-002": "У нас иначе."},
                     "rules": [record("PRJ-SEC-001")]}
        overrides["rules"].append({"id": "PRJ-BAD-001", "applies_to": ["requirements"]})
        packs, manifest = build(self.kb, PROFILE, overrides, ["requirements"])
        ids = self.ids(packs)
        self.assertNotIn("PRJ-BAD-001", ids)
        self.assertTrue(any("PRJ-BAD-001 skipped" in w for w in manifest["warnings"]))
        self.assertNotIn("QAC-REQ-001", ids)
        self.assertIn("PRJ-SEC-001", ids)
        self.assertEqual(manifest["excluded"]["QAC-REQ-001"], "disabled by project")
        self.assertEqual(manifest["decisions_applied"], ["QAC-HIG-002"])
        line = rule_line(packs["platform"][0])
        self.assertIn("РЕШЕНИЕ ПРОЕКТА (приоритетнее): У нас иначе.", line)

    def test_overrides_with_pre_0_8_1_ids_still_apply(self):
        overrides = {"disabled": ["SRK-REQ-001"], "decisions": {"SRK-HIG-002": "У нас иначе."}}
        packs, manifest = build(self.kb, PROFILE, overrides, ["requirements"])
        self.assertNotIn("QAC-REQ-001", self.ids(packs))
        self.assertEqual(manifest["excluded"]["QAC-REQ-001"], "disabled by project")
        self.assertEqual(manifest["decisions_applied"], ["QAC-HIG-002"])

    def test_scope_filters_pass_through_and_bad_entries_warn(self):
        scope = [{"exclude": "cloud runtime mode", "reason": "not developed or tested", "source": "owner 2026-10-15"},
                 {"exclude": "role and permission tests"},
                 "no-dict"]
        _, manifest = build(self.kb, PROFILE, {"scope": scope}, ["requirements"])
        self.assertEqual(manifest["scope"], [scope[0]])
        self.assertEqual(sum("scope entry" in w for w in manifest["warnings"]), 2)

    def test_scope_absent_gives_empty_list(self):
        _, manifest = build(self.kb, PROFILE, {}, ["requirements"])
        self.assertEqual(manifest["scope"], [])

    def test_scope_null_or_not_a_list(self):
        _, manifest = build(self.kb, PROFILE, {"scope": None}, ["requirements"])
        self.assertEqual((manifest["scope"], manifest["warnings"]), ([], []))
        _, manifest = build(self.kb, PROFILE, {"scope": {"exclude": "cloud", "reason": "frozen"}}, ["requirements"])
        self.assertEqual(manifest["scope"], [])
        self.assertEqual(sum("scope skipped" in w for w in manifest["warnings"]), 1)


class AuthorityAndTopicsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        kb = Path(self.tmp.name)
        (kb / "catalog" / "rules").mkdir(parents=True)
        (kb / "qa-pilot" / "rules").mkdir(parents=True)
        (kb / "qa-pilot" / "drafts").mkdir(parents=True)
        (kb / "catalog" / "rules" / "requirements.json").write_text(json.dumps([
            {**record("QAC-REQ-001"), "authority": "author-opinion"},
            {**record("QAC-REQ-002"), "authority": "normative"},
            record("QAC-REQ-003"),
            {**record("QAC-REQ-004"), "authority": "vendor-guideline"},
        ]))
        (kb / "qa-pilot" / "rules" / "web-patterns.json").write_text(json.dumps([record("QAP-WEB-001")]))
        (kb / "qa-pilot" / "rules" / "security.json").write_text(json.dumps([record("QAP-SEC-001")]))
        (kb / "qa-pilot" / "rules" / "ai-systems.json").write_text(json.dumps([record("QAP-AI-001", ["needs-ai"])]))
        (kb / "qa-pilot" / "drafts" / "auth.json").write_text(json.dumps([record("QAP-AUTHN-001")]))
        self.kb = kb

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, profile=PROFILE):
        packs, manifest = build(self.kb, profile, {}, ["requirements"])
        return {r["id"]: (name, r) for name, rs in packs.items() for r in rs}, manifest

    def test_author_opinion_must_shown_as_should(self):
        rules, _ = self.build()
        self.assertEqual(effective_severity(rules["QAC-REQ-001"][1]), "should")
        self.assertEqual(effective_severity(rules["QAC-REQ-004"][1]), "should")
        self.assertIn("[should/heuristic/author-opinion]", rule_line(rules["QAC-REQ-001"][1]))
        self.assertIn("[must/heuristic/normative]", rule_line(rules["QAC-REQ-002"][1]))

    def test_conflict_rule_line_carries_the_correction(self):
        r = {**record("QAC-REQ-009"), "external_check": "conflict", "modern_note": "RFC 9110 §12.5.1 разрешает иное."}
        self.assertIn("РАСХОДИТСЯ СО СТАНДАРТОМ (приоритетнее проверки выше): RFC 9110", rule_line(r))
        self.assertNotIn("РАСХОДИТСЯ", rule_line(record("QAC-REQ-010")))

    def test_unclassified_must_stays_must(self):
        rules, _ = self.build()
        self.assertEqual(effective_severity(rules["QAC-REQ-003"][1]), "must")
        self.assertIn("[must/heuristic]", rule_line(rules["QAC-REQ-003"][1]))

    def test_web_patterns_not_in_packs_and_qap_topics_mapped(self):
        rules, _ = self.build()
        self.assertNotIn("QAP-WEB-001", rules)
        self.assertEqual(rules["QAP-SEC-001"][0], "api-data")

    def test_drafts_ignored(self):
        rules, _ = self.build()
        self.assertNotIn("QAP-AUTHN-001", rules)

    def test_needs_ai_trait(self):
        rules, manifest = self.build()
        self.assertNotIn("QAP-AI-001", rules)
        self.assertIn("needs-ai", manifest["excluded"]["QAP-AI-001"])
        rules, _ = self.build(PROFILE.replace("i18n: yes", "i18n: yes\nhas_ai_features: true"))
        self.assertIn("QAP-AI-001", rules)


class RuleLineTest(unittest.TestCase):
    def test_truncates_long_check(self):
        line = rule_line(record("QAC-REQ-009", how="а" * 400))
        self.assertTrue(line.endswith("…"))
        self.assertIn("[must/heuristic]", line)


if __name__ == "__main__":
    unittest.main()
