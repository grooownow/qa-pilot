---
name: project-audit
description: Whole-project QA audit — the big picture a per-task check cannot give. Assesses the maturity of the project's "test framework" (layers, CI gates, mocking, test data, selectors, flaky handling, linting), confirms the 3–7 critical user flows with the owner, runs spec-audit at depth "critical" on each chosen flow (entity cards of must-check web patterns: modify vs delete, double submit, silent mutations, UI-only permissions…), samples the test code around those flows, and writes one prioritized roadmap — framework fixes, Must tests per flow, questions, highlights — plus an English action list an agent can execute. Use when entering a project, for an interim audit, or after a large feature or many small changes ("аудит проекта", "общая картина по тестам", "что у нас с тестами в целом", "project QA audit", "health check of QA"). Costs ~250k tokens per flow; the owner picks the flows. Not for a single feature (use qa-pilot:spec-audit) or a single task (use qa-pilot:task-qa).
user-invocable: false
---

# Project Audit

A per-task check sees only the task. This skill re-reads the whole picture:
- Is the test framework good enough to rely on?
- Are the flows that matter most protected against the failures web apps typically have?

It **orchestrates**. The heavy lifting lives in `qa-pilot:onboard`, `qa-pilot:spec-audit` and `qa-pilot:test-code-audit`. Invoke them as steps; do not duplicate them.

Read first:
- `../../references/test-delta.md` (depth and buckets);
- `../../references/web-patterns.md`;
- `../../references/severity-calibration.md`.

**Never edit product code or specs.** Write as you go to `docs/qa/project-audit/<YYYY-MM-DD>.md`.

## Phase 0 — Cost and scope (ask once, in one message)

- **Fixed part:**
  - profile + maturity: about 30–60k tokens;
  - test-code sample, including the failure proof of up to 10 critical-flow tests: about 50–100k tokens plus test run time.
- **Variable part:** about 150–250k tokens per critical flow at depth `critical`.
- **Before starting**, state the estimate for the proposed flows and let the owner choose. Default: the top 3 flows. Full depth (`standard`) per flow only when asked.
- **Ask for owner scope filters** (areas not developed, on hold, tests not wanted), unless `docs/qa/rule-overrides.json` has `scope`. Filtered items are listed as suppressed, never silently dropped.

## Phase 1 — Profile and framework maturity

1. If `docs/qa/project-profile.md` is missing, or has no `## Framework maturity` / `## Test layers` / `## Error plumbing` sections, run `qa-pilot:onboard`, or just its missing parts. Also read `docs/qa/learnings.md` if it exists, per `../../references/learnings.md`.
2. Score each maturity area as present / partial / missing, with evidence. The areas are listed in onboard Phase 1. Back each gap with a rule from `../../knowledge/qa-pilot/rules/test-code.json` or `test-strategy.json` where one fits (cite the id).
3. **Framework blockers come first.** These are gaps that make tests untrustworthy or unrunnable:
   - no CI gate on the main layer;
   - a layer counted as coverage that CI never runs;
   - no network-mock seam;
   - shared mutable test data;
   - no selector convention.

   Each blocker is a **Must** item in the roadmap, because every test added before the fix inherits the problem.

## Phase 2 — Critical flows

- Use `## Critical flows` from the profile.
- If it is missing, propose 3–7 flows from routes, entities, docs and git activity: money, data loss, the core job of the product, auth. The owner confirms or edits them.
- Offer to save the confirmed list to the profile.
- For each flow, list its entities and its specs or tickets. If there are no specs, the behaviour is derived from the code; say so.

## Phase 3 — spec-audit per flow (depth `critical`)

- For each confirmed flow, in order of risk, invoke `qa-pilot:spec-audit` with:
  - scope = that flow;
  - `depth: critical`;
  - the same scope filters and critical flows.
- Run them **sequentially** and reuse the audit profile and the decisions digest between runs.
- Each run produces its own `-actions.md` / `-actions.json`. Keep them; the roadmap links to them.
- Stop and tell the owner if a run's Must list exceeds 10. The flow needs its own `standard` audit later.

## Phase 4 — Test-code sample

Run `qa-pilot:test-code-audit` limited to the test files that exercise the critical flows (from the spec-audit coverage evidence). Look for false greens, flakiness and wrong layers, and run its failure proof (test-code-audit Phase 3) on those tests: a `survived` probe is a P1 finding. Only P1/P2 findings go to the roadmap; the rest stays in the audit's report. Rows of `docs/qa/coverage-matrix.md` are coverage evidence: a row with Proof `none` on a critical flow is a finding (`../../references/coverage-matrix.md`). A `survived` probe and a Proof `none` row for the same test are one finding, not two.

## Phase 5 — Roadmap

`docs/qa/project-audit/<date>.md`:

```markdown
# QA project audit — <project> — <date>
> profile date · flows audited · depth · filters · cost

## Verdict             — 5 lines: can the team trust the tests today? What protects the critical flows, what doesn't?
## Framework maturity  — area table (present/partial/missing, evidence); blockers marked
## Roadmap
### 1. Framework fixes (Must)    — each: what · why (rule id) · effort S/M/L
### 2. Must tests per flow       — per flow: link to its -actions.md; top items inline
### 3. Should (≤8 per flow)      — links
### 4. Questions for the owner   — merged across flows, de-duplicated, each with options
### 5. Highlighted, not drilled  — one line each
### 6. Suppressed by your filters
## Test-code findings (P1/P2)
## Per-flow reports    — links to spec-audit reports
```

Also write `docs/qa/project-audit/<date>-actions.md` and `<date>-actions.json` (`../../references/actions-schema.md`), one English list in the spec-audit 6a format: framework fixes first, then the Must items of every flow, then Should.

## Phase 6 — Hand-off

- Show the owner the verdict and the first five roadmap items in plain words.
- Offer the next steps:
  - fix the framework blockers;
  - run `plan-tests` / `write-tests` on the Must list;
  - wire `qa-pilot:task-qa` into the team's feature workflow (`../../references/orchestrator-integration.md`), so that new tasks keep the picture intact.
- **Lessons.** If a trigger from `../../references/learnings.md` occurred in this run, propose the lessons to the owner as that file says; write them only after a yes. If invoked by another qa-pilot skill, hand the candidates back to it instead of asking.
- Re-run cadence: after a large feature, after a round of small changes, or quarterly. Each re-run compares with the previous roadmap and lists what was closed.
