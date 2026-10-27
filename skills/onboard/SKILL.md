---
name: onboard
description: One-time qa-pilot setup for a project - analyzes the stack, test frameworks, conventions, CI, and existing rules, asks the user what cannot be detected, and writes docs/qa/project-profile.md, the persistent project memory every other qa-pilot skill reads. Use when starting qa-pilot on a new project, when the user says "set up qa-pilot", "onboard this project", "create project profile", or when another qa-pilot skill reports the profile is missing or stale. Not for QA work itself (use qa-pilot:test or qa-pilot:audit).
---

# Onboard

Build `docs/qa/project-profile.md` — the single document that lets every other
qa-pilot skill work WITHOUT re-scanning the repo (the main token saver of this
plugin). Run once per project; re-run only when the stack or conventions change
materially.

**Refresh mode.** When `/qa-pilot:test` or `/qa-pilot:audit` sends you here because
`profile_drift.py` reported drift, do not rebuild the profile. Re-detect only the
drifted facts (Phase 1 checks for those commands, paths and CI jobs), edit just
those lines, update the `Generated … on <date>` line, show the user the diff, and
finish with the Phase 4 drift check. Ask questions only when the repo cannot
answer them. Per drift kind:

- `new-test-dep`: update Test landscape and Framework maturity with the new package.
- `rules-changed`: re-read that file, update Conventions, and show the owner any
  lesson in `docs/qa/learnings.md` that it contradicts.
- `lost-test`: not a profile fact. Tell the owner which matrix row lost its test
  and offer three options: drop the row, point it to the new test path, or keep it
  as history (append ` (removed <YYYY-MM-DD>)` to its Test cell; the drift check
  then skips it) (`../../references/coverage-matrix.md`). Edit the matrix only after a yes.

A refresh also re-runs the harness scan and the fit estimate (both cheap: no new scanning beyond
Phase 1) and rewrites `## Harness` in the profile and `## qa-pilot fit` / `## Harness proposals` in
`docs/qa/strategy-check.md`. The strategy check itself is re-run only when the owner asks, or when the drift
check reported `new-test-dep` or `rules-changed`; otherwise keep its section and say it was not re-run.

In a full or refresh run, also check `docs/qa/learnings.md` if it exists
(`../../references/learnings.md`): list lessons that name a path, command or
dependency that no longer exists and ask whether to drop them; over 60 lines,
propose merges. Delete nothing without a yes.

Create a todo per phase.

Also read `docs/qa/learnings.md` if it exists, per `../../references/learnings.md`.

