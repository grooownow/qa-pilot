# Playwright E2E Patterns

> Distilled from production Playwright experience across several real projects.

The canonical how-to for writing Playwright end-to-end tests in this project. Load this
before writing or reviewing any e2e spec. It sets defaults — a project's own testing docs
win on conflict.

## Quick checklist

- One `test.describe` per spec file; the file name and describe title both name the feature.
- Locate every element by `data-testid`; if it is missing, add it to the component. A role or
  text locator only when a test id cannot be added, with a `// no testid: <reason>` comment
  (see Locator strategy); never CSS classes or `nth-child`.
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
import { CHECKOUT_TEST_IDS } from "@app/checkout/testIds"; // constants owned by the component

export class CheckoutPage {
  constructor(private readonly page: Page) {}

  // Locators are private and lazy — built on access, not in the constructor.
  // Test ids first (survive restyling and translation); bare roles where unambiguous.
  private el = {
    cardNumber: (): Locator => this.page.getByTestId(CHECKOUT_TEST_IDS.cardNumber),
    expiry: (): Locator => this.page.getByTestId(CHECKOUT_TEST_IDS.expiry),
    payButton: (): Locator => this.page.getByTestId(CHECKOUT_TEST_IDS.payButton),
    errorBanner: (): Locator => this.page.getByRole("alert"),
  };

  // Methods are business actions, not "fillCardNumber" + "clickPay" busywork.
  async payWithCard(cardNumber: string, expiry: string): Promise<void> {
    await this.el.cardNumber().fill(cardNumber);
    await this.el.expiry().fill(expiry);
    await this.el.payButton().click();
  }

  // Return the locator, not its text: the test asserts with a retrying web-first assertion.
  errorBanner(): Locator {
    return this.el.errorBanner();
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
    await expect(pages.checkout.errorBanner()).toContainText("declined");
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

**Hard rule: every element a test touches is found by `data-testid`.** A missing test id is
not a reason to fall back to a role or a text: **add the test id to the component** as part of
writing the test. This is not a code fix — it changes no behaviour — and the auto-test guard
allows it (test-delta §6).

- Export `data-testid` values as named constants from the component that owns them, not as
  string literals sprinkled through tests. A rename becomes a one-file diff instead of a
  find-and-replace across specs.
- **Fall back only when a test id cannot be added.** Before falling back, try in this order:
  1. pass it through the component's props (`data-testid`, `inputProps`, `slotProps`,
     `PaperProps` and the like — most UI libraries forward `data-*`);
  2. put it on the nearest element you own (a wrapper or container) and find the inner
     element inside it;
  3. only then a fallback locator, scoped inside an element found by test id.

  Cases where a test id is impossible: markup of a third-party library that forwards no
  props and cannot be wrapped; a cross-origin iframe or external widget (payment form,
  captcha, maps); generated or vendored code you must not edit; native browser UI (file
  chooser, permission and print dialogs).
- **Fallback order** (only in those cases):
  1. `getByRole` without a text name (e.g. `getByRole("dialog")`) — language-independent;
  2. `getByRole`/`getByLabel` with a name — breaks on copy edits and on every non-default
     locale; on multilingual projects only with a locale-independent source (translation-key
     lookup or a pinned test locale);
  3. `getByText` — only when the text itself is the behaviour under test.

  Every fallback carries a comment with the reason: `// no testid: <library> renders this
  without forwarding props`. A fallback without that comment is a finding.
- Never `.locator('.some-class')`, XPath or `nth-child` — they break the moment styling or
  DOM order changes, independent of any user-visible change.
- Asserting a visible text is fine (it is the result the user sees); find the element by test
  id and assert its text.
- Test ids are hooks for tests, not a replacement for accessibility: if an interactive
  element has no role or accessible name at all, flag the component — screen-reader users
  hit the same wall the locator did.
- A project that documents a different locator policy (in its own rules, see the profile's
  Conventions) keeps it: project rules win (`quality-rules.md` rule 6). Without such a rule,
  this hard rule applies.

## Waiting strategy

- Web-first assertions (`expect(locator).toBeVisible()`, `.toHaveText()`, `.toBeEnabled()`)
  auto-retry until the timeout; they are the default and cover most cases.
- `page.waitForResponse(...)` when a test needs to assert on the network call itself (status
  code, response body) **in addition to** the resulting UI state. The final assertion of a UI
  test is what the user sees (QAP-TC-032): a 200 on delete with the row still in the list is
  a passing test over a bug.
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

## Accessibility check

An automated scan catches the mechanical part of accessibility (missing names, contrast, invalid ARIA); it does
not replace a manual check.

- Scan each critical-flow page that is in the smoke set with axe (`@axe-core/playwright`), after the page has
  reached its final state (a web-first assertion on a visible element first, never a fixed pause).
- Violations with impact `serious` or `critical` fail the test. `minor` and `moderate` are reported (printed or
  attached), not failed.
- A known violation that cannot be fixed now is excluded by rule id with a `// a11y: <reason>, <ticket>`
  comment, not by dropping the page from the scan.
- Only when the project already has axe, or the owner accepts it. If it is missing, show the exact install list
  (package `@axe-core/playwright` with a version, the package-manager command, the files it changes:
  `package.json` and the lockfile) and install only after an explicit yes to that list. A yes covers that list
  only; anything added later is asked again. Never install globally, never touch CI.
- Storybook projects: `addon-a11y` plays the same role for components.

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
