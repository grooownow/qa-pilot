# qa-pilot

A QA copilot plugin for [Claude Code](https://code.claude.com). Install it into
any existing project and Claude becomes a disciplined QA engineer: it audits
your test codebase, designs test scenarios, writes Playwright tests, and runs
exploratory testing in a real browser — with strict quality gates and token
economy tuned for subscription plans (works fine on Claude Pro).

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
Use qa-pilot:onboard to set up this project
```

This analyzes your stack and conventions, asks you a few questions, and writes
`docs/qa/project-profile.md` — the persistent memory all other skills reuse
(so they don't burn tokens re-scanning your repo every session). Then:

| You want | Say | Skill |
|---|---|---|
| Health-check the existing tests | "Audit our test suite" | `qa-pilot:audit` |
| Test scenarios for a feature | "Plan tests for <feature/ticket/PR>" | `qa-pilot:plan-tests` |
| Automated tests written | "Write the tests from the plan" | `qa-pilot:write-tests` |
| A feature tested in the browser | "Test <feature> in the browser" | `qa-pilot:test` |

The natural first project cycle: **onboard → audit → refactoring plan →
plan-tests → write-tests**, with `test` for hands-on verification anytime.

All outputs live in `docs/qa/` in your repo — reports, plans, session logs.
If a session hits your plan's usage limit mid-task, nothing is lost: every
skill writes progress to its document as it works, and the next session
resumes from the file.

## What's inside

- **5 skills** (`skills/`) — onboard, audit, plan-tests, write-tests, test.
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
- **Playwright MCP** (`.mcp.json`) — the official
  [@playwright/mcp](https://www.npmjs.com/package/@playwright/mcp) server
  (pinned version), giving Claude real browser control for `qa-pilot:test`.

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

## License

MIT
