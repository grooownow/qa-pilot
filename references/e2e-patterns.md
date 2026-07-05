# Playwright E2E Patterns

> Distilled from production Playwright experience across several real projects.

The canonical how-to for writing Playwright end-to-end tests in this project. Load this
before writing or reviewing any e2e spec. It sets defaults — a project's own testing docs
win on conflict.

## Quick checklist

- One `test.describe` per spec file; the file name and describe title both name the feature.
- Locate by role/label/text or a dedicated `data-testid`; never CSS classes or `nth-child`.
- Page Object Model for any flow with more than a couple of interactions; injected via a
  fixture, not `new`'d inline in every test.
- Web-first assertions and `waitForResponse`, never `page.waitForTimeout()`.
- Tag every describe with `@feature:<Name>` plus exactly one tier tag
  (`@ui-contract` / `@real-backend` / `@real-data`).
- Register cleanup as you create data; don't hand-roll `afterAll` unless the block is
  `test.describe.serial` and shares state across cases.
- Timeouts come from a shared constants file, never a magic number typed inline.

---

## Test structure & naming

- **One `describe` block per spec file**, one feature or user flow per file. Splitting a
  flow across files (or cramming several flows into one file) breaks the feature-tag
  contract below and makes failures harder to triage.
- File name mirrors the feature: `checkout.spec.ts`, not `test3.spec.ts` or `misc.spec.ts`.
- Test titles describe observable behavior ("shows an error when the card is declined"),
  not implementation ("calls handleSubmit").
- Arrange (navigate + set up state) → Act (the user action under test) → Assert. Keep each
  test to one behavior; multiple loosely-related assertions in one test make failures
  ambiguous about what actually broke.

## Fixture-injected Page Object Model

Use POM for anything beyond trivial flows, but don't hand-construct page objects in every
test — inject them through a `pages` fixture so tests just ask for what they need. Each
Page Object exposes **business-action-first methods** (what a user does), not raw locator
plumbing, and keeps its locators lazy and private under an `el` namespace so a locator that
is never touched by a given test never pays construction cost and isn't part of the public
surface.

```typescript
// page-objects/checkout-page.ts
import type { Page, Locator } from "@playwright/test";

export class CheckoutPage {
  constructor(private readonly page: Page) {}

  // Locators are private and lazy — built on access, not in the constructor.
  private el = {
    cardNumber: (): Locator => this.page.getByLabel("Card number"),
    expiry: (): Locator => this.page.getByLabel("Expiry"),
    payButton: (): Locator => this.page.getByRole("button", { name: "Pay now" }),
    errorBanner: (): Locator => this.page.getByRole("alert"),
  };

  // Methods are business actions, not "fillCardNumber" + "clickPay" busywork.
  async payWithCard(cardNumber: string, expiry: string): Promise<void> {
    await this.el.cardNumber().fill(cardNumber);
    await this.el.expiry().fill(expiry);
    await this.el.payButton().click();
  }

  async getError(): Promise<string> {
    return (await this.el.errorBanner().textContent()) ?? "";
  }
}
```

```typescript
// fixtures/page-objects.ts
import { test as base } from "./cleanup";
import { CheckoutPage } from "../page-objects/checkout-page";
import { OrdersPage } from "../page-objects/orders-page";

type Pages = {
  checkout: CheckoutPage;
  orders: OrdersPage;
};

type Fixtures = {
  pages: Pages;
};

export const test = base.extend<Fixtures>({
  pages: async ({ page }, use) => {
    // Lazy getters: a Page Object is only constructed the first time a test touches it.
    const cache = new Map<string, unknown>();
    const pages: Pages = {
      get checkout() {
        return (cache.get("checkout") ??
          cache.set("checkout", new CheckoutPage(page)).get("checkout")) as CheckoutPage;
      },
      get orders() {
        return (cache.get("orders") ??
          cache.set("orders", new OrdersPage(page)).get("orders")) as OrdersPage;
      },
    };
    await use(pages);
  },
});

export { expect } from "@playwright/test";
```

```typescript
// tests/checkout.spec.ts
import { test, expect } from "../fixtures/page-objects";

// @feature:Checkout
// @ui-contract
test.describe("Checkout", () => {
  test("declined card shows an error", async ({ pages }) => {
    await pages.checkout.payWithCard("4000000000000002", "12/29");
    expect(await pages.checkout.getError()).toContain("declined");
  });
});
```

