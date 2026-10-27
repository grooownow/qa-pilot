# Coverage matrix

A minimal feature → requirement → test table, so a lost test does not go unnoticed. It lives in the user's project as
`docs/qa/coverage-matrix.md`. It is not a traceability system: no id scheme, no CI gate.

## Format

```markdown
# Coverage matrix
> Maintained by qa-pilot. A row means: this requirement has this test, and here is how we know it can fail.

| Feature | Requirement | Test | Layer | In CI | Proof | Updated |
|---|---|---|---|---|---|---|
| Checkout | Order total includes shipping (PROJ-123 AC2) | e2e/checkout.spec.ts › "total with shipping" | e2e | yes | failed when broken, 2026-10-26 | 2026-10-26 |
```

## Columns

- **Feature**: the feature or flow name, as the owner says it.
- **Requirement**: one line in the user's words. A ticket or AC reference goes in brackets when one exists.
- **Test**: `path › test name`. One row per (requirement, test).
- **Layer**: unit, component, integration, e2e, or the project's own layer name.
- **In CI**: `yes` or `no`, from the profile's test-layers table.
- **Proof**, exactly one of:
  - `failed when broken, <date>`: the test was seen red. A BUG test against unfixed code, a `failure_probe.py` kill, or `write-tests`' own failure proof.
  - `distinguishing assertion`: read, not run. The assertion tells the correct result from the wrong one.
  - `none`: the test exists but nothing shows it can fail.
  - `none` goes with a short note in the Test cell after the name, for example `... › "name" (survived probe 2026-10-26)`. The Proof cell holds only the value.
- **Updated**: date of the last change to the row.

`failed when broken` is allowed only when the test was seen failing in the run that writes the row. An existing test that was only read gets `distinguishing assertion`, or `none` when its assertion does not tell right from wrong. An upsert never downgrades an existing `failed when broken` to a weaker value unless the test itself changed or a probe in this run reported `survived` (then `none`).

A BUG test left failing, expected-fail or uncommitted (written against unfixed code): `In CI: no`, Proof `failed when broken, <date>`. If that uncommitted test is later discarded, the row shows up as `lost-test`.

## Upsert

The key is (Feature, Requirement, Test). A matching row is updated in place; a new key adds a row. Create the file
with the header if it is missing. Rows are never deleted automatically: a row whose test path is gone is reported by
`profile_drift.py` as `lost-test`, and `qa-pilot:onboard` (refresh) offers to drop it, repoint it, or keep it as history, after the owner's yes. Keeping it as history appends ` (removed <YYYY-MM-DD>)` to the Test cell; `lost-test` skips rows with that marker.

## Writers

Writing the matrix is part of the skill's normal output, with no extra question.

- `task-qa` verify: the "Covered (CI)" and "Added" items, when it appends to the task file.
- `cover` and `write-tests`: the tests they add, with their proof.
- `test-code-audit`: probe verdicts update Proof. `killed` → `failed when broken, <date>`. `survived` → `none`, with the note in the Test cell after the name.

## Readers

- `task-qa` plan: existing coverage of the touched features feeds the regression set.
- `spec-audit` and `project-audit`: coverage evidence. A row with Proof `none` on a critical flow is a finding.

## Example

A small online shop: catalog, cart, checkout, accounts.

```markdown
| Feature | Requirement | Test | Layer | In CI | Proof | Updated |
|---|---|---|---|---|---|---|
| Cart | Adding the same item twice raises its quantity to 2 | src/lib/cart.test.ts › "merges duplicate items" | unit | yes | failed when broken, 2026-10-24 | 2026-10-24 |
| Checkout | Order total includes shipping (SHOP-42 AC2) | e2e/checkout.spec.ts › "total with shipping" | e2e | yes | failed when broken, 2026-10-26 | 2026-10-26 |
| Checkout | A declined card keeps the cart and shows a retry | e2e/checkout.spec.ts › "declined card keeps cart" | e2e | yes | distinguishing assertion | 2026-10-26 |
| Accounts | Password reset link works once | src/lib/auth.test.ts › "reset link is single use" | unit | no | none | 2026-10-20 |
```

<!-- qa-pilot · © 2026 Ludvik4 · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
