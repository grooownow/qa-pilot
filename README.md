# qa-pilot

A QA copilot plugin for [Claude Code](https://code.claude.com). Install it into
any existing project and Claude becomes a disciplined QA engineer, driven by
three commands. `/qa-pilot:onboard` sets it up. `/qa-pilot:test` does the QA
of every task: a plan before coding, verification and missing tests after,
and the browser when you ask. `/qa-pilot:audit` gives you the big picture of
the project, of a feature's requirements, or of the test code. Quality gates
are strict and token use is tuned for subscription plans (works fine on
Claude Pro).

Built for QA engineers who are new to AI agents: every skill asks when it's
missing context, persists its work to files in your repo, and never claims
something works without showing the evidence.

## Install

**Licence:** free for noncommercial use; commercial use needs a licence — see
[COMMERCIAL.md](COMMERCIAL.md). Version 0.9.0 and earlier stay MIT: to stay on MIT, install
from the `v0.9.0` tag and do not update.

Prerequisites: [Claude Code](https://code.claude.com/docs/en/overview) and
Node.js (for the bundled Playwright MCP browser tools).

Inside Claude Code, run:

```
/plugin marketplace add grooownow/qa-pilot
/plugin install qa-pilot@qa-pilot
```

Restart Claude Code when prompted. That's it — the skills, subagents, and
browser tools are now available in every project.

To update later: `/plugin marketplace update qa-pilot`. What changed in each version: [CHANGELOG.md](CHANGELOG.md).

## Quickstart

In your project, start with:

```
/qa-pilot:onboard
```

This analyzes your stack and conventions, asks you a few questions, and writes
`docs/qa/project-profile.md` — the persistent memory all other skills reuse
(so they don't burn tokens re-scanning your repo every session).

## Three commands

You only need to remember three. Add context after a command if you have it,
for example a ticket, a feature, a URL or "in the browser". Without context the
agent works it out from your branch, and asks once when it is unsure.

| Command | When | What it does |
|---|---|---|
| `/qa-pilot:onboard` | Once per project | Profiles the stack, test layers, CI, error handling, test-framework maturity and critical flows → `docs/qa/project-profile.md` |
| `/qa-pilot:test [context]` | Every task | Picks the mode from context. **Before coding:** a QA plan (AC check, impact map, which tests to change or add). **After coding:** verifies the change (diff vs plan, "intended?" questions, proof of coverage, missing tests under guards). **"In the browser" or a URL:** exploratory testing in a real browser. **A test plan:** writes the tests. |
| `/qa-pilot:audit [context]` | Big picture | **Nothing:** a whole-project audit (framework maturity, critical flows, per-flow audit, one roadmap). **A feature, spec or ticket:** a requirements audit (missing test cases, bugs, product questions). **"tests" or "flaky":** a test-code audit. **"ui" or "storybook":** a bottom-up audit of the component library (atoms, then compositions). |

The natural rhythm:
1. `onboard` once;
2. `audit` when you join a project, after a large feature, or after a round of small changes;
3. `test` on every task.

If your team runs tasks through a feature workflow skill, plug the QA step
into its plan and test phases (`references/orchestrator-integration.md`).

### Under the hood

The commands route to internal skills. They are hidden from the slash menu,
but the agent invokes them:

| Internal skill | Used by | Writes to your repo |
|---|---|---|
| `task-qa` (plan / verify) | `test` | `docs/qa/tasks/<ticket>.md` (+ tests in verify) |
| `cover` | `test` ("cover what I shipped") | `docs/qa/test-plans/<feature>.md` + test files |
| `plan-tests`, `write-tests` | `test`, `cover` | test plans, test files |
| `explore` | `test` (browser) | `docs/qa/test-sessions/<date>-<slug>.md` |
| `project-audit` | `audit` (no context) | `docs/qa/project-audit/<date>.md` |
| `spec-audit` | `audit` (feature/spec) | `docs/qa/spec-audit/<date>-<slug>[-actions].md/.json` |
| `test-code-audit` | `audit` ("tests") | `docs/qa/audit-report.md`, `docs/qa/refactoring-plan.md` |
| `ui-test-audit` | `audit` ("ui") | `docs/qa/ui-test-audit-<date>[-actions].md/.json` (+ stories and `play` tests after a yes) |

Every skill except `onboard` reads the project profile. If a session hits your
plan's usage limit mid-task, nothing is lost: every skill writes its progress
to a file in your repo as it works, and the next session resumes from there.

## Strategy, budget and UI testing (0.9)

- **Harness and fit.** `onboard` finds your own workflow files by name and heading, records where qa-pilot fits (or that nothing does), grades the fit, and gives the exact step to add. The profile keeps the facts (`## Harness`); advice goes to `docs/qa/strategy-check.md`, rewritten on each run. qa-pilot never edits your CI.
- **Strategy check.** Compares the test layers with the code (logic without unit tests, components without component tests, layers that run only locally) and ends the CI part with a `Not in CI:` line. `project-audit` reads it.
- **Budget.** `economy`, `standard` or `thorough`, chosen once in `onboard` (`## Budget` in the profile). It sets audit depth, number of flows and sample sizes. `standard` is the 0.8 behaviour; a profile without the section runs as `standard`.
- **Locator rule.** `data-testid` is required: if a component has none, the agent adds one. Other locators only where a test id is impossible, with a `// no testid:` comment.
- **E2E skeleton.** `write-tests` in `bootstrap` mode writes config, fixtures, a page object and a smoke test for a project with no e2e layer. It installs nothing until you say yes to the exact list of packages, commands and files; one more item later is asked again.
- **UI testing.** `/qa-pilot:audit ui` counts components with `ui_inventory.py`, splits atoms from compositions, and orders the work bottom-up. After a yes, `write-tests` writes the missing stories and `play` tests. Rules: `QAP-UI-001..007`, `references/ui-testing.md`.

## What it remembers

Two small files in your project carry knowledge from run to run. Both are plain Markdown you can read and edit.

- **`docs/qa/learnings.md`: project lessons.** A finding you rejected as wrong for this project, a flaky test's root cause, a command quirk. At the end of a run qa-pilot shows the lessons it wants to keep (at most 3) and writes them only after your yes. Every skill reads the file before it starts. `onboard` flags lessons that have gone stale.
- **`docs/qa/coverage-matrix.md`: what is covered.** One table: feature, requirement, test, layer, in CI, proof, updated. `test` and `audit` add rows for coverage they proved, and read it to avoid planning a test that exists. The proof column says `failed when broken` only when the run saw the test fail. It is a record, not a CI gate.

Before every run, `test` and `audit` also check the profile against the repo. Besides renamed scripts, moved paths and CI changes, they now notice a new test dependency, a changed `CLAUDE.md`, `AGENTS.md` or lint/test config (git only, committed edits only), and a matrix row whose test file is gone.

## What's inside

- **12 skills** (`skills/`). Three are commands: onboard, test, audit. Nine are internal skills the commands route to: task-qa, cover, plan-tests, write-tests, explore, project-audit, spec-audit, test-code-audit, ui-test-audit.
  Each follows the same contract: numbered phases, batched questions when
  context is missing, mandatory self-review of any code it changes, evidence
  before claims. The five that write documents have an example output in their
  `examples/` folder. `test-code-audit` names ten test anti-patterns (Liar,
  Mirror, Mockery, Status-only and others) and finds them with a grep pass first.
- **3 subagents** (`agents/`) — `test-author` (Sonnet, writes test code from
  precise briefs), `qa-reviewer` (adversarial review lenses), and
  `mechanical-editor` (Haiku, bulk mechanical edits). Cheap models do the
  volume; judgment stays on your session's main model.
- **Reference library** (`references/`) — Playwright e2e patterns, a flakiness
  catalog, browser/dev-server hygiene, the review-loop protocol, quality rules,
  and model-routing rules. Skills load these on demand.
- **QA rules catalog** (`knowledge/`) — 1137 paraphrased rules, recommendations,
  tips and checklist items distilled from a large QA rule catalog (test design, requirements, test artifacts, forms, API, a11y/WCAG
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
  (pinned version), giving Claude real browser control for browser testing (`explore`).

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
5. **Evidence before claims.** New tests are proven able to fail; an audit of
   existing tests breaks the code under a sample of them with a script that
   restores the file; UI tests assert what the user sees, not the response
   status; fixes are re-verified in the browser; suspicious greens are
   re-checked cold.

## Security notes

- The plugin bundles one MCP server: the official `@playwright/mcp` at a
  **pinned version** (no `@latest` auto-drift). It launches a local browser;
  it does not send your code anywhere.
- Browser testing (`explore`) refuses to run against environments you haven't marked safe
  in the project profile, and asks before destructive actions on shared
  environments.
- Skills never read secret values; credential handling goes through the
  mechanism you name during onboarding (env vars / storageState).
- Recommended companions, install at your discretion:
  `chrome-devtools-mcp@claude-plugins-official` (deep network/console/
  performance inspection — official Chrome DevTools team).

## Made by

qa-pilot is built by **Ekaterina Pustovaia ([Ludvik4](https://ludvik4.dev))**, who builds
digital products with a focus on AI-assisted development. The same philosophy
you see here — project rules win, spec-first, evidence before claims — is how
the client work is built too.

## License

Free for noncommercial use under the [PolyForm Noncommercial License 1.0.0](LICENSE).
Commercial use (work for a for-profit employer or for clients, use inside a company) needs
a commercial licence: see [COMMERCIAL.md](COMMERCIAL.md). The rule catalog in
`knowledge/catalog/` is derived from a third-party book and is not covered by commercial
licences. Versions up to and including 0.9.0 were released under the MIT licence and stay
under it.
