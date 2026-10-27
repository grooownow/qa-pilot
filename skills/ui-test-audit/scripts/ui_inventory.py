#!/usr/bin/env python3
"""Inventory of a UI component library: atoms vs compositions, stories, play stories, tests.

Usage: python3 ui_inventory.py --root <dir> --lib <path> [--lib <path> ...]
                               [--alias <prefix>=<path> ...] [--json]

Component files are *.tsx, *.jsx, *.vue and *.svelte under the --lib paths, except *.stories.*,
*.test.*, *.spec.* and *.d.ts. The name is the file stem, or the parent directory for `index`.
A component that imports another library component is a composition, otherwise an atom.
Imports are followed through relative paths and --alias prefixes (`@/ui=src/ui`), including
barrel files (index.ts with only re-exports). Package imports are ignored; an alias-looking
import (`@/`, `~/` or a given prefix) that resolves to nothing is listed as unresolved.
Stories are `X.stories.*` next to component X; play stories are exports that define `play`.
Tests are `X.test.*` / `X.spec.*`.

Prints a markdown summary and table (or JSON with --json). Exit 0 ok, 2 bad input.
The import scan is regex-based and shallow on purpose: dynamic imports and computed paths are not seen.
"""
import argparse
import json
import re
import sys
from pathlib import Path

COMPONENT_EXTS = (".tsx", ".jsx", ".vue", ".svelte")
RESOLVE_EXTS = (".tsx", ".jsx", ".vue", ".svelte", ".ts", ".js")
SKIP_DIRS = {"node_modules", ".git", "dist", "build"}
IMPORT_RE = re.compile(r"""(?:^|\n)\s*import\s+(?:type\s+)?(?:([^'";]*?)\s+from\s+)?['"]([^'"]+)['"]""")
EXPORT_FROM_RE = re.compile(r"""export\s+(?:type\s+)?(\*(?:\s+as\s+\w+)?|\{[^}]*\})\s*from\s*['"]([^'"]+)['"]""")
STORY_EXPORT_RE = re.compile(r"export\s+(?:const|function)\s+(\w+)")
PLAY_RE = re.compile(r"play\s*[:(]")


def is_aux(name):
    return bool(re.search(r"\.(stories|test|spec)\.[^.]+$", name)) or name.endswith(".d.ts")


def is_barrel(path, text):
    if path.stem != "index" or path.suffix not in (".ts", ".tsx", ".js"):
        return False
    body = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
    body = EXPORT_FROM_RE.sub("", body)
    return not body.strip().strip(";").strip()


def comp_name(path):
    return path.parent.name if path.stem == "index" else path.stem


def candidates(base):
    yield base
    for ext in RESOLVE_EXTS:
        yield Path(str(base) + ext)
    for ext in RESOLVE_EXTS:
        yield base / ("index" + ext)


def resolve(base):
    for c in candidates(base):
        if c.is_file():
            return c.resolve()
    return None


def spec_base(spec, file, aliases):
    """Return (kind, base path or None). kind: rel | alias | alias-miss | pkg."""
    if spec.startswith("."):
        return "rel", file.parent / spec
    for prefix, target in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
        if spec == prefix or spec.startswith(prefix.rstrip("/") + "/"):
            rest = spec[len(prefix):].lstrip("/")
            return "alias", target / rest if rest else target
    if spec.startswith(("@/", "~/")):
        return "alias-miss", None
    return "pkg", None


