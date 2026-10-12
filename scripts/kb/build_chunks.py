#!/usr/bin/env python3
"""Split the Surkov QA book PDF into heading-bounded chunks.

Usage: python3 scripts/kb/build_chunks.py <book.pdf> <kb_dir>

Writes the full text only under <kb_dir>/raw/ (gitignored) and a text-free
table of contents to <kb_dir>/toc.json and <kb_dir>/toc.md. If
<kb_dir>/topics.json exists, chunks are tagged with topics and
<kb_dir>/topics.md is rendered. Output is deterministic.

Requires poppler (pdftotext, pdfimages).
"""
import difflib
from collections import Counter
import json
import re
import subprocess
import sys
from pathlib import Path

MAX_WORDS = 1500
MIN_WORDS = 80
SEARCH_WINDOW_PAGES = 40

LEADER_RE = re.compile(r"^(?P<title>.*?)\s*\.{2,}\s*(?P<page>\d+)\s*$")
PAGE_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*$")
RUNNING_HEADER_RE = re.compile(r"^\s*(ГЛАВА|РАЗДЕЛ)\s+\d+")
SECTION_RE = re.compile(r"^РАЗДЕЛ\s+(\d+)")
CHAPTER_RE = re.compile(r"^ГЛАВА\s+(\d+)")
GLUED_ENTRY_RE = re.compile(r"^(.*\S)\.?\s+(\d{2,3})\s+(\S.*)$")
INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)


