# Browser & Dev-Server Hygiene

> Distilled from production Playwright experience across several real projects.

Browser-driven verification (Playwright MCP, chrome-devtools MCP, or any tool that drives a
real browser against a real dev server) is the single biggest source of runaway memory and
zombie processes in agent-driven workflows. A single Chromium tab can balloon to tens of GB;
several un-closed tabs, or more than one agent driving a browser at once, compound it fast
enough to hang the machine. Treat both the browser and the dev server as scarce, leaky
resources that must be explicitly managed, not fire-and-forget.

## Dev-server lifecycle

1. **Check the port before starting anything.** Someone (a human, a parallel agent) may
   already be running a dev server on the default port for other work.
   ```bash
   lsof -ti :3000
   ```
   If that returns a PID, do **not** kill it blindly — it may be someone else's live work,
   and it may be serving a different branch/checkout than the one you're about to verify.
   Killing it either destroys someone's session or, worse, lets you go on to test against
   the wrong code while believing you tested your own.
2. **Start your own server on a different port** if the default is occupied
   (`PORT=3100 pnpm dev`), or use a production build (`build && start`) for a more faithful,
   more stable render than a dev server with hot-reload churn.
3. **Record what you started**: PID and port, written down (not just held in your head) so
   cleanup later is unambiguous even across a context reset.
4. **Wait for ready** by polling the URL/health endpoint before pointing a browser at it —
   don't guess a fixed sleep.
5. **Beware "reuse existing server" settings.** Playwright's `webServer.reuseExistingServer`
   (and equivalents in other tools) will happily reuse *whatever* is already listening on the
   configured port — including a stale server from a previous run, a leftover background
   process, or a server for a different branch. A reused-but-stale server is how you get a
   test run that looks already authenticated, or renders old copy, while the runner believes
   it just started fresh. If you didn't explicitly start the server this run, verify it
   before trusting it (health/version endpoint, or just check the PID against what you
   expect) rather than assuming reuse is safe.
6. **Reap it when done, and only what you started.** `kill <pid>` the moment verification is
   finished — don't wait for end-of-session cleanup to be the only safety net, and never
   kill a server you didn't start yourself.

A fresh worktree/checkout typically needs its own `node_modules` and a copied
gitignored env file for its dev server to boot — don't assume a sibling checkout's install
is shared.

### Polling for readiness

Poll the health/URL, don't sleep-and-hope:

```bash
url="http://localhost:3100"
for i in $(seq 1 30); do
  if curl -sf "$url" > /dev/null; then
    echo "ready after ${i}s"
    break
  fi
  sleep 1
done
```

Cap the loop (here, 30 attempts) and fail with a clear message if it never comes up —
see Retry caps below.

## One browser, reused, closed immediately

- **One context, one page, reused across every check.** Navigate the same tab through each
  state you need to verify — do not open a new tab per state or per screenshot. Each open
  tab is a standing memory cost even when idle.
- **Never run two browser-driving sessions in parallel** against the same machine. Sequence
  the work instead; the memory cost compounds faster than the time saved.
- **Close it the moment you're done** — call the tool's close/`tabs_close` equivalent right
  after the last check, not "later" or "at the end of the whole task." Don't rely on a
  final cleanup phase as the only place the browser gets closed; if that phase is skipped or
  the session ends early, the browser is still running.
- **Keep the surface small.** Use a reasonable viewport, not a 4K canvas; avoid reloading
  heavy pages in a loop; cap screenshots to the states you actually need evidence for; don't
  leave trace/video recording on for longer than the specific debugging session that needs
  it (see `e2e-patterns.md` for when trace/video are worth the overhead in CI).

## Memory watch

Sample RSS before and after any heavy browser/e2e step — don't wait for the machine to
become obviously sluggish before checking:

```bash
# top memory consumers (RSS in MB): overall, and the browser/node/dev-server specifically
ps -A -o rss=,pid=,comm= | sort -rn | awk '{$1=int($1/1024)" MB"; print}' | head -12
```

Thresholds:

- If a `Chromium` / `node` / dev-server process climbs past **~4–6 GB RSS**, stop driving it
  — close the browser or kill the process and restart clean rather than pushing on with a
  process that's already ballooning.
- If usage still won't come back down after closing/killing, **stop and escalate** rather
  than continuing on a thrashing machine. A memory leak that survives a close is a signal
  something is wrong (a stray process, a retained reference), not something to work around
  by pushing forward.

## Retry caps

- Cap retries on flaky browser interactions (an element not yet actionable, a navigation
  that hasn't settled) to a small fixed number (2–3) with a real wait condition between
  attempts — not an unbounded loop and not a longer fixed sleep. If it still doesn't
  succeed after the cap, that's a signal to fix the underlying wait condition (see
  `flakiness-catalog.md`), not to raise the cap.
- The same applies to dev-server readiness polling: cap the number of poll attempts with a
  sane total timeout, and fail with a clear message ("server never became ready on
  :3100 after 30s") rather than hanging indefinitely.

## What to screenshot, and when

- One screenshot per meaningful **state**, not per action — the states a spec/ticket
  actually defines (empty, loading, error, validation, success, disabled), not every
  intermediate frame.
- Both viewports (mobile + desktop) only when the design actually differs between them —
  don't double every screenshot by default.
- Capture the console alongside the screenshot when verifying a state, not after the fact —
  a clean-looking screenshot with a console error underneath is not a pass.
- Skip the screenshot when a state genuinely can't be reached in this session (e.g. the only
  available port was someone else's server) — say so explicitly instead of screenshotting
  the wrong thing and implying it was verified.

## Cleanup checklist (end of session)

- [ ] Every dev server you started is killed (`kill <pid>`); none left running past the task.
- [ ] Browser/browser context is closed — no lingering Chromium process.
- [ ] `ps` RSS check shows no runaway `node`/`Chromium`/dev-server process left behind.
- [ ] Any trace/video/screenshot files produced for debugging are either attached as
      evidence or deleted — don't leave scratch artifacts in the repo.
- [ ] If any state could not be verified (port conflict, missing data), that gap is stated
      explicitly in the report rather than implied as covered.

## Common mistakes

- **Killing a server you didn't start** because it happened to be on "your" port. Verify
  ownership (PID, what it's serving) before touching anything you didn't launch.
- **Trusting a green run because the app rendered** without checking *which* build rendered
  it — a stale reused server can render a plausible-looking, wrong page.
- **Leaving a browser open "just in case"** you need one more screenshot. Close it; reopen
  if genuinely needed. The idle cost is not free.
- **Treating a hung `kill` as done.** If a process doesn't die and free its memory, that's a
  signal to investigate, not to move on assuming it will clean itself up eventually.
- **Screenshotting every click** instead of every state. This produces a wall of redundant
  images that hide the one that actually shows the bug.

<!-- qa-pilot · © 2026 Ludvik4 · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
