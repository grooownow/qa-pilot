#!/usr/bin/env python3
"""Validate knowledge/<book>/rules/*.json and render them to Markdown.

Usage: python3 scripts/kb/render_rules.py <kb_dir> [--check]

Exits 1 with a list of errors if any record is invalid. With --check, only
validates. Otherwise writes rules/<topic>.md and the stats block between
<!-- stats --> markers in <kb_dir>/README.md. If <kb_dir>/raw/chunks.jsonl
exists, source.chunk_id and source.printed_pages are checked against it.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

KINDS = ("rule", "recommendation", "tip", "checklist")
SEVERITIES = ("must", "should", "nice")
MODES = ("deterministic", "heuristic", "manual")
TARGETS = ("requirements", "test-plan", "test-code", "live-product", "test-cases")
VERIFICATION = ("ok", "fixed", "doubtful")
AUTHORITY = ("normative", "industry-practice", "vendor-guideline", "author-opinion", "unclassified")
EXTERNAL_CHECK = ("aligned", "conflict", "unchecked")
PATTERN_TIERS = ("must-check", "highlight")
PATTERN_LEVELS = ("unit", "component", "backend-integration", "e2e")
ID_RE = re.compile(r"^(SRK|QAP|PRJ)-[A-Z0-9]+(-[A-Z0-9]+)*-\d{3}$")
REQUIRED_TEXT = ("id", "kind", "severity", "title", "statement")
OPTIONAL_TEXT = ("rationale", "modern_note", "decision")
ALLOWED = set(REQUIRED_TEXT + OPTIONAL_TEXT + ("applies_to", "check", "source", "tags", "verification",
                                               "authority", "external_check", "pattern"))

KIND_RU = {"rule": "Жёсткие правила", "recommendation": "Рекомендации",
           "tip": "Практические советы", "checklist": "Чек-лист"}
MODE_RU = {"deterministic": "детерминированно", "heuristic": "эвристика агента", "manual": "вручную"}


def load_chunks(kb_dir):
    path = kb_dir / "raw" / "chunks.jsonl"
    if not path.exists():
        return None
    chunks = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        chunks[c["id"]] = c
    return chunks


def validate_record(r, chunks):
    """Return a list of error strings for one record (empty if valid)."""
    errors = []
    rid = r.get("id", "<no id>") if isinstance(r, dict) else "<not an object>"
    if not isinstance(r, dict):
        return [f"{rid}: record is not an object"]
    for key in REQUIRED_TEXT:
        if not isinstance(r.get(key), str) or not r[key].strip():
            errors.append(f"{rid}: missing or empty '{key}'")
    for key in OPTIONAL_TEXT:
        if key in r and not isinstance(r[key], str):
            errors.append(f"{rid}: '{key}' must be a string")
    extra = set(r) - ALLOWED
    if extra:
        errors.append(f"{rid}: unknown fields {sorted(extra)}")
    if isinstance(r.get("id"), str) and not ID_RE.match(r["id"]):
        errors.append(f"{rid}: id must look like SRK-TOPIC-001")
    if r.get("kind") not in KINDS:
        errors.append(f"{rid}: kind must be one of {KINDS}")
    if r.get("severity") not in SEVERITIES:
        errors.append(f"{rid}: severity must be one of {SEVERITIES}")
    applies = r.get("applies_to")
    if not isinstance(applies, list) or not applies or any(a not in TARGETS for a in applies):
        errors.append(f"{rid}: applies_to must be a non-empty subset of {TARGETS}")
    check = r.get("check")
    if not isinstance(check, dict) or check.get("mode") not in MODES \
            or not isinstance(check.get("how"), str) or not check["how"].strip():
        errors.append(f"{rid}: check must be {{mode: {MODES}, how: non-empty string}}")
    if "tags" in r and (not isinstance(r["tags"], list) or not all(isinstance(t, str) for t in r["tags"])):
        errors.append(f"{rid}: tags must be a list of strings")
    if "verification" in r and r["verification"] not in VERIFICATION:
        errors.append(f"{rid}: verification must be one of {VERIFICATION}")
    if "authority" in r and r["authority"] not in AUTHORITY:
        errors.append(f"{rid}: authority must be one of {AUTHORITY}")
    if "external_check" in r and r["external_check"] not in EXTERNAL_CHECK:
        errors.append(f"{rid}: external_check must be one of {EXTERNAL_CHECK}")
    if "pattern" in r:
        errors.extend(validate_pattern(rid, r["pattern"]))
    source = r.get("source")
    from_book = str(r.get("id", "")).startswith("SRK-")
    if not from_book:
        if not isinstance(source, dict) or not isinstance(source.get("origin"), str) or not source["origin"].strip():
            errors.append(f"{rid}: source.origin is required for non-book rules")
    elif not isinstance(source, dict) or not isinstance(source.get("chunk_id"), str):
        errors.append(f"{rid}: source.chunk_id is required")
    else:
        pages = source.get("printed_pages", [])
        if not isinstance(pages, list) or not all(isinstance(p, int) for p in pages) or len(pages) > 2:
            errors.append(f"{rid}: source.printed_pages must be [from] or [from, to]")
        elif chunks is not None:
            chunk = chunks.get(source["chunk_id"])
            if chunk is None:
                errors.append(f"{rid}: unknown chunk_id '{source['chunk_id']}'")
            elif pages and chunk["printed_pages"]:
                lo, hi = chunk["printed_pages"]
                if any(p < lo - 1 or p > hi + 1 for p in pages):
                    errors.append(f"{rid}: printed_pages {pages} outside chunk {source['chunk_id']} [{lo}, {hi}]")
    return errors


def validate_pattern(rid, pattern):
    """The `pattern` object of a web-pattern record (QAP-WEB-…)."""
    if not str(rid).startswith("QAP-WEB-"):
        return [f"{rid}: pattern is only allowed on QAP-WEB-… records"]
    if not isinstance(pattern, dict):
        return [f"{rid}: pattern must be an object"]
    errors = []
    if pattern.get("tier") not in PATTERN_TIERS:
        errors.append(f"{rid}: pattern.tier must be one of {PATTERN_TIERS}")
    if pattern.get("level") not in PATTERN_LEVELS:
        errors.append(f"{rid}: pattern.level must be one of {PATTERN_LEVELS}")
    for key in ("triggers", "book_refs"):
        value = pattern.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(f"{rid}: pattern.{key} must be a list of strings")
    if not pattern.get("triggers"):
        errors.append(f"{rid}: pattern.triggers must not be empty")
    return errors


def validate_all(rule_sets, chunks):
    """rule_sets: {topic: [records]}. Returns a list of errors."""
    errors, seen = [], {}
    for topic, records in rule_sets.items():
        if not isinstance(records, list):
            errors.append(f"{topic}.json: top level must be an array")
            continue
        for r in records:
            errors.extend(f"{topic}.json: {e}" for e in validate_record(r, chunks))
            rid = r.get("id") if isinstance(r, dict) else None
            if rid in seen:
                errors.append(f"{topic}.json: duplicate id {rid} (also in {seen[rid]}.json)")
            elif rid:
                seen[rid] = topic
    return errors


REF_RE = re.compile(r"\b(?:SRK|QAP|PRJ)-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")
REF_FIELDS = ("statement", "rationale", "modern_note", "decision", "title")


def dangling_refs(rule_sets, known_ids):
    """Rule ids mentioned in text fields or pattern.book_refs that no catalog defines."""
    errors = []
    for records in rule_sets.values():
        for r in records:
            text = " ".join(str(r.get(k, "")) for k in REF_FIELDS) + " " + str(r.get("check", {}).get("how", ""))
            refs = set(REF_RE.findall(text)) | set((r.get("pattern") or {}).get("book_refs", []))
            errors.extend(f"{r['id']}: refers to unknown {ref}" for ref in sorted(refs - known_ids - {r["id"]}))
    return errors


def known_catalog_ids(kb_dir):
    """Every id in the sibling catalogs (knowledge/*/rules/*.json), so cross-catalog refs resolve."""
    ids = set()
    for path in kb_dir.resolve().parent.glob("*/rules/*.json"):
        try:
            ids.update(r.get("id") for r in json.loads(path.read_text(encoding="utf-8")) if isinstance(r, dict))
        except json.JSONDecodeError:
            pass
    return ids


def render_topic(topic, records):
    from_book = all(r["id"].startswith("SRK-") for r in records)
    provenance = ("Формулировки — пересказ книги Р. Суркова «Качество решает всё»; страницы — печатные номера книги."
                  if from_book else "Собственные правила qa-pilot: источник каждого правила указан в поле «источник».")
    out = [f"# {topic}", "",
           f"Сгенерировано из `{topic}.json` скриптом `scripts/kb/render_rules.py` — правьте JSON, не этот файл.",
           provenance, ""]
    for kind in KINDS:
        group = [r for r in records if r["kind"] == kind]
        if not group:
            continue
        out += [f"## {KIND_RU[kind]} ({len(group)})", ""]
        for r in group:
            src = r["source"]
            if "chunk_id" in src:
                where = f"`{src['chunk_id']}`, с. " + ("–".join(map(str, src.get("printed_pages", []))) or "?")
            else:
                where = src["origin"]
            flag = " ⚠️ сомнительно" if r.get("verification") == "doubtful" else ""
            meta = (f"`{r['severity']}` · проверка: {MODE_RU[r['check']['mode']]} · "
                    f"для: {', '.join(r['applies_to'])} · источник: {where}")
            if r.get("authority", "unclassified") != "unclassified":
                meta += f" · авторитет: {r['authority']}"
            if r.get("external_check"):
                meta += f" · сверка со стандартом: {r['external_check']}"
            out += [f"### {r['id']} · {r['title']}{flag}", "", meta, "", r["statement"], ""]
            if r.get("rationale"):
                out += [f"**Почему:** {r['rationale']}", ""]
            out += [f"**Как проверить:** {r['check']['how']}", ""]
            if r.get("modern_note"):
                out += [f"**Сегодня:** {r['modern_note']}", ""]
            if r.get("decision"):
                out += [f"**Решение команды (приоритетнее книги):** {r['decision']}", ""]
    return "\n".join(out).rstrip() + "\n"


def stats_block(rule_sets):
    records = [r for rs in rule_sets.values() for r in rs]
    lines = [f"Всего записей: **{len(records)}**", "",
             "| Тема | Всего | rule | recommendation | tip | checklist | deterministic |",
             "|---|---|---|---|---|---|---|"]
    for topic, rs in sorted(rule_sets.items()):
        k = Counter(r["kind"] for r in rs)
        det = sum(1 for r in rs if r["check"]["mode"] == "deterministic")
        lines.append(f"| [{topic}](rules/{topic}.md) | {len(rs)} | {k['rule']} | {k['recommendation']} "
                     f"| {k['tip']} | {k['checklist']} | {det} |")
    sev = Counter(r["severity"] for r in records)
    mode = Counter(r["check"]["mode"] for r in records)
    lines += ["", "По severity: " + ", ".join(f"{s} — {sev[s]}" for s in SEVERITIES),
              "", "По способу проверки: " + ", ".join(f"{m} — {mode[m]}" for m in MODES)]
    return "\n".join(lines)


def write_stats(readme, block):
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    new = re.sub(r"<!-- stats -->.*?<!-- /stats -->", f"<!-- stats -->\n{block}\n<!-- /stats -->",
                 text, flags=re.S)
    readme.write_text(new, encoding="utf-8")


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    kb_dir = Path(args[0])
    rule_sets = {}
    for path in sorted((kb_dir / "rules").glob("*.json")):
        try:
            rule_sets[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{path.name}: invalid JSON: {e}", file=sys.stderr)
            return 1
    errors = validate_all(rule_sets, load_chunks(kb_dir))
    if not errors:
        errors = dangling_refs(rule_sets, known_catalog_ids(kb_dir))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print(f"\n{len(errors)} error(s)", file=sys.stderr)
        return 1
    total = sum(len(rs) for rs in rule_sets.values())
    if "--check" not in argv:
        for topic, records in rule_sets.items():
            (kb_dir / "rules" / f"{topic}.md").write_text(render_topic(topic, records), encoding="utf-8")
        write_stats(kb_dir / "README.md", stats_block(rule_sets))
    print(f"OK: {total} records in {len(rule_sets)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
