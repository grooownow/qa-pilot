# Test code audit: online shop — 2026-10-26
> Example for an invented project: a small online shop (catalog, cart, checkout, accounts).

## Scope and baseline
- Scope: `e2e/` (22 tests) and `src/**/*.test.ts(x)` (140 tests); critical flows from the profile: checkout, add to cart, login, order history.
- Baseline run: `pnpm test:unit` 140 passed, 0 failed, 2 skipped, 38 s. `pnpm test:e2e` 21 passed, 1 skipped, 4 min 10 s.
- Failure-proof sample: 10 tests (the checkout and cart tests plus 3 suspects from the false-green lens); about 25 min.

## First pass: grep hints
| Name | Pattern hits | Read, confirmed |
|---|---|---|
| Sleeper | 9 | 7 |
| Ghost | 3 | 3 |
| Status-only | 5 | 3 |
| Mockery | 11 | 2 |
| Copycat | 6 | 4 |

## Critical
### [Liar]
- `e2e/checkout.spec.ts:61` "applies discount code": the discount is applied in a `try` block and the `expect` sits in the `catch`; the test passes when the code is rejected (QAP-TC-003). Probe below: survived.
- `src/lib/pricing.test.ts:44` "total with shipping": the test has no assertion on the total, only that the function returns (QAP-TC-002). Probe: survived.

### [Status-only]
- `e2e/checkout.spec.ts:48` "pays for the order": waits for `POST /api/orders` to return 200 and ends. The confirmation page is never checked (QAP-TC-032). Fix: after the click, assert the order number is visible.

## Important
### [Sleeper]
- `e2e/cart.spec.ts:19,33,57`: `page.waitForTimeout(3000)` before the badge check (QAP-TC-026). Fix: `await expect(badge).toHaveText('2')`.
- `e2e/account.spec.ts:12`: a fixed 2 s wait after login; the same fix.

### [Ghost]
- `e2e/orders.spec.ts:70`: `test.skip` with no reason (QAP-TC-010).
- `src/lib/cart.test.ts:88`: `it.todo("merges duplicates")`: the behaviour exists and is untested.
- `e2e/catalog.spec.ts:9`: a committed `test.only`; the other 6 tests of the file do not run (QAP-TC-009).

### [Mockery]
- `src/components/cart/CartSummary.test.tsx:30`: asserts that `formatPrice` was called twice, not what the user reads (QAP-TC-013).

## Worth-fixing
### [Copycat]
- `e2e/cart.spec.ts`, `e2e/checkout.spec.ts`: the same 6-line "log in, add product, open cart" block in 9 tests. Move it to a fixture.

### [other]
- `playwright.config.ts`: `retries: 2` in CI hides the Sleeper failures above; revisit after they are fixed.

## Failure proof
| Test | Mutation (file:line, find → replace) | Verdict | Last output line |
|---|---|---|---|
| checkout › "total with shipping" | `src/lib/pricing.ts:27`, `subtotal + shipping` → `subtotal` | killed | `Expected: "$54.90"  Received: "$50.00"` |
| checkout › "applies discount code" | `src/lib/discount.ts:15`, `rate` → `0` | survived | `1 passed` |
| pricing › "total with shipping" | `src/lib/pricing.ts:27`, `subtotal + shipping` → `subtotal` | survived | `1 passed` |
| cart › "merges duplicate items" | `src/lib/cart.ts:12`, `qty + 1` → `qty` | killed | `Expected: 2  Received: 1` |
| login › "wrong password shows error" | `src/app/login/actions.ts:20`, `if (!ok)` → `if (ok)` | not proved | `timeout after 240 s` |

`git status` after the probes shows no change to product code.
Matrix: the two survivors are now `none` in `docs/qa/coverage-matrix.md`; the two kills are `failed when broken, 2026-10-26`.

## What's healthy
- Locators are by role or label in 31 of 35 places; no CSS or XPath in `e2e/`.
- Cart merge and quantity tests assert concrete values and die when the code breaks.
- Network mocks live in one file (`src/mocks/handlers.ts`), so a contract change touches one place.
