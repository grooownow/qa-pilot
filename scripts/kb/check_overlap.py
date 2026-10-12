#!/usr/bin/env python3
"""Flag rule records that copy the book verbatim.

Usage: python3 scripts/kb/check_overlap.py <kb_dir> [min_words]

For every record in <kb_dir>/rules/*.json, finds the longest run of words
shared with the WHOLE book text (raw/chunks.jsonl), not just the cited chunk.
Records with a run of >= min_words (default 8) are printed and the script
exits 1. Requires the local raw/ corpus.
"""
import json
import re
import sys
from pathlib import Path

FIELDS = ("title", "statement", "rationale")


def words(text):
    return re.findall(r"\w+", text.lower().replace("ё", "е"))


def longest_shared_run(record_words, book_ngrams, n):
    """(length, phrase) of the longest run of record_words found in the book."""
    best, phrase, i = 0, "", 0
    while i + n <= len(record_words):
        if tuple(record_words[i:i + n]) in book_ngrams:
            j = i + n
            while j < len(record_words) and tuple(record_words[j - n + 1:j + 1]) in book_ngrams:
                j += 1
            if j - i > best:
                best, phrase = j - i, " ".join(record_words[i:j])
            i = j
        else:
            i += 1
    return best, phrase


def record_text(r):
    return " ".join(r.get(f, "") for f in FIELDS) + " " + r.get("check", {}).get("how", "")


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    kb_dir = Path(argv[1])
    n = int(argv[2]) if len(argv) == 3 else 8
    book = []
    for line in (kb_dir / "raw" / "chunks.jsonl").read_text(encoding="utf-8").splitlines():
        book.extend(words(json.loads(line)["text"]) + ["\0"])
    ngrams = {tuple(book[i:i + n]) for i in range(len(book) - n + 1)}
    hits = []
    for path in sorted((kb_dir / "rules").glob("*.json")):
        for r in json.loads(path.read_text(encoding="utf-8")):
            run, phrase = longest_shared_run(words(record_text(r)), ngrams, n)
            if run:
                hits.append((run, r["id"], phrase))
    for run, rid, phrase in sorted(hits, reverse=True):
        print(f"{rid}: {run} words: «{phrase}»")
    print(f"{len(hits)} record(s) with >= {n} shared consecutive words")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
