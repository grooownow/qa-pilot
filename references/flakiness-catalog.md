# Flakiness Catalog

> Distilled from production Playwright experience across several real projects.

A field guide to why Playwright e2e tests go flaky, organized as symptom → root cause →
fix. Consult this when a test fails intermittently before reaching for a retry or a longer
timeout — both usually paper over one of the causes below instead of fixing it.

## Timing waits

**Symptom:** test passes locally, fails intermittently in CI (or the reverse); adding a
longer `waitForTimeout` "fixes" it for a while, then it comes back.

**Root cause:** the test is waiting on a fixed clock instead of a real signal. CI machines
are slower/noisier than a dev laptop, so any fixed sleep is either too short under load or
wastefully long the rest of the time.

**Fix:** replace every `page.waitForTimeout()` with a web-first assertion or
`waitForResponse` tied to the actual condition the test cares about (element visible,
network call resolved, URL changed). See `e2e-patterns.md` — waiting strategy.

## Race conditions with network

**Symptom:** an action's effect is asserted immediately after a click, and sometimes the
assertion runs before the triggering request has resolved.

**Root cause:** `click()` returns as soon as the click event fires, not when whatever it
triggered (an API call, a re-render) finishes.

**Fix:** use `clickAndWaitForResponse` (see `e2e-patterns.md`) to wait on the specific
response the click triggers before asserting on its effect. Don't blanket-wait on
`networkidle` — pages with polling, analytics beacons, or websockets never go idle, so that
wait either times out or waits far longer than necessary.

## Shared state between tests

**Symptom:** a test fails only when run after a specific other test, or only in full-suite
runs, never in isolation (`test.only`).

**Root cause:** two tests touch the same record (same seeded user, same fixed slug, a
global feature flag) and one test's side effect leaks into the next.

**Fix:** generate unique data per test (`test-${Date.now()}-${crypto.randomUUID()}`), and
use the cleanup fixture so every test tears down what it created. Never assert on global
counts ("there are 3 items in the list") in a suite that runs in parallel — assert on the
item you created instead.

## Order dependence

**Symptom:** suite is green with `fullyParallel: false` / `workers: 1`, red with
parallelism on, or green only when files run in a specific order.

**Root cause:** a test relies on setup performed by an earlier test rather than its own
fixtures — often a symptom of tests that grew as a chain instead of independent units.

**Fix:** every test must be runnable alone. If a flow genuinely needs multi-step shared
state, use an explicit `test.describe.serial` block with its own `afterAll` cleanup —
don't rely on file execution order, which Playwright does not guarantee under parallelism.

## Animations & transitions

**Symptom:** a click lands on the wrong coordinates, or a screenshot diff fails, only on
elements that slide/fade in.

**Root cause:** Playwright's actionability checks wait for an element to be stable, but a
CSS transition can still be mid-flight when the check passes, or a screenshot can be taken
mid-animation.

**Fix:** prefer asserting on the end state (`toBeVisible`, `toHaveText`) rather than timing
the animation. For visual snapshots, disable animations for the test (a small `page.addStyleTag`
that sets `animation-duration: 0s !important; transition-duration: 0s !important` scoped to
test runs) rather than adding a wait long enough to outlast the longest transition.

## Unstable selectors

**Symptom:** a test breaks on an unrelated styling or refactor PR, with no behavior change.

**Root cause:** the locator targets a CSS class, DOM position (`nth-child`), or generated
class name, none of which are part of the component's contract with its users.

**Fix:** switch to a stable `data-testid` exported as a named constant from the component,
or a semantic role locator. Text-based locators are not a fix — they trade DOM-flakiness
for copy/translation-flakiness. See `e2e-patterns.md` — locator strategy.

## Real-backend data drift

**Symptom:** an `@real-backend` or `@real-data` test passes for weeks, then starts failing
with no related code change — usually an assertion on a specific count, label, or record
that has since changed upstream.

**Root cause:** the test asserts on live or shared data instead of data it created and
owns, so it's coupled to whatever state that backend happens to be in in.

**Fix:** create the exact records the test needs via API helpers and assert only on those;
don't assert on totals or on records the test doesn't control. For the `@real-data` tier,
keep the seeded reference dataset under version control and regenerate it deliberately
rather than letting it drift silently.

## Viewport & font rendering

**Symptom:** visual regression / screenshot tests fail only in CI, or only on one OS,
with sub-pixel differences nobody can see by eye.

**Root cause:** font rendering and anti-aliasing differ across OS/font availability; a
locally-installed font isn't present in the CI image, so text reflows slightly.

**Fix:** pin a consistent viewport size in config, run screenshot tests against a
containerized browser image with pinned fonts (matching whatever CI uses), and set a
reasonable `maxDiffPixels`/threshold rather than requiring pixel-perfect equality.

## Dev-server reuse on the wrong port

**Symptom:** a test suite reports the app is in a state it shouldn't be in yet (e.g. looks
already authenticated, or shows stale copy from a previous branch) even though the test
just started.

