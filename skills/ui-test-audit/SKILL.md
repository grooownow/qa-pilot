---
name: ui-test-audit
description: Bottom-up audit of a UI component library. A deterministic inventory splits the library into atoms and compositions by imports and counts stories, play tests and component tests. Then, by the project's state, it writes a setup plan for this repo (Storybook with the Vitest addon by default) and an atoms-first order when there are no UI tests; a gap table per component (missing states, missing behaviours, compositions that re-test atoms) citing QAP-UI rules, atoms before compositions, when some tests exist; or a rating of the project's own UI-test rules, which it then works by. Writes docs/qa/ui-test-audit-<date>.md and an action list, and with the owner's yes writes stories and play tests via qa-pilot:write-tests. Called by /qa-pilot:audit ui (storybook, компоненты, UI-тесты, библиотека компонентов). Requires docs/qa/project-profile.md (run qa-pilot:onboard first). Not for the quality of existing test code (use qa-pilot:test-code-audit) or missing test cases of a feature (use qa-pilot:spec-audit).
user-invocable: false
---

# UI test audit

Audit a component library bottom-up: atoms first, then compositions, complex app-level behaviour left to e2e. Outputs, written as you go (a dead session must lose nothing):

- `docs/qa/ui-test-audit-<date>.md`: the report
- `docs/qa/ui-test-audit-<date>-actions.md` and `-actions.json`: the action list (`../../references/actions-schema.md`)
- with the owner's yes: stories and `play` tests, written by `qa-pilot:write-tests` (target `story`)

Create a todo per phase. Read `../../references/ui-testing.md` (the strategy), the rules in `../../knowledge/qa-pilot/rules/ui-testing.json` (QAP-UI-001 and up; cite their ids), and `../../references/budget.md`. Prerequisite: `docs/qa/project-profile.md`; if it is missing, stop and run `qa-pilot:onboard`. Also read `docs/qa/learnings.md` if it exists, per `../../references/learnings.md`.

## Phase 1 — Preconditions

**Find the library path**, first match wins:
1. a path the owner named in the request;
2. `## UI state` in `docs/qa/strategy-check.md`: `UI library: <path> · ...`;
3. the `component/UI` row of the profile's `Test layers`;
4. neither exists (an older onboard): run the cheap UI detection from `../onboard/SKILL.md` (Phase 1, "UI library and UI tests") and use the library path it finds.

**No UI library → stop.** If `## UI state` says `No UI library found.`, or step 4 finds no library path, say in one line: "No UI library found (`docs/qa/strategy-check.md`); there is nothing for the UI audit to check. Name the library path if one exists." Write no report and no action list, and stop. A project whose UI lives only in app pages has no atoms to audit; its UI behaviour is checked inside e2e flows (QAP-UI-005).

**Aliases.** Read `compilerOptions.paths` in `tsconfig.json` (or `jsconfig.json`) and shadcn's `components.json` `aliases`. Each `"@/*": ["./src/*"]` becomes `--alias @=src`. Do not invent aliases the config does not have.

**Budget.** Read the mode per `../../references/budget.md`. Components per run: economy 10, standard 30, thorough all. An explicit request from the owner for a number or a list of components beats the mode. In economy, show the estimate before a run over ~150k tokens and ask.

## Phase 2 — Inventory

