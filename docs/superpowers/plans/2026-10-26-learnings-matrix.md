# qa-pilot 0.8.0 — learnings, coverage matrix, wider drift, routing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give qa-pilot a per-project memory of lessons, a minimal requirement → test matrix, a drift check that also sees new test dependencies, changed project rules and lost tests, "Not for:" routing clauses, example outputs and named test anti-patterns.

**Architecture:** Two stdlib Python scripts change (`profile_drift.py`, `check_skills.py`) with unit tests; everything else is Markdown: three new shared references, four example files, and edits to the SKILL.md files that read or write the new documents.

**Tech Stack:** Python 3 stdlib + `unittest`; Markdown skills for Claude Code.

**Spec:** `docs/superpowers/specs/2026-10-26-learnings-matrix-design.md`

## Global Constraints

- Scripts: stdlib only; tests with `unittest` in the existing test files; run with `python3 -m unittest discover -s <dir>`.
- Every skill `description` ≤ 1024 characters and contains `Not for` (enforced by `check_skills.py` after Task 2).
- Skills reference shared files as `../../references/<file>.md` (that form is what `check_skills.py` validates).
- New documents in the user's project: `docs/qa/learnings.md`, `docs/qa/coverage-matrix.md` — exact formats are in the spec §1 and §3; copy them verbatim into the references.
- Learnings are written only after the owner says yes, at most 3 new lines per run; the matrix is written without asking; nothing deletes learnings or matrix rows automatically.
- Drift output format unchanged: `- <kind>: <detail>`; exit 0 / 1 / 2 unchanged; the check never blocks a run.
- Copy tone: solution + mechanism, no hype. Skill files in English.
- No push, merge or tag. Commit on branch `feat/learnings`, ending commit messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Profile says "Playwright" / "MSW" / "Testing Library" in prose and the dep is `@playwright/test` / `msw` / `@testing-library/react` → no `new-test-dep` (case-insensitive, bare name, `testing-library` matches "Testing Library" with a space or hyphen).
2. No git, profile untracked, or a rules file only modified in the working tree → `rules-changed` silently skipped, no crash, other kinds still reported.
3. Matrix missing, matrix with no table, a row whose Test cell has `path › name` with backticks, or a path with a `::` / `›` suffix → only a truly missing path yields `lost-test`.
4. `pyproject.toml` without a `[tool.pytest` section is not a rules file; one with it is.
5. A description in double quotes with escaped `\"` and the words "Not for" → `check_skills.py` passes; a description without it fails with a clear message.

---

### Task 1: Wider drift check

**Files:**
- Modify: `skills/onboard/scripts/profile_drift.py` (docstring "Drift:" list, constants, `check()`)
- Test: `skills/onboard/scripts/test_profile_drift.py`

