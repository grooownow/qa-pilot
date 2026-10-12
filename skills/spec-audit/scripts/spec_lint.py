#!/usr/bin/env python3
"""Deterministic, low-noise text checks over requirement/spec Markdown files.

Usage: python3 spec_lint.py [--overrides docs/qa/rule-overrides.json] <file.md> ...

Prints a JSON array of candidates: {file, line, check, rule, match, text}.
Checks only requirement prose: skips fenced code, inline code, quoted strings
(«…», "…", “…”) and whole sections whose heading looks like rationale, history,
changes, open questions or alternatives (extendable via overrides).

Also skips lines that record a dated decision ("решение 2026-06-13").

Checks:
  vague-word  (SRK-REQ-014)  unmeasurable words: быстро, удобно, интуитивно…
                             quantified=true when the line already has a number
                             with a unit — usually a false positive, triage drops it
  unfinished  (QAP-REQ-001)  TBD / TBC / TODO / ??? / ЧЕРНОВИК (caps) / уточнить
"""
import argparse
import json
import re
import sys
from pathlib import Path

VAGUE_STEMS = ["быстр", "удобн", "адекватн", "интуитивн", "гибк", "корректн"]
DEFAULT_SKIP_SECTIONS = [
    r"rationale", r"обоснован", r"истори", r"history", r"изменени", r"changes?\b", r"changelog",
    r"open questions", r"открыт\w*\s+(вопрос|решени)", r"альтернатив", r"alternatives",
    r"почему", r"\bwhy\b", r"контекст", r"context", r"\bцел[ьи]\b", r"\bgoals?\b",
]
UNFINISHED = re.compile(r"\b(TBD|TBC|TODO)\b|\?\?\?|ЧЕРНОВИК|(?<![а-яёa-zА-ЯЁ])[Уу]точнить")
# A line that records a dated product decision is rationale, not a requirement.
DATED_DECISION = re.compile(r"(decision|решени\w*)\W{0,3}(от\s+)?\d{4}-\d{2}-\d{2}", re.I)
# A number with a unit on the same line usually already makes the wording measurable.
QUANTITY = re.compile(r"\d+(?:[.,]\d+)?\s*(мс|ms|сек|с|s|min|мин|кб|kb|мб|mb|гб|gb|%|px|vh|vw|rem|fps)(?![а-яёa-z])", re.I)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE = re.compile(r"^\s*(```|~~~)")
STRIP = [re.compile(p) for p in (r"`[^`]*`", r"«[^»]*»", r"\"[^\"]*\"", r"“[^”]*”", r"„[^“]*“")]


def vague_regex(extra):
    stems = "|".join(re.escape(s) for s in VAGUE_STEMS + [e for e in extra if e not in VAGUE_STEMS])
    return re.compile(rf"(?<![а-яё])(не)?({stems})[а-яё]*|(?<![а-яё])(по\s+мере|при)\s+необходимости", re.I)


def prose(line):
    """The line with code spans and quoted strings blanked out."""
    for rx in STRIP:
        line = rx.sub(lambda m: " " * len(m.group(0)), line)
    return line


def lint_text(path, text, vague, skip_rx):
    findings = []
    in_fence = False
    skip_level = None
    for n, raw in enumerate(text.splitlines(), start=1):
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        h = HEADING.match(raw)
        if h:
            level = len(h.group(1))
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is None and skip_rx.search(h.group(2)):
                skip_level = level
            continue
        if skip_level is not None or DATED_DECISION.search(raw):
            continue
        line = prose(raw)
        quantified = bool(QUANTITY.search(line))
        for check, rule, rx in (("vague-word", "SRK-REQ-014", vague), ("unfinished", "QAP-REQ-001", UNFINISHED)):
            for m in rx.finditer(line):
                findings.append({"file": str(path), "line": n, "check": check, "rule": rule,
                                 "match": raw[m.start():m.end()], "quantified": quantified and check == "vague-word",
                                 "text": raw.strip()[:200]})
    return findings


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--overrides", type=Path)
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args(argv[1:])
    overrides = (json.loads(args.overrides.read_text(encoding="utf-8"))
                 if args.overrides and args.overrides.exists() else {})
    vague = vague_regex(overrides.get("extra_vague_words", []))
    skip_rx = re.compile("|".join(DEFAULT_SKIP_SECTIONS + overrides.get("skip_section_patterns", [])), re.I)
    findings = []
    for path in args.files:
        findings += lint_text(path, path.read_text(encoding="utf-8"), vague, skip_rx)
    print(json.dumps(findings, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
