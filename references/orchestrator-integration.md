# Plugging qa-pilot into a development orchestrator

Many projects run tasks through a feature workflow skill: ticket → plan → implement → tests → review → PR. qa-pilot adds the QA step at two points, through the internal skill `qa-pilot:task-qa`. A person runs the same thing with `/qa-pilot:test <ticket>`. The orchestrator stays in charge; qa-pilot only reads, writes tests under its guard, and reports back.

## Contract

| Point | Call | Input | Output the orchestrator uses |
|---|---|---|---|
| After the ticket is understood, **before the plan is approved** | `qa-pilot:task-qa plan` | ticket id or AC text; the planned approach if one exists | AC verdicts and proposed AC edits; questions; impact map; test delta (Must / Should / Highlight) and the regression set. The Must tests go into the plan. |
| After implementation and the project's own test phase, **before review/finalize** | `qa-pilot:task-qa verify` | the task file `docs/qa/tasks/<ticket>.md`; the branch diff | Reconcile table; "intended?" questions; proof of coverage; tests added under the guard; the `## QA verification` block for the PR body |

Rules:
- `verify` never fixes product code. A BUG is reported to the owner. Only with the owner's OK does the orchestrator return to its implement phase to fix it. The BUG test stays marked expected-fail until then (test-delta §6).
- An open "intended?" question blocks the PR the same way a failed acceptance criterion does. The owner answers it, or the orchestrator stops.
- Cost: plan ≈ 80k and verify ≈ 100k tokens (targets). For a well-understood small fix (the orchestrator's short path), run `verify` only.
- For a large feature, or after a round of small changes, run `/qa-pilot:audit <feature>` (one feature) or `/qa-pilot:audit` (the whole picture) instead of relying on per-task checks.

## Generic snippet: a workflow with a plan phase and a test/review phase

Onboard proposes this for any project workflow (skill, command, `AGENTS.md` flow) that has a plan step and a test or review step. Adapt the phase names; the owner pastes it, qa-pilot never edits the workflow file.

**In the plan phase, before the plan is approved:**

```markdown
- **QA plan (qa-pilot).** Invoke the `qa-pilot:task-qa` skill in mode `plan` for <TICKET> (internal: use the Skill tool, not a slash command). Put its Must tests into the plan, its proposed AC edits and questions into the open questions, and its regression set into the final checks. Skip on the short path.
```

**After the tests are written and green, before review or PR:**

```markdown
- **QA verify (qa-pilot).** Invoke `qa-pilot:task-qa` in mode `verify` for <TICKET>. A BUG it reports goes back to the implement phase with the owner's OK. Paste its `## QA verification` block into the PR body.
```

**Periodic (release, or after a round of small changes):** run `/qa-pilot:audit` for the whole picture, or `/qa-pilot:audit <feature>` for one feature.

## Example: TDK `gov-front-feature`

The owner adds the following to `.claude/skills/gov-front-feature/SKILL.md`. qa-pilot does not edit the project itself.

**Phase 3 — Plan.** Add before "Get user approval on the plan":

```markdown
- **QA plan (qa-pilot).** Invoke the `qa-pilot:task-qa` skill in mode `plan` for <GOV-N> (it is internal: call it with the Skill tool, not as a slash command). Put its Must tests into the plan's slices, its proposed AC edits and questions into the plan's open questions, and its regression set into the Phase 8 checks. Skip on the short path.
```

**Phase 6 — Tests.** Add after the `gov-front-testing` line:

```markdown
- **QA verify (qa-pilot).** After the tests from this phase are written and green, invoke the `qa-pilot:task-qa` skill in mode `verify` for <GOV-N>. It reconciles the diff with the QA plan, asks "intended?" about unplanned behaviour changes, proves coverage (test + distinguishing assertion + layer in CI), and adds up to 5 missing tests under its guard. A BUG is reported to the user; with their OK, go back to Phase 4 to fix it. Paste its `## QA verification` block into the PR body in Phase 10, next to `## AC verification`.
```

**Phase table (Model routing).** Both calls are judgment work. Run them inline on the session model, or delegate them to a subagent that returns only the task file path and the summary block.
