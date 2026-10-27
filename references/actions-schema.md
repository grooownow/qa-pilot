# `-actions.json`: machine-readable action list

Every spec-audit run, and every project-audit run, writes `<date>-<slug>-actions.json` next to `-actions.md`. The Markdown file is for people. This file feeds scoring, run-to-run comparison and the owner's verdicts.

Check it with `python3 <plugin>/skills/spec-audit/scripts/score.py validate <file>`, where `<plugin>` is the qa-pilot plugin root.

```json
{
  "feature": "workflows + templates",
  "depth": "critical | standard | thorough",
  "actions": [
    {
      "id": "A1",
      "bucket": "must | should | highlight | question",
      "kind": "bug | test | question",
      "title": "Rename to a taken name fails silently",
      "expected": "A visible conflict error; the dialog stays open",
      "source": "QAP-WINV-002 | spec.md:42 | decision | src/x.ts:10 (convention)",
      "level": "unit | component | backend-integration | e2e",
      "target": "src/features/workflow/useUpdateWorkflowForm.ts:31",
      "pattern": "QAP-WEB-006",
      "owner_verdict": "accepted | fixed | rejected"
    }
  ],
  "suppressed": [
    {"title": "Delete during an active run", "pattern": "QAP-WEB-001", "filter": "owner 2026-10-15: no delete-during-run tests"}
  ],
  "cells": [
    {"entity": "workflow", "pattern": "QAP-WEB-001", "verdict": "OK | BUG | GAP | N/A | DECISION | SUPPRESSED", "evidence": "file:line or search"}
  ]
}
```

## Fields

- **Required on every action:** `id`, `bucket`, `kind`, `title`.
- **`kind: question` always takes `bucket: "question"`.** Questions are counted on their own and never count toward the Must/Should caps.
- **Required on `test` and `bug` actions:** `expected`, `source`, `level`, `target`. On a `question`, these are optional.
- **`pattern`:** optional. Fill it in when the action came from an entity-card cell.
- **`owner_verdict`:** filled in later by the owner, or by `task-qa`/`cover` when a test lands. It is the cheap, permanent quality signal: acceptance rate and tokens per accepted item.
- **`suppressed`:** items removed by owner scope filters. They are **not** actions. They do not count toward bucket caps, and they are not scored as action-list items.
- **`cells`:** one entry per (entity, must-check pattern). An empty `verdict` means the card is incomplete, and the Phase 5 gate does not pass it. An `N/A` cell needs `evidence`. A `SUPPRESSED` cell names the filter in `evidence`, and its risk also appears in `suppressed`.
- **Checked by `validate` as errors:** a `test` or `bug` action missing `expected`, `source`, `level` or `target`; an `N/A` cell without `evidence`; a bucket that does not fit the kind. A `bug` outside Must is a warning.

## Buckets

| Bucket | Contents | Cap |
|---|---|---|
| **Must** | P1, any BUG, P2 on a confirmed critical flow | none; above 10 the run warns: narrow the scope |
| **Should** | other P2 | ≤8 |
| **Highlight** | P3, and P2s that did not fit the Should cap; one line each | none; no tests are prescribed |
| **Question** | every product question | none; separate from the caps |

## Scoring an eval

1. The audited run never sees the rubric.
2. After the run, a judge (a subagent) reads the rubric JSON, the actions and the findings. It writes `mapping.json`: `{"G1": {"verdict": "pass|partial|fail", "actions": ["A3"], "note": "..."}}`.
3. Run `score.py score --actions … --mapping … --rubric …` to get the pass/partial/fail counts, the bucket counts and the share of product questions.
4. Run `score.py agreement run1.json run2.json` to get the share of (entity, pattern) cells with the same verdict. A cell present in only one run counts as a disagreement.

<!-- qa-pilot · © 2026 Ludvik4 · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
