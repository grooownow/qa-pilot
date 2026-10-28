# spec-audit regression eval: pilot project, workflows + templates

**Ground truth:** the pilot project agent's review of 2026-10-19. It lives outside this repo, in the owner's artifacts repo at `reviews/2026-10-19-qa-review-workflow-templates-audit.md`.

**Setup:**
- Scope: `workflows.md` and `workflow-templates.md`.
- Baseline: `0f7f4d3f99`.
- Owner scope filters (the same as the v1 filtered report):
  - no cloud;
  - no roles;
  - no delete-during-run;
  - no length tests.

A v2 run passes a check when its action list (or findings, before the list exists) matches the expected behaviour.

| # | Check | Expected | Root cause it guards |
|---|---|---|---|
| G1 | PDF report download failure | BUG: the direct SDK call bypasses the cache, so there is no toast | R1 |
| G2 | Delete closes the modal before the request | Found, as a BUG or a gap | R1 |
| G3 | Error mocks | No claim that "a 500 with a message is silent". Proposed mocks are a 404 or a 500 with an empty body | R1 / plumbing |
| G4 | Run history poll failure | BUG, fixed with `isError && !data` | — |
| G5 | Auto PII scan on create | BUG (toast and auto-apply on failure). Flat-file is already excluded, so it is not claimed broken | R5 |
| G6 | Template 404 on PUT/DELETE | BUG: raw message, the dialog stays open, no refetch | — |
| G7 | Data-source failure shows `—` | Low BUG, or omitted | — |
| G8 | Activity logs on on-prem | Not a gap: already covered by `onPremiseApp/workflow/workflow-activity-logs.spec.ts` | R1 |
| G9 | Landing tab after create | A unit test on `getDefaultWorkflowTab`. Not "already unit-covered", because the existing test mocks it | R3 / R4 |
| G10 | Run modal: Cancel after changing the output | Needs product decision, not a test | R5 |
| G11 | Run during an active run | Test that the active run's modal opens. No invented 409 or "already running" expectation | R5 |
| G12 | Same input and output | The confirmation is on wizard **submit**, not on the Connect step. Existing e2e tests do not assert it | R4 (target) |
| G13 | Configure-step flags | Target: the hook plus the component filter. A unit test after extracting a pure function, or e2e with stubbed flags. Not `configureStepHelpers` | R4 |
| G14 | Direct URL to a hidden tab | Product decision, or omitted. Never a BUG or a redirect test | R5 |
| G15 | Template id from another project | Backend integration test (`owner: backend`), not Playwright | R4 |
| G16 | Save as template UI | A gap, ranked at or near the top. The 422 shows as a toast | — |
| G17 | Wrong template kind in the URL | A low-priority mocked case | — |
| G18 | Discard on Cancel, × and backdrop | e2e. Stories do not count as coverage, because they do not run in CI | R2 |
| G19 | 409 on "Save and create workflow" | A gap, not "covered" | R3 |
| G20 | `file-workflow-run-output-connection.spec.ts` | Not cited as covering the result download | R3 |
| G21 | Scope filters | No cloud-only or role/permission items in the action list | R6 |

**Score:**
- passed checks out of 21;
- the cost (agent tokens);
- any new false absence claim, which counts as a regression even if it is not on this list.
