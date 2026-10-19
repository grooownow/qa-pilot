#!/usr/bin/env python3
"""Validate the plugin's skills: frontmatter, cross-references and referenced files.

Usage: python3 scripts/plugin/check_skills.py [plugin_root]

Checks every skills/<dir>/SKILL.md:
- frontmatter has `name` equal to the directory and a non-empty `description` of at most 1024
  characters (longer descriptions are dropped by Claude Code and the skill loses its trigger);
- `user-invocable`, if present, is true or false;
- every `qa-pilot:<skill>` it mentions exists;
- every `../../references/…` or `../../knowledge/…` path it mentions exists.
Exits 1 with a list of errors.
"""
import re
import sys
from pathlib import Path

MAX_DESCRIPTION = 1024
SKILL_REF = re.compile(r"qa-pilot:([a-z][a-z0-9-]*)")
PATH_REF = re.compile(r"\.\./\.\./((?:references|knowledge)/[A-Za-z0-9_./-]+\.(?:md|json))")


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^([a-z-]+):\s*(.*)$", line)
        if kv:
            value = kv.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1].replace('\\"', '"')
            fields[kv.group(1)] = value
    return fields


def check(root):
    errors = []
    skills_dir = root / "skills"
    names = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        where = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            errors.append(f"{where}: no frontmatter")
            continue
        if fm.get("name") != path.parent.name:
            errors.append(f"{where}: name '{fm.get('name')}' must equal the directory '{path.parent.name}'")
        description = fm.get("description", "")
        if not description:
            errors.append(f"{where}: description is empty")
        elif len(description) > MAX_DESCRIPTION:
            errors.append(f"{where}: description is {len(description)} chars, max {MAX_DESCRIPTION}")
        if "user-invocable" in fm and fm["user-invocable"] not in ("true", "false"):
            errors.append(f"{where}: user-invocable must be true or false")
        for ref in sorted(set(SKILL_REF.findall(text)) - names):
            errors.append(f"{where}: mentions unknown skill qa-pilot:{ref}")
        for ref in sorted(set(PATH_REF.findall(text))):
            if not (root / ref).exists():
                errors.append(f"{where}: missing file {ref}")
    return errors


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[2]
    errors = check(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"OK: {len(list((root / 'skills').glob('*/SKILL.md')))} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