Register every new Page Object in one place (a barrel + the `Pages` type) so adding a page
object is a one-line change, not a hunt through the fixture chain.

## Fixtures & cleanup

Compose fixtures instead of duplicating setup:

- A base `test` wrapper (see `flakiness-catalog.md` for the quarantine variant) that every
  spec imports instead of `@playwright/test` directly — this is the one place that can
  enforce project-wide policy (tags, quarantine, custom reporting hooks).
- A `cleanup` fixture with typed registration methods, one per entity kind the test suite
  creates (`cleanup.addUser(id)`, `cleanup.addOrder(id)`, ...). Tests register an id the
  moment they create it; the fixture deletes everything it was handed, in reverse order,
  after the test — whether the test passed or failed. Swallow delete errors and log them;
  a cleanup failure must never fail an otherwise-passing test.
- Data-heavy fixtures (`with-seeded-account`, `with-active-subscription`, ...) compose the
  `pages` and `cleanup` fixtures and additionally create the precondition entities via API
  calls before the test body runs — never through the UI, see below.

```typescript
// fixtures/cleanup.ts
import { test as base } from "@playwright/test";
import { deleteUser, deleteOrder } from "../helpers/api";

type Cleanup = {
  addUser(id: string): void;
  addOrder(id: string): void;
};

export const test = base.extend<{ cleanup: Cleanup }>({
  cleanup: async ({}, use) => {
    const userIds: string[] = [];
    const orderIds: string[] = [];
    await use({
      addUser: (id) => userIds.push(id),
      addOrder: (id) => orderIds.push(id),
    });
    // Teardown runs after the test body, success or failure.
    for (const id of orderIds.reverse()) {
      await deleteOrder(id).catch((e) => console.error(`cleanup: order ${id}`, e));
    }
    for (const id of userIds.reverse()) {
      await deleteUser(id).catch((e) => console.error(`cleanup: user ${id}`, e));
    }
  },
});
```

Exception: `test.describe.serial` blocks that share one entity across multiple cases still
need a hand-rolled `test.afterAll` — the per-test cleanup fixture doesn't fit a shared id.

## Locator strategy

- Prefer, in order: `getByRole`, `getByLabel`, `getByText`, then a dedicated `data-testid`
  for elements with no accessible role/label/text (icon-only buttons, decorative containers
  used as hooks). Never `.locator('.some-class')` or `nth-child` — both break the moment
  styling or DOM order changes, independent of any user-visible change.
- Export `data-testid` values as named constants from the component that owns them, not as
  string literals sprinkled through tests. A rename becomes a one-file diff instead of a
  find-and-replace across specs.
- If a locator strategy forces you into brittle selectors, that's a signal the component is
  missing an accessible name — fix the component, don't work around it in the test.

## Waiting strategy

- Web-first assertions (`expect(locator).toBeVisible()`, `.toHaveText()`, `.toBeEnabled()`)
  auto-retry until the timeout; they are the default and cover most cases.
- `page.waitForResponse(...)` when a test needs to assert on the network call itself (status
  code, response body), not just the resulting UI state.
- **`page.waitForTimeout()` is banned outright.** A fixed sleep is always either too short
  (flaky under load) or too long (slow for no reason), and it hides the real signal the test
  should be waiting on. If nothing else works, add a `data-testid` or a state the app
  already exposes and wait on that instead.
- Wrap the common "click something, then wait for the response it triggers" shape in one
  helper so tests don't hand-roll `Promise.all([waitForResponse, click])` repeatedly:

```typescript
// helpers/click-and-wait-for-response.ts
import type { Locator, Page } from "@playwright/test";

export async function clickAndWaitForResponse(
  page: Page,
  locator: Locator,
  urlPattern: string | RegExp,
  method = "POST",
) {
  const [response] = await Promise.all([
    page.waitForResponse(
      (res) => matchesUrl(res.url(), urlPattern) && res.request().method() === method,
    ),
    locator.click(),
  ]);
  return response;
}

function matchesUrl(url: string, pattern: string | RegExp): boolean {
  return pattern instanceof RegExp ? pattern.test(url) : url.includes(pattern);
}
```

## Network mocking & tier tags

Not every test should hit a real backend — decide deliberately and tag the decision so CI
can route it:

