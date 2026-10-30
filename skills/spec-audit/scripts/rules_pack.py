#!/usr/bin/env python3
"""Build compact rule packs for a spec audit, filtered by product traits.

Usage:
  python3 rules_pack.py --kb <plugin>/knowledge --profile docs/qa/project-profile.md \
      [--overrides docs/qa/rule-overrides.json] [--targets requirements,test-plan] --out <dir>

Reads every rules/*.json under <kb>/catalog and <kb>/qa-pilot (never drafts/), plus project
rules (PRJ-…) and owner scope filters from the overrides file. Keeps rules whose applies_to meets the
targets and whose needs-* tags are all satisfied by the product traits. A `must` rule
classified as author-opinion or vendor-guideline is shown as `should`. Web patterns and
invariants are not packed: agents get them from references/web-patterns.md.
Writes <out>/packs/<pack>.md (one line per rule) and <out>/manifest.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_TRAITS = {"platform": ["web"], "api_style": [], "has_ui": True, "has_backend": True,
                  "has_payments": False, "has_auth": False, "has_user_uploads": False, "i18n": False,
                  "rtl": False, "regulated": [], "has_ai_features": False}

MOBILE_PLATFORMS = {"ios", "android", "pwa", "mobile-web"}
WEB_PLATFORMS = {"web", "mobile-web", "pwa"}
INSTALLED_PLATFORMS = {"ios", "android", "desktop", "game", "cli", "pwa"}

# needs-* tag -> predicate over traits
NEEDS = {
    "needs-ui": lambda t: t["has_ui"],
    "needs-backend": lambda t: t["has_backend"],
    "needs-app": lambda t: t["has_ui"] or t["has_backend"],
    "needs-web": lambda t: t["has_ui"] and bool(WEB_PLATFORMS & set(t["platform"])),
    "needs-installed": lambda t: bool(INSTALLED_PLATFORMS & set(t["platform"])),
    "needs-ios": lambda t: "ios" in t["platform"],
    "needs-android": lambda t: "android" in t["platform"],
    "needs-native-mobile": lambda t: bool({"ios", "android"} & set(t["platform"])),
    "needs-mobile": lambda t: bool(MOBILE_PLATFORMS & set(t["platform"])),
    "needs-desktop": lambda t: "desktop" in t["platform"],
    "needs-game": lambda t: "game" in t["platform"],
    "needs-payments": lambda t: t["has_payments"],
    "needs-rest": lambda t: "rest" in t["api_style"],
    "needs-graphql": lambda t: "graphql" in t["api_style"],
    "needs-soap": lambda t: "soap" in t["api_style"],
    "needs-auth": lambda t: t["has_auth"],
    "needs-uploads": lambda t: t["has_user_uploads"],
    "needs-i18n": lambda t: t["i18n"],
    "needs-rtl": lambda t: t["rtl"],
    "needs-ai": lambda t: t["has_ai_features"],
}

PACKS = {
    "core": ["requirements", "test-design", "test-artifacts", "test-strategy", "principles", "ai-in-qa"],
    "forms-ui": ["forms", "gui", "usability", "ux-laws-dark-patterns"],
    "api-data": ["api", "databases", "performance"],
    "a11y-l10n": ["accessibility", "localization"],
    "platform": ["mobile", "mobile-hig", "mobile-material", "games", "install-config", "process"],
}
# qa-pilot rule files (by stem) -> pack; unknown stems go to core
QAP_PACKS = {"pilot": "core", "security": "api-data", "auth": "api-data", "api-http": "api-data",
             "test-strategy": "core", "test-code": "core", "ai-systems": "core"}
SKIP_TOPICS = {"web-patterns", "web-invariants"}
CAPPED_AUTHORITY = {"author-opinion", "vendor-guideline"}
HOW_LIMIT = 260


def parse_scalar(value):
    value = value.strip().split(" #", 1)[0].strip()
    if value.startswith("[") and value.endswith("]"):
        return [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
    value = value.strip("'\"")
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    return value


def parse_traits(profile_text):
    """Traits from the '## Product traits' section. Supports `key: value`,
    inline lists `[a, b]`, comma lists `a, b`, block lists (`key:` then `- a`)
    and true/false/yes/no (quoted or not). Missing keys fall back to
    DEFAULT_TRAITS. Returns (traits, section_found, warnings)."""
    traits = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_TRAITS.items()}
    warnings = []
    m = re.search(r"^##\s+Product traits\s*$(.*?)(?=^##\s|\Z)", profile_text or "", re.M | re.S)
    if not m:
        return traits, False, warnings
    block_key = None
    for line in m.group(1).splitlines():
        item = re.match(r"^\s*-\s+(.+)$", line)
        if item and block_key:
            traits[block_key].append(str(parse_scalar(item.group(1))))
            continue
        kv = re.match(r"^\s*([a-z0-9_]+)\s*:\s*(.*)$", line)
        if not kv:
            continue
        key, raw = kv.group(1), kv.group(2).split(" #", 1)[0].strip()
        block_key = None
        if key not in traits:
            warnings.append(f"unknown trait '{key}' ignored")
            continue
        expected = DEFAULT_TRAITS[key]
        if isinstance(expected, list):
            if not raw:
                traits[key] = []
                block_key = key
                continue
            value = parse_scalar(raw)
            if not isinstance(value, list):
                value = [v.strip() for v in str(value).split(",") if v.strip() and v.strip() != "none"]
            traits[key] = value
        else:
            value = parse_scalar(raw)
            if not isinstance(value, bool):
                warnings.append(f"trait '{key}' expects true/false, got '{raw}' — kept default {expected}")
                continue
            traits[key] = value
    return traits, True, warnings


def commercial_use(profile_text):
    """True when the profile's '## Licence' section says `use: commercial`. The book-derived
    catalog is not covered by commercial licences (COMMERCIAL.md), so it is skipped then."""
    m = re.search(r"^##\s+Licence\s*$(.*?)(?=^##\s|\Z)", profile_text or "", re.M | re.S)
    return bool(m and re.search(r"^\s*use\s*:\s*[\"']?commercial\b", m.group(1), re.M))


def load_rules(kb, overrides, catalog=True):
    rules = []
    for source in (("catalog", "qa-pilot") if catalog else ("qa-pilot",)):
        for path in sorted((kb / source / "rules").glob("*.json")):
            for r in json.loads(path.read_text(encoding="utf-8")):
                rules.append((path.stem if source == "catalog" else f"qa-pilot:{path.stem}", r))
    rules += [("project", r) for r in overrides.get("rules", [])]
    return rules


def malformed(r):
    """Missing fields a pack line needs (project rules are not validated elsewhere)."""
    missing = [k for k in ("id", "title", "severity", "applies_to") if not r.get(k)]
    if not isinstance(r.get("check"), dict) or not r["check"].get("how") or not r["check"].get("mode"):
        missing.append("check.mode/how")
    return missing


def pack_of(topic):
    if topic.startswith("qa-pilot:"):
        return QAP_PACKS.get(topic.split(":", 1)[1], "core")
    for name, topics in PACKS.items():
        if topic in topics:
            return name
    return "core"


def effective_severity(r):
    """`must` from a classified author opinion or vendor guideline counts as `should`."""
    if r["severity"] == "must" and r.get("authority") in CAPPED_AUTHORITY:
        return "should"
    return r["severity"]


def rule_line(r):
    how = re.sub(r"\s+", " ", r["check"]["how"])
    if len(how) > HOW_LIMIT:
        how = how[:HOW_LIMIT - 1] + "…"
    tag = f"{effective_severity(r)}/{r['check']['mode']}"
    if r.get("authority", "unclassified") != "unclassified":
        tag += f"/{r['authority']}"
    line = f"- {r['id']} [{tag}] {r['title']} — проверка: {how}"
    if r.get("decision"):
        line += f" ⚖️ РЕШЕНИЕ ПРОЕКТА (приоритетнее): {r['decision']}"
    if r.get("external_check") == "conflict" and r.get("modern_note"):
        note = re.sub(r"\s+", " ", r["modern_note"])
        if len(note) > HOW_LIMIT:
            note = note[:HOW_LIMIT - 1] + "…"
        line += f" ⚠️ РАСХОДИТСЯ СО СТАНДАРТОМ (приоритетнее проверки выше): {note}"
    return line


def scope_entries(overrides, warnings):
    """Owner scope filters (areas not developed, on hold, or not to be tested), passed to the agents."""
    kept, raw = [], overrides.get("scope") or []
    if not isinstance(raw, list):
        warnings.append("scope skipped: must be a list of {exclude, reason, source} objects")
        raw = []
    for entry in raw:
        if isinstance(entry, dict) and entry.get("exclude") and entry.get("reason"):
            kept.append(entry)
        else:
            warnings.append(f"scope entry skipped: needs 'exclude' and 'reason': {json.dumps(entry, ensure_ascii=False)}")
    return kept


# Catalog ids were renamed in 0.8.1 (same numbers); override files written before still use the old prefix.
OLD_CATALOG_PREFIX = "SRK-"


def current_id(rule_id):
    return "QAC-" + rule_id[len(OLD_CATALOG_PREFIX):] if rule_id.startswith(OLD_CATALOG_PREFIX) else rule_id


def build(kb, profile_text, overrides, targets, catalog=True):
    traits, has_section, warnings = parse_traits(profile_text)
    if catalog and commercial_use(profile_text):
        catalog = False
        warnings.append("book catalog skipped: profile says use: commercial (not covered by commercial licences)")
    scope = scope_entries(overrides, warnings)
    disabled = {current_id(i) for i in overrides.get("disabled", [])}
    decisions = {current_id(k): v for k, v in overrides.get("decisions", {}).items()}
    packs = {name: [] for name in PACKS}
    excluded, unknown_tags, applied = {}, set(), []
    for topic, r in load_rules(kb, overrides, catalog):
        if topic.split(":", 1)[-1] in SKIP_TOPICS:
            continue
        missing = malformed(r)
        if missing:
            warnings.append(f"rule {r.get('id', '<no id>')} skipped: missing {', '.join(missing)}")
            continue
        if not set(r.get("applies_to", [])) & set(targets):
            continue
        if r["id"] in disabled:
            excluded[r["id"]] = "disabled by project"
            continue
        needs = [t for t in r.get("tags", []) if t.startswith("needs-")]
        unknown_tags.update(t for t in needs if t not in NEEDS)
        missing = [t for t in needs if t in NEEDS and not NEEDS[t](traits)]
        if missing:
            excluded[r["id"]] = "trait not present: " + ", ".join(missing)
            continue
        if r["id"] in decisions:
            r = {**r, "decision": decisions[r["id"]]}
            applied.append(r["id"])
        packs[pack_of(topic)].append(r)
    manifest = {
        "targets": targets, "traits": traits, "traits_section_found": has_section,
        "catalog": catalog,
        "counts": {name: len(rs) for name, rs in packs.items()},
        "excluded": dict(sorted(excluded.items())),
        "decisions_applied": sorted(applied),
        "unknown_needs_tags": sorted(unknown_tags),
        "scope": scope,
        "warnings": warnings,
    }
    return packs, manifest


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kb", required=True, type=Path)
    ap.add_argument("--profile", type=Path)
    ap.add_argument("--overrides", type=Path)
    ap.add_argument("--targets", default="requirements,test-plan")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--no-catalog", action="store_true",
                    help="skip the book-derived catalog (also automatic with `use: commercial` in the profile)")
    args = ap.parse_args(argv[1:])
    profile_text = args.profile.read_text(encoding="utf-8") if args.profile and args.profile.exists() else ""
    overrides = (json.loads(args.overrides.read_text(encoding="utf-8"))
                 if args.overrides and args.overrides.exists() else {})
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    packs, manifest = build(args.kb, profile_text, overrides, targets, catalog=not args.no_catalog)
    (args.out / "packs").mkdir(parents=True, exist_ok=True)
    for name, rules in packs.items():
        lines = [f"# Pack: {name} ({len(rules)} rules)", ""] + [rule_line(r) for r in rules]
        (args.out / "packs" / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                                            encoding="utf-8")
    print(json.dumps({"counts": manifest["counts"], "catalog": manifest["catalog"],
                      "excluded": len(manifest["excluded"]),
                      "traits_section_found": manifest["traits_section_found"],
                      "warnings": manifest["warnings"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