def inventory(root, libs, aliases):
    root = Path(root).resolve()
    libs = [Path(p).resolve() for p in libs]
    aliases = {k: Path(v).resolve() for k, v in aliases.items()}
    files = sorted({f.resolve() for lib in libs for f in lib.rglob("*")
                    if f.is_file() and not (SKIP_DIRS & set(f.relative_to(lib).parts))})
    texts = {}

    def text(f):
        if f not in texts:
            texts[f] = f.read_text(encoding="utf-8", errors="replace")
        return texts[f]

    comps = {}
    barrels = set()
    for f in files:
        if f.suffix in COMPONENT_EXTS and not is_aux(f.name):
            comps[f] = {"name": comp_name(f), "path": f}
        elif f.stem == "index" and f.suffix in (".ts", ".js") and is_barrel(f, text(f)):
            barrels.add(f)
    # tsx barrels are also barrels (they are not components when they only re-export)
    for f in list(comps):
        if f.stem == "index" and is_barrel(f, text(f)):
            barrels.add(f)
            del comps[f]

    def exports_of(barrel, seen):
        """Map exported name -> component file, following nested barrels; cycle-safe."""
        out = {}
        if barrel in seen:
            return out
        seen.add(barrel)
        for what, spec in EXPORT_FROM_RE.findall(text(barrel)):
            kind, base = spec_base(spec, barrel, aliases)
            target = resolve(base) if base is not None else None
            if target is None:
                continue
            if target in barrels:
                sub = exports_of(target, seen)
                if what.startswith("{"):
                    wanted = {p.split(" as ")[-1].strip() for p in what.strip("{}").split(",") if p.strip()}
                    sub = {k: v for k, v in sub.items() if k in wanted}
                out.update(sub)
            elif target in comps:
                if what.startswith("{"):
                    for part in what.strip("{}").split(","):
                        part = part.strip()
                        if part:
                            out[part.split(" as ")[-1].strip()] = target
                else:
                    out[comps[target]["name"]] = target
        return out

    unresolved = []
    for f, c in comps.items():
        uses = []
        for clause, spec in IMPORT_RE.findall(text(f)):
            kind, base = spec_base(spec, f, aliases)
            if kind == "pkg":
                continue
            target = resolve(base) if base is not None else None
            if target is None:
                if kind != "rel":
                    unresolved.append({"file": str(f.relative_to(root)) if root in f.parents else str(f),
                                       "import": spec})
                continue
            found = []
            if target in barrels:
                table = exports_of(target, set())
                named = re.search(r"\{([^}]*)\}", clause or "")
                if named:
                    for part in named.group(1).split(","):
                        name = part.strip().split(" as ")[0].strip().removeprefix("type ").strip()
                        if name in table:
                            found.append(comps[table[name]]["name"])
                else:
                    found.extend(comps[t]["name"] for t in table.values())
            elif target in comps:
                found.append(comps[target]["name"])
            for n in found:
                if n != c["name"] and n not in uses:
                    uses.append(n)
        c["uses"] = uses

    by_name = {}
    for c in comps.values():
        by_name.setdefault(c["name"], c)
    for c in comps.values():
        c.update(stories=[], play_stories=[], tests=[])
    for f in files:
        m = re.match(r"(.+)\.(stories|test|spec)\.[^.]+$", f.name)
        if not m:
            continue
        stem, kind = m.groups()
        c = by_name.get(stem)
        if c is None and stem == "index":
            c = by_name.get(f.parent.name)
        if c is None:
            continue
        if kind == "stories":
            body = text(f)
            exports = list(STORY_EXPORT_RE.finditer(body))
            for i, e in enumerate(exports):
                c["stories"].append(e.group(1))
                end = exports[i + 1].start() if i + 1 < len(exports) else len(body)
                if PLAY_RE.search(body[e.end():end]):
                    c["play_stories"].append(e.group(1))
        else:
            c["tests"].append(str(f.relative_to(root)) if root in f.parents else str(f))

    components = []
    for c in sorted(comps.values(), key=lambda c: str(c["path"])):
        components.append({
            "name": c["name"],
            "path": str(c["path"].relative_to(root)) if root in c["path"].parents else str(c["path"]),
            "kind": "composition" if c["uses"] else "atom",
            "uses": c["uses"], "stories": c["stories"], "play_stories": c["play_stories"],
            "tests": sorted(c["tests"]),
        })
    return {
        "components": components,
        "unresolved": unresolved,
        "summary": {
            "components": len(components),
            "atoms": sum(c["kind"] == "atom" for c in components),
            "compositions": sum(c["kind"] == "composition" for c in components),
            "with_stories": sum(bool(c["stories"]) for c in components),
            "with_play": sum(bool(c["play_stories"]) for c in components),
        },
    }


def render(result):
    s = result["summary"]
    lines = [f"{s['components']} components: {s['atoms']} atoms, {s['compositions']} compositions; "
             f"{s['with_stories']} with stories, {s['with_play']} with play tests", "",
             "| Name | Kind | Stories | Play | Tests | Uses |", "|---|---|---|---|---|---|"]
    for c in result["components"]:
        lines.append(f"| {c['name']} | {c['kind']} | {len(c['stories'])} | {len(c['play_stories'])} | "
                     f"{len(c['tests'])} | {', '.join(c['uses'])} |")
    if result["unresolved"]:
        lines += ["", f"Unresolved imports ({len(result['unresolved'])}):"]
        lines += [f"- {u['file']}: {u['import']}" for u in result["unresolved"]]
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(prog="ui_inventory.py", description="Inventory of a UI component library.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--lib", action="append", default=[])
    ap.add_argument("--alias", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    try:
        args = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    root = Path(args.root)
    if not args.lib:
        print("error: at least one --lib is required")
        return 2
    libs = []
    for lib in args.lib:
        p = Path(lib) if Path(lib).is_absolute() else root / lib
        if not p.exists():
            print(f"error: --lib path does not exist: {lib}")
            return 2
        libs.append(p)
    aliases = {}
    for a in args.alias:
        if "=" not in a:
            print(f"error: --alias must be prefix=path, got: {a}")
            return 2
        prefix, path = a.split("=", 1)
        aliases[prefix] = Path(path) if Path(path).is_absolute() else root / path
    result = inventory(root, libs, aliases)
    print(json.dumps(result, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
