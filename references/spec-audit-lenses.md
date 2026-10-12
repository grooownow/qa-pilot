# Spec Audit Lenses

The brief for one `spec-audit` cluster agent. The dispatching skill gives you:
- your spec files;
- the project root;
- the rule-pack directory;
- your findings file path.

Read this whole file before starting.

The work is **read-only.** Never edit the project. You write only your findings file.

## 0. Before the specs: load what overrides the book

1. Read the project's `CLAUDE.md` / `AGENTS.md`, its test-strategy doc (named in `docs/qa/project-profile.md`), and every decision record referenced by your specs (`docs/decisions/*`, ADRs).
2. Project decisions **win over the catalog**. So does any rule line carrying `⚖️ РЕШЕНИЕ ПРОЕКТА`. A rule that would fire but is overridden goes to *Skipped as project decision*, never to *Findings*.
3. Load the rule packs economically. Each pack is 10–25k tokens.
   - Read `core.md` in full.
   - For `forms-ui`, `api-data`, `a11y-l10n` and `platform`, do not read the whole file. `grep` them for the domain words of your specs (e.g. `upload|файл`, `share|ссылк`, `date|дат`, `password|парол`, `focus|keyboard`) and read only the matching lines.

   Full records are in the catalog JSON (`knowledge/*/rules/*.json`); look a record up with `jq` by id when a one-line summary is not enough.

## 1. Lenses: apply them in this order to every spec

The order matters. The first lenses find real defects; the later ones mostly find gaps.

1. **Lifecycle → state model + action × state grid** (SRK-TD-039/040/042).
   - For every entity with a lifecycle (links, jobs, documents, accounts, subscriptions, soft-delete), list its states and every action. For each (action, state) cell, ask:
     - Is the cell defined?
     - Is it guarded?
     - Who writes the transition in the code?
   - Undefined or unguarded off-path cells are the richest source of P1/P2 findings: for example "restore" on a live link, or a status flipped only in UI state.
2. **Combined conditions → decision table** (SRK-TD-030/031). Landing or routing logic, eligibility and permission matrices. Missing rows are findings.
3. **Every input and limit → equivalence classes + 3BVA** (SRK-TD-001/007/008/009). Take the limits from the spec AND from the schemas in code (Zod, DB CHECKs). Test lengths at min−1…max+1, impossible dates (Feb 30, Feb 29 in a non-leap year), and the timezone of "today" (QAP-DATE-001).
4. **Contradictions** (SRK-REQ-009, QAP-REQ-002). Check each of these pairs:
   - a spec and its sibling (feature ↔ page);
   - a spec and the decisions it cites;
   - a spec's dated "Changes/Изменения" sections and its own AC block;
   - a spec and the architecture/overview docs.

   This is the highest-volume lens.
5. **Error / empty / loading states and error guessing.** Every read needs a defined failure presentation; "error looks like no data" is a finding.
6. **Domain packs.** Apply the remaining pack rules that fit your specs: security and privacy (QAP-PRIV-001, IDOR), a11y, i18n, forms. Skip rules that obviously do not fit the product. Rules that cannot fit were already removed by traits.

## 2. Reality check against code (mandatory when code exists)

A spec-only audit produced about one third false "missing" items in the pilot, and it missed every P1. For each candidate:

- **Missing scenario:** grep the test files (`*.test.*`, `*.spec.*`, integration and e2e dirs) for the function, action, route or error code. If you find a test, write `covered in code: <path>` instead of listing the scenario as missing.
- **Invariant in every write path** (QAP-INV-001): list every place that writes the entity (actions, RPC, migrations with CHECK, background jobs, review screens, imports) and say where the invariant is enforced in each.
- **Security AC → anti-false-green:**
  - find the test that asserts the *specific* failure (error code, status, `rate_limited`);
  - check that no mock hard-wires the guard to succeed;
  - check that paired guards are each proven alone (QAP-AUTH-002).
- **Spec claims "X exists / is absent / is guaranteed":** verify in the code. When spec and code disagree, report drift. Name the side that is real, and set the severity by what breaks if someone "fixes" the code to match the spec.
- **Data exposure:** for anonymous endpoints, read the actual returned fields (the RPC body, the select list, the serializer) against the spec's privacy claims.

Every P1/P2 needs a `code` reference: the `file:line` of the implementing code, or `n/a` with the reason.

## 3. Findings file format (append after EACH spec, so progress survives a dead session)

```
## <spec file>
### Findings
| # | Rule | Sev | Where (file:line) | Code (file:line) | Finding | Fix (concrete) |
### Missing test scenarios
- [P1|P2|P3] <one line> — <rule id / technique> — <tier: unit | integration | e2e> — gap | covered in code: <path>
### Skipped as project decision
- <rule id> — <decision source>
```

- Set severity with `references/severity-calibration.md`. The rule's own severity is only a hint.
- **Be sharp, not long.** 10 grounded findings beat 50 generic ones. No finding without a location.
- **End the file with `## Lens notes`** (≤5 bullets): rules that were noisy or missing for this product. The main session uses these notes to tune overrides.

## 4. Final reply (short)

- Counts of P1/P2/P3 and missing scenarios per spec.
- The top 3 findings.
- The findings file path.
