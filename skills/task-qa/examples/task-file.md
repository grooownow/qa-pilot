# QA: SHOP-57 — Free shipping above 50
> mode: plan · 2026-10-26 · base sha 3f9c2ab · depth standard · critical flow: yes (checkout)

## Scope
Orders with a subtotal of 50.00 or more get free shipping; below it, shipping costs 4.90.
The cart summary and the checkout total show the shipping line. Touches `src/lib/pricing.ts`,
`src/components/cart/CartSummary.tsx`, `src/app/checkout/page.tsx`. Entities: cart, order.

## AC check
- AC1 "Subtotal ≥ 50 → shipping 0": ok. Testable; boundary 50.00 is included by the wording.
- AC2 "Total shown in the cart equals the total charged": incomplete (double submit, QAP-WEB-002). Proposed AC: a second click on "Pay" while the first request runs sends no second charge.
- AC3 "Discount codes still work": unclear. Is the threshold checked before or after the discount? Question Q1.

## Impact map
| Edge | file:line | Expected effect |
|---|---|---|
| `pricing.ts` → `CartSummary.tsx` | `CartSummary.tsx:22` | intended: shipping line shows 0 |
| `pricing.ts` → checkout total | `checkout/page.tsx:64` | intended: charged amount follows the new rule |
| `pricing.ts` → order email template | `emails/order.tsx:18` | unknown: prints a fixed shipping price |
| cart quantity change → `invalidateQueries(['cart'])` | `useCart.ts:41` | unchanged |

## Test delta
### Change existing
- `src/lib/pricing.test.ts:30` "total for 3 items": asserts shipping 4.90 for a 60.00 cart; the old contract.

### Must / Should / Highlight
- **Must** · subtotal 50.00 gives shipping 0.00 · expected: AC1 · unit · `src/lib/pricing.test.ts`
- **Must** · subtotal 49.99 gives shipping 4.90 · expected: AC1 (the other side of the boundary) · unit · same file
- **Must** · the amount sent to the payment provider equals the total on screen · expected: AC2 · e2e · `e2e/checkout.spec.ts`
- **Should** · removing an item that drops the subtotal below 50 brings shipping back · expected: AC1 · component · `CartSummary.test.tsx`
- **Highlight** · order email prints a fixed shipping price (`emails/order.tsx:18`); not tested until Q2 is answered.

### Regression set
`src/lib/pricing.test.ts`, `src/components/cart/CartSummary.test.tsx`, `e2e/checkout.spec.ts` › "total with shipping".

## Questions
- Q1: Is the 50.00 threshold checked before or after a discount code? Options: (a) before, (b) after. Default: (b), the customer pays less than 50.
- Q2: Should the order email show the new shipping amount? Default: yes.

## Suppressed by your filters
- Gift-card payment during checkout · QAP-WEB-013 · owner 2026-10-20: gift cards are not live.

## Verify log
> mode: verify · 2026-10-27 · diff 3f9c2ab...b81d4e0

### Reconcile
| Item | Status |
|---|---|
| `pricing.ts` threshold rule | planned, done |
| `CartSummary.tsx` shipping line | planned, done |
| `checkout/page.tsx` total | planned, done |
| `emails/order.tsx` | not planned, behaviour change: email now prints the new rule |
| `useCart.ts` rename of a helper | not planned, explained (refactor) |

### New questions
- Intended? `emails/order.tsx:18` now prints "Shipping: free" for large orders (the customer sees it in the confirmation email). Looks right under Q2; pinned by one component test once the owner confirms.

### Tests added
- `src/lib/pricing.test.ts` › "free shipping at exactly 50.00", "paid shipping at 49.99": both seen red against the old rule.
- `e2e/checkout.spec.ts` › "charged amount equals displayed total": seen red after breaking the amount in the request.
- Not added (guard: at most 5, at most 1 e2e): the Should test on item removal; listed for the owner.

### Proof results
`pnpm test:unit src/lib/pricing.test.ts` 14 passed; `pnpm test:e2e e2e/checkout.spec.ts` 6 passed; regression set green.

### Coverage matrix upsert (`docs/qa/coverage-matrix.md`)
| Feature | Requirement | Test | Layer | In CI | Proof | Updated |
|---|---|---|---|---|---|---|
| Checkout | Subtotal ≥ 50.00 gives free shipping (SHOP-57 AC1) | src/lib/pricing.test.ts › "free shipping at exactly 50.00" | unit | yes | failed when broken, 2026-10-27 | 2026-10-27 |
| Checkout | Subtotal below 50.00 pays 4.90 (SHOP-57 AC1) | src/lib/pricing.test.ts › "paid shipping at 49.99" | unit | yes | failed when broken, 2026-10-27 | 2026-10-27 |
| Checkout | Charged amount equals displayed total (SHOP-57 AC2) | e2e/checkout.spec.ts › "charged amount equals displayed total" | e2e | yes | failed when broken, 2026-10-27 | 2026-10-27 |
| Checkout | Total includes shipping (SHOP-42 AC2) | e2e/checkout.spec.ts › "total with shipping" | e2e | yes | distinguishing assertion | 2026-10-27 |

### PR block
## QA verification
- Scope reconciled: 3 planned / 3 done / 1 unplanned (explained) / 1 unplanned behaviour change
- Covered (CI): "total with shipping" (SHOP-42 AC2), cart summary tests (AC1)
- Added: `src/lib/pricing.test.ts` (2), `e2e/checkout.spec.ts` (1)
- Questions: intended? order email now says "Shipping: free" (`emails/order.tsx:18`)
- Highlighted, not drilled: item removal below the threshold has no test
- Suppressed by your filters: gift-card payment in checkout (owner 2026-10-20)
- Not run: nightly `@full` e2e (runs in CI only)
