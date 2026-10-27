---
name: write-tests
description: Implements automated tests (Playwright e2e and below) from a qa-pilot test plan or a direct request, following the project's own conventions, with a mandatory review loop and proof that every new test can fail. Mode bootstrap sets up an e2e skeleton (config, fixtures, page object, one smoke test) in a project with no e2e layer, installing tools only after a yes to the exact list. Use when the user asks to write/add/implement tests, automate scenarios from a test plan, cover a feature/bugfix with tests, or bootstrap/set up e2e. Requires docs/qa/project-profile.md (run qa-pilot:onboard first). Not for deciding what to test (use qa-pilot:plan-tests) or auditing existing tests (use qa-pilot:test-code-audit).
user-invocable: false
---

# Write Tests

Turn scenarios into merged-quality test code. Input: a plan from
`docs/qa/test-plans/` (preferred) or a direct request — for a direct request
covering more than ~3 scenarios, run `qa-pilot:plan-tests` first instead of
designing scope on the fly.

**Mode.** Invoked with mode `bootstrap` (by onboard's Strategy check, or `/qa-pilot:test` on "set up e2e") → go to "Mode bootstrap" at the end and skip Phases 1-5. Anything else is the normal flow below.

Create a todo per phase. Read `../../references/quality-rules.md`,
`../../references/model-routing.md`, and `../../references/e2e-patterns.md`.
Prerequisite: `docs/qa/project-profile.md`. Also read `docs/qa/learnings.md` if it exists, per `../../references/learnings.md`.

## Phase 1 — Prepare briefs

- From the plan: take the automatable scenarios (or the subset the user picked).
- From the profile + 1–2 neighboring test files: pin down the exact conventions
  (imports, fixtures, POM usage, tags, data setup/cleanup).
- **Shared data.** A new test that logs in as a shared account or depends on data another test created or left behind is not written that way unless it carries a comment with the reason (QAP-TC-020). By default it creates its own data and registers cleanup; see `../../references/e2e-patterns.md`, Fixtures & cleanup and Test data management. Put this rule in every brief.
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
   per package yourself with the restoring script; trust but verify
   (`SKILL_DIR` is this skill's base directory, shown when it loads; give the
   shell call a 600s timeout):
   `python3 "$SKILL_DIR/../test-code-audit/scripts/failure_probe.py" --file <src> --line <n> --find "<text>" --replace "<text>" -- <command for this test>`.
   Skip BUG tests that stay red on purpose (expected-fail): their proof is the
   recorded failure against the unfixed code.
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
- Upsert a row in `docs/qa/coverage-matrix.md` for each test added (`../../references/coverage-matrix.md`): Proof `failed when broken, <date>` only if you saw it fail in this run, else `distinguishing assertion`.
- **Lessons.** If a trigger from `../../references/learnings.md` occurred in this run, propose the lessons to the owner as that file says; write them only after a yes. If invoked by another qa-pilot skill, hand the candidates back to it instead of asking.
- Commit/PR per the repo's own policy from the profile; if the policy is
  unknown, show the diff and ask.

## Mode bootstrap — e2e skeleton

Creates the first e2e layer of a project that has none. Read `../../references/e2e-patterns.md` first; the skeleton follows it and this section does not repeat it.

**Preconditions** (same as the offer in `../onboard/SKILL.md`, Strategy check):
- The profile's `Test layers` shows no e2e layer (the project is empty or has unit tests only). If an e2e runner with its own config already exists, refuse in one line, create nothing, and point to `docs/qa/strategy-check.md` (the gaps are reported there).
- Framework: the e2e runner already in the dependencies, else Playwright.
- A JS/TS project (a `package.json`). Otherwise bootstrap stops and lists what the owner would need to set up.
- The profile has at least one critical flow and the run commands. If it has no critical flow, ask the owner for the first one; do not guess it.

**1. Install list. Show it, then stop.** Print in the chat, in full:
- packages with exact versions (look up the current version; no ranges, no `latest`), as dev dependencies of this project;
- the commands it will run: the package manager's install command and the browser download (for Playwright `npx playwright install chromium`);
- the files it will create or edit, each as a resolved path (find the lockfile of the project's package manager, and read the smoke flow's components to see which lack a `data-testid`, before printing): `package.json` (dependency and script), the named lockfile, the framework config, the auth fixture, the base page object, the cleanup fixture, the test-id constants file, the smoke test, and every component to edit, one path each. A file not on the list is a new ask.

Install nothing and write nothing until the owner answers yes to this exact list. Without a yes, stop at the list. **A yes covers this list only.** If a later step needs one more package, command or file outside the list (an extra plugin, a different browser, a dependency for the cleanup), show the addition and ask again before doing it. Never install globally (no `-g`, no `sudo`), and never edit CI.

**2. Create** (after the yes), reusing the project's folder layout and naming from the profile:
- the framework config (base URL and the dev-server command from the profile, trace and screenshots on first retry, projects/tags per `../../references/e2e-patterns.md`);
- an auth fixture (`storageState` or API login per "Auth & storageState"); credentials come from the profile's Environments credential mechanism, and if it names none, ask the owner;
- a base page object, fixture-injected ("Fixture-injected Page Object Model");
- the cleanup fixture ("Fixtures & cleanup");
- the test-id constants file, owned by the component side as the patterns file says;
- one smoke test on the first critical flow: the shortest path that proves the flow works, its own data, cleanup registered;
- the package script (`test:e2e` unless the project names scripts differently).

The smoke test follows the hard test-id rule: every element it touches is found by `data-testid`. A missing test id is added to the component. That is not a code fix (`../../references/test-delta.md`, section 6): it changes no behaviour, so list each such component edit in the report and the commit. A role or text locator only with the `// no testid: <reason>` comment the patterns file requires.

**3. Run and prove.** Start the dev server per the profile's Commands (the test needs it running). Run the smoke test: green. Then the failure proof, as in Phase 3 step 2: temporarily break the behaviour the smoke test checks, watch it fail for the right reason, restore, watch it green (use the `failure_probe.py` command from Phase 3). A smoke test that cannot fail is not delivered; fix it first. Run it twice more for flakiness.

**4. Finish.** Run the project's typecheck and lint over the new files. Run the review loop (Phase 4) on the diff. Add the coverage-matrix row for the smoke test (Phase 5). Commit per the repo's policy, or show the diff and ask. The closing message lists the files created, the installs that were approved, the component edits for test ids, and the CI job the owner should add (the run command, the browser install step, the report and trace upload). CI itself is not touched.
