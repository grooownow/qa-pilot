# qa-pilot 0.8.0 — project learnings, coverage matrix, wider drift check, routing and examples — design

Date: 2026-10-26 · Status: owner said "do it yourself, no questions"; calls below are Claude's.

## Intent

A study of 11 free QA skills on Agensi.io (notes in the session scratchpad, summary in memory `agensi-free-pro`)
showed qa-pilot ahead on proof that tests can fail, AC checks and requirement-vs-code audits, but behind on a few
cheap things other skills do. The owner picked which gaps to close:

1. **Project learnings.** qa-pilot forgets what it learned on a project: a rejected finding, a flaky root cause, a
   command quirk. Next run repeats the mistake. The profile holds detected facts; nothing holds experience.
2. **Wider profile drift check.** `profile_drift.py` (0.7.0) catches renamed scripts, moved paths and CI changes.
   It misses new test dependencies and changed project rules (CLAUDE.md, AGENTS.md, lint and test configs).
3. **A minimal coverage matrix.** Coverage proved in `task-qa verify` leaves no lasting trace: if a test is deleted
   later, nobody notices that a requirement lost its test. The owner wants a "super basic" feature → requirement →
   tests matrix, not a traceability system.
4. **Routing and readability:** "Not for:" lines in every skill description, example output files next to the
   skills that write documents, and named test anti-patterns in `test-code-audit`.

Dropped by the owner: environment/dev-server diagnosis (env-doctor style), a browser smoke sweep in `explore`.

## Goals

- `docs/qa/learnings.md` in the user's project: written only after the owner agrees, read by every skill.
- `profile_drift.py` reports `new-test-dep`, `rules-changed` and `lost-test`; onboard refresh handles them.
- `docs/qa/coverage-matrix.md` in the user's project: one table, upserted by the skills that prove or add coverage.
- Every skill description has a "Not for:" clause; `check_skills.py` enforces it.
- Example outputs for the four document-writing flows; anti-pattern catalog used by `test-code-audit`.
- Release 0.8.0: CHANGELOG entry, version bump, README sections. Tag and push only after the owner's OK.

## Non-goals

- No CI gate, no exit-code traceability checker, no AC id scheme imposed on the user's tracker.
- No change to the Free/Pro split (`feat/editions` is shelved; it rebases onto this later).
- No automatic deletion of learnings or matrix rows.

## Anti-goals

- Learnings turning into a dump of generic advice ("write good tests") or task diaries.
- A matrix that claims coverage it never proved.
- Drift noise that nags on every run (each new kind must clear after one onboard refresh).

## 1. Project learnings

