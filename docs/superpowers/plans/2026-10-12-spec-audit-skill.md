# spec-audit Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship `qa-pilot:spec-audit`, which audits requirements and test plans against the book catalog plus qa-pilot's own rules, cross-checks against code, and writes a calibrated report.

**Architecture:** Two stdlib Python scripts do the deterministic work:
- `rules_pack.py` filters the catalog by product traits and project overrides, then writes compact packs;
- `spec_lint.py` runs the low-noise text checks.

SKILL.md orchestrates phases 0–6 from the spec. Cluster agents apply the lenses from `references/spec-audit-lenses.md`. Triage and severity calibration stay in the main session.

**Tech Stack:** Python 3 stdlib, `unittest`, Markdown skills.

**Spec:** `docs/superpowers/specs/2026-10-12-spec-audit-skill-design.md`

## Global Constraints

- Scripts use the Python stdlib only. The skill must still work without `python3` by following the manual fallback in SKILL.md.
- Catalog schema is unchanged except:
  - ids may be `QAC-`, `QAP-` or `PRJ-`;
  - `source` is either `{chunk_id, printed_pages}` (QAC) or `{origin}` (QAP/PRJ).
- Trait tags are written `needs-<trait>`. A rule is kept only if every one of its `needs-*` tags is satisfied by the product traits.
- The skill never edits the project's specs. It writes only `docs/qa/spec-audit/*`, and the profile's Product traits section after asking.
- SKILL.md is in English, like the other skills. Rules and reports use the user's or the project's language.

## Review Focus

1. `spec_lint` must stay quiet in quotes, code spans, fenced code, and rationale/history/changes/open-questions sections.
2. `spec_lint` must still fire in AC bullets and requirement lines.
3. A rule with `needs-ios` must be excluded for a web+pwa product. A rule with no `needs-*` tag must always be kept.
4. A project `decisions` entry must appear in the pack. A `disabled` rule must be absent from the pack.
5. A missing `rule-overrides.json` or missing Product traits must not crash; defaults are web, everything else false.

---

### Task 1: Catalog schema for QAP/PRJ and the first 5 qa-pilot rules
- [ ] Extend `render_rules.py`:
  - ID_RE accepts `(QAC|QAP|PRJ)`;
  - `source.origin` (non-empty string) is allowed for non-QAC ids;
  - QAC ids still require `chunk_id`.
- [ ] Tests:
  - a QAP record with an origin passes;
  - a QAP record without a source fails;
  - an QAC record with only an origin fails.
- [ ] `knowledge/qa-pilot/rules/pilot.json` holds the 5 rules from spec §6. Then validate, render and commit.

### Task 2: needs-* trait tags across the catalog (subagents, in parallel)
- [ ] Trait vocabulary: `needs-ios`, `needs-android`, `needs-native-mobile`, `needs-mobile`, `needs-desktop`, `needs-game`, `needs-payments`, `needs-rest`, `needs-graphql`, `needs-soap`, `needs-auth`, `needs-uploads`, `needs-i18n`, `needs-rtl`.
- [ ] 3 agents tag the records. Rules for tagging:
  - only add `needs-*` tags, never change content;
  - tag a record only when it clearly does not apply without that trait;
  - when in doubt, leave the record untagged.
- [ ] Validate, then spot-check 20 random tagged records.

### Task 3: rules_pack.py
- **Interface:** `rules_pack.py --kb <knowledge_dir> --targets requirements,test-plan --profile <project-profile.md> [--overrides <rule-overrides.json>] --out <dir>`.
- **Writes:**
  - `<out>/packs/{core,forms-ui,api-data,a11y-l10n,platform}.md`;
  - `<out>/manifest.json` with counts per pack, excluded rules with the reason, disabled rules, and applied decisions.
- **Traits parsing:** read the fenced YAML-ish block under `## Product traits`. Support only the simple subset: `key: value`, `key: [a, b]`, and true/false.
- [ ] Tests for all Review Focus items 3–5. Implement, then commit.

### Task 4: spec_lint.py
- **Interface:** `spec_lint.py [--overrides f] <files…>`. It prints JSON `[{file, line, check, rule, match, text}]` and exits 0.
- **Checks:**
  - `vague-word`, rule QAC-REQ-014: the regex plus `extra_vague_words` plus the defaults `корректн` and `нормальн`;
  - `unfinished`, rule QAP-REQ-001 (added in Task 1 as a 6th rule): TBD, TODO, ???, ЧЕРНОВИК, «уточнить», TBC.
- **Skipping:** fenced code, inline code, «…» and "…" quotes, and sections under headings that match the default or project skip patterns (rationale, обоснование, история, history, изменения, changes, changelog, open questions, открытые вопросы/решения, альтернативы, alternatives).
- [ ] Tests for Review Focus items 1–2. Implement, then commit.

### Task 5: references
- [ ] `references/spec-audit-lenses.md`: the 6 lenses, the code-reality instructions (R1, R3, R6, drift), the finding format, and the persistence rules.
- [ ] `references/severity-calibration.md`: P1, P2 and P3 definitions with examples from the pilot, plus "book must ≠ P1".

### Task 6: SKILL.md + onboard Product traits + docs
- [ ] `skills/spec-audit/SKILL.md`: phases 0–6, the cost estimate, the manual fallback, the report template, and the hand-off to test-plans.
- [ ] `skills/onboard/SKILL.md`: add a Product traits question and the profile section.
- [ ] Update the plugin docs and metadata:
  - README skills table and a command example;
  - `docs/guide.md` section;
  - `docs/design.md` skill list and architecture;
  - `plugin.json` version 0.3.0, description and keywords.
- [ ] Include `knowledge/` in the README description.

### Task 7: Evals
- [ ] Deterministic eval: `spec_lint` over all pawfile specs. Compare with the pilot's 16 regex matches; the target is ≤2 false positives. Record the result.
- [ ] `rules_pack` for pawfile traits: excluded counts are sensible, no HIG/game rules remain.
- [ ] Single-feature eval: a fresh agent follows SKILL.md on pawfile F06+P07. Record tokens, time and findings, and compare with the pilot's g4 findings for F06/P07.
- [ ] P1-recall eval: a fresh agent follows SKILL.md on the F05+P06 and F11 clusters plus the project-level NFR phase. It must surface the 3 pilot P1 root causes.
- [ ] Write the results to `docs/superpowers/notes/2026-10-12-spec-audit-evals.md`. Fix the skill where an eval shows a gap, then re-run the affected eval.

### Task 8: Final gates
- [ ] All unit tests pass, the validator passes, overlap is 0, the render is up to date and `git status` is clean. Final whole-branch review by one reviewer agent; fix its findings. Commit.
