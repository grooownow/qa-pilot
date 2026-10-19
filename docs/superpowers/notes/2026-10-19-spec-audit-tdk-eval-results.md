# spec-audit 0.4.0 regression eval on TDK: results

**Setup:**
- Rubric: `2026-10-19-spec-audit-tdk-eval-rubric.md` (21 checks from the TDK reviewer's verdicts).
- Same scope, baseline (`0f7f4d3f99`), traits and scope filters as v1.
- Two cluster agents on the session model, briefed per SKILL.md 0.4.0.
- The audit profile carried the Test layers and Error plumbing sections, filled in Phase 0.
- The decisions digest was built from decision sources only.
- Raw findings are local in TDK: `frontend/docs/qa/spec-audit/.work/workflows-templates-v2/`.

## Score

| | v1 (0.3.0) | v2 (0.4.0) |
|---|---|---|
| Pass | ~6 | **14** |
| Partial | ~3 | 5 |
| Fail | ~11 | **2** |
| False absence claims (verified) | 4 (#1 overstated, #6, #16 Cancel, 409 "covered") | **0** found |
| Items violating owner scope filters | n/a (filters given after the run) | 0 |
| Agent tokens | ~463k | ~508k |

The v1 column is scored retrospectively on the same rubric. "~" marks a judgement call on partial items.

## Per check (v2)

**Pass (14):**
- G1: PDF download found as a BUG, with a 404 mock and "bypasses the cache".
- G3: mocks are a 404 or an empty-body 500; no "500 with a message is silent" claim.
- G7: the data-source failure `—` is reported.
- G8: Activity logs is not a gap. The agent also found the platform-mode spec drift.
- G10: Cancel in the run modal goes to product decision.
- G12: the input = output confirmation is placed on Create, and the agent noticed that the existing e2e tests wait for it only optionally.
- G14: hidden tabs are not treated as a BUG or as a redirect test.
- G15: the cross-project id becomes a backend integration test (`owner: backend`).
- G16: Save as template is a P2 gap, and the 422 shows as a toast.
- G17: the wrong template kind is a hook unit test.
- G18: discard on ×/backdrop is e2e. Cancel is correctly cited as covered by `project-workflow-templates-real-backend.spec.ts:115-117`. The main session verified this: **the reviewer's "Cancel is not covered" was wrong.**
- G19: the 409 on Save and create is a gap, and the agent noted "covered but not in CI" for the story.
- G20: the result download is not claimed as covered.
- G21: scope filters were respected, and every exclusion is listed with its source.

**Partial (5):** each was found, but routed too conservatively.
- G5: the PII-scan failure is described as a defect, but its test went to product decision.
- G6: the template 404 dead end went to product decision; the reviewer calls it a BUG.
- G9: the landing tab went to product decision instead of a unit test on `getDefaultWorkflowTab`.
- G11: no invented 409. The agent found that the **backend allows parallel runs**, a new and verified finding, but did not propose the "opens the active run's modal" test.
- G13: the Configure-step flags are reported as a finding, but no scenario was proposed.

**Fail (2):** both are recall misses.
- G2: the delete modal closes before the request; it was not found.
- G4: the run history refetch failure was not found. The agent tested only an initial-load failure, which is correct as far as it goes.

## New, verified findings v1 did not have
- **Renaming a workflow to a taken name fails silently.**
  - The backend returns a 409 `ConflictException` (`WorkflowService.checkOnUpdateDuplicateWorkflowName`).
  - `useUpdateWorkflowForm` has no `.catch`, and 409 is not in `ERROR_CODES`.
  - Create, by contrast, auto-suffixes the name.
- **The backend has no guard against concurrent runs of one workflow.** Only orchestrated runs are rejected (`WorkflowRunLifecycleService.runWorkflow`). Stop then cancels only the first in-flight run.
- **Config saves ignore `version` for INTERNAL storage,** so the last write wins. Not verified by the main session.
- **Save as template is offered for SAP workflows without a spec,** which always fail with a 422.

## Changes made after this eval (in 0.4.0, before the commit)
- Lenses 2d, "Do not over-correct": a plainly wrong current behaviour is a **BUG**, with the nearest in-code convention as its source. Needs product decision is only for genuinely different acceptable behaviours. This targets G5, G6 and G9.
- Lens 5 gained three easy-to-miss cases: a failure after data was shown, a modal that closes before its request settles, and direct calls that bypass the plumbing. This targets G2 and G4.

## Not exercised
- **Phase 6a.** The `-actions.md` list was not generated for this eval. Scoring used the findings files.
- **Phase 5 at full depth.** The main session verified only the contested and new claims: Cancel coverage, rename 409, parallel runs.
- **A re-run after the two last tweaks.** Their effect is unmeasured.
