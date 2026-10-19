# spec-audit on TDK: why the agents missed what the project reviewer found

**Run:** 2026-10-15, TDK Governor frontend, scope `workflows.md` + `workflow-templates.md`, baseline `0f7f4d3f99`. Skill 0.3.0.
**Ground truth:** the TDK project agent's review on 2026-10-19 of the final 16-case list.
- 8 cases were exact.
- 5 needed a fix: a wrong test level or a wrong detail.
- 3 had to be dropped or handed to product.

**Method:**
- I read both agents' transcripts (`subagents/agent-*.jsonl`, 97 + 50 tool calls) and replayed the searches behind each wrong claim.
- I re-checked every reviewer claim against the code at the baseline.

All reviewer claims I checked were correct. I could not check one: GOV-617 is a Linear ticket and is not in the repo.

## Error → root cause

| # | Reviewer finding | What the agent actually did | Root cause |
|---|---|---|---|
| 1 | "Write failures are silent" is overstated: `systemNotifications.ts` already toasts. | Call 24: `gg "MutationCache\|mutationCache\|QueryCache\(" frontend/src \| head`. `head` cut the output at 10 lines, all from `__tests__`, `userSession.ts` and `queryClient.test.ts`. `shared/notifications/model/systemNotifications.ts` was further down the list. The agent then read only `configureApiClient.ts` and `queryClient.ts` and concluded "no global error toast". | **R1: an absence claim was made from a truncated search.** |
| 2 | The Activity logs e2e already exists. | Call 11 searched only `frontend/src`. Call 66 ran `git ls-tree … frontend/e2e/src/tests \| grep … \| head -80`. The list is sorted alphabetically, so `general/*` filled all 80 lines and `onPremiseApp/workflow/workflow-activity-logs.spec.ts` was cut off. | **R1** again. |
| 3 | Storybook interaction tests do not run in CI, so they are not coverage. Cancel is therefore not covered either. | The profile lists Storybook as a test layer (`pnpm test:storybook`), and **my brief** told the agents that tests live in `*.stories.tsx`. Neither says what runs in CI. | **R2: "covered" does not check that the test runs in CI.** The profile has no CI column per layer, and the brief passed the gap on. |
| 4 | 409 on "Save and create workflow" is not covered anywhere. | The templates agent read `TemplateDetailsDialog.stories.tsx:128-172`. `CreateWorkflowStopsWhenSavingFails` mocks `save → false`, which is a generic failure, not a 409. The agent cited it as covering the 409 case. | **R3: a "covered" claim was matched by topic, not by the scenario's distinguishing condition** (the status code). |
| 5 | Wrong test level: the landing tab needs a unit test on `getDefaultWorkflowTab`, not e2e. | The output format asks for `tier: unit \| integration \| e2e` with no criteria. The agent picked e2e because the spec describes a user flow. | **R4: there is no test-level rubric** ("test where the logic lives"). |
| 6 | Wrong location: the flag logic is in the hook and the component filter, not in `configureStepHelpers`. | The agent read `workflowTemplateOptions.ts` (the hook), but proposed the test next to the existing helper test. | **R4.** |
| 7 | Template isolation must be a backend integration test, not Playwright. | **My decisions digest** said "backend is out of qa-pilot scope". The agent therefore routed a backend invariant into a Playwright API test. | **R4 + R6** (the digest pushed tests to the wrong layer). |
| 8 | "Pin that Cancel does not roll back the output" would lock in a UX bug. | The agent wrote "(documented, or fixed)", which has no single expected result. In my rewrite for the user, I turned it into "pin current behaviour". | **R5: the expected result was undecided or invented, yet presented as a test.** |
| 9 | "Redirect a direct URL to a hidden tab" was never designed; the placeholders are deliberate. | The agent invented the expected result ("redirect to the default tab"). No spec line or decision says so. In my rewrite I made it worse: "if no redirect, treat as BUG". | **R5.** |
| — | (from my own triage) The digest carried "SAP only" from spec prose. | I built the decisions digest partly from the spec text. | **R6: the main session's inputs, the digest and the brief, injected errors.** |
| — | The main-session triage did not catch #1–#4. | Triage verified **positive** claims: "this line exists, this guard is there". It never re-ran **negative** claims ("no global toast", "not covered", "no test"). | **R7: triage checks presence evidence but trusts absence claims.** |

**Pattern:**
- The agents' positive findings (bugs, drift) held up, and the reviewer confirmed every bug.
- Every error sits in one of two places:
  - a **negative claim** ("does not exist", "not covered");
  - a **prescription** (test level, expected result).
- The lenses only demand evidence for positive claims (`file:line`). Absence claims need a different kind of evidence, which is the search itself, and nothing asks for it.

## How to strengthen the skill

