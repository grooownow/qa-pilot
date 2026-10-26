# Changelog

All notable changes to qa-pilot. Versions follow `.claude-plugin/plugin.json`; each release is tagged `vX.Y.Z`.

To update an installed plugin: `/plugin` → marketplace qa-pilot → update, then `/reload-plugins`.

## [0.8.1] — 2026-10-26

### Changed
- **The book catalog no longer names its author.** It moved from its old folder to `knowledge/catalog/`, and its rule ids now start with `QAC-` instead of `SRK-` (the numbers are the same, e.g. `SRK-API-001` → `QAC-API-001`). The book is cited by its title only. Project override files (`docs/qa/rule-overrides.json`) written before this release keep working: `rules_pack.py` reads old ids in `disabled` and `decisions` as the new ones. A test checks that no tracked file names the author.
- `check_skills.py`: the "Not for" clause must name the sibling skill (`qa-pilot:<skill>`).
- `task-qa` plan now has a lessons step: a proposed AC, impact edge or test the owner rejects as wrong for the project is a lesson candidate.
- `project-audit` counts a `survived` probe and a Proof `none` matrix row for the same test as one finding.

### Fixed
- `lost-test` checked only the first code span of the Test cell and missed `` `path › name` `` written as one span. It now checks every span, and paths with `[slug]` or `(group)` segments and `.tsx` / `.jsx` file names count as paths.
- `new-test-dep` stopped reading a `pyproject.toml` dependency array at the `]` of an extra such as `pytest[cov]`, so the packages after it were missed.
- Test anti-pattern hints, after a run on a real suite of 349 test files: `getByTestId(` is no longer an Inspector hint (it was 1174 of 1197 hits, and qa-pilot itself recommends test ids). A `toHaveBeenCalled` hit is named Status-only when it is the last assertion of a UI test, Mockery otherwise. The Giant count is per file, and the empty-body hint says it also matches no-op callbacks.
- `write-tests` and `cover` say who writes the matrix row and when its Proof is `failed when broken`.

### Known limits
- Old ids stay in your own documents (task files, audit reports). Only the override file is translated.

## [0.8.0] — 2026-10-26

### Added
- **Project learnings.** qa-pilot keeps what it learned on a project in `docs/qa/learnings.md`: a finding the owner rejected as wrong for this project, a review finding that came back twice, a flaky test's root cause, a command quirk that cost a retry. At the end of a run the skill shows the proposed lines and writes them only after your yes, at most 3 per run. A duplicate is merged into the existing line. Every skill reads the file right after the profile. Your words in the session win over a lesson, a lesson wins over skill defaults, and a lesson that contradicts the profile or the repo is shown as a question. `onboard` lists lessons that name a path, command or dependency which no longer exists and asks whether to drop them. Format and rules: `references/learnings.md`.
- **Wider profile drift check.** `profile_drift.py` reports three more kinds:
  - `new-test-dep`: a known test package (Playwright, Cypress, Vitest, Jest, MSW, pytest, Stryker and others) is a dependency, but its name appears nowhere in the profile;
  - `rules-changed`: `CLAUDE.md`, `AGENTS.md`, Cursor rules, or a lint or test config was committed after the profile;
  - `lost-test`: a row of the coverage matrix names a test file that no longer exists.

  `onboard` refresh updates the profile lines for the first two. For `lost-test` it asks whether to drop the row or point it to the new path, and edits the matrix only after a yes.
- **Coverage matrix.** `docs/qa/coverage-matrix.md` is one table: feature, requirement, test, layer, in CI, proof, updated. `task-qa` verify, `cover`, `write-tests` and `test-code-audit` add or update rows for coverage they proved. `task-qa` plan, `spec-audit` and `project-audit` read it, so a requirement that already has a test is not planned twice. Proof is `failed when broken, <date>` only when the run saw the test fail; a test that was only read gets `distinguishing assertion` or `none`. Format: `references/coverage-matrix.md`.
- **Named test anti-patterns.** `references/test-anti-patterns.md` names ten: Liar, Mirror, Mockery, Status-only, Giant, Inspector, Chain Gang, Sleeper, Ghost, Copycat. Each has a definition and grep hints. `test-code-audit` runs the hints as a cheap first pass and groups its findings by name.
- **Routing.** Every skill description now has a "Not for … (use qa-pilot:X)" clause, so the agent picks the right skill. `check_skills.py` enforces the clause and checks that the `examples/` files a skill points to exist.
- **Example outputs** for the four skills that write documents: `skills/{onboard,task-qa,test-code-audit,spec-audit}/examples/*.md`.

### Changed
- The `spec-audit` description no longer names the author of the book the rule catalog comes from.

