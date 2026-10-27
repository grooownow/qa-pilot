# Budget mode

How much a heavy qa-pilot skill spends. The owner picks a mode once in `qa-pilot:onboard`; it lives in the profile.

## Reading the mode

Read `docs/qa/project-profile.md` → `## Budget`:

```
mode: economy|standard|thorough
report_spend: yes|no
```

If the section is absent (a profile written before 0.9), `mode` is missing, or the value is not one of the three, use `standard`. `report_spend` defaults to `no`. Do not ask the owner and do not report the fallback as a problem.

`standard` is exactly the behaviour each skill had before budget modes existed. The defaults written in the skills' own text are the `standard` values.

## What a mode changes

| Knob | economy | standard (today) | thorough |
|---|---|---|---|
| standalone spec-audit default depth | critical | standard | thorough |
| spec-audit inside project-audit | critical | critical | standard |
| project-audit default flows | 1 | 3 | 5 |
| failure-probe sample (project-audit) | 3 | up to 10 | up to 20 |
| test-code-audit probe sample | critical flows only | critical flows + suspects | + one per suite |
| review-loop rounds | 1 | today's cap | today's cap |
| ui-test-audit components per run | 10 | 30 | all |

An explicit request from the owner for a depth, a number of flows or a sample size beats the mode.

## Economy

Before any run estimated over ~150k tokens, show the estimate and ask whether to go on, narrow the scope or switch the mode for this run.

## Not done (budget)

Anything a mode skipped is listed in the report under "Not done (budget)", one line each: what was skipped and which mode setting caused it. Leave the line out when nothing was skipped.

## Spend reporting

The agent cannot read its own token count. With `report_spend: yes`, each heavy skill states its own estimate before the run and an estimate after ("~120k by the size of what was read"), and points the owner to Claude Code's `/cost` (or `/usage`) for the real number.

<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
