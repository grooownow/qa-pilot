# Spec Audit Lenses

The brief for one `spec-audit` cluster agent. The dispatching skill gives you:
- your spec files;
- the project root;
- the rule-pack directory;
- your findings file path.

Read this whole file before starting.

The work is **read-only.** Never edit the project. You write only your findings file.

## 0. Before the specs: load what overrides the book

1. Read the decisions digest from your brief, if you got one. Otherwise read the project's `CLAUDE.md` / `AGENTS.md`, its test-strategy doc (named in `docs/qa/project-profile.md`), and every decision record your specs reference (`docs/decisions/*`, ADRs, accepted items in `docs/code-review/`).
   - **Read code at the baseline sha from your brief.** If the working tree is dirty, use `git show "${SHA}:<path>"` (quote it: in zsh an unquoted `$SHA:A…` is read as a path modifier), because uncommitted edits by someone else must not leak into your verdicts.
2. Project decisions **win over the catalog**. So does any rule line carrying `⚖️ РЕШЕНИЕ ПРОЕКТА`. A rule that would fire but is overridden goes to *Skipped as project decision*, never to *Findings*.
3. Load the rule packs economically. Each pack is 10–25k tokens.
   - Read `core.md` in full.
   - For `forms-ui`, `api-data`, `a11y-l10n` and `platform`, do not read the whole file. `grep` them for the domain words of your specs (e.g. `upload|файл`, `share|ссылк`, `date|дат`, `password|парол`, `focus|keyboard`) and read only the matching lines.

   Full records are in the catalog JSON (`<catalog path from your brief>/*/rules/*.json`); look a record up with `jq` by id when a one-line summary is not enough.

## 1a. Entity cards (before the lenses)

Read `references/web-patterns.md` (absolute path in your brief). For every entity with a lifecycle in your specs (workflows, templates, runs, documents, accounts…), fill one **entity card**: one row per must-check pattern, with a verdict and evidence.

- **OK**: the code handles it (cite the line) and a test that runs in CI proves it (2b), or the handling is trivially correct.
- **BUG**: the code mishandles it (cite the line). A scenario with a BUG mark follows.
- **GAP**: the code may be fine but nothing in CI proves it. A scenario follows.
- **N/A**: the pattern cannot occur for this entity. Evidence is mandatory (e.g. "no delete endpoint: searched `git grep -n 'delete' -- src/api/workflow*` → 0").
- **DECISION**: the right behaviour is a product choice. It goes to *Needs product decision*.

Run the pattern's trigger searches from `web-patterns.md`; do not decide a cell from memory. An empty cell is a defect of the run, not a pass. Highlight-only patterns get a one-line mention only when you see them, with no card row.

With `depth: critical`, do only the entity cards plus lens 4 (contradictions), and only for entities on the critical flows in your brief.

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
5. **Error / empty / loading states and error guessing.** Every read needs a defined failure presentation; "error looks like no data" is a finding. Check these cases, which are easy to miss:
   - a polled or refetched read that fails **after** data was already shown. Does the loaded data survive?
   - a modal write that closes the modal **before** the request settles. Where does a failure go?
   - a direct client call that bypasses the shared query/mutation layer, and with it the global error plumbing.
6. **Domain packs.** Apply the remaining pack rules that fit your specs: security and privacy (QAP-PRIV-001, IDOR), a11y, i18n, forms. Skip rules that obviously do not fit the product. Rules that cannot fit were already removed by traits.

## 2. Reality check against code (mandatory when code exists)

A spec-only audit produced about one third false "missing" items in the pilot, and it missed every P1. For each candidate:

### 2a. Absence claims need a proving search

"X does not exist" is the weakest claim you make. "Not covered", "no handler", "no guard", "no global toast" and "nobody calls it" are all absence claims. On TDK every wrong claim was an absence claim, and two of them came from a search piped through `head` that cut off the file that would have refuted it.

- **Cite the search.** Each absence claim carries the exact command and its match count, e.g. `searched: git grep -n -i 'activity.\?log' $SHA -- frontend/e2e frontend/src → 0 matches in tests`.
- **Never truncate a proving search.** No `head`, `tail` or `cut` on it. Run `| wc -l` first. If there are too many matches, narrow the pattern or the path, then read all of them.
- **Search at least three ways:**
  - the feature name, case-insensitive, with separator variants (`activity.?log`);
  - the route or API path;
  - a testid, a component name, or the user-visible string.
- **Search every test root** listed in the profile's test-layers table, not just `src/`. That includes per-mode or per-project folders (e.g. `onPremiseApp/`) and backend test dirs.
- **Before calling a failure "silent"**, find the global error plumbing:
  - query/mutation cache subscribers;
  - `onError` in providers;
  - fetch/axios interceptors;
  - `unhandledrejection` listeners;
  - error boundaries;
  - "notifications"/"toast" modules.

  State which statuses and bodies it covers. Then say exactly which cases it does not cover, e.g. "404, or a 500 with an empty body".

### 2b. "Covered in code" needs three proofs

