# Project learnings

What qa-pilot learned on one project and must not forget: a rejected finding, a flaky root cause, a command quirk.
The profile holds detected facts; this file holds experience. It lives in the user's project as
`docs/qa/learnings.md`, is written only with the owner's yes, and is read by every qa-pilot skill.

## File format

```markdown
# QA learnings
> Written by qa-pilot with the owner's OK. Every qa-pilot skill reads this before it starts.
> One line per lesson. Newest first inside a section.

## <area: e2e · unit · test data · auth · CI · review · audit · <feature name>>
- <date> · <the lesson as a rule: do / don't + why> · source: <owner | review | probe | flaky | run> · for: <skills or all>
```

## When a lesson is proposed

Strict. Anything outside this list is not a lesson:

- the owner rejected or corrected a qa-pilot finding, plan item or test as wrong *for this project*;
- the same review finding came back in two review rounds or two runs;
- a flaky or failing test got a project-specific root cause;
- a command or environment quirk cost a retry, and the profile is not the right home for it.

## Not a lesson

- generic testing advice ("write good tests");
- a fact the repo shows: that goes to the profile via `qa-pilot:onboard`;
- an owner scope filter ("don't test X"): that goes to `docs/qa/rule-overrides.json` → `scope`;
- details of one task: they stay in the task file.

## Writing

At the end of a run, a skill that met a trigger shows the proposed lines in one message and writes them only after
the owner says yes. At most 3 new lines per run. A duplicate is merged into the existing line (date updated), not added.

## Reading

Every skill reads the file at start, right after the profile, when it exists. It is capped at about 60 lines, so it
is read whole. Precedence: the owner's words in this session, then learnings, then skill defaults. A lesson that
contradicts the profile or the repo is shown to the owner as a question, not applied silently.

## Maintenance

`qa-pilot:onboard` (full and refresh) lists lessons that look stale, meaning they name a path, command or
dependency that no longer exists, and asks whether to drop them. Over 60 lines, it proposes merges. Nothing is
deleted without a yes.

## Example

A small online shop: catalog, cart, checkout, accounts.

```markdown
## e2e
- 2026-10-24 · Seed the cart through the API, not the UI: the add-to-cart animation made UI seeding flaky · source: flaky · for: write-tests, cover
## checkout
- 2026-10-22 · Do not propose a test for the promo-code field length: the owner confirmed the limit is enforced by the payment provider · source: owner · for: all
## CI
- 2026-10-20 · `npm run test:e2e` needs `SHOP_BASE_URL`; without it every test passes against an empty page · source: run · for: all
```