def normalize(s):
    """Canonical form of a heading for matching TOC entries to body lines."""
    s = s.translate(INVISIBLE).replace(" ", " ").lower().replace("ё", "е")
    s = re.sub(r"[‐-―−]", "-", s)
    s = re.sub(r"^[\s\-•●○■▪*]+", "", s)
    s = re.sub(r"[\s:.]+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def word_count(text):
    return len(re.findall(r"\w+", text))


def strip_page_furniture(page_text, prev_header=None):
    """Drop the page-number footer and a running header repeated from the
    previous page. A header that differs from prev_header is kept: it is the
    first page of a chapter and often the only copy of the chapter heading.

    Returns (body_lines, printed_page or None, header or None).
    """
    lines = page_text.translate(INVISIBLE).split("\n")
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    printed = None
    if nonempty:
        m = PAGE_NUM_RE.match(lines[nonempty[-1]])
        if m:
            printed = int(m.group(1))
            lines[nonempty[-1]] = ""
            nonempty.pop()
    header = None
    if nonempty and RUNNING_HEADER_RE.match(lines[nonempty[0]]):
        header = lines[nonempty[0]].strip()
        if normalize(header) == normalize(prev_header or ""):
            lines[nonempty[0]] = ""
    return [line.rstrip() for line in lines], printed, header


def is_toc_page(page_text):
    lines = [line for line in page_text.split("\n") if line.strip()]
    if len(lines) < 5:
        return False
    return sum(1 for line in lines if LEADER_RE.match(line)) / len(lines) >= 0.5


def parse_toc(lines):
    """Parse dot-leader TOC lines into [(level, number, title, toc_page)].

    level is "section", "chapter" or "sub". number is the section/chapter
    number for those levels, else None. A line without a leader is joined to
    the following line (wrapped entry).
    """
    entries = []
    pending = ""
    for raw in lines:
        line = raw.translate(INVISIBLE).strip()
        if not line or PAGE_NUM_RE.match(line):
            continue
        m = LEADER_RE.match(line)
        if not m:
            if line.upper() != "СОДЕРЖАНИЕ":
                pending = (pending + " " + line).strip()
            continue
        title = re.sub(r"\s+", " ", (pending + " " + m.group("title")).strip())
        pending = ""
        page = int(m.group("page"))
        glued = GLUED_ENTRY_RE.match(title)
        prev_page = entries[-1][3] if entries else 0
        if glued and prev_page <= int(glued.group(2)) <= page:
            entries.append(("sub", None, glued.group(1), int(glued.group(2))))
            title = glued.group(3)
        sm, cm = SECTION_RE.match(title), CHAPTER_RE.match(title)
        if sm:
            entries.append(("section", int(sm.group(1)), title, page))
        elif cm:
            entries.append(("chapter", int(cm.group(1)), title, page))
        else:
            entries.append(("sub", None, title, page))
    return entries


def split_long(text, max_words=MAX_WORDS):
    """Split text on blank-line paragraph boundaries into parts <= max_words.

    A single paragraph longer than max_words stays whole.
    """
    paragraphs = re.split(r"\n\s*\n", text.strip())
    parts, current, count = [], [], 0
    for para in paragraphs:
        n = word_count(para)
        if current and count + n > max_words:
            parts.append("\n\n".join(current))
            current, count = [], 0
        current.append(para)
        count += n
    if current:
        parts.append("\n\n".join(current))
    return parts


def find_heading(norm_lines, title, start, stop):
    """Index of the body line matching title within [start, stop), else None.

    Tries exact (single line, then up to four joined lines), then a long
    prefix of the title (body headings sometimes drop a parenthetical), then
    scattered words, then fuzzy >= 0.88.
    """
    target = normalize(title)
    for i in range(start, stop):
        if not norm_lines[i]:
            continue
        joined = norm_lines[i]
        if joined == target:
            return i
        for k in range(1, 4):
            if i + k >= stop or not norm_lines[i + k] or not target.startswith(joined):
                break
            joined = normalize(joined + " " + norm_lines[i + k])
            if joined == target:
                return i
    for i in range(start, stop):
        line = norm_lines[i]
        if len(line) >= 20 and target.startswith(line) and len(line) >= 0.6 * len(target):
            return i
    hit = find_scattered(norm_lines, target, start, stop)
    if hit is not None:
        return hit
    best, best_ratio = None, 0.88
    for i in range(start, stop):
        line = norm_lines[i]
        if not line or abs(len(line) - len(target)) > max(8, len(target) // 3):
            continue
        ratio = difflib.SequenceMatcher(None, line, target).ratio()
        if ratio > best_ratio:
            best, best_ratio = i, ratio
    return best


def find_scattered(norm_lines, target, start, stop, max_lines=12):
    """Justified headings come out of pdftotext as word fragments on separate
    lines, out of order. Match a run of non-empty lines made only of the
    title's words that together contain all of them."""
    want = Counter(re.findall(r"\w+", target))
    if len(want) < 3:
        return None
    for i in range(start, stop):
        if not norm_lines[i]:
            continue
        got, used, j = Counter(), 0, i
        while j < stop and used < max_lines:
            line = norm_lines[j]
            j += 1
            if not line:
                continue
            words = Counter(re.findall(r"\w+", line))
            if not words or any(w not in want for w in words):
                break
            got += words
            used += 1
            if not (want - got):
                return i
    return None


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def image_counts(pdf):
    counts = {}
    for line in run(["pdfimages", "-list", str(pdf)]).splitlines()[2:]:
        fields = line.split()
        if fields and fields[0].isdigit():
            counts[int(fields[0])] = counts.get(int(fields[0]), 0) + 1
    return counts


def yaml_scalar(v):
    return json.dumps(v, ensure_ascii=False)


def build(pdf, kb_dir):
    raw_dir = kb_dir / "raw"
    pages = run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"]).split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    images = image_counts(pdf)

    (raw_dir / "pages").mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(pages, start=1):
        (raw_dir / "pages" / f"{i:03d}.txt").write_text(text, encoding="utf-8")

    toc_idx = [i for i, p in enumerate(pages) if is_toc_page(p)]
    toc_first, toc_last = toc_idx[0], toc_idx[-1]
    toc_lines = [line for p in pages[toc_first:toc_last + 1] for line in p.split("\n")]
    toc = parse_toc(toc_lines)
    first_section = next(i for i, e in enumerate(toc) if e[0] == "section")
    front_titles = [e[2] for e in toc[:first_section]]
    toc = toc[first_section:]

    # Body lines with their page; front matter (before the TOC) is chunk s0.
    body = []  # (pdf_page, printed_page, line)
    header = None
    for pidx in range(toc_last + 1, len(pages)):
        lines, printed, page_header = strip_page_furniture(pages[pidx], header)
        header = page_header or header
        body.extend((pidx + 1, printed, line) for line in lines)
    norm_lines = [normalize(line) for _, _, line in body]
    page_start = {}
    for i, (pdf_page, _, _) in enumerate(body):
        page_start.setdefault(pdf_page, i)

    # Match TOC entries to body lines, in order.
    matches, unmatched, cursor = [], [], 0
    for entry in toc:
        stop_page = body[cursor][0] + SEARCH_WINDOW_PAGES if cursor < len(body) else 0
        stop = page_start.get(stop_page, len(body))
        idx = find_heading(norm_lines, entry[2], cursor, stop)
        if idx is None:
            unmatched.append(entry)
            matches.append(None)
        else:
            matches.append(idx)
            cursor = idx + 1

    # Assign ids: walk entries, tracking section/chapter, numbering subs.
    boundaries = []  # (line_idx, entry, chunk_id, section_title, chapter_title)
    sec = ch = sub = 0
    sec_title = ch_title = ""
    for entry, idx in zip(toc, matches):
        level, number, title, _ = entry
        if level == "section":
            sec, ch, sub, sec_title, ch_title = number, 0, 0, title, ""
        elif level == "chapter":
            ch, sub, ch_title = number, 0, title
        else:
            sub += 1
        if idx is not None:
            boundaries.append((idx, entry, f"s{sec}-c{ch:02d}-{sub:02d}", sec_title, ch_title))

    def span_meta(lo, hi):
        pdf_pages = sorted({body[i][0] for i in range(lo, hi)} or {body[lo][0]})
        printed = [body[i][1] for i in range(lo, hi) if body[i][1] is not None]
        return pdf_pages, printed

    raw_chunks = []
    for n, (idx, entry, cid, sec_title, ch_title) in enumerate(boundaries):
        if n == 0:
            idx = 0  # body lines before the first heading belong to the first chunk
        end = boundaries[n + 1][0] if n + 1 < len(boundaries) else len(body)
        text = "\n".join(body[i][2] for i in range(idx, end)).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        pdf_pages, printed = span_meta(idx, end)
        raw_chunks.append({
            "id": cid, "section": sec_title, "chapter": ch_title,
            "headings": [entry[2]], "pdf_pages": [pdf_pages[0], pdf_pages[-1]],
            "printed_pages": [printed[0], printed[-1]] if printed else [],
            "text": text,
        })

    # Merge tiny chunks into the next chunk of the same chapter.
    merged = []
    carry = None
    for c in raw_chunks:
        if carry:
            same_chapter = carry["id"].rsplit("-", 1)[0] == c["id"].rsplit("-", 1)[0]
            if same_chapter:
                c = {**c, "id": carry["id"], "headings": carry["headings"] + c["headings"],
                     "pdf_pages": [carry["pdf_pages"][0], c["pdf_pages"][1]],
                     "printed_pages": [(carry["printed_pages"] or c["printed_pages"])[0],
                                       (c["printed_pages"] or carry["printed_pages"])[-1]]
                     if (carry["printed_pages"] or c["printed_pages"]) else [],
                     "text": carry["text"] + "\n\n" + c["text"]}
            else:
                merged.append(carry)
            carry = None
        if word_count(c["text"]) < MIN_WORDS:
            carry = c
        else:
            merged.append(c)
    if carry:
        merged.append(carry)

    # Front matter chunk (author, about the book) from pages before the TOC.
    front_text = "\n".join(
        line for p in pages[:toc_first] for line in strip_page_furniture(p)[0]).strip()
    front = {"id": "s0-c00-00", "section": "Вводная часть", "chapter": "",
             "headings": front_titles, "pdf_pages": [1, toc_first],
             "printed_pages": [], "text": re.sub(r"\n{3,}", "\n\n", front_text)}

    chunks = []
    for c in [front] + merged:
        parts = split_long(c["text"]) if word_count(c["text"]) > MAX_WORDS else [c["text"]]
        for k, part in enumerate(parts, start=1):
            cid = c["id"] if len(parts) == 1 else f"{c['id']}-p{k}"
            chunks.append({**c, "id": cid, "text": part, "words": word_count(part)})

    for c in chunks:
        lo, hi = c["pdf_pages"]
        c["images"] = sum(images.get(p, 0) for p in range(lo, hi + 1))

    topics_cfg = load_topics(kb_dir)
    for c in chunks:
        c["topics"] = topics_for(c["id"], topics_cfg)

    # Write chunks.
    chunk_dir = raw_dir / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for old in chunk_dir.glob("*.md"):
        old.unlink()
    with open(raw_dir / "chunks.jsonl", "w", encoding="utf-8") as jl:
        for c in chunks:
            record = {k: c[k] for k in ("id", "section", "chapter", "headings", "pdf_pages",
                                        "printed_pages", "words", "images", "topics", "text")}
            jl.write(json.dumps(record, ensure_ascii=False) + "\n")
            meta = "\n".join(f"{k}: {yaml_scalar(record[k])}" for k in record if k != "text")
            (chunk_dir / f"{c['id']}.md").write_text(f"---\n{meta}\n---\n\n{c['text']}\n", encoding="utf-8")

    # TOC (text-free) — each entry points at the chunk holding its heading.
    heading_to_chunk = {}
    for c in chunks:
        for h in c["headings"]:
            heading_to_chunk.setdefault(h, c["id"].split("-p")[0] if "-p" in c["id"] else c["id"])
    chunk_words = {}
    for c in chunks:
        base = re.sub(r"-p\d+$", "", c["id"])
        chunk_words[base] = chunk_words.get(base, 0) + c["words"]
    toc_out = []
    for entry, idx in zip(toc, matches):
        level, number, title, toc_page = entry
        cid = heading_to_chunk.get(title) if idx is not None else None
        toc_out.append({
            "level": level, "title": title, "toc_page": toc_page,
            "pdf_page": body[idx][0] if idx is not None else None,
            "chunk_id": cid, "words": chunk_words.get(cid) if cid else None,
            "parts": sorted(c["id"] for c in chunks if cid and re.sub(r"-p\d+$", "", c["id"]) == cid),
        })
    (kb_dir / "toc.json").write_text(json.dumps(toc_out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (kb_dir / "toc.md").write_text(render_toc_md(toc_out), encoding="utf-8")

    if topics_cfg:
        (kb_dir / "topics.md").write_text(render_topics_md(topics_cfg, chunks), encoding="utf-8")

    # Report.
    body_words = word_count("\n".join(line for _, _, line in body)) + word_count(front_text)
    chunk_words_total = sum(c["words"] for c in chunks)
    report = [
        f"pages: {len(pages)}  toc pages: {toc_first + 1}-{toc_last + 1}",
        f"toc entries: {len(toc)}  matched: {len(toc) - len(unmatched)}  unmatched: {len(unmatched)}",
        f"chunks: {len(chunks)}",
        f"coverage: {chunk_words_total}/{body_words} words = {100 * chunk_words_total / body_words:.2f}%",
        "", "UNMATCHED (text stays in the preceding chunk):",
    ] + [f"  [{e[0]}] {e[2]} (toc p.{e[3]})" for e in unmatched]
    if topics_cfg:
        untagged = [c["id"] for c in chunks if not c["topics"]]
        report += ["", f"UNTAGGED CHUNKS: {len(untagged)}"] + [f"  {u}" for u in untagged]
    (raw_dir / "build-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:4]))
    return len(unmatched)


def load_topics(kb_dir):
    path = kb_dir / "topics.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def topics_for(chunk_id, cfg):
    """Topics whose prefixes match chunk_id (longest-prefix semantics not needed:
    a chunk may legitimately belong to several topics)."""
    if not cfg:
        return []
    return sorted(name for name, t in cfg["topics"].items()
                  if any(chunk_id == p or chunk_id.startswith(p + "-") for p in t["prefixes"]))


def render_toc_md(toc_out):
    out = ["# Оглавление книги (без текста)", "",
           "Сгенерировано `scripts/kb/build_chunks.py`. `chunk_id` → `raw/chunks/<id>.md` "
           "(локально, не в git). Номера страниц — индекс PDF.", ""]
    for e in toc_out:
        ref = f"`{e['chunk_id']}` · стр. {e['pdf_page']} · {e['words']} сл." if e["chunk_id"] else "—"
        if e["parts"] and len(e["parts"]) > 1:
            ref += f" · {len(e['parts'])} части"
        if e["level"] == "section":
            out += ["", f"## {e['title']}", ""]
        elif e["level"] == "chapter":
            out += [f"- **{e['title']}** — {ref}"]
        else:
            out += [f"  - {e['title']} — {ref}"]
    return "\n".join(out) + "\n"


def render_topics_md(cfg, chunks):
    out = ["# Индекс тем", "",
           "Тема → файл правил → куски книги. Источник: `topics.json`; файл генерируется "
           "`scripts/kb/build_chunks.py`. Глубина: deep — извлекается максимально полно, "
           "medium — советы и «на что смотреть», index — только оглавление и саммари.", ""]
    for name, t in cfg["topics"].items():
        ids = [c["id"] for c in chunks if name in c["topics"]]
        words = sum(c["words"] for c in chunks if name in c["topics"])
        out += [f"## {name} — {t['title']}", "",
                f"- Глубина: {t['depth']}",
                f"- Правила: {'`' + t['rules'] + '`' if t.get('rules') else '— (не извлекаются)'}",
                f"- Главы: {', '.join(t['prefixes'])}",
                f"- Куски ({len(ids)}, {words} слов): " + (", ".join(f"`{i}`" for i in ids) or "—")]
        if t.get("note"):
            out.append(f"- Примечание: {t['note']}")
        out.append("")
    return "\n".join(out)


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    pdf, kb_dir = Path(argv[1]), Path(argv[2])
    kb_dir.mkdir(parents=True, exist_ok=True)
    build(pdf, kb_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