Read `../../references/model-routing.md` (relative to this skill's base directory) before dispatching any
subagent.

## Phase 1 — Detect (no questions yet)

Discover from the repo itself. Prefer cheap, targeted reads (manifests, configs,
a few representative tests) over crawling. For a large/unfamiliar repo, dispatch
ONE Explore-type subagent with this checklist instead of scanning inline:

- **Stack:** language(s), package manager, monorepo layout, frameworks.
- **Test landscape:** frameworks present (Playwright? unit runner? component
  tests?), where tests live, how many, how they are run (exact commands from
  package.json / CI), which suites exist (smoke/regression/lanes).
- **Playwright specifics** (if present): config file(s), projects, fixtures,
  page objects, tagging, storageState/auth approach, CI reporters.
- **Conventions & rules:** CLAUDE.md, AGENTS.md, docs/, lint rules that
  constrain tests, PR/commit policy.
- **Gates:** the exact commands for tests, typecheck, lint — and whether CI runs
  more.
- **Which test layers CI actually runs:** read the CI workflow files. For each
  layer (unit, component, Storybook/interaction, e2e projects, visual, backend
  suites), record whether a CI job runs it, and on which trigger. A layer that
  exists locally but not in CI does not count as coverage.
- **Error plumbing:** how API failures reach the user. Look for:
  - global query/mutation error subscribers;
  - interceptors;
  - toast/notification modules;
  - error boundaries.

  Record which statuses and response bodies produce a message and which stay
  silent. Audits need this before they can call anything "silent".
- **Framework maturity** (the "test framework" in the broad sense): for each
  area record present / partial / missing with one line of evidence:
  - test layers and runners (unit, component, API/contract, e2e, visual);
  - CI gates: which layers block a merge or deploy; smoke/regression sets;
  - mocking strategy: a network mock layer, fixtures, factories;
  - test data and isolation: seeding, cleanup, per-test accounts;
  - selector convention: testids, roles, shared constants;
  - auth in tests: storageState, API login;
  - flaky handling: retries, quarantine, tracking;
  - coverage or reporting tooling;
  - test-code linting (eslint-plugin-playwright/jest/testing-library).

  `qa-pilot:project-audit` turns the gaps into a roadmap. Rules that back
  each area: `../../knowledge/qa-pilot/rules/test-code.json` and
  `test-strategy.json`.
- **Harness** (how the project's own workflow could call qa-pilot): search cheaply, by file names and headings,
  not whole files:
  - agent workflows: `.claude/skills/*/SKILL.md`, `.claude/commands/*.md`, `.claude/agents/*.md`, `AGENTS.md`,
    `CLAUDE.md` sections that describe a task flow, `.cursor/rules/**`, `.github/copilot-instructions.md`;
  - hooks: `hooks` in `.claude/settings*.json`, git hooks (`.husky/`, `lefthook.yml`, `.pre-commit-config.yaml`);
  - review and quality steps in CI: review bots (CodeRabbit, Danger), required checks, PR templates with a QA section.

  For each workflow found, record its phases (from headings) and whether a phase matches a qa-pilot point:
  "before the plan is approved" is `task-qa plan`; "after implementation / tests, before review or PR" is
  `task-qa verify`; "periodic / release" is `/qa-pilot:audit`. Nothing found means qa-pilot is called `manually`.
  The snippets to propose are in `../../references/orchestrator-integration.md`.
- **UI library and UI tests** (grep-cheap, no budget knob): a component library at `packages/ui`,
  `src/components/ui`, a shadcn `components.json` (its `aliases.ui` path), or a design-system package; Storybook
  (`.storybook/`); story files (`*.stories.*`) counted by `ls`/`grep -l`; stories with a `play` function
  (`grep -l "play"` over the story files); the runner (Storybook Vitest addon, Storybook test-runner, Playwright
  component tests, or none); whether a CI workflow runs it. Count components as the component files in the
  library path. No library path found means `No UI library found.` and nothing else is looked for. Strategy and
  atom/composition split: `../../references/ui-testing.md`. The result goes to `## UI state` in
  `docs/qa/strategy-check.md` (below) and to the `component/UI` row of `Test layers`.
- **Trackers & environments:** references to issue trackers, deployment URLs,
  env files (never read secret VALUES — note only which env vars exist).

## Phase 2 — Ask what cannot be detected

Batch ALL questions in one message (see quality-rules rule 5). Typical gaps:

- Which environment may tests/browser sessions safely run against? Any
  environment that must NEVER be touched (production)?
- Where do test credentials come from? (Ask for the mechanism, not the secrets.)
- Tracker of record (GitHub Issues / Linear / Jira) and whether an MCP or CLI for
  it is connected. If access is needed but absent, name the exact missing piece
  and how to connect it.
- **Critical flows:** the 3–7 user flows whose failure hurts most (money,
  data loss, a blocked core job). Propose them from routes, entities and docs;
  the user confirms. Audits put any P2 on these flows into Must.
- **Budget:** how to spend, one choice (`../../references/budget.md`):
  `economy` (smallest depth, asks before any run over ~150k tokens),
  `standard` (default), `thorough` (deeper audits, larger probe samples).
  Also: should heavy skills report their spend estimate (`report_spend`)?
- Team intent: what hurts most today (flaky tests? no coverage? slow suite?) —
  this seeds priorities for `/qa-pilot:audit`.
- **Product traits** (used by `qa-pilot:spec-audit` to drop rules that cannot
  apply): platforms (web / mobile-web / pwa / ios / android / desktop / game),
  API style (rest / graphql / soap / server-actions / rpc), payments, accounts
  & login, user file uploads, more than one locale, RTL, regulation (gdpr /
  hipaa / pci / eaa). Pre-fill what Phase 1 detected; ask only to confirm.
- Anything Phase 1 found contradictory (e.g. docs claim a convention the code
  doesn't follow — ask which is the truth).

If the user cannot answer something, record it in the profile under
**Open gaps** — do not guess.

## Phase 3 — Write the profile

Write `docs/qa/project-profile.md` (create `docs/qa/` if needed). Sections:

```markdown
# QA Project Profile
> Generated by qa-pilot:onboard on <date>. Other qa-pilot skills read this file
> instead of re-scanning the repo. Re-run qa-pilot:onboard if it goes stale.

## Stack            — language, PM, layout, app type, how to run the app locally
## Test landscape   — frameworks, locations, counts, suites/lanes
## Test layers      — table: layer · path(s) · command · runs in CI (job + trigger) or not · being phased out?
                        Include a `component/UI` row when a UI library or stories exist (stories and `play` tests, runner, CI job); omit it when there is no UI library.
## Error plumbing   — global error/notification handling: file, which statuses/bodies toast, which stay silent
## Commands         — exact commands: run tests (all/one file), typecheck, lint, start dev server (+port)
## Conventions      — locator policy, fixtures/POM approach, tagging, naming, imports; LINK to repo's own docs rather than duplicating them
## Environments     — safe-to-test URLs, forbidden environments, credential mechanism
## Tracker & access — tracker of record, connected MCPs/CLIs, missing access
## Framework maturity — table: area · present / partial / missing · evidence (path or "searched: … → 0")
## Critical flows   — 3–7 flows, one line each: name · entry route/screen · why it is critical (confirmed by the user)
## Product traits   — fenced yaml: platform, api_style, has_payments, has_auth, has_user_uploads, i18n, rtl, regulated, has_ai_features (format: skills/spec-audit/SKILL.md)
## Priorities       — what the team wants improved first
## Harness         — facts only. Table: workflow · path · phases · fit point (or "none fits"). Then one line: `How qa-pilot is called here: orchestrator <name>` or `manually`. Paths in code spans are checked by the drift script
## Budget          — fenced yaml: mode (economy|standard|thorough, default standard), report_spend (yes|no)
## Open gaps        — unanswered questions, marked blocking or non-blocking
```

Keep it under ~180 lines: link to the repo's own docs instead of copying them.
Facts only — no recommendations (those belong to `/qa-pilot:audit`).

Example: `examples/project-profile.md`.

### Recommendations go to `docs/qa/strategy-check.md`

The profile holds facts; everything advisory goes to a second file, `docs/qa/strategy-check.md`, which the
profile links to under Open gaps or Priorities. Rewrite it whole on each run so stale findings disappear, and
give it its own line `Generated by qa-pilot:onboard on <date>`. Sections, in this order:

```markdown
## qa-pilot fit          — written now (below)
## Harness proposals     — written now (below)
## Strategy check        — written by Phase 3b (below), only when it runs
## UI state              — filled by UI detection, only when it runs
```

**`## UI state`.** One line from the UI detection in Phase 1, in exactly this form:
`UI library: <path> · <N> components · <M> with interaction tests · runner <name|none> · in CI <yes|no>`.
When no library was found, the line is `No UI library found.` UI detection runs on every onboard (it is cheap), so
the line is always rewritten; the other two sections keep their rule above.

On a run that does not fill the last two, keep their previous text if the file has it; otherwise omit the heading.

**`## qa-pilot fit`.** One grade, then one line per limiting factor: factor, effect on qa-pilot, what would fix
it. No new scanning: the inputs are what Phase 1 and 2 already produced.

| Factor | Effect when missing |
|---|---|
| a runnable test command | verify and the failure proof only read tests, never run them |
| tests run in CI | coverage claims are "local only"; a test can rot unnoticed |
| a test-id convention (or the hard rule accepted) | new tests need component edits; more fallback locators |
| a network-mock seam | UI tests need a real backend; slower, flakier |
| a harness fit point | plan/verify happen only when someone remembers |
| tracker access | AC come from pasted text only |
| answered critical flows | audits cannot prioritise; everything is "standard" |
| open blocking gaps | named one by one |

Grade: **full** = no factor missing; **partial** = 1-3 missing and a runnable test command exists;
**limited** = no runnable test command, or 4 or more missing.

**`## Harness proposals`.** For each workflow with a fit point: the exact step to add and the snippet from
`../../references/orchestrator-integration.md`, adapted to the workflow's phase names. Proposals and snippets
live only in this file and in the closing message. Never edit the project's own workflow files; the owner pastes.
With `manually`, write the minimal habit instead (see Phase 4) and say what the fit estimate loses: nobody calls
verify automatically.

**`## Strategy check`.** Written by Phase 3b below.

## Phase 3b — Strategy check

Runs after the profile is written, before Phase 4. It writes only `## Strategy check` in
`docs/qa/strategy-check.md` (rewrite the whole file with the other sections, keeping their text; see above). Budget:
about 30-50k tokens on top of onboard. Read the mode per `../../references/budget.md`: in `economy`, skip the
3-5 sample test files per layer, check from the profile, the rules files and directory listings only, and say so
in the section ("sample files not read: economy mode") and under "Not done (budget)".

**Empty project** (no test files, or only framework boilerplate; nothing to check). Say so, mark `Framework
maturity` as mostly missing (already in the profile) and point to `/qa-pilot:audit` for the roadmap.

**E2e skeleton offer.** Whenever the project has no e2e layer (empty, or unit tests only), offer a skeleton once:
- Framework: the e2e runner already in the dependencies, else Playwright.
- If an e2e runner with its own config already exists, offer nothing: report the gaps as findings instead.
- On a yes, invoke `qa-pilot:write-tests` in mode `bootstrap`. It shows the exact install list first and installs only after an explicit yes to that list (`../../references/e2e-patterns.md`; a yes covers that list only, anything added later is asked again; never global, never CI).
- It adds the framework config, an auth fixture, a base page object, the cleanup fixture, a test-id constants file, one smoke test on the first critical flow and the package script. CI is not touched; the closing message says which job to add.
- On a no, write nothing and move on.

**Project with tests.** Inputs: the maturity table and `Test layers` from the profile, the project's own test
rules (the docs and `CLAUDE.md` sections linked under Conventions), and 3-5 test files per layer. Five checks:

1. **Layer fit.** Logic-heavy modules (services, utils, reducers) with no unit tests; a UI component library with no component tests; everything only in e2e. Rules: QAP-TC-030, QAP-TS-014.
2. **Own rules vs qa-pilot rules.** A project rule that contradicts a must rule (for example "use CSS selectors" against QAP-TC-028, "waitForTimeout is fine" against QAP-TC-026) is a finding with both texts. A missing rule area (no e2e rules, no locator policy, no test-data rule) is a finding. If the project has its own complete rules, record "project rules adopted" and list only the contradictions; qa-pilot then works by the project's rules (`../../references/quality-rules.md`, rule 6).
3. **CI.** Layers in `Test layers` that CI does not run. No rule id: write "none (CI line)". The finding is the same as the closing line below.
4. **Test data and isolation.** Shared accounts, no cleanup, suites that depend on order. Rule: QAP-TC-020; the fix is in `../../references/e2e-patterns.md` (Fixtures & cleanup, Test data management).
5. **Accessibility.** No automated a11y check anywhere (axe in e2e, `addon-a11y` in Storybook) on a product with public UI. No rule id: write "none (a11y policy)". The fix is the "Accessibility check" in `../../references/e2e-patterns.md`.

Write at most 8 findings under `## Strategy check`, each on one line:
`area · what we saw (path) · rule id · the one change that fixes it`. Pick the 8 with the largest effect when
there are more, and say how many were left out. Then one line per layer (`unit`, `component`, `e2e`, `visual`,
`a11y`): `<layer> — ok | weak | missing`. If any layer in `Test layers` does not run in CI,
end the section with the line `Not in CI: <layers>. These tests count as local only.`

Example: `examples/strategy-check.md`.

## Phase 4 — Verify & hand off

- Sanity-check the profile's commands by running the cheapest one (e.g. list
  tests) — a profile with wrong commands poisons every later skill. If the
  check fails, fix before finishing: re-detect from CI config / package
  scripts, or ask the user for the correct command.
- Run the drift check on the profile you just wrote (`SKILL_DIR` is this
  skill's base directory):
  `python3 "$SKILL_DIR/scripts/profile_drift.py"`. It must exit 0. Every line it
  prints is a claim in the profile that the repo does not back, or a repo change
  the profile does not know about. Fix the profile, or if the script misread a correct claim, say so to
  the user. `test` and `audit` run the same check before every run, so a profile
  that fails here will nag the user every time.
- Show the strategy check verdict (findings and the layer line) at the end of the summary when Phase 3b ran.
- Show the user a 5-line summary of what was written and where, then the fit grade with its limiting factors and
  the harness proposals once, with the snippet to paste. If the profile says `manually`, give the minimal habit
  instead: before coding `/qa-pilot:test <ticket>` (plan), after coding `/qa-pilot:test` (verify), and run the
  regression set locally before the PR. That is enough for qa-pilot to work.
- When a UI library was found, close with: `UI library: N components, M with interaction tests; run /qa-pilot:audit ui for the gap list.` (the deep audit is Pro). When none was found, say `No UI library found.` and nothing more.
- Suggest the natural next step: `/qa-pilot:audit` for the big picture of an existing project,
  or `/qa-pilot:test <feature or ticket>` if they came with a specific task.
