# Book Knowledge Base (A+B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a chunked local corpus of Surkov's QA book and a verified, paraphrased rules catalog plus summary, committed to git without any raw book text.

**Architecture:** `scripts/kb/build_chunks.py` turns the PDF into per-page text, then into heading-bounded chunks (gitignored `raw/`) and a text-free TOC (committed). Parallel subagents extract rules per topic into `rules/<topic>.json`. Verifier subagents check them against the chunks. `scripts/kb/render_rules.py` validates the schema and renders the Markdown.

**Tech Stack:** Python 3 stdlib, `pdftotext`/`pdfinfo` (poppler), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-12-book-knowledge-base-design.md`

## Global Constraints

- The full book text never enters git. `knowledge/surkov/raw/` is listed in `.gitignore`.
- Rule `statement` text is always a paraphrase. Verbatim quotes are allowed only for terms and short standard wording (WCAG).
- Rules are written in Russian.
- No new dependencies: Python stdlib plus poppler only.
- Chunk ids follow `s{section}-c{chapter:02}-{sub:02}[-pN]`.
- Rule ids follow `SRK-<TOPIC>-NNN`.
- Enums: `kind` ∈ {rule, recommendation, tip, checklist}; `severity` ∈ {must, should, nice}; `check.mode` ∈ {deterministic, heuristic, manual}; `applies_to` ⊆ {requirements, test-plan, test-code, live-product, test-cases}.
- Career (7.8), Belarus (5.7) and the author bio are recorded in the TOC and summary only. No rules are extracted from them.

## Review Focus

1. A TOC heading that cannot be found in the body text: it must be reported, never dropped silently, and its text must stay in the previous chunk.
2. Running headers and page numbers leaking into chunk text: they must be stripped.
3. A rule whose `source.chunk_id` does not exist: the validator must fail.
4. A rule that duplicates book text verbatim: the verifier flags it and it gets rewritten.
5. Re-running the build: the output must be byte-identical.

---

### Task 1: Chunker

**Files:** Create `scripts/kb/build_chunks.py` and `scripts/kb/test_build_chunks.py`. Modify `.gitignore`.

**Interfaces:** `python3 scripts/kb/build_chunks.py <pdf> <out_dir>` writes:
- `out_dir/raw/pages/NNN.txt`;
- `out_dir/raw/chunks/<id>.md`;
- `out_dir/raw/chunks.jsonl`;
- `out_dir/toc.json` and `out_dir/toc.md`;
- `out_dir/raw/build-report.txt`, which lists unmatched headings and the coverage percentage.

Pure functions under unit test: `normalize(s)`, `parse_toc(lines)`, `strip_page_furniture(page_text)`, `split_long(text, max_words)`.

- [ ] Write unit tests for the pure functions using fixture strings copied from the book's layout: a TOC line with dot leaders, a page with a "ГЛАВА N:" header and a page-number footer, and zero-width characters.
- [ ] Implement until the tests pass.
- [ ] Run on the real PDF. Iterate until ≥98% of TOC entries are matched and coverage is ≥98%.
- [ ] Run twice and `diff -r` the outputs: the diff must be empty.
- [ ] Confirm `git status` shows no `raw/` files. Commit.

### Task 2: Rules validator/renderer

**Files:** Create `scripts/kb/render_rules.py` and `scripts/kb/test_render_rules.py`.

**Interfaces:** `python3 scripts/kb/render_rules.py <kb_dir>` validates every `rules/*.json`. It exits 1 and prints errors when it finds:
- a bad enum value;
- a missing field;
- a duplicate id;
- an unknown `chunk_id` (checked only when `raw/chunks.jsonl` exists).

Otherwise it writes `rules/<topic>.md` and a stats block into `README.md`, between the `<!-- stats -->` markers.

- [ ] Write tests: a valid record passes; each invalid case fails with a specific message.
- [ ] Implement until the tests pass. Commit.

### Task 3: Topic tagging + extraction (subagents)

- [ ] Write `knowledge/surkov/topics.md`: a topic → chunk ids mapping from `toc.json`, following spec §5.2.
- [ ] Dispatch about 10 extraction agents in parallel, one per topic group. Each one appends to `rules/<topic>.json` as it goes and keeps notes in the scratchpad.
- [ ] Run the validator and fix any errors.

### Task 4: Verification + dedup

- [ ] Dispatch verifier agents per topic. Coverage: 100% of the deep tier, ≥30% of the medium tier.
- [ ] Each verifier deletes false records, fixes wrong severity or mode, and rewrites near-verbatim text. It writes a report to the scratchpad.
- [ ] Deduplicate across topics. Re-validate. Commit.

### Task 5: Summary + README

- [ ] `knowledge/surkov/summary.md` (RU) per spec §5.4.6.
- [ ] `knowledge/surkov/README.md`: purpose, rebuild instructions, agent lookup contract (spec §6), license note, stats.
- [ ] Final gates: unit tests, validator, `git status` clean of raw text, grep the committed files for long verbatim runs. Commit.
