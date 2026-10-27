# Named test anti-patterns

Ten names for the ways a test goes wrong. A name in a finding tells the reader
the mechanism at once and points to the fix. Names stay in English in every
report; the rest of the report is in the user's language. A finding that fits
none of them is tagged `other`.


## Grep hints are suspects, not verdicts

The patterns in "Grep hints" below are for a cheap first pass over the scoped
test files: `git grep -nE '<pattern>' -- <test paths>`. They are POSIX extended
regex and work with both GNU and BSD (macOS) grep. A hit means "read this line",
nothing more: a `setTimeout` can be a legitimate fake-timer setup, a `.skip` can
carry a ticket and a reason. A hit becomes a finding only after the surrounding
test has been read. A name with no pattern needs reading; no hit never means the
file is clean.

## Catalog

| Name | Sign | How to spot it | Fix |
|---|---|---|---|
| **Liar** | The test passes while the feature is broken. | No grep; only proof. Break the code under test and run the test: if it stays green, it is a Liar (`failure_probe.py`, quality-rules rule 3). Suspects: no assertion, assertion inside a `catch`, `if` around an `expect`. | Assert the outcome the user or caller sees; re-run the failure proof after the change. |
| **Mirror** | The expected value is computed the way the code computes it, so a wrong formula passes. | Reading cue: the expectation calls the same helper or repeats the same arithmetic as the code under test. Grep hint: Mirror. | Hard-code the expected value from the spec or from a worked example. |
| **Mockery** | The test asserts the mock, not the behaviour. | Grep hint: Mockery, on the module that was mocked; or mocks outnumber real objects in the test. | Mock only the boundary (network, clock); assert the result of the real code. |
| **Status-only** | A UI test confirms an action by the response status or a mocked call, not by what the user sees (QAP-TC-032). | Grep hint: Status-only, when it is the last assertion of a UI test. | After the action, assert the visible result: text, row, state. Keep the status check only with a comment giving the reason. |
| **Giant** | One test checks many behaviours; the first failure hides the rest and the name says nothing. | Reading cue: more than one action-then-assert round, a name with "and", a long body. Grep hint: Giant. | Split by behaviour, one reason to fail per test; share setup in a fixture. |
| **Inspector** | The test asserts internals (private fields, call order, CSS classes, state shape) and breaks on a refactor that changes no behaviour. | Grep hint: Inspector, when the hit is the assertion target; `as any` casts to reach private members. | Assert through the public interface or the visible result. |
| **Chain Gang** | The test needs other tests to run first or leaves state for the next one. | Grep hint: Chain Gang; module-level `let` assigned in one test and read in another. Also run the file alone, then in reverse order. | Each test creates and cleans its own data; see the shared state and order dependence sections of `flakiness-catalog.md`. |
| **Sleeper** | A fixed wait instead of waiting for a condition: slow when the app is fast, flaky when it is slow. | Grep hint: Sleeper. | Wait for the condition (locator state, response, event); see timing waits in `flakiness-catalog.md` and `e2e-patterns.md`. |
| **Ghost** | A test that does not run, or runs nothing: skipped, `.only` hiding the others, empty, or a TODO. | Grep hint: Ghost. | Delete it, or fix and enable it; a skip keeps a ticket and a date. A committed `.only` is always a finding. |
| **Copycat** | Copy-pasted setup or bodies; one change has to be made in many places. | Reading cue: identical blocks across tests. Grep hint: Copycat. | Move the shared part into a fixture or helper; parametrise tests that differ only in data. |

## Grep hints

Paste each line after `git grep -nE`, quoted. Liar has no hint.

- **Mirror:** `<helperName>\(` (put the name of the helper the code under test uses)
- **Mockery:** `toHaveBeenCalled|toBeCalled|verify\(|assert_called|\.mock\.calls`
- **Status-only:** `waitForResponse|expect\(.*status.*\)|response\.ok\(\)|toHaveBeenCalled`
- **Giant:** `expect\(|assert` (`git grep -cE` counts per file; read the tests in the files with the most hits)
- **Inspector:** `\._[a-zA-Z]+|\["_[a-z]+"\]|toHaveClass\(|\.state\.` (a `data-testid` locator is not an Inspector: it is the stable selector most suites are told to use)
- **Chain Gang:** `describe\.serial|\.serial\(|@Order|dependsOn`
- **Sleeper:** `waitForTimeout\(|sleep\(|setTimeout\(|time\.sleep|Thread\.sleep|cy\.wait\([0-9]`
- **Ghost:** `\.(skip|only)\(|xit\(|xdescribe\(|it\.todo|test\.fixme|@Disabled|@pytest\.mark\.skip|pytest\.skip\(`
- **Ghost, empty bodies:** `\(\) *=> *\{ *\}` (also matches harmless no-op callbacks such as `onClick={() => {}}`; only an empty test body counts)
- **Copycat:** a distinctive setup line, e.g. `page\.goto\('/cart'\)`; a count (`git grep -cE`) above a few is a cue

A `toHaveBeenCalled` hit matches both Mockery and Status-only: name it Status-only when it is the last assertion of a UI test, Mockery otherwise.

## Tagging in reports

Write the name in brackets in front of the finding title:
`[Critical] [Sleeper] Fixed 3 s wait before the cart badge check`. The report
groups findings by name inside each severity.

## Example

A Phase 1 first-pass count for a small shop suite, and one finding it led to:

| Name | Pattern hits | Read, confirmed |
|---|---|---|
| Sleeper | 14 | 11 |
| Ghost | 3 | 3 |
| Status-only | 6 | 4 |

`[Important] [Status-only] checkout.spec.ts:48` — the test clicks "Pay" and
asserts `response.status() === 200`; it never checks the confirmation page.
Fix: assert the order number is visible after the click.

<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