### Known limits
- The drift kinds are text matching. `new-test-dep` looks for a package name in the profile; it does not read how the package is used.
- `rules-changed` needs git and ignores uncommitted edits and files git does not track.
- The matrix records what the skills proved; it is not a CI gate and nothing fails when a row is stale. `lost-test` only notices a deleted or moved test file, not a test that was emptied.
- Learnings are written by the agent with your yes. Nothing deletes them automatically.

## [0.7.0] — 2026-10-20

### Added
- **Stale-profile check.** Before every run, `/qa-pilot:test` and `/qa-pilot:audit` compare `docs/qa/project-profile.md` with the repo. They flag:
  - a renamed or deleted test script;
  - a test directory or config that has moved;
  - a test layer the profile says CI runs, which no CI job runs any more (or the other way round);
  - a test command in CI that the profile does not mention.

  On a difference you get the list and one question: refresh only those lines of the profile, or go on as is. The check never blocks and takes well under a second. Workflows that only run by hand (`workflow_dispatch`) do not count as CI. In a monorepo it reads the CI files at the repository root.
- **`onboard` refresh mode.** When the check finds drift, `onboard` re-detects and rewrites only the drifted lines instead of rebuilding the profile. A freshly written profile must also pass the same check.
- `check_skills.py` now also checks that every script a skill runs (`$SKILL_DIR/…/scripts/*.py`) exists.
- **Failure proof of existing tests.** `/qa-pilot:audit tests` (and the test-code part of a project audit) no longer only reads tests. For a sample (by default 10 tests: the critical flows from the profile plus the ones that look like false greens), it breaks one line of the code under test, runs the test and restores the file. The new script `failure_probe.py` does this:
  - it runs the test on untouched code first (it must pass);
  - it keeps a backup, applies the mutation, runs the test again and restores the file byte for byte, also on timeout, Ctrl-C, SIGTERM or SIGHUP, and stops the test runner's child processes;
  - it moves the file's modification time forward on each write, so bytecode caches never run stale code;
  - it reports `killed` (the test can fail), `survived` (a proven false green, Critical), `baseline-red`, `timeout`, `interrupted` or `error`.

  If the project already has mutation testing set up (Stryker, mutmut, PIT), the audit uses its report instead. `write-tests` uses the same script when it spot-checks new tests.
- **Rule QAP-TC-032 (must): a UI test confirms an action by what the user sees.** For example, the deleted row is gone from the list, not "the DELETE returned 200". A response status may be checked in addition, never instead. Exceptions (no visible effect, or an API-level test) are allowed when the test says why in a comment. The rule is wired into test plans (expected results), the test-writing agent, the review loop and the test-code audit. QAP-TC-013 and the e2e waiting guide no longer suggest that a response status is enough for a UI test.

### Known limits
- The check compares commands, paths and CI jobs as text. It does not notice drift in conventions, critical flows or environments; re-run `onboard` for those.
- CI that starts tests through its own wrapper script is recognised only when the profile names the CI job.
- The failure probe needs a test command that runs one test, and a mutation chosen by the agent. A probe killed outright (SIGKILL) leaves the mutation in place with a `.qa-probe-orig` backup; the next probe refuses to start until it is restored.

## [0.6.0] — 2026-10-19

### Changed
- **Three commands instead of nine.** Only `/qa-pilot:onboard`, `/qa-pilot:test` and `/qa-pilot:audit` are in the slash menu. The other skills are internal (`user-invocable: false`), and the commands call them for you.
- **`/qa-pilot:test [context]`** reads the context and picks the mode itself:
  - a ticket with no code changes → a QA plan for the task;
  - a diff on the branch → verification of the change and the missing tests;
  - "in the browser" or a URL → exploratory browser testing;
  - "cover" → tests for what you shipped;
  - a path to a plan → writes the tests from it.

  When the signals conflict it asks you once. When there is no information it picks the most useful action itself.
- **`/qa-pilot:audit [context]`** picks the audit:
  - nothing → a whole-project audit;
  - a feature, spec or ticket → a requirements audit;
  - "tests" or "flaky" → a test-code audit.
- **Renamed:** the old `audit` skill is now `test-code-audit`, and the old `test` skill is now `explore`.

### Fixed
- The `task-qa` description was longer than 1024 characters. Claude Code dropped it silently, so the skill had no trigger.

### Added
- `scripts/plugin/check_skills.py`, a validation gate. It checks that every skill's name matches its directory, that its description is at most 1024 characters, and that every referenced skill and file exists.

## [0.5.0] — 2026-10-19

