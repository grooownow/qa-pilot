# Changelog

All notable changes to qa-pilot. Versions follow `.claude-plugin/plugin.json`; each release is tagged `vX.Y.Z`.

To update an installed plugin: `/plugin` → marketplace qa-pilot → update, then `/reload-plugins`.

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
- **Book rules are checked against standards.** Rules from the Surkov book carry `authority` (standard / industry practice / vendor guideline / author opinion) and `external_check`. 427 must and deterministic rules were checked against RFC, W3C, ISTQB, OWASP and NIST. In audit packs an author opinion is never a hard `must`, and remaining conflicts are flagged.
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
- **`spec-audit` skill.** It audits requirements and test plans against a catalog of 1137 rules distilled from R. Surkov's QA handbook, plus qa-pilot's own rules, and cross-checks every claim against the code and tests.
- **Knowledge base** in `knowledge/`: the rule catalog and its summary. The book text itself is not included (copyright).

## [0.2.0 – 0.2.4] — 2026-07

### Added
- **`cover` skill:** covers new code with tests in one command (0.2.0).
- **Docs:** the user guide, the skills-at-a-glance table, a test-id-first locator strategy, and attribution.

## [0.1.0] — 2026-07-05

### Added
- **First release.** Skills: `onboard`, `audit`, `plan-tests`, `write-tests` and `test`. Subagents: `test-author`, `qa-reviewer` and `mechanical-editor`. Playwright MCP and a reference library.
