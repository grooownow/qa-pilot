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
ID_RE = re.compile(r"^SRK-[A-Z0-9]+(-[A-Z0-9]+)*-\d{3}$")
REQUIRED_TEXT = ("id", "kind", "severity", "title", "statement")
OPTIONAL_TEXT = ("rationale", "modern_note", "decision")
ALLOWED = set(REQUIRED_TEXT + OPTIONAL_TEXT + ("applies_to", "check", "source", "tags", "verification"))

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
    source = r.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("chunk_id"), str):
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


def render_topic(topic, records):
    out = [f"# {topic}", "",
           f"Сгенерировано из `{topic}.json` скриптом `scripts/kb/render_rules.py` — правьте JSON, не этот файл.",
           "Формулировки — пересказ книги Р. Суркова «Качество решает всё»; страницы — печатные номера книги.", ""]
    for kind in KINDS:
        group = [r for r in records if r["kind"] == kind]
        if not group:
            continue
        out += [f"## {KIND_RU[kind]} ({len(group)})", ""]
        for r in group:
            src = r["source"]
            pages = "–".join(map(str, src.get("printed_pages", []))) or "?"
            flag = " ⚠️ сомнительно" if r.get("verification") == "doubtful" else ""
            out += [f"### {r['id']} · {r['title']}{flag}", "",
                    f"`{r['severity']}` · проверка: {MODE_RU[r['check']['mode']]} · "
                    f"для: {', '.join(r['applies_to'])} · источник: `{src['chunk_id']}`, с. {pages}", "",
                    r["statement"], ""]
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
