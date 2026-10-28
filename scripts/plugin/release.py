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
# What users receive and what changes how the plugin behaves or is licensed. Docs, dev
# scripts and CI are not here: changing them needs no new version.
PLUGIN_PATHS = ("skills/", "agents/", "references/", "knowledge/", ".claude-plugin/", ".mcp.json",
                "LICENSE", "COMMERCIAL.md")


def plugin_version(root=ROOT):
    return json.loads((root / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]


def changelog_section(text, version):
    """Body of the `## [version]` section, without its heading; None when there is none."""
    match = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else None


def plugin_files(paths):
    return [p for p in paths if p.startswith(PLUGIN_PATHS)]


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
        changed = subprocess.run(["git", "diff", "--name-only", argv[2], "HEAD"], cwd=ROOT,
                                 check=True, capture_output=True, text=True).stdout.split()
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
