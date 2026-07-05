---
name: write-tests
description: Implements automated tests (Playwright e2e and below) from a qa-pilot test plan or a direct request, following the project's own conventions, with a mandatory review loop and proof that every new test can fail. Use when the user asks to write/add/implement tests, automate scenarios from a test plan, or cover a feature/bugfix with tests. Requires docs/qa/project-profile.md (run qa-pilot:onboard first).
---

# Write Tests

Turn scenarios into merged-quality test code. Input: a plan from
`docs/qa/test-plans/` (preferred) or a direct request — for a direct request
covering more than ~3 scenarios, run `qa-pilot:plan-tests` first instead of
designing scope on the fly.

Create a todo per phase. Read `../../references/quality-rules.md`,
`../../references/model-routing.md`, and `../../references/e2e-patterns.md`.
Prerequisite: `docs/qa/project-profile.md`.

## Phase 1 — Prepare briefs

- From the plan: take the automatable scenarios (or the subset the user picked).
- From the profile + 1–2 neighboring test files: pin down the exact conventions
  (imports, fixtures, POM usage, tags, data setup/cleanup).
- Check reuse FIRST: existing fixtures, page objects, helpers, seeded data that
  cover part of the work. New infrastructure only when nothing reusable exists
  (quality-rules rule 1).
- Split work into packages of 3–6 related scenarios. Write a precise brief per
  package: scenarios (verbatim from the plan), target files, conventions,
  reusable pieces, run command, required output format.

## Phase 2 — Implement

- Dispatch `test-author` (one per package; ≤3 in parallel — test runs contend
  for the dev server and DB). Small single-package jobs: implement inline
  instead, same rules.
- New shared infrastructure (a fixture, a page object) is designed in the main
  session — its shape is judgment — then handed to `test-author` to finish.
- If `test-author` returns a question instead of finished work, answer it
  (asking the user if needed), fold the answer into the brief, and re-dispatch —
  never leave a package half-done silently.
- Track progress in the plan file: mark each scenario `automated → <file>` as
  it lands. Sessions die; the plan file is the resume point.

## Phase 3 — Verify

For the full batch, in this order:

1. Run the new tests. All green.
2. **Failure proof** per test (or per tightly-related group): break the subject
   or assertion, watch the RIGHT failure, restore, watch green
   (quality-rules rule 3). `test-author` reports include this — spot-check one
   per package yourself; trust but verify.
3. Flakiness shake: run the new tests twice more (use the project's repeat flag
   if it has one). Any flake → fix the root cause now via
   `../../references/flakiness-catalog.md` — never ship with retries/sleeps
   masking it.
4. Project gates from the profile (typecheck, lint, full affected suite).

## Phase 4 — Review loop

Run `../../references/review-loop.md` on the whole diff. Default lenses:
correctness/false-green, flakiness, simplicity & slop, conventions. Fix, re-gate,
re-review (≤3 rounds).

## Phase 5 — Finish

- Update the plan file: scenario→file map complete, leftovers (non-automatable
  or deferred) explicitly listed with reasons.
- Summarize for the user: tests added (count, files), evidence (runs, failure
  proofs), review rounds, debt accepted.
- Commit/PR per the repo's own policy from the profile; if the policy is
  unknown, show the diff and ask.