**File:** `docs/qa/learnings.md` (user's project). Format and rules live in one new reference,
`references/learnings.md`; skills only point to it.

```markdown
# QA learnings
> Written by qa-pilot with the owner's OK. Every qa-pilot skill reads this before it starts.
> One line per lesson. Newest first inside a section.

## <area: e2e · unit · test data · auth · CI · review · audit · <feature name>>
- <date> · <the lesson as a rule: do / don't + why> · source: <owner | review | probe | flaky | run> · for: <skills or all>
```

**When a lesson is proposed** (strict; anything else is not a lesson):
- the owner rejected or corrected a qa-pilot finding, plan item or test as wrong *for this project*;
- the same review finding came back in two review rounds or two runs;
- a flaky or failing test got a project-specific root cause;
- a command or environment quirk cost a retry (and the profile is not the right home — see below).

**Not a lesson:** generic testing advice; a fact the repo shows (that goes to the profile via onboard); an owner
scope filter ("don't test X") — that goes to `docs/qa/rule-overrides.json` → `scope`, as today; details of one task.

**Writing.** At the end of a run, a skill that met a trigger shows the proposed lines in one message and writes
them only after the owner says yes (same pattern as scope filters). At most 3 new lines per run. Duplicates are
merged into the existing line (date updated) instead of added.

**Reading.** Every skill reads the file at start, right after the profile, when it exists (cap ~60 lines, so it is
read whole). Precedence: the owner's words in this session > learnings > skill defaults. A lesson that contradicts the
profile or the repo is shown to the owner as a question, not applied silently.

**Maintenance.** `onboard` (full and refresh) shows lessons that look stale (they name a path, command or
dependency that no longer exists) and asks whether to drop them. Over 60 lines → onboard proposes merges.

## 2. Wider drift check (`skills/onboard/scripts/profile_drift.py`)

Three new drift kinds, same output format (`- <kind>: <detail>`), same exit codes, same "shallow string matching"
philosophy, stdlib only.

- **`new-test-dep`** — a known test-related package is a dependency (any `package.json` `dependencies` /
  `devDependencies`, `pyproject.toml`, `requirements*.txt`) but its name does not appear anywhere in the profile
  (case-insensitive). Known list (exact set is the builder's, must include): `@playwright/test`, `playwright`,
  `cypress`, `vitest`, `jest`, `mocha`, `msw`, `nock`, `supertest`, `@testing-library/*` (reported once as
  `testing-library`), `storybook` / `@storybook/test`, `@stryker-mutator/*`, `testcontainers`, `pytest`,
  `pytest-playwright`, `hypothesis`, `mutmut`. Match the bare name (`@playwright/test` → `playwright`).
- **`rules-changed`** — a project-rules file changed after the profile. Files: `CLAUDE.md`, `AGENTS.md`,
  `.cursor/rules/**`, `.cursorrules`, ESLint configs (`eslint.config.*`, `.eslintrc*`), `playwright.config.*`,
  `vitest.config.*`, `jest.config.*`, `cypress.config.*`, `pytest.ini`, `pyproject.toml` only if its
  `[tool.pytest*]` section exists. "After the profile" = the file's last commit time is later than the later of the
  profile's last commit time and its `Generated … on <date>` (end of that day). Untracked or uncommitted rule files
  are ignored (no git → skip this kind). Detail names the file and both dates.
- **`lost-test`** — `docs/qa/coverage-matrix.md` exists and a row's test path no longer exists in the repo. Detail
  names the feature, requirement and path. (Placed in the drift check because `test` and `audit` already run it
  before every run; the name of the script stays.)

`test` and `audit` keep their current handling (show lines, ask once, never block). Onboard refresh mode:
`new-test-dep` → update Test landscape / Framework maturity; `rules-changed` → re-read that file, update
Conventions (and lessons it contradicts are shown); `lost-test` → not onboard's job: refresh tells the owner and
offers to drop the row or point it to the new test path; it edits the matrix only after a yes.

## 3. Minimal coverage matrix

**File:** `docs/qa/coverage-matrix.md` (user's project). Format in a new reference `references/coverage-matrix.md`.

```markdown
# Coverage matrix
> Maintained by qa-pilot. A row means: this requirement has this test, and here is how we know it can fail.

| Feature | Requirement | Test | Layer | In CI | Proof | Updated |
|---|---|---|---|---|---|---|
| Checkout | Order total includes shipping (PROJ-123 AC2) | e2e/checkout.spec.ts › "total with shipping" | e2e | yes | failed when broken, 2026-10-26 | 2026-10-26 |
```

- **Requirement**: one line in the user's words; ticket/AC reference in brackets when one exists. No id scheme.
- **Test**: `path › test name`. One row per (requirement, test).
- **Proof**: `failed when broken, <date>` (seen red: a BUG test against unfixed code, a `failure_probe.py` kill, or
  write-tests' own fail proof) · `distinguishing assertion` (read, not run) · `none`.
- **Upsert key**: (Feature, Requirement, Test). Rows are never deleted automatically.
- **Writers**: `task-qa verify` (its "Covered (CI)" and "Added" items), `cover` and `write-tests` (tests they add,
  with their proof), `test-code-audit` (probe verdicts update Proof: `killed` → failed when broken; `survived` →
  `none` plus a note). Writing the matrix is part of the skill's normal output — no extra question.
- **Readers**: `task-qa plan` (existing coverage for touched features → regression set), `project-audit` and
  `spec-audit` (coverage evidence; a row with Proof `none` on a critical flow is a finding).

## 4. Routing, examples, anti-patterns

- **"Not for:" clause** in every skill's `description`, naming the sibling to use instead (e.g. task-qa: "Not for a
  whole-feature requirements audit (spec-audit) or for writing tests without a plan (cover)"). Descriptions stay ≤
  1024 chars; `spec-audit` (985 now) is shortened to fit. `check_skills.py` gets a rule: description contains
  `Not for` (case-sensitive), with a test.
- **Examples** — synthetic, one invented project ("a small online shop: catalog, cart, checkout, accounts"), real
  formats, short:
  - `skills/onboard/examples/project-profile.md`
  - `skills/task-qa/examples/task-file.md` (plan + verify log)
  - `skills/test-code-audit/examples/audit-report.md`
  - `skills/spec-audit/examples/actions.md`
  - plus a filled example block inside each of the two new references.

  Each SKILL.md points to its example in its output step ("Example: `examples/<file>`"). `check_skills.py` checks
  that every `examples/…` path a SKILL.md mentions exists.
- **Named anti-patterns** — new `references/test-anti-patterns.md`: name · sign · how to spot it (grep hint where
  one exists) · fix. Must include: **Liar** (passes while the feature is broken), **Mirror** (expected value
  re-computed the way the code computes it), **Mockery** (asserts the mock), **Status-only** (UI test confirms by
  response status or mocked call, QAP-TC-032), **Giant** (one test, many behaviours), **Inspector** (asserts
  internals, breaks on refactor), **Chain Gang** (depends on other tests' order or state), **Sleeper** (fixed
  waits: `waitForTimeout`, `sleep`), **Ghost** (skipped, `.only`, empty or never-run test), **Copycat** (copy-pasted
  setup or bodies). `test-code-audit` lenses 1–3 tag each finding with a name; the report groups by name; Phase 1
  runs the grep hints as a cheap first pass. `qa-reviewer` may use the names.

## Constraints

- Skills stay instructions-first; the only script changes are `profile_drift.py` and `check_skills.py` (stdlib,
  unit-tested in their existing test files).
- All existing gates stay green: `scripts/kb`, `scripts/plugin`, `skills/*/scripts` tests, `check_skills.py`,
  `claude plugin validate .`.
- Release rule: CHANGELOG entry + version bump to 0.8.0. Push, merge and tag only with the owner's OK; push via the
  `github.com-grooownow` SSH alias.
- Copy tone: solution + mechanism, no hype.

## Calls made by Claude (owner to check)

- Version **0.8.0** for this release; the shelved `feat/editions` (also labelled 0.8.0, unreleased) moves to 0.9.0.
- Branch `feat/learnings` from `main`.
- Learnings are written only after the owner's yes; the matrix is written without asking (it is output, like the task
  file).
- `lost-test` lives in the drift check so it runs before every `test`/`audit` without a new hook.
- `rules-changed` ignores uncommitted rule edits (avoids nagging during the edit itself).
- Anti-pattern names are in English (they are labels); report text stays in the user's language.