**Interfaces:**
- Produces: drift kinds `new-test-dep`, `rules-changed`, `lost-test` in the list returned by `check(root, profile_text) -> (drifts, ci_file_count)`; `drifts` stays `list[tuple[str, str]]`.
- New helpers (names fixed, bodies the implementer's): `test_deps(top, files) -> set[str]` (bare names), `rules_changed(top, files, profile_path, generated_date) -> list[str]` (details), `lost_tests(root, top, names) -> list[str]` (details). `check()` may take an optional `profile_path=None` keyword so `main()` passes the real path; when `None`, `rules-changed` is skipped.

- [ ] **Step 1: Write failing tests** in `DriftTest` (extend `repo()` with optional `deps`, `dev_deps`, `pyproject`, `requirements`, `matrix`, `git=False` params; when `git=True` init a repo, commit with fixed `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`):
  - `test_new_test_dep_reported`: dev dep `msw` not in profile → one drift `("new-test-dep", …)` whose detail contains `` `msw` ``.
  - `test_known_dep_named_in_prose_is_quiet`: deps `@playwright/test`, `@testing-library/react`, `vitest`; profile text mentions "Playwright", "Testing Library", "Vitest" → no `new-test-dep`.
  - `test_testing_library_reported_once`: `@testing-library/react` and `@testing-library/user-event`, profile silent → exactly one `new-test-dep` naming `testing-library`.
  - `test_python_deps`: `requirements-dev.txt` with `pytest==8.0` and `hypothesis>=6`; profile mentions pytest → one drift for `hypothesis`; `pyproject.toml` `[project.optional-dependencies]` listing `pytest-playwright` → reported.
  - `test_rules_changed_after_profile`: git repo; profile committed 2026-10-01 (Generated 2026-10-01); `CLAUDE.md` committed 2026-10-05 → one `rules-changed` naming `CLAUDE.md`, `2026-10-05`, `2026-10-01`.
  - `test_rules_same_day_or_before_is_quiet`: `CLAUDE.md` committed 2026-10-01 18:00 with Generated 2026-10-01 → none.
  - `test_rules_uncommitted_or_no_git_is_quiet`: no git at all → no `rules-changed` and no exception; git repo with `AGENTS.md` only modified in the working tree → none.
  - `test_pyproject_rules_only_with_pytest_section`: committed-later `pyproject.toml` without `[tool.pytest` → none; with `[tool.pytest.ini_options]` → one.
  - `test_lost_test`: matrix row Test cell `` `e2e/checkout.spec.ts` › "total with shipping" `` and the file is absent → one `lost-test` with "Checkout" and the path; when the file exists → none; matrix absent → none; matrix with no table → none.
- [ ] **Step 2: Run** `python3 -m unittest discover -s skills/onboard/scripts` — new tests FAIL, old 21 pass.
- [ ] **Step 3: Implement.** Known package list and rules globs exactly as spec §2 (the implementer may add, never drop). Bare name: drop scope (`@playwright/test` → `playwright`, `@storybook/test` → `storybook`, `@stryker-mutator/core` → `stryker`, `@testing-library/*` → `testing-library`); match against the profile lowercased with `-`/space treated alike. Python deps: names before any of `[<>=~! ;` in `requirements*.txt` and in `pyproject.toml` dependency arrays (regex, no TOML parser). Commit times via `git log -1 --format=%ct -- <path>`; "uncommitted" = `git status --porcelain -- <path>` non-empty → skip that file. Generated date counts as its end of day (23:59:59 local). Matrix path = first inline-code span in the Test cell, else text before ` ›`; strip a `::…` suffix; existence via the existing `path_exists`. Update the module docstring's "Drift:" list with the three kinds.
- [ ] **Step 4: Run** the same command — all pass. Also run it against this repo: `cd /tmp && python3 <repo>/skills/onboard/scripts/profile_drift.py --root <repo>` exits 2 (no profile) without a traceback.
- [ ] **Step 5: Commit** `feat(onboard): drift check sees new test deps, changed project rules, lost matrix tests`.

### Task 2: Routing clauses and the checks that guard them

**Files:**
- Modify: `scripts/plugin/check_skills.py`, `scripts/plugin/test_check_skills.py`
- Modify: frontmatter `description` of all 11 `skills/*/SKILL.md`

**Interfaces:**
- Produces: `check_skills.py` errors `"<path>: description has no 'Not for' clause"` and `"<path>: missing example <rel>"` for a mentioned `examples/<file>.md` that does not exist next to the SKILL.md (regex on `` `examples/[A-Za-z0-9_.-]+\.md` ``). Task 5 relies on the examples check.

- [ ] **Step 1: Failing tests:** `test_description_needs_not_for` (description without `Not for` → that error), `test_not_for_in_quoted_description` (description `"Does \"x\". Not for y."` → no error), `test_missing_example` (body mentions `` `examples/report.md` ``, file absent → error; present → none). Update the `skill()` helper default description to include `Not for z.` so existing tests stay valid.
- [ ] **Step 2: Run** `python3 -m unittest discover -s scripts/plugin` — new tests fail.
- [ ] **Step 3: Implement** both checks; update the module docstring.
- [ ] **Step 4: Add a "Not for:" sentence to every description**, naming the sibling to use instead (keep the existing text otherwise; shorten `spec-audit` and others only as needed to stay ≤ 1024). Required content per skill:
  - `onboard`: not for QA work itself (`test`, `audit`).
  - `test`: not for the whole project or a whole feature's requirements (`audit`), not for first setup (`onboard`).
  - `audit`: not for one task's plan or verification (`test`).
  - `task-qa`: not for a whole-feature requirements audit (`spec-audit`) or tests for already-shipped code without a plan (`cover`).
  - `plan-tests`: not for writing the tests (`write-tests`) or checking AC against code (`task-qa`).
  - `write-tests`: not for deciding what to test (`plan-tests`) or auditing existing tests (`test-code-audit`).
  - `cover`: not for a task with AC still to check (`task-qa`).
  - `explore`: not for writing automated tests (`write-tests`).
  - `spec-audit`: not for one task's diff (`task-qa`) or the test code (`test-code-audit`).
  - `project-audit`: not for a single feature (`spec-audit`) or a single task (`task-qa`).
  - `test-code-audit`: not for missing scenarios in a feature (`spec-audit`, `plan-tests`).
- [ ] **Step 5: Run** `python3 -m unittest discover -s scripts/plugin && python3 scripts/plugin/check_skills.py` — `OK: 11 skills`.
- [ ] **Step 6: Commit** `feat(skills): "Not for" routing clause in every description, enforced by check_skills`.

### Task 3: Project learnings and the coverage matrix in the skills

**Files:**
- Create: `references/learnings.md`, `references/coverage-matrix.md`
- Modify: `skills/{onboard,test,audit,task-qa,plan-tests,write-tests,cover,explore,spec-audit,project-audit,test-code-audit}/SKILL.md`, `agents/qa-reviewer.md` only if it reads project docs today (check; otherwise leave)

**Interfaces:**
- Consumes: Task 1 drift kinds (`new-test-dep`, `rules-changed`, `lost-test`).
- Produces: the two references (paths above) that Task 5's examples and Task 6's docs point to.

- [ ] **Step 1: Write `references/learnings.md`**: the file format (spec §1 block verbatim), when a lesson is proposed / not a lesson (spec §1 lists verbatim in meaning), writing rule (one message, owner's yes, ≤ 3 per run, merge duplicates), reading rule and precedence, maintenance, plus one filled example section (3 lines, the invented online shop).
- [ ] **Step 2: Write `references/coverage-matrix.md`**: format (spec §3 block verbatim), column meanings, Proof values exactly `failed when broken, <date>` · `distinguishing assertion` · `none`, upsert key, writers, readers, "never delete automatically", plus a 4-row filled example.
- [ ] **Step 3: Wire learnings into all 11 skills**: at the point each reads the profile, add one line: read `docs/qa/learnings.md` if it exists, per `../../references/learnings.md`. In the final step of the skills that produce findings or tests (`task-qa`, `plan-tests`, `write-tests`, `cover`, `explore`, `spec-audit`, `project-audit`, `test-code-audit`), add the "propose lessons if a trigger occurred" step pointing to the reference.
- [ ] **Step 4: Wire the matrix**: writers `task-qa` (verify step 5), `cover`, `write-tests`, `test-code-audit` (Phase 3 verdicts); readers `task-qa` (plan step 4 regression set), `spec-audit`, `project-audit` (a critical-flow row with Proof `none` is a finding). Each points to `../../references/coverage-matrix.md`.
- [ ] **Step 5: Onboard refresh mode**: handle `new-test-dep` (update Test landscape / Framework maturity), `rules-changed` (re-read the file, update Conventions, show contradicted lessons), `lost-test` (tell the owner, offer to drop the row or repoint it; edit only after yes). Full and refresh runs: list lessons that name a path/command/dependency that no longer exists and ask whether to drop them; over 60 lines → propose merges. In `test` and `audit`, nothing changes beyond the shared drift handling already there — verify the wording still fits the three new kinds.
- [ ] **Step 6: Run** `python3 scripts/plugin/check_skills.py` (OK) and `grep -L "learnings.md" skills/*/SKILL.md` (prints nothing).
- [ ] **Step 7: Commit** `feat(skills): project learnings and coverage matrix`.

### Task 4: Named test anti-patterns

**Files:**
- Create: `references/test-anti-patterns.md`
- Modify: `skills/test-code-audit/SKILL.md` (Phase 1, Phase 2 lenses 1–3, Phase 4 report grouping), `agents/qa-reviewer.md` (one line: findings may use the names)

- [ ] **Step 1: Write the reference**: a table name · sign · how to spot it · fix for exactly the ten names in spec §4 (Liar, Mirror, Mockery, Status-only, Giant, Inspector, Chain Gang, Sleeper, Ghost, Copycat). "How to spot it" gives a grep pattern where one exists (e.g. Sleeper: `waitForTimeout\(|sleep\(|setTimeout\(` in test files; Ghost: `\.(skip|only)\(|xit\(|it\.todo`), else the reading cue. Status-only cites QAP-TC-032. Liar links to the failure proof.
- [ ] **Step 2: Wire into test-code-audit**: Phase 1 runs the grep hints over the scoped tests as a cheap first pass and records counts in the report; lenses 1–3 tag each finding with a name (or `other`); Phase 4 report groups findings by name inside each severity.
- [ ] **Step 3: Run** `python3 scripts/plugin/check_skills.py` — OK.
- [ ] **Step 4: Commit** `feat(test-code-audit): named test anti-patterns with cheap grep pass`.

### Task 5: Example outputs

**Files:**
- Create: `skills/onboard/examples/project-profile.md`, `skills/task-qa/examples/task-file.md`, `skills/test-code-audit/examples/audit-report.md`, `skills/spec-audit/examples/actions.md`
- Modify: the four SKILL.md files — one line "Example: `examples/<file>.md`" in the step that writes the document.

**Interfaces:**
- Consumes: Task 2 examples check; formats from the SKILL.md files and from Task 3/4 references (the task file's verify log mentions a matrix upsert; the audit report groups by anti-pattern names).

- [ ] **Step 1: Write the four examples** for one invented project ("a small online shop: catalog, cart, checkout, accounts"; Next.js + Playwright + Vitest + MSW). Each follows its SKILL.md format section exactly, is under ~120 lines, uses `QAP-*` rule ids only (no other catalog prefix), and contains no real company, person or URL other than `localhost`.
- [ ] **Step 2: Add the pointers** and run `python3 scripts/plugin/check_skills.py` — OK; temporarily rename one example to confirm the check fails, then restore.
- [ ] **Step 3: Commit** `docs(skills): example outputs for onboard, task-qa, test-code-audit, spec-audit`.

### Task 6: Release 0.8.0 docs

**Files:**
- Modify: `.claude-plugin/plugin.json` (version `0.8.0`), `CHANGELOG.md` (new `## [0.8.0] — 2026-10-26` on top, same structure as 0.7.0: Added / Known limits), `README.md` (short sections on learnings and the coverage matrix; mention the new drift kinds), `docs/HANDOFF.md` (gates list unchanged; add one line on 0.8.0 state)

- [ ] **Step 1: Write the changes.** CHANGELOG Known limits must state: drift kinds are text matching; `rules-changed` needs git and ignores uncommitted edits; the matrix records what skills proved, it is not a CI gate.
- [ ] **Step 2: Run all gates:** `python3 -m unittest discover -s scripts/kb`, `-s scripts/plugin`, `-s skills/spec-audit/scripts`, `-s skills/onboard/scripts`, `-s skills/test-code-audit/scripts`; `python3 scripts/plugin/check_skills.py`; `claude plugin validate .` — all green.
- [ ] **Step 3: Commit** `release: 0.8.0 changelog, version bump`.
