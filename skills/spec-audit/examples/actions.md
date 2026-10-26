# Missing tests: checkout (cart, payment, order confirmation)
Source: spec audit of `docs/specs/checkout.md` at sha 3f9c2ab, 2026-10-26.
> Example for an invented project: a small online shop (catalog, cart, checkout, accounts).

## How to work through this list
- BUG cases fail against the current code: fix the code first, then write the test, and confirm it fails without the fix.
- Conventions: `docs/qa/project-profile.md` and `docs/testing.md`. Role or label locators; fixtures from `e2e/fixtures.ts`.
- Error mocks: the global handler already toasts 5xx and 429, so tests do not mock those. 400 and 409 are silent: each form must show its own message, and tests mock those.
- Scope: the gift-card payment method is not live, so it is not covered (owner, 2026-10-20).

## Must
1. **BUG: double click on "Pay" creates two orders.** Fix: disable the button and send one idempotency key per attempt (`src/app/checkout/actions.ts:34`). Expected: exactly one order and one charge (spec line 58: "one payment per order"). Level and target: e2e, `e2e/checkout.spec.ts`; confirm it fails without the fix.
2. **BUG: the confirmation modal closes before the order request finishes.** On a 500 the customer sees "Order placed" for a moment, then an error toast (`src/components/checkout/PayDialog.tsx:51`). Expected: the dialog stays open and shows the error (decision: errors are shown where the action happened). Level and target: component, `PayDialog.test.tsx`.
3. **No test for the total sent to the payment provider.** Expected: the amount in the request equals the total on screen (spec line 40). Level and target: e2e, `e2e/checkout.spec.ts`.
4. **BUG: a stale cart can be paid after an item was removed in another tab.** Expected: the checkout reloads the cart and shows the change (spec line 66). Fix in `src/app/checkout/page.tsx:22`, then a backend-integration test on `POST /api/orders` with an outdated cart version.

## Should (5 of 8)
1. Shipping returns when a removed item drops the subtotal below 50.00. Expected: spec line 31. Component, `CartSummary.test.tsx`.
2. A declined card keeps the cart and offers a retry. Expected: spec line 72. E2E, `e2e/checkout.spec.ts` (a test with a weaker assertion exists; strengthen it instead of adding a new one).
3. Order history shows the new order right after payment, without a reload. Expected: spec line 80. E2E, `e2e/orders.spec.ts`.
4. A quantity of 0 or a negative number is rejected by the server, not only by the form. Expected: spec line 18. Backend-integration, `POST /api/cart/items`.
5. Password reset link works once (spec line 95). Unit, `src/lib/auth.test.ts`; owner: backend.

## Highlighted, not drilled
- Price changes between "add to cart" and "pay": the spec is silent (`src/lib/pricing.ts`).
- Two browsers paying the same cart at the same moment.
- The order email repeats a fixed shipping price (`emails/order.tsx:18`).

## Needs product decision
- Is the 50.00 free-shipping threshold checked before or after a discount code? Options: (a) before, (b) after. Suggested: (b).
- Is guest checkout still supported? The code has it; the spec does not mention it. Options: keep and spec it, or remove the route.

## Suppressed by your filters
- Paying with a gift card during checkout: double submit and partial payment risks; filter: gift cards are not live (owner 2026-10-20).

## Already covered
- Cart merges duplicate items: `src/lib/cart.test.ts` › "merges duplicate items" (unit, runs in CI).
- Total includes shipping: `e2e/checkout.spec.ts` › "total with shipping" (e2e smoke, runs in CI).
