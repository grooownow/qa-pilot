# Model Routing & Token Economy

qa-pilot assumes a subscription plan with usage limits (e.g. Claude Pro).
The goal: **one high-quality task per session window beats a day of cheap,
sloppy iterations.** Quality is never traded down — waste is.

## Principles

1. **The main session keeps the judgment.** Planning, architectural decisions,
   review verdicts, and anything ambiguous stay in the main conversation on the
   session's default model. Never delegate judgment to a cheaper model.
2. **Delegate volume, not decisions.** Subagents are for well-specified,
   self-contained work packages with a precise brief and a defined output format.
   If you cannot write a precise brief, the task is not ready to delegate.
3. **Route subagents down, never up.** A subagent gets the cheapest model that
   can do its job *well*:

   | Work | Agent / model |
   |---|---|
   | Bulk mechanical edits: renames, moves, find-replace across files | `mechanical-editor` (haiku) |
   | Writing test code from a precise brief; adapting a known pattern | `test-author` (sonnet) |
   | Repo exploration / searching when the answer location is unknown | Explore agent (sonnet) |
   | Review lenses in the review loop | `qa-reviewer` (inherits session model — verdicts are judgment) |
   | Parallel judgment-heavy analysis with a precise brief (e.g. `spec-audit` clusters) | general-purpose agent on the session model; the main session re-verifies every high-severity result |
   | Planning, triage, final verdicts, anything underspecified | main session, no delegation |

4. **Escalate on failure, don't retry in place.** If a cheap agent produces a bad
   result once, do not re-run it with the same brief. Either fix the brief or do
   the work at a higher tier. Two failed cheap attempts cost more than one good one.

## Token-saving rules

- **Read the profile, not the repo.** `docs/qa/project-profile.md` exists so that
  skills do not re-scan the codebase every session. If the profile answers the
  question, do not open source files to double-check.
- **Read narrow.** Open the specific file section you need, not the whole file;
  ask Explore agents for conclusions, not file dumps.
- **Persist state continuously.** Every skill writes its findings/progress to its
  output document *as it works*, not at the end. If the session dies at 80%,
  the next session resumes from the document instead of redoing the work.
- **Batch questions to the user.** Each round-trip costs a fresh context read.
  Ask everything foreseeable at once.
- **Plan before touching code.** A 10-line plan reviewed once is cheaper than
  three wrong implementations.
- **Don't gold-plate.** When the agreed scope is "smoke tests", do not silently
  expand to thorough coverage. Scope changes go through the user.
- **Parallel agents: cap at 4–6.** More parallelism burns tokens faster than it
  saves wall-clock on a limited plan.

## Session-window strategy (Pro plan)

- Prefer finishing one skill's full cycle (e.g. audit → report) in one window
  over starting three things.
- If the window limit is near, stop at a clean checkpoint: write the state
  document, list "next steps" in it, and tell the user exactly how to resume
  (`continue the audit from docs/qa/audit-report.md, phase 3`).

<!-- qa-pilot · © 2026 Ludvik4 · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
