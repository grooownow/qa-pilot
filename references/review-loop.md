# Review Loop

Parallel adversarial self-review of a diff. Every qa-pilot skill runs this
before presenting changed code as done. Provenance: generalized from the
author's private skill library (battle-tested on several production repos).

## Protocol

```
review (parallel agents) → triage & verify → fix → re-review changed areas → done
                                   ↑______________________|  (max 3 rounds)
```

### 1. Dispatch reviewers — all in ONE message, in parallel

Use the `qa-reviewer` agent. Each reviewer gets ONE narrow lens. Default lenses
for test-code changes (drop lenses irrelevant to the diff, don't add more than ~5):

- **Correctness:** do these tests actually verify the claimed behavior? Could
  they pass while the feature is broken (false-green)? Are assertions specific
  enough? Does a UI/e2e test confirm the action by what the user sees, not
  only by the response status (QAP-TC-032)?
- **Flakiness:** timing assumptions, race conditions, shared state, order
  dependence, unstable selectors — anything from `flakiness-catalog.md`.
- **Simplicity & slop:** over-engineering, needless abstraction, copy-paste,
  junk comments, dead code, deviation from the project's own idioms.
- **Conventions:** does the diff follow the project profile and the repo's own
  rules (imports, fixtures, tags, naming)?
- **Safety** (only when the diff touches auth, data cleanup, or destructive
  operations): can this leak credentials, delete real data, hit production?

Each reviewer brief must include: repo root, the exact diff (or file list),
the task context (one paragraph), a pointer to `docs/qa/project-profile.md`,
the required output format, and a hard cap (~300 words).

Required finding format:

```
[Critical|Important|Worth-fixing] <title>
file:line —
Issue: <what is wrong>
Why it matters: <consequence>
Fix: <concrete suggestion>
```

Reviewers with no findings must say "No findings" — not invent filler.

### 2. Triage & verify — in the main session

For EVERY finding, check it against the actual code before acting.
Reviewers see narrowly and report confidently; some findings are wrong.
Drop false positives explicitly (one line: finding → why it's wrong).

- **Critical / Important:** fix now.
- **Worth-fixing:** fix if cheap (< a few minutes); otherwise list in the
  output document as known debt.

### 3. Fix, then re-review

Apply fixes yourself or via `test-author`/`mechanical-editor` per
`model-routing.md`. Re-run the project gates. Then re-dispatch ONLY the lenses
that had Critical/Important findings, scoped to the changed areas.

### 4. Exit

- Clean round (no Critical/Important) → done. Record round count and any
  accepted Worth-fixing debt in the output document.
- Budget mode `economy` (`budget.md`) caps the loop at 1 round; `standard` and `thorough` keep 3. In economy, a
  round 1 that leaves Critical/Important findings open is handled like round 3 below: stop, summarize what
  remains, and hand the findings to the owner.
- Round 3 still not clean → stop, summarize what remains and why, and hand the
  decision to the user. Never loop past 3; a loop that doesn't converge means
  the approach is wrong, not that more rounds are needed.

## Anti-patterns

- Accepting every finding without verification (reviewer sycophancy in reverse).
- Re-reviewing the whole diff every round — round 2+ is scoped to changes.
- Fixing Worth-fixing items by rewriting half the file (scope creep).
- Running reviewers sequentially — dispatch is always one parallel batch.

<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