### Added
- **Per-task QA step (`task-qa`):**
  - `plan`, before coding: checks the acceptance criteria, builds an impact map (what else the change reaches, with file:line references), and lists which tests to change or add;
  - `verify`, after coding: reconciles the diff with the plan, asks "intended?" about unplanned behaviour changes, proves coverage (test + exact assertion + layer that runs in CI), and writes up to 5 missing tests under strict guards. Bug tests stay red, and code fixes always go to the owner;
  - a ready snippet for feature-workflow orchestrators: `references/orchestrator-integration.md`.
- **Whole-project audit (`project-audit`):** rates test-framework maturity, confirms 3–7 critical flows, audits each flow, samples the test code, and writes one roadmap (framework blockers → must-have tests → questions → highlights).
- **Web failure patterns.** 10 must-check patterns are checked for every entity with a lifecycle:
  - modify vs delete;
  - double submit;
  - a mutation with no error handling;
  - a modal that closes before its request finishes;
  - a failed refetch that wipes shown data;
  - a 409 the user never sees;
  - permissions checked only in the UI;
  - a nested id not checked against its parent;
  - a session that expires mid-action;
  - routes that depend on a mode or flag.

  There are also 8 highlight-only patterns and 6 web invariants that serve as expected results when a spec is silent.
- **No over-testing.** Results are bucketed:
  - **Must**: always covered;
  - **Should**: at most 8;
  - **Highlight**: one line, no test;
  - **Question**: for the owner.

  Risks removed by the owner's scope filters stay visible under "Suppressed by your filters".
- **Machine-readable output.** `spec-audit` writes `-actions.json` next to `-actions.md`, and `score.py` validates, scores and compares runs.
- **Own knowledge domains: 141 rules from open sources.** Each rule was checked against its source by an independent agent:
  - security: OWASP ASVS 5.0, API Top 10;
  - test-code quality: Playwright, ESLint plugins, test smells;
  - HTTP APIs: RFC 9110/9457, Zalando;
  - authentication: NIST 800-63B-4;
  - test strategy: ISTQB v4;
  - AI features: OWASP LLM Top 10.
- **Onboard records more.** The profile now captures test-framework maturity and critical flows.

### Changed
- **Book rules are checked against standards.** Rules from the book carry `authority` (standard / industry practice / vendor guideline / author opinion) and `external_check`. 427 must and deterministic rules were checked against RFC, W3C, ISTQB, OWASP and NIST. In audit packs an author opinion is never a hard `must`, and remaining conflicts are flagged.
- **Shared test-delta rules.** Depth, buckets, the three proofs of coverage and the auto-test guard now live in `references/test-delta.md`, which `plan-tests`, `cover`, `task-qa` and `spec-audit` all follow.

### Fixed
- **False-positive book rules corrected:** content negotiation (RFC 9110 §12.5.1), boundary values (ISTQB allows 2-point BVA), and the full-name field. Numeric "myths" are marked as author opinion.

### Known limits
- On the TDK eval, `spec-audit` 0.5 scored 14 of 21, the same as 0.4.0.
  - **Gained:** the two previous misses are now found, and new real bugs were found too.
  - **Lost:** four spec-specific checks.
- Fixes for this (a mandatory spec walk, and "a mock of the deciding function is not coverage") are in place but not re-measured. Details: `docs/superpowers/notes/2026-10-19-spec-audit-0.5-eval.md`.

## [0.4.0] — 2026-10-19

### Changed (`spec-audit`, after a review of a real project run)
- **Proof of absence.** "Not covered", "silent" and "no guard" claims must cite an untruncated search.
- **Proof of coverage.** "Covered" needs a matching assertion in a test layer that runs in CI.
- **Prescriptions.** Every prescribed test has a level, a target and a sourced expected result.
- **Owner scope filters** are asked for up front and can be saved.
- **The primary output** is an agent-executable action list, `-actions.md`.
- **Onboard records** which test layers CI runs and how errors reach the user.

## [0.3.0] — 2026-10-12

### Added
- **`spec-audit` skill.** It audits requirements and test plans against a catalog of 1137 rules distilled from a QA handbook, plus qa-pilot's own rules, and cross-checks every claim against the code and tests.
- **Knowledge base** in `knowledge/`: the rule catalog and its summary. The book text itself is not included (copyright).

## [0.2.0 – 0.2.4] — 2026-07

### Added
- **`cover` skill:** covers new code with tests in one command (0.2.0).
- **Docs:** the user guide, the skills-at-a-glance table, a test-id-first locator strategy, and attribution.

## [0.1.0] — 2026-07-05

### Added
- **First release.** Skills: `onboard`, `audit`, `plan-tests`, `write-tests` and `test`. Subagents: `test-author`, `qa-reviewer` and `mechanical-editor`. Playwright MCP and a reference library.
