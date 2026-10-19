---
name: onboard
description: One-time qa-pilot setup for a project - analyzes the stack, test frameworks, conventions, CI, and existing rules, asks the user what cannot be detected, and writes docs/qa/project-profile.md, the persistent project memory every other qa-pilot skill reads. Use when starting qa-pilot on a new project, when the user says "set up qa-pilot", "onboard this project", "create project profile", or when another qa-pilot skill reports the profile is missing or stale.
---

# Onboard

Build `docs/qa/project-profile.md` — the single document that lets every other
qa-pilot skill work WITHOUT re-scanning the repo (the main token saver of this
plugin). Run once per project; re-run only when the stack or conventions change
materially.

Create a todo per phase. Read `../../references/model-routing.md` (relative to
this skill's base directory) before dispatching any subagent.

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
- Team intent: what hurts most today (flaky tests? no coverage? slow suite?) —
  this seeds priorities for `qa-pilot:audit`.
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
## Error plumbing   — global error/notification handling: file, which statuses/bodies toast, which stay silent
## Commands         — exact commands: run tests (all/one file), typecheck, lint, start dev server (+port)
## Conventions      — locator policy, fixtures/POM approach, tagging, naming, imports; LINK to repo's own docs rather than duplicating them
## Environments     — safe-to-test URLs, forbidden environments, credential mechanism
## Tracker & access — tracker of record, connected MCPs/CLIs, missing access
## Framework maturity — table: area · present / partial / missing · evidence (path or "searched: … → 0")
## Critical flows   — 3–7 flows, one line each: name · entry route/screen · why it is critical (confirmed by the user)
## Product traits   — fenced yaml: platform, api_style, has_payments, has_auth, has_user_uploads, i18n, rtl, regulated, has_ai_features (format: skills/spec-audit/SKILL.md)
## Priorities       — what the team wants improved first
## Open gaps        — unanswered questions, marked blocking or non-blocking
```

Keep it under ~180 lines: link to the repo's own docs instead of copying them.
Facts only — no recommendations (those belong to `qa-pilot:audit`).

## Phase 4 — Verify & hand off

- Sanity-check the profile's commands by running the cheapest one (e.g. list
  tests) — a profile with wrong commands poisons every later skill. If the
  check fails, fix before finishing: re-detect from CI config / package
  scripts, or ask the user for the correct command.
- Show the user a 5-line summary of what was written and where.
- Suggest the natural next step: `qa-pilot:audit` for an existing test codebase,
  or `qa-pilot:plan-tests` if they came with a specific feature.
