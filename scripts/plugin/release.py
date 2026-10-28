"""Release helper for .github/workflows/release.yml (runs on every push to main).

Users get a new copy of the plugin only when `version` in plugin.json changes. The workflow
publishes a GitHub Release (and tag) for a new version, with its CHANGELOG section as notes,
and fails when plugin files changed since the last release while the version stayed the same.

Usage: python3 scripts/plugin/release.py version      print the version in plugin.json
       python3 scripts/plugin/release.py notes        print its CHANGELOG section, exit 1 if missing
       python3 scripts/plugin/release.py stale TAG    list plugin files changed since TAG, exit 1 if any
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Files that do not change how the plugin behaves or is licensed: docs, dev scripts, CI and
# the marketplace listing. Every other file is shipped plugin content, so a new component
# (hooks/, commands/, settings.json) needs a new version without editing this list.
EXEMPT = ("README.md", "CHANGELOG.md", ".gitignore", "docs/", "scripts/", ".github/",
          ".claude-plugin/marketplace.json")


def plugin_version(root=ROOT):
    return json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]


def changelog_section(text, version):
    """Body of the `## [version]` section, without its heading; None when there is none."""
    match = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else None


def plugin_files(paths):
    return [p for p in paths if p and not p.startswith(EXEMPT)]


def main(argv):
    command = argv[1] if len(argv) > 1 else ""
    if command == "version":
        print(plugin_version())
        return 0
    if command == "notes":
        version = plugin_version()
        notes = changelog_section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version)
        if not notes:
            print(f"CHANGELOG.md has no '## [{version}]' section", file=sys.stderr)
            return 1
        print(notes)
        return 0
    if command == "stale" and len(argv) == 3:
        tag = subprocess.run(["git", "rev-parse", "--verify", "-q", f"{argv[2]}^{{commit}}"], cwd=ROOT,
                             capture_output=True)
        if tag.returncode:
            print(f"Tag {argv[2]} is not in this checkout: fetch tags (fetch-depth: 0).", file=sys.stderr)
            return 1
        # -z: paths with spaces or non-ASCII names come through unquoted.
        changed = subprocess.run(["git", "diff", "-z", "--name-only", argv[2], "HEAD"], cwd=ROOT,
                                 check=True, capture_output=True, text=True).stdout.split("\0")
        stale = plugin_files(changed)
        if stale:
            print(f"Plugin files changed since {argv[2]}, but plugin.json still says "
                  f"{plugin_version()}. Users will not get these changes: bump the version and add "
                  "a CHANGELOG section.", file=sys.stderr)
            print("\n".join(stale), file=sys.stderr)
            return 1
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
