# qa-pilot — Design

**Date:** 2026-07-05
**Status:** living document — v1 approved 2026-07-05; `cover` skill added in 0.2.0

## What

A Claude Code **plugin** that turns Claude into a QA copilot for an existing project:
audit the test codebase, design test scenarios for features, write Playwright tests,
and run exploratory browser testing — with strict quality gates and token economy
tuned for a Claude Pro ($20) subscription.

Target user: a QA engineer (manual + automation) new to AI agents. Playwright is the
assumed e2e framework; everything else is discovered from the project at runtime.

## Distribution

Public GitHub repo `grooownow/qa-pilot` that is both a plugin and its own marketplace:

```
/plugin marketplace add grooownow/qa-pilot
/plugin install qa-pilot@qa-pilot
```

Skills get the `qa-pilot:` namespace automatically. Updates propagate via
`/plugin marketplace update`. Bundles the official `@playwright/mcp` (pinned version)
via `.mcp.json` so browser tools work out of the box.

## Architecture

```
qa-pilot/
├── .claude-plugin/
│   ├── plugin.json          # manifest
│   └── marketplace.json     # makes the repo installable directly
├── .mcp.json                # @playwright/mcp, pinned
├── skills/
│   ├── onboard/SKILL.md     # project profiling → docs/qa/project-profile.md
│   ├── audit/SKILL.md       # test-codebase audit → report + refactoring plan → execute
│   ├── cover/SKILL.md       # everyday orchestrator: changed code → gap map → plan → write
│   ├── plan-tests/SKILL.md  # feature → test scenarios (cost/value tradeoff)
│   ├── spec-audit/          # requirements & test plans vs the rules catalog (+ scripts/)
│   ├── write-tests/SKILL.md # scenarios → Playwright tests per project conventions
│   └── test/SKILL.md        # exploratory browser testing via Playwright MCP
├── agents/
│   ├── test-author.md       # sonnet — writes test code from a precise brief
│   ├── qa-reviewer.md       # inherit — adversarial reviewer, narrow lens per dispatch
│   └── mechanical-editor.md # haiku — bulk mechanical edits (renames, moves)
├── references/              # shared docs, loaded on demand by skills
│   ├── quality-rules.md     # no-slop, complexity check, self-review contract
│   ├── model-routing.md     # token economy: which model/agent for which phase
│   ├── review-loop.md       # parallel adversarial review→fix→re-review protocol
│   ├── e2e-patterns.md      # Playwright patterns: fixtures, POM-via-fixtures, waiting, mocking
│   ├── flakiness-catalog.md # known flakiness sources + fixes + quarantine pattern
│   └── browser-hygiene.md   # dev-server lifecycle, one-page rule, memory caps
├── knowledge/               # QA rules catalog: surkov/ (book-derived), qa-pilot/ (own rules)
└── README.md                # install + quickstart for an AI-agent beginner
```

## The skills

Every skill follows the same contract: numbered phases, todo per phase, reads
`docs/qa/project-profile.md` first (or tells the user to run `qa-pilot:onboard`),
persists progress to files as it goes (survives session limits); every skill
that writes or changes code applies `references/quality-rules.md` before
claiming done.

1. **onboard** — one-time per project. Detects stack, test framework(s), conventions,
   CI lanes, existing rules (CLAUDE.md/AGENTS.md/docs). Asks the user what it cannot
   detect (environments, credentials, tracker of record). Output:
   `docs/qa/project-profile.md` — the persistent memory all other skills read instead
   of re-scanning the repo (major token saver).
2. **audit** — deep review of the existing test codebase: anti-patterns, copy-paste,
   flakiness sources, over-complexity, dead tests. Output: `docs/qa/audit-report.md`
   with severity-ranked findings (each verified against real code before reporting)
   and `docs/qa/refactoring-plan.md` with ordered, independently-shippable steps.
   Can then execute the plan step-by-step, review-loop after each step.
3. **plan-tests** — input: a feature (description, ticket, diff, or URL). Explicitly
   negotiates depth-vs-breadth-vs-cost with the user (smoke / standard / thorough),
   asks for missing context or access (MCP, credentials) instead of guessing. Output:
   `docs/qa/test-plans/<feature>.md` — scenarios with priority, tier (mocked/real),
   data needs, and out-of-scope notes.
4. **write-tests** — turns a test plan (or direct request) into Playwright tests that
   match the project's own conventions from the profile. Dispatches test-author
   agent(s) with precise briefs; runs the tests; mandatory review loop; proves tests
   can fail (no false-green).
5. **cover** (added in 0.2.0) — the everyday orchestrator after new code lands:
   scope the change (from description/ticket/PR or branch diff) → map coverage
   gaps against existing tests (including green-but-outdated tests of modified
   behavior) → invoke plan-tests for the gaps → invoke write-tests → close the
   loop with gates and a covered-before/after summary.
6. **test** — exploratory/manual testing in a real browser via Playwright MCP: walks
   scenarios, records findings with repro steps, optionally fixes low-risk bugs
   (guarded), re-verifies after fixes. Output: `docs/qa/test-sessions/<date>-<slug>.md`.

7. **spec-audit** (added in 0.3.0) — audits requirements and test plans against
   the `knowledge/` catalog: product traits filter the rules (`rules_pack.py`), a
   low-noise lint flags vague/unfinished wording (`spec_lint.py`), cluster agents
   apply lenses (state models, decision tables, BVA, contradictions, error states)
   and cross-check every claim against the code and existing tests; the main
   session verifies P1s and calibrates severity. Output:
   `docs/qa/spec-audit/<date>-<slug>.md`. Design:
   `docs/superpowers/specs/2026-10-12-spec-audit-skill-design.md`.

## Cross-cutting rules (in every skill)

- **Token economy:** phase→model routing (haiku for mechanical, sonnet for authoring,
  main/strongest model only for judgment: planning, review verdicts, architecture).
  Read the profile, not the repo. Persist state to files; assume the session may die.
  Prefer one high-quality pass over many cheap retries.
- **Quality gates:** simplest-solution check (complexity challenge before writing),
  no junk comments (comments only for non-obvious constraints), no dead code,
  evidence before claims (run it, show output), mandatory self-review loop
  (parallel reviewer agents, verify findings against real code, fix, re-review, ≤3 rounds).
- **Ask, don't guess:** missing credentials, environments, tracker access, product
  intent → ask the user explicitly and list exactly what's needed.
- **Project rules win:** the target repo's CLAUDE.md/AGENTS.md/docs override qa-pilot
  defaults on any conflict.

## Provenance

Patterns generalized from the author's prior QA-automation skill work and
production Playwright conventions (fixture-injected POM, tier tags,
flaky-quarantine registry, cleanup fixtures).

## Out of scope (v1)

Nightly scheduled QA runs, performance/load testing skill, non-Playwright frameworks
(Cypress etc.), CI pipeline generation. The architecture leaves room: each is a new
skill in `skills/` later.
