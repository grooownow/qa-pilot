#!/usr/bin/env python3
"""Validate and score a spec-audit `-actions.json` (schema: references/actions-schema.md).

Usage:
  python3 score.py validate <actions.json>
  python3 score.py score --actions <actions.json> --mapping <mapping.json> --rubric <rubric.json>
  python3 score.py agreement <run1-actions.json> <run2-actions.json>

`mapping.json` is written by a judge after the run ({check_id: {verdict: pass|partial|fail, ...}}),
so the audited run never sees the rubric. Prints JSON; `validate` exits 1 on schema errors.
"""
import json
import sys
from collections import Counter
from pathlib import Path

BUCKETS = ("must", "should", "highlight", "question")
KINDS = ("bug", "test", "question")
VERDICTS = ("OK", "BUG", "GAP", "N/A", "DECISION")
REQUIRED = ("id", "bucket", "kind", "title")
SHOULD_CAP, MUST_WARN = 8, 10


def validate_actions(doc):
    """Return (errors, warnings). Errors break the schema; warnings break the budget or leave cells empty."""
    errors, warnings = [], []
    actions = doc.get("actions") if isinstance(doc, dict) else None
    if not isinstance(actions, list):
        return ["actions must be a list"], warnings
    for a in actions:
        aid = a.get("id", "<no id>") if isinstance(a, dict) else "<not an object>"
        if not isinstance(a, dict):
            errors.append(f"{aid}: action is not an object")
            continue
        for key in REQUIRED:
            if not a.get(key):
                errors.append(f"{aid}: {key} is missing")
        if a.get("bucket") and a["bucket"] not in BUCKETS:
            errors.append(f"{aid}: bucket must be one of {BUCKETS}")
        if a.get("kind") and a["kind"] not in KINDS:
            errors.append(f"{aid}: kind must be one of {KINDS}")
        if (a.get("kind") == "question") != (a.get("bucket") == "question") and a.get("kind") and a.get("bucket"):
            errors.append(f"{aid}: a question takes bucket 'question', and only questions do")
    for key in ("suppressed", "cells"):
        if not isinstance(doc.get(key, []), list):
            errors.append(f"{key} must be a list")
    for c in doc.get("cells", []) if isinstance(doc.get("cells", []), list) else []:
        where = f"{c.get('entity')} × {c.get('pattern')}" if isinstance(c, dict) else "<not an object>"
        verdict = c.get("verdict") if isinstance(c, dict) else None
        if not verdict:
            warnings.append(f"empty cell: {where}")
        elif verdict not in VERDICTS:
            errors.append(f"{where}: verdict must be one of {VERDICTS}")
    buckets = Counter(a.get("bucket") for a in actions if isinstance(a, dict))
    if buckets["should"] > SHOULD_CAP:
        warnings.append(f"should>{SHOULD_CAP}")
    if buckets["must"] > MUST_WARN:
        warnings.append(f"must>{MUST_WARN}")
    return errors, warnings


def score(doc, mapping, rubric):
    """Aggregate judge verdicts per rubric check plus bucket counts and the product-question share."""
    counts = Counter()
    warnings = []
    for check in rubric:
        verdict = (mapping.get(check["id"]) or {}).get("verdict")
        if verdict not in ("pass", "partial", "fail"):
            warnings.append(f"{check['id']}: not mapped, counted as fail")
            verdict = "fail"
        counts[verdict] += 1
    actions = [a for a in doc.get("actions", []) if isinstance(a, dict)]
    buckets = Counter(a.get("bucket") for a in actions)
    questions = sum(1 for a in actions if a.get("kind") == "question")
    _, budget_warnings = validate_actions(doc)
    return {"pass": counts["pass"], "partial": counts["partial"], "fail": counts["fail"],
            "buckets": {b: buckets[b] for b in BUCKETS},
            "questions": questions,
            "question_share": round(questions / len(actions), 3) if actions else 0.0,
            "warnings": warnings + budget_warnings}


def agreement(doc_a, doc_b):
    """Cell-verdict agreement over the union of (entity, pattern); a cell missing in one run disagrees."""
    def cells(doc):
        return {(c.get("entity"), c.get("pattern")): c.get("verdict") for c in doc.get("cells", [])
                if isinstance(c, dict)}
    a, b = cells(doc_a), cells(doc_b)
    union = set(a) | set(b)
    agree = sum(1 for key in union if key in a and key in b and a[key] == b[key])
    return {"cells_union": len(union), "agree": agree,
            "ratio": round(agree / len(union), 3) if union else 0.0}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv):
    if len(argv) < 3 or argv[1] not in ("validate", "score", "agreement"):
        print(__doc__, file=sys.stderr)
        return 2
    command, args = argv[1], argv[2:]
    if command == "validate":
        errors, warnings = validate_actions(load(args[0]))
        print(json.dumps({"errors": errors, "warnings": warnings}, ensure_ascii=False, indent=1))
        return 1 if errors else 0
    if command == "agreement":
        print(json.dumps(agreement(load(args[0]), load(args[1]))))
        return 0
    opts = dict(zip(args[::2], args[1::2]))
    missing = [k for k in ("--actions", "--mapping", "--rubric") if k not in opts]
    if missing:
        print(f"missing {', '.join(missing)}", file=sys.stderr)
        return 2
    result = score(load(opts["--actions"]), load(opts["--mapping"]), load(opts["--rubric"]))
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