1. **The test** at path:line.
2. **The assertion** that checks the scenario's **distinguishing condition**: the status code, the branch, or the input class. A test of a neighbouring case does not count. Example: a story where `save` resolves `false` does not cover "409 on save".
3. **The layer runs in CI.** Check the profile's test-layers table. A layer that CI does not run, or that is being phased out, does not count. Write `covered but not in CI: <path>` and treat the scenario as a gap.

If any of the three is missing, the scenario is a **gap**.

### 2c. Other checks

- **Missing scenario:** run the 2a searches for the function, action, route or error code. If you find a test that passes 2b, write `covered in code: <path:line>` instead of listing the scenario as missing.
- **Invariant in every write path** (QAP-INV-001): list every place that writes the entity (actions, RPC, migrations with CHECK, background jobs, review screens, imports) and say where the invariant is enforced in each.
- **Security AC → anti-false-green:**
  - find the test that asserts the *specific* failure (error code, status, `rate_limited`);
  - check that no mock hard-wires the guard to succeed;
  - check that paired guards are each proven alone (QAP-AUTH-002).
- **Spec claims "X exists / is absent / is guaranteed":** verify in the code. When spec and code disagree, report drift. Name the side that is real, and set the severity by what breaks if someone "fixes" the code to match the spec.
- **Data exposure:** for anonymous endpoints, read the actual returned fields (the RPC body, the select list, the serializer) against the spec's privacy claims.

Every P1/P2 needs a `code` reference: the `file:line` of the implementing code, or `n/a` with the reason. A P1/P2 that rests on an absence claim also needs the proving search (2a).

## 2d. Prescribing a test: level, location, expected result

A finding is half the work. The scenario you propose will be implemented by another agent exactly as written. On TDK, 5 of 16 scenarios had the wrong level or location, and 2 had an invented expected result.

- **Test where the logic lives.** Pick the level from where the behaviour is decided, not from how the spec describes it:

  | The behaviour is decided in… | Level |
  |---|---|
  | a pure function, mapper, or decision table in code | unit test on that function |
  | a hook or component branch (flags, conditional rendering) | hook/component unit test |
  | a backend guard, invariant, or query scope (IDOR, uniqueness) | backend integration test in the backend's own suite; mark it `owner: backend` even if qa-pilot writes only frontend tests |
  | a user-visible flow that crosses layers | e2e |

- **Name the target:** the function, hook or component under test, at the path:line where the logic actually lives. Do not use the nearest existing test file as the target.
- **One expected result, with a source.** Every scenario states a single expected result and cites where it comes from:
  - a spec line;
  - a project decision;
  - a web invariant `QAP-WINV-…` from `web-patterns.md`, when the spec is silent (e.g. "every write has a visible failure reaction");
  - an existing convention elsewhere in the code (path:line).
- **Do not over-correct.** When the current behaviour is plainly wrong, it is a **BUG**, not a product question. Examples: success shown after a failure, raw ids shown to the user, a retry that can never succeed. Cite the nearest in-code convention as the source, e.g. another flow that notifies on failure. Use Needs product decision only when there are genuinely different acceptable behaviours.
- **Otherwise it is a question, not a test.** If the expected result is undecided, would be invented by you, or would pin behaviour you suspect is a bug, the item goes to **Needs product decision**, never to the scenarios.
  - "Documented, or fixed" is not an expected result.
  - "Redirect to the default tab" with no source is invented.
- **Mocked tests must not be masked.** For a `@ui-contract`-style test, name the mocked response and why the global plumbing (2a) will not already satisfy the assertion. Example: "mock a 500 with an empty body; the global toast fires only when `message` is present".
- **Respect scope filters.** Scope filters from the brief (areas not developed, on hold, or not to be tested) remove scenarios and findings. List what they removed under *Skipped as project decision*.

## 3. Findings file format (append after EACH spec, so progress survives a dead session)

If your Write tool is blocked, append with a shell command (`cat >> <file> <<'EOF'`). If that is blocked too, put the full findings in your final reply, and say that you did.

```
## Entity cards
| Entity | Pattern | Verdict | Evidence (file:line or search → count) |

## <spec file>
### Findings
| # | Rule | Sev | Where (file:line) | Code (file:line) | Finding | Fix (concrete) |
### Missing test scenarios
- [P1|P2|P3] <scenario> → expected: <one result> (source: <spec line | decision | path:line>) — <level: unit | component | backend-integration | e2e> — target: <function/hook/component path:line> — <rule id / technique> — gap (searched: <command> → <n> matches) | covered in code: <test path:line, assertion line> | covered but not in CI: <path>
- Mark a scenario **BUG** when the current code fails it (cite the line). The implementing agent fixes the code first, then writes the test.
### Needs product decision
- <question> — why it is not a test yet (undecided / no source / would pin a suspected bug) — options
### Skipped as project decision
- <rule id> — <decision source>
```

- Set severity with the severity-calibration file from your brief. The rule's own severity is only a hint.
- **Be sharp, not long.** 10 grounded findings beat 50 generic ones. No finding without a location.
- **End the file with `## Lens notes`** (≤5 bullets): rules that were noisy or missing for this product. The main session uses these notes to tune overrides.

## 4. Final reply (short)

- Counts of P1/P2/P3 and missing scenarios per spec.
- The top 3 findings.
- The findings file path.
