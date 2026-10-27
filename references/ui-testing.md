# UI testing strategy

Bottom-up. Used by `qa-pilot:onboard` (detection), the UI audit (`/qa-pilot:audit ui`) and `qa-pilot:write-tests`.
Rules: `../knowledge/qa-pilot/rules/ui-testing.json` (QAP-UI-001 and up).

## The three levels

1. **Atoms** are library components that use no other library component. Write a story for every state: variants,
   sizes, disabled, loading, error, empty, long content, focus. Write an interaction test for every behaviour: click,
   keyboard, open/close, validation, controlled and uncontrolled value.
2. **Compositions** are library components built from atoms. Test only what the composition adds: its wiring, the
   state passed between atoms, its own logic. Atom behaviour is not tested again; if it broke, the atom's test fails.
3. **E2E.** Complex UI behaviour that needs the real app (routing, data) is checked as a step inside an e2e flow, not
   as a separate UI test.

How to tell atom from composition: open the component file and look at its imports. If it imports another component
from the same library, it is a composition. Imports from the framework, icons and utilities do not count.

## Tooling

- If the project already has UI tests, keep its tooling (Storybook test-runner, Playwright component tests).
- If it has none, default to Storybook with interaction tests in `play` functions, run by the Storybook Vitest addon
  (browser mode, Playwright provider), and `addon-a11y` for accessibility.
- A story state that has behaviour gets a `play` test; a story without one only renders.

## Locators

Inside stories and `play` functions the hard test-id rule applies as everywhere else: see "Locator strategy" in
`e2e-patterns.md`. Missing test ids are added to the component.

## Visual snapshots

Only for stable, deterministic components, only where CI renders in a pinned environment (same browser build, fonts,
OS image). Never the only assertion for a behaviour (QAP-TC-024).

## CI

A UI test that CI does not run counts as local only. Report it with the "Not in CI" line; do not draft the CI job.

<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
