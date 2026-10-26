---
name: test-code-audit
description: Deep audit of an existing test codebase - finds anti-patterns, copy-paste, flakiness sources, over-complexity, false-green and dead tests; proves on a sample (critical flows + suspects) that existing tests can fail by breaking the code under test with a restoring script; produces a severity-ranked report and an ordered refactoring plan, then can execute the plan step by step. Use when the user asks to audit/review/health-check the test suite, complains about flaky or slow tests, or wants a refactoring plan for tests. Requires docs/qa/project-profile.md (run qa-pilot:onboard first). Not for missing scenarios in a feature (use qa-pilot:spec-audit or qa-pilot:plan-tests).
user-invocable: false
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
Also read `docs/qa/learnings.md` if it exists, per `../../references/learnings.md`.

## Phase 1 — Scope & baseline

- From the profile: test locations, commands, team priorities.
- Agree scope with the user if ambiguous (whole suite vs one package; e2e only
  vs everything). State the scope in the report header.
- Baseline run: execute the suite once (or the target subset). Record pass/fail/
  skip counts and duration in the report. A suite that doesn't run is finding #1.
- State the failure-proof sample (Phase 3): which tests, how many, rough time.

## Phase 2 — Parallel audit lenses

Dispatch qa-reviewer agents in ONE parallel batch, one lens each (see
`../../references/review-loop.md` for dispatch mechanics — same protocol,
pointed at the whole scoped test codebase instead of a diff). Lenses:

1. **Flakiness sources** — everything in `../../references/flakiness-catalog.md`:
   timing waits, race conditions, shared state, order dependence, unstable
   selectors.
2. **False-green & assertion quality** — tests that can pass while the feature
   is broken: missing/weak assertions, swallowed errors, over-mocking that tests
   the mock, conditional assertions, a UI/e2e test that confirms an action only
   by the response status or a mocked API call instead of what the user sees
   (QAP-TC-032; an exception counts only with a comment giving the reason).
   This lens also names its **suspects** for Phase 3: test, file:line, why.
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

## Phase 3 — Failure proof of existing tests

Reading a test does not prove it can fail. Break the code it guards and run it.

- **Sample:** the tests of the critical flows from the profile, plus the
  suspects of lens 2. Default 10 tests; the size goes into the Phase 1 scope
  with its cost (each probe runs one test twice). The user can widen it.
- **If the project already runs mutation testing** (a Stryker, mutmut or PIT
  config in the repo), run it on the scoped modules and use its report instead
  of hand-picked mutations.
- **Otherwise, per test, one mutation** in the code under test, on the line
  the test's main assertion depends on: invert the condition, drop the call
  that performs the action, return the old value. The mutation must change the
  behaviour the test names, or the probe proves nothing. Run it with the
  script, never by editing the file yourself:

  ```bash
  SKILL_DIR=<absolute base directory of this skill>   # shown when the skill loads
  python3 "$SKILL_DIR/scripts/failure_probe.py" --file <src> --line <n> \
      --find "<text>" --replace "<text>" -- <profile command for this one test>
  ```

  The script runs the test on untouched code (it must pass), applies the
  mutation, runs again, and restores the file byte for byte, also on timeout or
  interrupt. Run probes one at a time: they change shared files. Give the shell
  call a timeout of at least 2 × the probe's `--timeout` (default 240s) plus a
  minute, at most 600s in the foreground, or run it in the background: a killed probe leaves the mutation in
  place. If a probe reports a leftover `<file>.qa-probe-orig`, restore it with
  the `mv` it prints before anything else. Afterwards `git status` must show no
  change to product code.
- **Verdicts** go to the report as a table: test · mutation (file:line, find →
  replace) · verdict · the last output lines.
  - `survived`: a proven false green, **Critical**.
  - `killed`: listed under "what's healthy".
  - `baseline-red`: a broken test, Critical, reported with the baseline.
  - `timeout` / `interrupted` / `error`: "not proved", with the reason.
- **Matrix:** verdicts update the Proof column of `docs/qa/coverage-matrix.md` for the tests that have a row: `killed` → `failed when broken, <date>`; `survived` → `none` plus a note (`../../references/coverage-matrix.md`).

## Phase 4 — Triage, verify, report

- Verify EVERY finding against real code before it enters the report; drop
  false positives explicitly. This is main-session judgment — do not delegate.
- Merge duplicates, rank: **Critical** (false green, whether proven by a probe or found by reading; data risk; broken suite) →
  **Important** (flaky patterns, spreading drift) → **Worth-fixing**.
- Finalize `docs/qa/audit-report.md`: scope, baseline numbers, findings with
  file:line evidence, and a short "what's healthy" section (honest, not filler —
  it tells the team what to keep doing).

## Phase 5 — Refactoring plan

Write `docs/qa/refactoring-plan.md`: ordered steps, each independently shippable
and verifiable, roughly: (1) stop-the-bleeding (Critical), (2) flakiness root
causes, (3) structure/duplication, (4) conventions & polish. For each step:
goal, files, approach, verification command, rough size (S/M/L). Steps must be
small enough that one step fits comfortably in one session window.

Present report + plan to the user. **Stop here by default** — execution starts
only when the user picks steps (or says "do it all").

**Lessons.** If a trigger from `../../references/learnings.md` occurred in this run, propose the lessons to the owner as that file says; write them only after a yes.

## Phase 6 — Execute (on request, step by step)

Per step: implement (delegate mechanical bulk to `mechanical-editor`, test
rewrites to `test-author` — with precise briefs), run the step's verification
command plus the project gates, run the review loop on the diff, mark the step
done in the plan file with evidence, commit per the repo's policy if the
profile allows. Never batch multiple plan steps into one unreviewed diff.

Refactoring tests has a special trap: a "refactored" test that stops testing
the same behavior. For any rewritten test, re-prove it can fail
(quality-rules rule 3), with `failure_probe.py` and the same mutation as in
Phase 3 when the test was probed there.
