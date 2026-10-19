# qa-pilot

A QA copilot plugin for [Claude Code](https://code.claude.com). Install it into
any existing project and Claude becomes a disciplined QA engineer: it audits
your test codebase, covers new code with tests in one command, designs test
scenarios, writes Playwright tests, and runs exploratory testing in a real
browser — with strict quality gates and token economy tuned for subscription
plans (works fine on Claude Pro).

Built for QA engineers who are new to AI agents: every skill asks when it's
missing context, persists its work to files in your repo, and never claims
something works without showing the evidence.

## Install

Prerequisites: [Claude Code](https://code.claude.com/docs/en/overview) and
Node.js (for the bundled Playwright MCP browser tools).

Inside Claude Code, run:

```
/plugin marketplace add grooownow/qa-pilot
/plugin install qa-pilot@qa-pilot
```

Restart Claude Code when prompted. That's it — the skills, subagents, and
browser tools are now available in every project.

To update later: `/plugin marketplace update qa-pilot`.

## Quickstart

In your project, start with:

```
/qa-pilot:onboard
```

This analyzes your stack and conventions, asks you a few questions, and writes
`docs/qa/project-profile.md` — the persistent memory all other skills reuse
(so they don't burn tokens re-scanning your repo every session).

## The everyday command

Shipped a new feature or changed an existing one? One command closes the
testing loop — it detects what changed, checks what's already covered, plans
the missing scenarios, writes the tests, and reviews them:

```
/qa-pilot:cover <feature, ticket, PR — or nothing, to scope from your branch diff>
```

The natural rhythm: **onboard → audit → refactoring plan** once per project,
then **cover** for every feature you build after that, with `test` for
hands-on verification anytime.

## All skills at a glance

| Command | What it does | Writes to your repo |
|---|---|---|
| `/qa-pilot:onboard` | One-time setup: profiles your stack, test frameworks, conventions, environments | `docs/qa/project-profile.md` |
| `/qa-pilot:audit` | Deep health check of the test codebase: flakiness, false-greens, duplication → findings + ordered refactoring plan, executable step by step | `docs/qa/audit-report.md`, `docs/qa/refactoring-plan.md` |
| `/qa-pilot:cover` | The everyday orchestrator: what changed → coverage gaps → plan → write → review | `docs/qa/test-plans/<feature>.md` + test files |
| `/qa-pilot:plan-tests` | Feature → prioritized test scenarios with an explicit depth/cost tradeoff (smoke / standard / thorough) | `docs/qa/test-plans/<feature>.md` |
| `/qa-pilot:spec-audit` | Audits requirements & test plans against a 1100+ rule QA catalog (test design, requirements quality, a11y, API, UX…), cross-checked against your code → which test cases are missing, what's ambiguous, what the owner must decide | `docs/qa/spec-audit/<date>-<slug>.md` |
| `/qa-pilot:task-qa` | The QA step of one task: `plan` (AC check, impact map, test delta) before coding; `verify` (diff vs plan, "intended?" questions, proof of coverage, up to 5 guarded tests) after | `docs/qa/tasks/<ticket>.md` (+ tests in verify) |
| `/qa-pilot:project-audit` | The whole picture: test-framework maturity, critical flows, spec-audit per flow at depth critical, test-code sample → one roadmap | `docs/qa/project-audit/<date>.md` |
| `/qa-pilot:write-tests` | Implements tests from a plan per your conventions; proves each test can fail; adversarial review loop | test files + scenario→file map in the plan |
| `/qa-pilot:test` | Exploratory testing session in a real browser (Playwright MCP); guarded low-risk fixes on request | `docs/qa/test-sessions/<date>-<slug>.md` |

Every skill except `onboard` reads the project profile — run `onboard` once
first. If a session hits your plan's usage limit mid-task, nothing is lost:
every skill writes progress to its document as it works, and the next session
resumes from the file.

## Running steps individually

`cover` chains the middle of the pipeline for you; each step is also a
standalone command (add your context after it — a feature description,
ticket ID, or PR link):

Health-check the existing tests:

```
/qa-pilot:audit
```

Design test scenarios for a feature:

```
/qa-pilot:plan-tests <feature, ticket, or PR>
```

Audit the requirements / spec of a flow — what test cases are missing, what's
ambiguous or contradictory (one feature by default; whole project on request):

```
/qa-pilot:spec-audit <feature, spec files, or ticket>
```

Write the automated tests from a plan:

```
/qa-pilot:write-tests
```

Test a feature hands-on in the browser:

```
/qa-pilot:test <feature or flow>
```

## What's inside

- **9 skills** (`skills/`) — onboard, audit, cover, plan-tests, spec-audit, task-qa, project-audit, write-tests, test.
  Each follows the same contract: numbered phases, batched questions when
  context is missing, mandatory self-review of any code it changes, evidence
  before claims.
- **3 subagents** (`agents/`) — `test-author` (Sonnet, writes test code from
  precise briefs), `qa-reviewer` (adversarial review lenses), and
  `mechanical-editor` (Haiku, bulk mechanical edits). Cheap models do the
  volume; judgment stays on your session's main model.
- **Reference library** (`references/`) — Playwright e2e patterns, a flakiness
  catalog, browser/dev-server hygiene, the review-loop protocol, quality rules,
  and model-routing rules. Skills load these on demand.
- **QA rules catalog** (`knowledge/`) — 1137 paraphrased rules, recommendations,
  tips and checklist items distilled from Roman Surkov's QA handbook «Качество
  решает всё» (test design, requirements, test artifacts, forms, API, a11y/WCAG
  2.2, localization, performance, mobile HIG/Material, UX laws, dark patterns,
  AI-in-QA), each verified against its source and tagged with where it applies
  and how to check it — plus qa-pilot's own rules learned from real audits.
  The book text itself is not included (copyright); rules are in Russian.
  Book rules carry `authority` (standard / industry practice / vendor
  guideline / author opinion) after an external check against RFC, W3C,
  ISTQB, OWASP and NIST. An author opinion is never a hard `must`.
  qa-pilot's own domains are written from open sources and verified rule by
  rule:
  - web failure patterns and invariants;
  - security (OWASP ASVS 5.0 / API Top 10);
  - test-code quality;
  - HTTP APIs (RFC 9110/9457, Zalando);
  - authentication (NIST 800-63B-4);
  - test strategy (ISTQB v4);
  - AI-feature testing (OWASP LLM Top 10).
- **Playwright MCP** (`.mcp.json`) — the official
  [@playwright/mcp](https://www.npmjs.com/package/@playwright/mcp) server
  (pinned version), giving Claude real browser control for `qa-pilot:test`.

## Learn more

**[docs/guide.md](docs/guide.md)** — the practical guide: starting on a new
project, the everyday workflow, how coverage analysis actually works, how to
make your project qa-pilot-friendly, and current limitations.

## Frontend, backend, or both?

qa-pilot is **strongest on frontend/e2e testing, and usable well beyond it**:

- `onboard`, `audit`, `cover`, and `plan-tests` are test-framework-agnostic:
  onboarding profiles *all* test frameworks in your repo (unit, integration,
  API — not just Playwright); audit lenses (flakiness, false-green tests,
  duplication) apply to any test code; test planning explicitly pushes checks
  down the pyramid to unit and API level.
- `write-tests` writes unit, integration, and API tests too — Playwright itself
  can test APIs directly (request context, no browser), which covers the
  backend of a typical web project.
- `test` (browser sessions) is frontend/UI-only by nature.
- The bundled reference library (e2e patterns, flakiness catalog, browser
  hygiene) is Playwright/frontend-flavored. On a pure backend codebase
  (JVM, Python, Go) the skills still work but lean on your project's own
  conventions instead of a ready-made pattern library — expect less
  out-of-the-box guidance there. Backend-specific references (API contract
  testing, DB/migration testing) are on the roadmap.

## Design principles

1. **Quality over volume.** One well-reviewed task per session beats a day of
   sloppy iterations. Every code change passes a complexity challenge
   ("what can be deleted?"), a no-junk sweep, and an adversarial review loop.
2. **Token economy.** Project knowledge is captured once (`onboard`) and reused;
   subagents are routed to the cheapest model that does the job well; progress
   is persisted continuously so session limits never destroy work.
3. **Ask, don't guess.** Missing credentials, environments, tracker access, or
   product intent produce a batched question, not a hallucinated assumption.
4. **Your project rules win.** Your repo's CLAUDE.md / AGENTS.md / docs override
   qa-pilot defaults on any conflict.
5. **Evidence before claims.** Tests are proven able to fail; fixes are
   re-verified in the browser; suspicious greens are re-checked cold.

## Security notes

- The plugin bundles one MCP server: the official `@playwright/mcp` at a
  **pinned version** (no `@latest` auto-drift). It launches a local browser;
  it does not send your code anywhere.
- `qa-pilot:test` refuses to run against environments you haven't marked safe
  in the project profile, and asks before destructive actions on shared
  environments.
- Skills never read secret values; credential handling goes through the
  mechanism you name during onboarding (env vars / storageState).
- Recommended companions, install at your discretion:
  `chrome-devtools-mcp@claude-plugins-official` (deep network/console/
  performance inspection — official Chrome DevTools team).

## Made by

qa-pilot is built by **[Ludvik4](https://ludvik4.dev)** — a studio building
digital products with a focus on AI-assisted development. The same philosophy
you see here — project rules win, spec-first, evidence before claims — is how
we build client work.

## License

MIT