Run it from the project root (`SKILL_DIR` is this skill's base directory, shown when it loads):

```bash
SKILL_DIR=<absolute base directory of this skill>   # shown when the skill loads
python3 "$SKILL_DIR/scripts/ui_inventory.py" --root . --lib <library path> [--lib <path> ...] [--alias <prefix>=<path> ...] --json
```

It prints `components` (name, path, kind `atom` | `composition`, `uses`, `stories`, `play_stories`, `tests`), `unresolved` imports and a `summary`. Exit 2 means bad input (a missing `--lib` directory, a malformed `--alias`): fix the arguments, do not guess the inventory by hand.

The script's limits, and what to do about each:
- **Unresolved imports** (an alias-looking import that resolves to nothing) are listed in the report as they are, with the components they may affect marked `kind unverified`. Never guess where they point; fix the `--alias` list and rerun if the config explains them.
- **A default or namespace import from a barrel** counts every component the barrel exports, so a composition's `uses` can be too long. The kind is still right (it imports from the library); read the file before saying which atoms it wires.
- **Names come from the file stem** (or the folder for `index`). Where the exported identifier differs, say both in the gap table.
- **Dynamic imports and computed paths are not seen.** A component that loads library parts that way can show as an atom: when its file has `import(` or `lazy(`, read it and decide; note the override.
- **Alias misses inside barrels are not reported.** If a barrel re-exports through an alias, check that its components appear in the inventory.

Pick the components for this run: all atoms first, ordered by how many compositions use them (the inverse of `uses`), then compositions by the same count, up to the budget. The rest go to "Not done (budget)".

## Phase 3 — Project state

Decide which of the three states the project is in, and say it in the report header with the evidence.

1. **Library, no UI tests:** `summary.with_play` is 0, no component has `tests`, and no Playwright component test config exists. Stories without `play` only render; they are not tests (QAP-UI-004).
2. **Some tests, no clear strategy:** UI tests exist, and the project has no written UI-test rules.
3. **Tests and the project's own UI-test rules:** a written rule set for UI tests exists (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/testing*`, a README in `.storybook/` or the library). Quote the file and lines.

### State 1 — setup recommendation

- **Tooling.** Keep what the project already has (Storybook without tests gets only the test addon). With nothing, the default from `../../references/ui-testing.md`: Storybook, interaction tests in `play` functions run by the Storybook Vitest addon (browser mode, Playwright provider), `addon-a11y`.
- **Exact steps for this repo:** the install list in the form of `../write-tests/SKILL.md`, Mode bootstrap, step 1 (exact versions looked up now, every command, every file as a resolved path). Put it in the report. It is not asked for here: the owner's yes is asked once, in Phase 5. Install nothing and write nothing before that yes. A yes covers that list only: if a later step needs one more package, command or file (another addon, a browser, a config the list did not name), show the addition and ask again before doing it. Never install globally, never edit CI.
- **Accessibility:** the list includes `addon-a11y` (`../../references/e2e-patterns.md`, Accessibility check: it plays the role of the axe scan for components), so every story gets the a11y panel and check. Keep it out only if the project already checks components with axe another way; say which.
- **After the yes (Phase 5):** `qa-pilot:write-tests` target `story` does the setup, then writes the first `play` test on the top atom of the order below and proves it can fail. A setup whose first `play` test cannot fail is not delivered.
- **CI:** the job the owner should add (the run command, the browser install step). qa-pilot does not touch CI; until the job exists, these tests count as local only (QAP-UI-007).
- **Order:** the atoms of this run, most used first, each with its states and behaviours to cover; then the compositions, each with only what it adds.

### State 2 — gap table

Read each component of this run and its stories and tests. For an atom, list the states in its API (variants, sizes, disabled, loading, error, empty, long content, focus) that have no story (QAP-UI-001), and the behaviours (click, keyboard, open/close, validation, controlled and uncontrolled value) that have no `play` or component test (QAP-UI-002, QAP-UI-004). A state not in the component's API is not a gap. For a composition, list only what it adds (wiring, state passed between atoms, its own logic) and any check in its tests that re-tests a nested atom (QAP-UI-003). App-level behaviour that needs routing or data goes to an e2e flow step, not to this table (QAP-UI-005).

| Component | Kind | Missing states | Missing behaviours | Re-tests atoms? | Rule id |
|---|---|---|---|---|---|

If the project's Storybook has no `addon-a11y` (check `.storybook/main.*`) and no axe check covers the components, add one finding above the table: "no a11y check on stories", the fix is `addon-a11y` per story (`../../references/e2e-patterns.md`, Accessibility check), and it goes into the Phase 5 install list. No rule id: write "none (a11y policy)".

Rows ordered atoms, then compositions; inside each, most used first. `Re-tests atoms?` is `n/a` for an atom; for a composition, `yes: <test › name> re-checks <Atom> <behaviour>` or `no`. Every row cites at least one rule id. A component with no gap gets no row; count it under "What's healthy". Visual snapshots are a finding only where QAP-UI-006 says so.

### State 3 — adopt the project's rules

Read the project's UI-test rules and rate them against `../../references/ui-testing.md`. Report **contradictions only** (for example "compositions re-test every atom state" against QAP-UI-003), each with the project's file:line and the rule id. Ask the owner once, in one batched question, which side wins for each. Then build the gap table as in state 2 by the agreed rules; where the project's rule won, cite it as the source instead of the QAP-UI id. Propose the owner's choices as lessons (Phase 6).

## Phase 4 — Report and action list

`docs/qa/ui-test-audit-<date>.md`:

```markdown
# UI test audit: <library path> — <date>
> State <1|2|3> (evidence) · budget mode · components in this run N of M · inventory summary · skill version

## Inventory          — atoms and compositions, stories, play stories, tests (the script's table)
## Unresolved imports — as the script listed them; components marked kind unverified
## Setup              — state 1: tooling, install list, first play test, CI job to add
## Project rules      — state 3: contradictions and the owner's decisions
## Gaps               — the gap table (states 2 and 3); the ordered list (state 1)
## What's healthy     — components with full coverage; keep doing this
## Not done (budget)  — one line each; omit when nothing was skipped
```

End it with one line when the profile's `Test layers` has a layer not run in CI: `Not in CI: <layers>. These tests count as local only.` Leave it out when every layer runs in CI.

`docs/qa/ui-test-audit-<date>-actions.md` and `-actions.json`: the spec-audit 6a format (`../spec-audit/SKILL.md`) and `../../references/actions-schema.md`. Every action has `level: "component"`, `target` the story or test file, `source` the rule id (or the project rule's file:line), `pattern` the rule id. Buckets: an atom behaviour with no `play` or component test is Must; a missing atom state, a composition's own wiring and a composition re-testing atoms are Should (≤8, the rest Highlight); a removal or rewrite of an existing test is a proposal to the owner, never done by the audit. Questions for the owner (state 3 contradictions, unverified kinds) are `kind: question`. The action list ends with the same `Not in CI` line. Validate:

```bash
python3 "$SKILL_DIR/../spec-audit/scripts/score.py" validate docs/qa/ui-test-audit-<date>-actions.json
```

Errors must be zero; explain or fix warnings.

Example: `examples/ui-test-audit.md`.

## Phase 5 — Writing (only after a yes)

Present the report and the action list, and stop. Writing starts only when the owner picks gaps (or says "do the Must list").

When the project needs setup (state 1, or the a11y addon from the gap table), show the install list from the report in the chat, in full, in the same message as the question about the gaps. This is the only time the audit asks for the install yes; write-tests reuses it for the same, unchanged list and does not ask again. Anything added to the list later is asked again.

- Hand the picked gaps to `qa-pilot:write-tests`, target `story`: stories for missing states, `play` tests for missing behaviours, compositions tested only for what they add.
- Under the auto-test guard (`../../references/test-delta.md`, §6): at most 5 new tests per batch, no code fix. Adding a `data-testid` to a component so a `play` test can find an element is allowed and listed. More than 5 tests is another list for the owner.
- Each `play` test gets its failure proof: break the behaviour it checks, the test must fail, restore.
- Rows go to `docs/qa/coverage-matrix.md` with layer `component` (`../../references/coverage-matrix.md`). Mark the written actions `owner_verdict: fixed` in `-actions.json`.

## Phase 6 — Lessons

If a trigger from `../../references/learnings.md` occurred in this run (for example, the owner overruled a QAP-UI rule in state 3, or rejected a gap as wrong for this project), propose the lessons to the owner as that file says; write them only after a yes. If invoked by another qa-pilot skill, hand the candidates back to it instead of asking.

<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
