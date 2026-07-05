---
name: audit
description: Deep audit of an existing test codebase - finds anti-patterns, copy-paste, flakiness sources, over-complexity, false-green and dead tests; produces a severity-ranked report and an ordered refactoring plan, then can execute the plan step by step. Use when the user asks to audit/review/health-check the test suite, complains about flaky or slow tests, or wants a refactoring plan for tests. Requires docs/qa/project-profile.md (run qa-pilot:onboard first).
---

# Audit

Assess the test codebase, report what's wrong with evidence, plan the fix,
optionally execute it. Three outputs, all persisted as you go (a dead session
must lose nothing):

- `docs/qa/audit-report.md` — findings
- `docs/qa/refactoring-plan.md` — ordered fix plan
- execution happens step-by-step from the plan, each step reviewed

Create a todo per phase. Read `../../references/quality-rules.md` and
`../../references/model-routing.md` first. Prerequisite:
`docs/qa/project-profile.md` — if missing, stop and run `qa-pilot:onboard`.

## Phase 1 — Scope & baseline

- From the profile: test locations, commands, team priorities.
- Agree scope with the user if ambiguous (whole suite vs one package; e2e only
  vs everything). State the scope in the report header.
- Baseline run: execute the suite once (or the target subset). Record pass/fail/
  skip counts and duration in the report. A suite that doesn't run is finding #1.

## Phase 2 — Parallel audit lenses

Dispatch qa-reviewer agents in ONE parallel batch, one lens each (see
`../../references/review-loop.md` for dispatch mechanics — same protocol,
pointed at the whole scoped test codebase instead of a diff). Lenses:

1. **Flakiness sources** — everything in `../../references/flakiness-catalog.md`:
   timing waits, race conditions, shared state, order dependence, unstable
   selectors.
2. **False-green & assertion quality** — tests that can pass while the feature
   is broken: missing/weak assertions, swallowed errors, over-mocking that tests
   the mock, conditional assertions.
3. **Duplication & over-complexity** — copy-paste blocks, needless abstraction
   layers, dead helpers, unused fixtures, tests nobody could name the purpose of.
4. **Convention drift** — deviations from the project's own documented
   conventions and from `../../references/e2e-patterns.md` defaults (locator
   policy, fixtures, tagging, magic timeouts).
5. **Structure & cost** — suite runtime distribution, missing parallelism/
   isolation, redundant coverage (five e2e tests where one e2e + four unit
   would do).

Each agent brief: scope paths, profile pointer, lens description, the standard
finding format, word cap. Append raw findings to a scratch section of the
report as they return.

## Phase 3 — Triage, verify, report

- Verify EVERY finding against real code before it enters the report; drop
  false positives explicitly. This is main-session judgment — do not delegate.
- Merge duplicates, rank: **Critical** (false-green, data risk, broken suite) →
  **Important** (flaky patterns, spreading drift) → **Worth-fixing**.
- Finalize `docs/qa/audit-report.md`: scope, baseline numbers, findings with
  file:line evidence, and a short "what's healthy" section (honest, not filler —
  it tells the team what to keep doing).

## Phase 4 — Refactoring plan

Write `docs/qa/refactoring-plan.md`: ordered steps, each independently shippable
and verifiable, roughly: (1) stop-the-bleeding (Critical), (2) flakiness root
causes, (3) structure/duplication, (4) conventions & polish. For each step:
goal, files, approach, verification command, rough size (S/M/L). Steps must be
small enough that one step fits comfortably in one session window.

Present report + plan to the user. **Stop here by default** — execution starts
only when the user picks steps (or says "do it all").

## Phase 5 — Execute (on request, step by step)

Per step: implement (delegate mechanical bulk to `mechanical-editor`, test
rewrites to `test-author` — with precise briefs), run the step's verification
command plus the project gates, run the review loop on the diff, mark the step
done in the plan file with evidence, commit per the repo's policy if the
profile allows. Never batch multiple plan steps into one unreviewed diff.

Refactoring tests has a special trap: a "refactored" test that stops testing
the same behavior. For any rewritten test, re-prove it can fail
(quality-rules rule 3).