Each fix below is cheap to apply, except S4. The pilot data suggests R1 and R7 account for most of the damage.

### S1. Evidence standard for absence claims (fixes R1, R2, R3)
Add to `spec-audit-lenses.md` §2:
- Every "missing", "not covered", "no handler" or "no guard" claim must cite **the search that proves it**. That means the exact command and its match count.
- **Never** pipe a proving search through `head` or `cut`. Run `| wc -l` first. If the output is too long, narrow the pattern; do not truncate it.
- Search at least three ways:
  - the feature name (`activity.?log`, case-insensitive);
  - the route or path;
  - a testid or UI string.

  Search across **all** test roots from the profile, not just `src/`.
- Before calling a failure "silent", search for **global error plumbing**: query/mutation cache subscribers, `onError` in providers, fetch interceptors, `unhandledrejection` listeners, error boundaries. Then state which status codes and bodies it covers.
- **"Covered in code" requires three things:**
  - the test's path:line;
  - the assertion line that checks the scenario's **distinguishing condition** (status code, branch, input class);
  - proof that the layer **runs in CI** (from the profile).

  Otherwise the scenario is a "gap", or "covered but not in CI".

### S2. Triage re-runs absence claims (fixes R7)
Add to `SKILL.md` Phase 5:
- The main session re-runs the proving search for every absence claim that a P1/P2 or a "covered" verdict depends on.
- Use an untruncated search with a different pattern from the agent's.
- Absence claims are the weakest evidence, so they get verified first.

### S3. Test-level and expected-result rules (fixes R4, R5)
Add to the lenses' scenario format:
- **Level rubric:**
  - pure logic (a function, a mapper, a decision table in code) → a unit test on that function;
  - a hook or component branch → a component or hook test;
  - a backend invariant or guard → a backend integration test in the backend's own suite, even when qa-pilot only *writes* frontend tests (mark it "backend owner");
  - e2e only for a user-visible flow that crosses layers.
- Name the **file or function under test**, read from where the logic actually lives.
- Every scenario needs **one expected result with a source**: a spec line, a decision, or an existing convention with path:line.
  - If the expected result is undecided, invented, or would pin a suspected bug, the item goes to a **"Needs product decision"** bucket, never to the scenarios.
  - "Documented or fixed" is not allowed.
- When proposing a mocked test, say **why the mock is not masked**, e.g. "a 500 with an empty body, because `systemNotifications` toasts only when `message` is present".

### S4. A profile that knows what runs in CI (fixes R2 at the source)
Add to `onboard` → `project-profile.md`:
- a "Test layers" table: layer · path · command · **runs in CI (job name) or not** · being phased out?
- the global error/notification plumbing, if any. It is cheap to record once and expensive to rediscover in every audit.

### S5. Main-session inputs (fixes R6)
- **Decisions digest:** only from decision sources (CLAUDE.md, ADRs, recorded owner decisions, test-strategy non-goals). **Never from the spec under audit.**
- Each bullet keeps its source path. If a bullet only paraphrases a spec, drop it.
- **Phase 0 asks for owner scope filters together with the traits**, for example: modes or platforms not developed, areas on hold (a role-model redesign), test types not wanted. TDK needed two extra rounds because of this.
- Persist the filters in `docs/qa/rule-overrides.json` under a new `scope` block, so the next run starts with them.
- **Do not describe test locations in the brief by hand.** Point the agent at the profile's test-layers table.

### S6. Output for humans and agents (fixes the format problem)
Phase 6 writes **two artifacts**:
1. `…-actions.md`, the primary output. It is an English list an implementation agent can run:
   - "Bugs: fix, then test" (with location, fix, test level);
   - "Tests to add";
   - "Needs product decision";
   - "Already covered (with CI-running evidence)".

   It has no P-codes and no rule ids.
2. The technical report (P1/P2/P3, rule ids, re-grade log), kept as the evidence trail.

### S7. Regression eval from this run
We now have labelled ground truth: the reviewer's 16 verdicts on TDK at `0f7f4d3f99`.
- Re-run the same scope after S1–S6.
- Score:
  - no false absence claims (cases 1, 2, 3, 4 must not reappear);
  - correct levels for cases 5, 6 and 7;
  - cases 8 and 9 land in "Needs product decision";
  - all 5 bugs still found.
- Cost: about 450k tokens. Run it only after the changes are approved.

## Suggested order
1. S1 + S2 + S3: edits to `spec-audit-lenses.md` and `SKILL.md`. They are the highest leverage and only text changes.
2. S5 + S6: SKILL.md Phase 0 and Phase 6, plus a `scope` block in `rule_overrides` (small script change, with tests).
3. S4: an onboard profile section. It touches another skill, and TDK's profile would need the new section.
4. S7: re-run on TDK and compare against the reviewer's verdicts.
