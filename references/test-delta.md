# Test delta: shared rules for deciding which tests to add or change

Four skills share this file: `plan-tests`, `cover`, `task-qa` and `spec-audit`. It sets how much testing is enough, how to prove that something is covered, and when an agent may write a test without asking.

The main rule: **cover what is critical, highlight the rest.** Products change fast. A test suite that pins every detail costs more than the bugs it catches. A missed critical pattern, such as modify-vs-delete, costs more than a dozen edge-case tests.

## 1. Depth

| Depth | Includes | Use when |
|---|---|---|
| **smoke / critical** | Happy paths of critical flows. The must-check web patterns (`web-patterns.md`) for entities on those flows. | A quick pass, a project-level audit, a low-risk or fast-changing area |
| **standard** (default) | The above, plus main error states, the must-check patterns for every touched entity, the 2–3 nastiest edge cases, and a regression guard for adjacent behaviour | Most features and tasks |
| **thorough** | The above, plus the role/permission matrix, a sweep of concurrency and interruption cases, and a data-boundary sweep. Highlight items are drilled into scenarios. | Auth, payments, destructive operations, or when the owner asks |

**Volatility lowers depth.** For an area that changed a lot in the last 30 days (`git log --since=30.days -- <path> | wc -l`), prefer one level lower and push tests down the pyramid. Must items are never dropped.

## 2. Buckets

| Bucket | Contents | Cap |
|---|---|---|
| **Must** | P1, any BUG, or P2 on a critical flow (`## Critical flows` in the profile) | None. Above 10, tell the owner to narrow the scope. |
| **Should** | Other P2 | ≤8 per feature, ≤5 per task. Keep the ones with the highest risk on the most-used flows. |
| **Highlight** | P3, and P2 items that did not fit the cap | One line each; no test is prescribed |
| **Question** | Product questions: the expected result is undecided | Separate; never counts toward the caps |

Severity comes from `severity-calibration.md`. Owner scope filters remove the test but not the visibility: the item goes to **Suppressed by your filters** as one line.

## 3. Gap classes for an existing behaviour

- **Covered**: passes the three proofs below.
- **Partially covered**: the happy path is proven, but an error or edge case is not, or the other way round.
- **Covered but not in CI**: the test exists in a layer CI does not run (see `## Test layers` in the profile). Treat it as a gap.
- **Outdated**: the test is green but asserts the *old* contract after an intended change. It is a gap, and the test must change.
- **Uncovered.**

## 4. The three proofs of "covered"

1. **The test** at `path:line`.
2. **The assertion** checks the scenario's *distinguishing condition*: the status code, the branch or the input class. A test of a neighbouring case does not count.
3. **The layer runs in CI**, per `## Test layers` in the profile.

If any proof is missing, it is a gap. "Not covered" is an absence claim: cite the search (command → match count, untruncated, at least three angles: name, route/API, testid or visible text).

## 5. Each prescribed test

- **What:** one concrete line, for example "rename to a taken name shows the conflict error and keeps the dialog open".
- **Expected:** one result, with its **source**. Valid sources:
  - a spec or AC line;
  - a project decision;
  - a web invariant `QAP-WINV-…`;
  - an existing convention elsewhere in the code (path:line).

  The changed code itself is **never** a valid source (QAP-AIQA-002).
- **Level:** where the logic lives:
  - pure function → unit;
  - hook or component branch → component/unit;
  - backend guard or query scope → backend integration, `owner: backend`;
  - cross-layer flow → e2e.
- **Target:** the function, hook or component at path:line. Not the nearest test file.
- **BUG mark:** the current code fails the expected result. The code is fixed first, and the test must fail without the fix.

No source means it is a **question**, not a test.

## 6. Auto-test guard

`task-qa verify` and `cover` may write tests without a separate approval of each batch only when all of these hold:

- every test has a sourced expected result (§5);
- a test that marks a BUG has been run and **failed** against the unfixed code;
- at most **5 new tests per task**, and at most **1 new e2e**;
- no code fix is applied. BUG fixes, spec or AC edits, and deleting or weakening an existing test always go to the owner first.

Anything beyond that goes to the owner as a list. Silence is not approval.
