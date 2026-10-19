# qa-pilot user guide

How to use qa-pilot on a fresh project, how to use it in everyday development,
how its coverage analysis actually works — and how to organize your project so
the plugin performs at its best.

## Starting on a new project

You installed the plugin (see README), opened Claude Code in your project.
Do these two things once:

**1. Onboard** — `/qa-pilot:onboard`

Claude studies the project: stack, test frameworks, where tests live, how they
run, what conventions and rules exist. Then it asks you what it can't detect —
which environments are safe to test against, where credentials come from,
which tracker you use, what hurts most today. The result is
`docs/qa/project-profile.md`: a compact fact sheet about your project that
every other skill reads instead of re-scanning the repo. Commit it.

Ten minutes of your attention here pays off permanently: the better you answer,
the less the plugin guesses later.

**2. Audit** — `/qa-pilot:audit`

An honest health check of the tests you already have: flaky patterns, tests
that can pass while the feature is broken, copy-paste, dead weight. You get
`docs/qa/audit-report.md` (findings with file:line evidence) and
`docs/qa/refactoring-plan.md` (ordered fix steps, each small enough for one
session). Execution is up to you: tell it "do step 1" — or don't.

Why audit before writing new tests? Because `cover` builds on your existing
suite. New tests inherit the patterns around them — cleaning the foundation
first makes everything after cheaper.

## Everyday development (project already onboarded)

You built a new feature or changed an existing one. One command:

```
/qa-pilot:cover <feature, ticket, PR — or nothing, to scope from your branch diff>
```

What happens, in order:

1. **Scope** — it works out what changed: from your description/ticket/PR, or
   from your branch's diff against the main branch. If the scope is ambiguous,
   it shows you its understanding and asks before proceeding.
2. **Gap check** — it finds the tests that relate to the change and reads them:
   what's genuinely covered, what's partial, what's missing. Tests of behavior
   you *modified* get special attention — a green test describing the old
   contract is also a gap.
3. **Plan** — for the gaps only, it designs scenarios and asks you to pick the
   depth: smoke / standard / thorough, with the cost stated plainly.
4. **Write** — it implements the tests in your project's own style, proves each
   one can fail (a test that can't fail is worse than none), shakes them for
   flakiness, and runs an adversarial self-review before showing you the result.
5. **Summary** — covered before / covered now / consciously skipped, plus the
   updated plan document in `docs/qa/test-plans/`.

The individual commands (`plan-tests`, `write-tests`, `test`, `audit`) are for
when you want just one step — e.g. only scenarios for discussion with the team,
or a hands-on browser session on a bug report.

When to re-run `onboard`: after a framework migration, a test-layout
reorganization, new environments — any time the profile's facts go stale.

## Auditing requirements and test plans

Before (or instead of) writing tests, check the requirements themselves:

```
/qa-pilot:spec-audit <feature, spec files, or ticket>
```

It answers "which test cases are we missing for this flow?", "what in this spec
is ambiguous or contradicts another doc?", and "what does the owner still need
to decide?". How it works:

- **Rules, not vibes.** It checks against `knowledge/` — 1137 rules distilled
  from Roman Surkov's QA handbook (test design techniques, requirements quality,
  a11y/WCAG 2.2, API, forms, UX laws, dark patterns…) plus qa-pilot's own rules
  learned from real audits. Your **Product traits** (in the project profile)
  drop rules that cannot apply — no iOS guidelines for a web app, no checkout
  rules without payments.
- **Your decisions win.** Records in `docs/decisions/`, CLAUDE.md and
  `docs/qa/rule-overrides.json` override the book. When you say "that's
  deliberate" during triage, it offers to record the decision so it never
  nags again. At the start it also asks for **scope filters**: modes or areas
  you don't develop, areas on hold, kinds of tests you don't want. They can be
  saved under `scope` in the same file.
- **Checked against the code.** A "missing scenario" is only reported after
  grepping your tests; spec claims are compared with what the code actually
  does. In the pilot this was where every critical finding came from.
  - Every "not covered" or "silent" claim must show the search that proves it.
  - A test counts as coverage only if it asserts the exact case and its layer
    runs in CI.
  - The main session re-runs those searches before anything reaches the report.
