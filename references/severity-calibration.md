# Severity Calibration (P1 / P2 / P3)

This file is shared by qa-pilot audits. Severity measures the **impact on this product**, not how strongly a book or guideline words a rule. A catalog rule's `must` is a hint, never a verdict.

## P1: can ship a real defect, data or security harm, or an unguarded release

At least one of these must hold, with evidence:

- **Users can lose or corrupt their data.** Example: an edit is saved only in client state, so the next background sync overwrites it.
- **A security or privacy guard is broken or unproven.**
  - A guard mocked to always succeed in its only test.
  - A protection that fails open.
  - Internal ids or personal data leaking from an anonymous endpoint against an explicit project decision.
- **A legal or regulatory obligation the project has adopted is violated.** Example: a GDPR deletion that leaves personal data behind, when the project claims GDPR compliance.
- **There is no regression or smoke gate between merge and production** for a product with real users.

If you cannot point to the code or config that makes the harm reachable, it is not P1.

## P2: a meaningful coverage gap or a requirement that will mislead

- An undefined or contradictory requirement on a user-visible path. Spec-to-spec drift, or an AC that describes the old behaviour, so a test written from it would reintroduce a bug.
- A missing test on a non-trivial branch: an off-path state transition, an invariant missing from one write path, a security AC without a specific-failure assertion (unless that is P1 above).
- Non-functional requirements not stated measurably: WCAG target, supported browsers, CWV budget, offline behaviour, timeouts.
- An accessibility failure of a WCAG A/AA criterion on a core flow. Raise it to P1 only when the project is legally bound (e.g. EAA in scope) or has committed to the level.
- A privacy exposure without an explicit contrary decision.

## P3: polish

- Stale wording where the code and tests are right and no test would be written from it wrongly.
- Missing nice-to-have scenarios, AAA accessibility criteria, cosmetic UI guidance, typos in specs.

## Rules of thumb

- **Drift:** ask "what breaks if someone makes the code match the spec?" If the answer is real harm, it is P2. If it is nothing, P3.
- **"Covered in code"** is not a finding at all. Report it in the scenario list so the reader sees it was checked.
- **Never inflate drift to P1**, and never deflate a proven data or security issue because it is "only" in a test.
- **A project decision that consciously accepts a risk** is not a finding. If the decision's own premise is broken (e.g. it relies on a safeguard that does not exist or fails open), report *that* as **P2**, quote the decision, and add it to **Decisions needed**. It becomes P1 only when you can show concrete harm that is already reachable. The owner decides; the audit does not overrule a decision on its own.
- **A written process instruction is not a gate.** "Run the gates before pushing" in AGENTS.md is not enforcement. Only an automated check that blocks a merge or deploy counts. An explicit decision to *rely* on local checks is a decision (see above).
- **"Real users?"** Release-gating and data-loss severity depend on it. Count it as yes if the product is publicly reachable with sign-up, or the docs mention beta or production users. If you cannot tell, say which assumption you made.
