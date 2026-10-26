# Named test anti-patterns

Ten names for the ways a test goes wrong. A name in a finding tells the reader
the mechanism at once and points to the fix. Names stay in English in every
report; the rest of the report is in the user's language. A finding that fits
none of them is tagged `other`.

## Grep hints are suspects, not verdicts

The patterns below are for a cheap first pass over the scoped test files, for
example `git grep -nE '<pattern>' -- <test paths>`. They use POSIX extended
regex only (inside the table cells below `\|` stands for the alternation `|`, which a
table cannot hold unescaped; type it as `|`). A hit means "read this line", nothing more: a `setTimeout` can be
a legitimate fake-timer setup, a `.skip` can carry a ticket and a reason. A hit
becomes a finding only after the surrounding test has been read. A name with no
pattern needs reading; no hit never means the file is clean.

## Catalog

| Name | Sign | How to spot it | Fix |
|---|---|---|---|
| **Liar** | The test passes while the feature is broken. | No grep; only proof. Break the code under test and run the test: if it stays green, it is a Liar (`failure_probe.py`, quality-rules rule 3). Suspects: no assertion, assertion inside a `catch`, `if` around an `expect`. | Assert the outcome the user or caller sees; re-run the failure proof after the change. |
| **Mirror** | The expected value is computed the way the code computes it, so a wrong formula passes. | Reading cue: the expectation calls the same helper or repeats the same arithmetic as the code under test. Grep for the helper's name in test files: `grep -nE '<helperName>\('`. | Hard-code the expected value from the spec or from a worked example. |
| **Mockery** | The test asserts the mock, not the behaviour. | `toHaveBeenCalled\|toBeCalled\|verify\(\|assert_called\|\.mock\.calls` on the same module that was mocked; or mocks outnumber real objects in the test. | Mock only the boundary (network, clock); assert the result of the real code. |
| **Status-only** | A UI test confirms an action by the response status or a mocked call, not by what the user sees (QAP-TC-032). | `waitForResponse\|expect\(.*status.*\)\|response\.ok\(\)\|toHaveBeenCalled` as the last assertion of a UI test. | After the action, assert the visible result: text, row, state. Keep the status check only with a comment giving the reason. |
| **Giant** | One test checks many behaviours; the first failure hides the rest and the name says nothing. | Reading cue: more than one action-then-assert round, a name with "and", a long body. Rough count: `grep -cE 'expect\(\|assert'` per test. | Split by behaviour, one reason to fail per test; share setup in a fixture. |
| **Inspector** | The test asserts internals (private fields, call order, CSS classes, state shape) and breaks on a refactor that changes no behaviour. | `\._[a-zA-Z]+\|\[\"_[a-z]+\"\]\|toHaveClass\(\|\.state\.\|getByTestId\(` used as the assertion target; `as any` casts to reach private members. | Assert through the public interface or the visible result. |
| **Chain Gang** | The test needs other tests to run first or leaves state for the next one. | `test\.describe\.serial\|describe\.serial\|\.serial\(\|@Order\|dependsOn`; module-level `let` assigned in one test and read in another. Also run the file alone, then in reverse order. | Each test creates and cleans its own data; see the shared state and order dependence sections of `flakiness-catalog.md`. |
| **Sleeper** | A fixed wait instead of waiting for a condition: slow when the app is fast, flaky when it is slow. | `waitForTimeout\(\|sleep\(\|setTimeout\(\|time\.sleep\|Thread\.sleep\|cy\.wait\([0-9]` in test files. | Wait for the condition (locator state, response, event); see timing waits in `flakiness-catalog.md` and `e2e-patterns.md`. |
| **Ghost** | A test that does not run, or runs nothing: skipped, `.only` hiding the others, empty, or a TODO. | `\.(skip\|only)\(\|xit\(\|xdescribe\(\|it\.todo\|test\.fixme\|@Disabled\|@pytest\.mark\.skip\|pytest\.skip\(`; empty bodies: `\(\) *=> *\{ *\}`. | Delete it, or fix and enable it; a skip keeps a ticket and a date. A committed `.only` is always a finding. |
| **Copycat** | Copy-pasted setup or bodies; one change has to be made in many places. | Reading cue: identical blocks across tests. Cheap pass: repeated lines such as the same `goto(`/`fill(` sequence in many tests: `git grep -nE '<a distinctive setup line>' \| wc -l`. | Move the shared part into a fixture or helper; parametrise tests that differ only in data. |

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
