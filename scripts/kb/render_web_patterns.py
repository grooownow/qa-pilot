#!/usr/bin/env python3
"""Render web patterns and invariants into the agents' working reference.

Usage: python3 scripts/kb/render_web_patterns.py knowledge/qa-pilot references/web-patterns.md

Reads rules/web-patterns.json (QAP-WEB-…, with a `pattern` object) and
rules/web-invariants.json (QAP-WINV-…). Output is deterministic: edit the JSON,
never the Markdown.
"""
import json
import sys
from pathlib import Path

VERDICTS = "OK · BUG · GAP · N/A (with evidence) · DECISION · SUPPRESSED (owner filter)"


OWN_MARKER = ("<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · "
              "PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->")


def render(patterns, invariants):
    patterns = sorted(patterns, key=lambda r: r["id"])
    must = [r for r in patterns if r["pattern"]["tier"] == "must-check"]
    highlight = [r for r in patterns if r["pattern"]["tier"] == "highlight"]
    out = ["# Web patterns and invariants", "",
           "Generated from `knowledge/qa-pilot/rules/web-patterns.json` and `web-invariants.json` by "
           "`scripts/kb/render_web_patterns.py`. Edit the JSON, not this file.", "",
           "Used by `spec-audit` (entity cards), `task-qa` (touched entities), `project-audit` and `plan-tests`. "
           "Must-check patterns are asked of **every entity with a lifecycle**; an empty cell means the run is "
           "not finished. Highlight-only patterns get one line when seen, never a card row.", "",
           "## Entity card", "",
           f"One card per entity. Verdicts: {VERDICTS}. Evidence: file:line, or the search command with its "
           "match count (untruncated).", "",
           "| Pattern | Question | Verdict | Evidence |", "|---|---|---|---|"]
    out += [f"| {r['id']} | {r['title']} | | |" for r in must]
    out += ["", *not_applicable(patterns, invariants), "## Must-check patterns", ""]
    for r in must:
        out += pattern_block(r)
    out += ["## Highlight-only patterns", "", "Mention as one line in *Highlighted, not drilled* when you see one.", ""]
    out += [f"- **{r['id']}** {r['title']} — {r['check']['how']} _(triggers: "
            + ", ".join(f"`{t}`" for t in r["pattern"]["triggers"]) + ")_" for r in highlight]
    out += ["", "## Web invariants (expected-result sources)", "",
            "When a spec is silent, these are valid sources for a scenario's expected result "
            "(cite the id). A violation on a user-visible path is a BUG, not a product question.", ""]
    for r in sorted(invariants, key=lambda r: r["id"]):
        out += [f"- **{r['id']} · {r['title']}.** {r['statement']} _(source: {r['source']['origin']})_"]
    out += ["", OWN_MARKER]
    return "\n".join(out).rstrip() + "\n"


def not_applicable(patterns, invariants):
    """Patterns and invariants the project kind rules out, from their needs-ui / needs-backend tags."""
    ids = {tag: ", ".join(r["id"] for r in [*patterns, *sorted(invariants, key=lambda r: r["id"])]
                          if tag in r.get("tags", []))
           for tag in ("needs-ui", "needs-backend")}
    return ["## Not applicable by project kind", "",
            "Read `has_ui` and `has_backend` in the profile's `## Product traits`; a missing key counts as `true`. "
            "These patterns get N/A with the trait as evidence (`profile: has_ui false`), with no search:", "",
            f"- `has_ui: false`: {ids['needs-ui']}.",
            f"- `has_backend: false`: {ids['needs-backend']}.",
            "- Both `false` (a CLI, a library, a plugin marketplace): skip entity cards unless the repo has its own "
            "entities with a create, change and delete lifecycle.", ""]


def pattern_block(r):
    p = r["pattern"]
    lines = [f"### {r['id']} · {r['title']}", "",
             f"Catalog severity `{r['severity']}` (not a bucket: the cell's P1/P2 follows "
             f"`severity-calibration.md`) · test level: {p['level']} · authority: "
             f"{r.get('authority', 'unclassified')}", "", r["statement"], "",
             f"**Check per entity:** {r['check']['how']}", "",
             "**Triggers (where to look):** " + ", ".join(f"`{t}`" for t in p["triggers"]), ""]
    if r.get("rationale"):
        lines += [f"**Why:** {r['rationale']}", ""]
    if p.get("book_refs"):
        lines += ["**Book rules:** " + ", ".join(p["book_refs"]), ""]
    lines += [f"_Source: {r['source']['origin']}_", ""]
    return lines


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    kb, out = Path(argv[1]), Path(argv[2])
    patterns = json.loads((kb / "rules" / "web-patterns.json").read_text(encoding="utf-8"))
    invariants = json.loads((kb / "rules" / "web-invariants.json").read_text(encoding="utf-8"))
    out.write_text(render(patterns, invariants), encoding="utf-8")
    print(f"OK: {len(patterns)} patterns, {len(invariants)} invariants → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