| Tag | Backend | When to use |
|---|---|---|
| `@ui-contract` | Mocked at the network layer (`page.route`) | Default for most e2e: fast, deterministic, tests the frontend's contract with an API shape. |
| `@real-backend` | Live backend, minimal/synthetic data | Critical journeys where the mock could drift from reality (auth, payments, anything with real integration risk). Runs per-PR or nightly depending on cost. |
| `@real-data` | Live backend + a realistic seeded dataset | Flows that depend on data shape/volume a synthetic fixture can't represent. Nightly-only lane — too slow/expensive for per-PR. |

Every `test.describe` carries exactly one of these tags (lint/CI-enforced); per-PR CI
excludes `@real-data` via `grepInvert`, nightly runs include it with `workers: 1` and extra
retries to tolerate shared-database contention.

```typescript
test.route("**/api/orders", (route) =>
  route.fulfill({ status: 200, body: JSON.stringify({ orders: [] }) }),
);
```

Mock third-party calls (payment providers, analytics) even in `@real-backend` tests — the
tier tag is about *your* backend, not every downstream dependency.

## Auth & storageState

- Log in once per "app mode" (e.g. different tenant types, admin vs regular user) in
  `globalSetup`, save the authenticated `storageState` to a JSON file, and point each
  Playwright project's `use.storageState` at the file matching that mode.
- Tests that need a *different* identity than the project default authenticate explicitly
  (a `withRole(page, role)` fixture) rather than logging in through the UI inline — logging
  in via the UI in every test is slow and turns an auth bug into hundreds of unrelated
  failures.
- Never commit a `storageState` file with real credentials; generate it in `globalSetup` or
  CI, and gitignore it.

## Test data management

- Create preconditions via API helpers, not by driving the UI — a test for "cancel an
  order" shouldn't also be testing "create an order" through five UI steps first.
- Register everything created through the `cleanup` fixture the moment it's created, so a
  test that fails halfway still leaves no orphaned data behind.
- Prefer randomized/unique values (`test-${Date.now()}-${crypto.randomUUID()}`) over fixed
  fixture data so parallel test runs don't collide on the same email/slug/order number.
- For `@real-data` tests, use a seeded reference dataset maintained specifically for that
  lane — don't let ad hoc production-like data leak into `@ui-contract` tests, it defeats
  the point of them being fast and deterministic.

## Tagging convention

Two tag families, both required on every `test.describe`:

- **Feature tag** — `@feature:<Name>`, matching a canonical feature list. Enables an
  auto-generated coverage matrix (which routes/features have e2e coverage) and keeps
  ownership traceable when a spec fails.
- **Tier tag** — exactly one of `@ui-contract` / `@real-backend` / `@real-data` (see above).

```typescript
// @feature:Checkout
// @route:/checkout
// @real-backend
test.describe("Checkout — payment", () => {
  // ...
});
```

Add `@route:<path>` when the first navigation happens inside a helper that static analysis
can't see (e.g. a `login()` helper that also navigates onward).

## Timeout constants

Never type a bare number into a `waitFor*` or `expect(...).{toBeVisible,toBeEnabled}` call.
Keep one shared file:

```typescript
// shared/timeouts.ts
export const TIMEOUTS = {
  PAGE_LOAD: 15_000,
  ELEMENT_VISIBLE: 10_000,
  DROPDOWN: 5_000,
  OPTIONAL_ELEMENT: 2_000,
  API_RESPONSE: 10_000,
  TABLE_DATA: 30_000,
} as const;
```

A magic number in a test is either a copy-pasted guess or an undocumented tuning decision —
both are worth naming.

## Parallelism & isolation rules

- `fullyParallel: true` locally and in CI by default; each test must be independently
  runnable and order-independent (see `flakiness-catalog.md` for what breaks this).
- `workers: undefined` (auto) locally, but pin `workers: 1` for any lane hitting a shared,
  stateful resource (a shared real-backend/database lane) to avoid contention.
- `retries` on CI only (e.g. `1`), never locally — a locally-flaky test should fail loudly,
  not get silently retried into a false green.
- Shard long suites (`--shard=1/4`) rather than reducing parallelism to fit a CI time
  budget.
- `test.describe.serial` is an explicit escape hatch for a handful of cases that must share
  state — treat it as rare and document why cleanup couldn't be per-test.
