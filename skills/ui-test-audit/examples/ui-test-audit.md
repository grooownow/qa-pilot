# UI test audit: `packages/ui` — 2026-10-27
> Example for an invented project: a small online shop (catalog, cart, checkout, accounts).
> State 2: 5 stories with `play` in 4 components and 2 component tests exist; no written UI-test rules in `CLAUDE.md`, `docs/testing.md` or `packages/ui/README.md` · budget mode standard (30 per run) · components in this run 14 of 14 · inventory: 14 components, 9 atoms, 5 compositions, 12 with stories, 4 with `play` · qa-pilot 0.9.0

## Inventory
Command: `python3 ui_inventory.py --root . --lib packages/ui/src --alias @ui=packages/ui/src --json`

| Component | Kind | Uses | Stories | Play stories | Tests |
|---|---|---|---|---|---|
| Button | atom | | 4 | 2 | |
| Input | atom | | 3 | 1 | |
| Checkbox | atom | | 2 | 1 | |
| Badge | atom | | 2 | 0 | |
| Price | atom | | 2 | 0 | `Price.test.tsx` |
| ProductCard | composition | Button, Badge, Price | 2 | 0 | `ProductCard.test.tsx` |
| CheckoutForm | composition | Input, Checkbox, Button | 1 | 0 | |
| AddressForm | composition | Input, Button | 1 | 0 | |
| CartLine | composition | Price, Button | 1 | 0 | |

(Left out of this example: four atoms with no behaviour, Divider, Spinner, Skeleton and Icon, and the composition PageHeader, which has stories and a `play` test for its own menu toggle.)

## Unresolved imports
- `packages/ui/src/ProductCard.tsx`: `~/theme/tokens`. `tsconfig.json` has no `~` path, so the script cannot follow it. ProductCard is a composition through its Button import either way, so its kind stands. Question A9 asks where `~` points.

## Gaps
| Component | Kind | Missing states | Missing behaviours | Re-tests atoms? | Rule id |
|---|---|---|---|---|---|
| Button | atom | loading, long label | click while `loading` does nothing; Enter and Space activate | n/a | QAP-UI-001, QAP-UI-002 |
| Input | atom | error, disabled | controlled value (parent resets it); error message after blur | n/a | QAP-UI-001, QAP-UI-002 |
| Checkbox | atom | disabled | Space toggles; `onChange` gets the new value | n/a | QAP-UI-001, QAP-UI-002 |
| ProductCard | composition | out of stock | "Add to cart" sends the product id; out of stock disables it | yes: `ProductCard.test.tsx` › "button is disabled" re-checks Button `disabled` styling | QAP-UI-003 |
| CheckoutForm | composition | | submit stays disabled until terms are checked; an invalid email blocks submit and focuses the field | no | QAP-UI-004 |

`Price` formats with a currency and is covered by `Price.test.tsx` (unit); no gap. `Badge` has no behaviour; its two stories cover its states.

Complex UI behaviour left to e2e (QAP-UI-005): "add to cart updates the header badge" needs the cart store and routing; it is a step in `e2e/cart.spec.ts`, not a story.

## What's healthy
- Button, Input and Checkbox each have a `play` test for their main click or type behaviour, and they find elements by `data-testid`.
- `AddressForm` and `CartLine` add no logic of their own beyond passing values to their atoms; their render-only stories are enough (QAP-UI-004).

## Action list (`docs/qa/ui-test-audit-2026-10-27-actions.md`, excerpt)

### Must
1. **Button: no test that a click while loading does nothing.** Expected: `onClick` is not called and the button has `aria-busy` (QAP-UI-002). Level and target: component, `packages/ui/src/Button.stories.tsx`, new story `Loading` with `play`.
2. **Input: no test of the controlled value.** Expected: when the parent resets `value` to "", the field shows "" (QAP-UI-002). Component, `Input.stories.tsx`, story `Controlled` with `play`.
3. **Checkbox: no keyboard test.** Expected: Space toggles it and `onChange` gets `true` (QAP-UI-002). Component, `Checkbox.stories.tsx`, `play` on `Default`.

### Should
1. CheckoutForm: submit is disabled until terms are checked (QAP-UI-004). Component, `CheckoutForm.stories.tsx`, story `TermsRequired` with `play`; checks the wiring only, not Checkbox's own toggle.
2. ProductCard: "Add to cart" calls `onAdd` with the product id (QAP-UI-003). Component, `ProductCard.stories.tsx`.
3. ProductCard: drop the Button-styling check from `ProductCard.test.tsx` › "button is disabled" and assert that out of stock disables the action. A change to an existing test: the owner decides (QAP-UI-003).
4. Button and Input: stories for `loading`, `long label`, `error`, `disabled` (QAP-UI-001).

### Needs product decision
- A9. Where does the `~` import alias point? `tsconfig.json` has no path for it.

Not in CI: component/UI. These tests count as local only.