- **Cost.** One feature by default (~250–450k tokens for a feature with 2 spec docs). A
  whole-project audit is offered only on request, with the estimate first.

Two files land in `docs/qa/spec-audit/`:
- `<date>-<slug>-actions.md` is a plain list an agent can execute: bugs to fix
  and then test, tests to add (each with its level and target), questions for
  product, and what is already covered.
- `<date>-<slug>.md` is the evidence report: severities, rule ids, code lines.

On request, the action list becomes a `plan-tests` plan that `write-tests` can
implement.

## How coverage analysis actually works

Honestly: qa-pilot is not a coverage-percentage tool. It doesn't instrument
your code. It works the way a strong QA engineer works on day one:

- It **reads tests and judges them**. During `cover`, it maps each changed
  behavior to candidate tests — found by path proximity (tests near the changed
  code), by naming, and by feature tags if your suite has them — then reads
  those tests to decide whether they truly verify the behavior, not just touch
  the same file.
- If your project has **real coverage tooling** (Vitest/Jest `--coverage`,
  nyc, pytest-cov, JaCoCo…), onboarding records the command and the skills use
  its numbers as a signal. That's the only place real line-coverage math enters.
- During `audit`, review agents read the suite itself and hunt for tests that
  *look* like coverage but aren't (weak assertions, over-mocking, false-greens).

The practical consequence: **discovery quality depends on how findable your
tests are.** Which brings us to the next section.

## Making your project qa-pilot-friendly

Each of these helps the humans on your team too — none is agent-specific
busywork. Roughly in order of impact:

1. **Predictable test placement.** Tests co-located with code
   (`foo.ts` + `foo.spec.ts`) or mirrored in a parallel tree. One giant
   unsorted `e2e/` folder is where gap detection degrades most.
2. **A CLAUDE.md or AGENTS.md** at the repo root stating your testing
   conventions: how to run tests, locator policy, what to mock, naming. qa-pilot
   treats your rules as law — but only if they're written down. Even 20 lines help.
3. **Feature tags on test suites** (e.g. `@feature:Checkout` on `describe`
   blocks). This turns "which tests cover checkout?" from a fuzzy search into a
   grep — the single cheapest big win for `cover`.
4. **Coverage tooling wired up**, even if you don't gate on it. It gives the
   plugin (and you) real numbers instead of judgment alone.
5. **Test ids exported as constants** from components, per the locator policy in
   `references/e2e-patterns.md` — makes generated tests stable and reviewable.
6. **Tickets/PRs with acceptance criteria.** `plan-tests` quality tracks input
   quality directly: "what should happen when X fails" written down becomes a
   scenario; unwritten, it becomes a question to you — or a gap.
7. **A dedicated test environment + seeded test accounts**, named in the
   profile. Without them, browser testing (`test`) is limited to what's safe.

## Current limitations — what to expect

- **Judgment-based coverage has blind spots.** Behavior covered indirectly by a
  distant integration test may be counted as a gap (a duplicate test gets
  written), or subtle non-coverage may be missed. Real coverage tooling shrinks
  this; it doesn't vanish.
- **Messy suites degrade results.** If tests are unnamed, unsorted, and
  untagged, `cover`'s gap map gets fuzzy. That's what `audit` + its refactoring
  plan are for — run them first on a rough project.
- **The profile is per-repo.** In a multi-repo system (separate frontend/backend
  repos), each repo gets its own onboarding; qa-pilot won't reason across repos.
- **Frontend-flavored reference library.** The bundled patterns are
  Playwright/e2e-centric. On a pure backend codebase the skills work but lean on
  your project's own conventions — see "Frontend, backend, or both?" in the
  README. Backend-specific pattern references are on the roadmap.
- **Stale profile = wrong behavior.** The profile is a cache; like any cache it
  can go stale. If skills start using outdated commands or conventions, re-run
  `onboard`.
- **It asks rather than guesses.** By design, missing credentials, unclear
  acceptance criteria, or ambiguous scope produce questions. Budget a little
  interaction time — especially in the first week, before the profile and your
  docs absorb the answers.