**Root cause:** Playwright's `webServer.reuseExistingServer` (or an equivalent
"start if not already running" convenience) finds *some* process already answering on the
configured port and reuses it — but that process may be a stale server from a previous
run, a different branch/worktree, or a leftover background process, not the one this test
run just built. The suite then drives a completely different build while believing it
started fresh.

**Fix:** check what's actually listening on the target port before trusting
`reuseExistingServer`; when in doubt, bind an explicit port for this run and verify the
server's version/health endpoint (or a build marker) rather than assuming reuse is safe.
See `browser-hygiene.md` for the full dev-server lifecycle.

## CI-only flakes

**Symptom:** never reproduces locally, no matter how many times you run it.

**Root cause:** usually one of: CI is resource-constrained (shared CPU → slower
actionability timing), CI runs with more parallel workers than your machine (more
contention on shared fixtures/data), or CI environment variables/secrets differ subtly
from local `.env`.

**Fix:** reproduce locally with the same worker count and retries as CI
(`--workers=<ci-value>`); check for hardcoded assumptions about timing headroom; diff the
CI env against local `.env` for anything the test implicitly depends on. If it still won't
reproduce, capture trace + video on the CI run itself (see `e2e-patterns.md` config) rather
than guessing blind.

---

## Managed quarantine (the disciplined way to handle a flaky test)

Deleting a flaky test loses coverage; leaving it flaky wastes everyone's time re-running
CI. The middle path is an explicit, reviewable quarantine registry — never an inline
`test.skip()` or `.fixme()` that quietly rots.

### YAML registry

```yaml
# flaky-tests.yaml
"checkout.spec.ts > Checkout — payment > declined card shows an error":
  status: flaky
  owner: "@alice"
  expires: 2026-08-15
  reason: "Intermittent 3s delay on the payment webhook in CI; tracked in TICKET-123"

"orders.spec.ts > Orders > filters by date range":
  status: needs-data
  owner: "@bob"
  expires: 2026-07-30
  reason: "Depends on seeded dataset not yet available in the real-data lane"
```

Three statuses cover the common cases:

- `flaky` — known intermittent failure; still runs, but a failure doesn't block CI (the
  reporter reclassifies it as non-blocking rather than red).
- `needs-data` — blocked on test data / environment that doesn't exist yet.
- `slow` — correct but exceeds the default timeout; given a longer budget instead of being
  marked unreliable.

### Custom test wrapper

A single base `test` every spec imports reads the registry and applies the annotation —
this is also the enforcement point that makes the registry authoritative instead of
decorative.

```typescript
// fixtures/test.ts
import { test as base, type TestInfo } from "@playwright/test";
import { parse } from "yaml";
import { readFileSync } from "node:fs";

type Entry = { status: "flaky" | "needs-data" | "slow"; owner: string; expires: string; reason: string };

function loadRegistry(): Record<string, Entry> {
  const raw = readFileSync("flaky-tests.yaml", "utf-8");
  let parsed: unknown;
  try {
    parsed = parse(raw);
  } catch (err) {
    // Fail loud, not silent: a malformed registry must break CI immediately,
    // not silently stop applying quarantine annotations.
    throw new Error(`flaky-tests.yaml is malformed: ${(err as Error).message}`);
  }
  return (parsed ?? {}) as Record<string, Entry>;
}

const registry = loadRegistry();

export const test = base.extend({});

test.beforeEach(async ({}, testInfo: TestInfo) => {
  const key = `${testInfo.titlePath.slice(1).join(" > ")}`;
  const entry = registry[key];
  if (!entry) return;
  if (new Date(entry.expires) < new Date()) {
    throw new Error(
      `Quarantine entry for "${key}" expired on ${entry.expires} — fix it or renew the entry (owner: ${entry.owner}).`,
    );
  }
  if (entry.status === "flaky") testInfo.annotations.push({ type: "flaky", description: entry.reason });
  if (entry.status === "needs-data") test.skip(true, entry.reason);
  if (entry.status === "slow") testInfo.setTimeout(testInfo.timeout * 3);
});

export { expect } from "@playwright/test";
```

Key properties worth keeping if you build your own version:

- **Fail loud on a malformed file.** A YAML parse error should break the whole CI run, not
  silently drop every quarantine entry (which would either hide known flakes as failures or,
  worse, cause a giant swath of "needs-data" skips to start actually running unexpectedly).
- **Expiry is enforced, not decorative.** An expired entry throws instead of continuing to
  quarantine — this is what stops quarantine from becoming permanent.

### The rule: quarantine is temporary

- Every entry needs an **owner** and an **expiry date**. No anonymous, open-ended entries.
- An expired entry breaks the build until someone either fixes the test or deliberately
  renews the entry with a new expiry and a reason — renewal is a conscious decision, not a
  default.
- Track quarantine count as a metric worth watching: a registry that only grows is a sign
  the underlying flakiness sources above aren't being fixed, just hidden.
