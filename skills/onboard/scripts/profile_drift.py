#!/usr/bin/env python3
"""Check docs/qa/project-profile.md against the repo it describes: has the profile gone stale?

Usage: python3 profile_drift.py [--profile docs/qa/project-profile.md] [--root .]

Reads the inline-code commands and paths in the profile's `## Commands` and `## Test layers`
sections and compares them with package.json scripts, the Makefile and the CI config files.
Prints one line per drift and exits 1; prints "OK: …" and exits 0 when nothing drifted;
exits 2 when there is no profile to check.

Drift:
  missing-script  a profile command runs a package or make script that no longer exists
  missing-path    a path the profile names no longer exists
  left-ci         the profile says CI runs a layer, but no CI file runs its command any more
                  and none has the CI job the profile names for it
  joined-ci       the profile says CI does not run a layer, but a CI file runs its command now
  new-ci-command  a CI file runs a test command the profile does not mention
  new-test-dep    a known test package is a dependency, but its name appears nowhere in the profile
  rules-changed   a project-rules file (CLAUDE.md, lint or test config) was committed after the profile
  lost-test       docs/qa/coverage-matrix.md names a test file that no longer exists
                  (rows whose Test cell contains "(removed " are kept history and skipped)

Workflows that only run by hand (`on: workflow_dispatch`) are not CI. In a monorepo the CI files
at the repository root count too. The check is deliberately shallow (string matching, no YAML
parsing): it catches renamed scripts, moved test directories and changed CI jobs, the usual
reasons a profile goes stale.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CI_GLOBS = [".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml", ".circleci/config.yml",
            "azure-pipelines.yml", "bitbucket-pipelines.yml", "Jenkinsfile"]
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".venv", "venv"}
PACKAGE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
# Package-manager subcommands that are not user scripts.
PM_BUILTINS = {"install", "i", "ci", "add", "remove", "exec", "dlx", "x", "create", "init", "audit",
               "outdated", "update", "upgrade", "link", "publish", "pack", "why", "list", "ls", "config",
               "set", "workspace", "workspaces", "dedupe", "prune", "rebuild", "store", "env", "help", "version", "info"}
# Flags that take a value before the script name: `pnpm --filter web test:e2e`, `npm -w app run test`.
PM_VALUE_FLAGS = {"--filter", "-F", "-C", "--dir", "--prefix", "--workspace", "--cwd"}
# Binaries pnpm/yarn/bun run directly when no script has the name (`pnpm playwright test`).
KNOWN_BINS = {"playwright", "vitest", "jest", "cypress", "tsc", "eslint", "prettier", "biome", "vite", "next",
              "tsx", "mocha", "storybook", "turbo", "nx", "lerna"}
TEST_WORD = re.compile(r"test|spec|e2e|playwright|cypress|vitest|jest|pytest|mocha")
TEST_TOOL = re.compile(r"(playwright test|cypress run|vitest|jest|pytest|go test|cargo test|mocha)\b[^\n]*")
NOT_IN_CI = re.compile(r"^\s*(?:(?:no|not|none|never|manual|manually|local|locally|нет|не|вручную|локально|n/a)\b|[—–-]\s*$|[—–-]\s)", re.I)
# End of a script name inside a CI line: whitespace, a closing quote or the end of the line.
WORD_END = r"""(?:[\s'"]|$)"""
# Bare names of test-related packages (scope dropped); the first group of each is the family reported once.
TEST_DEPS = {"playwright", "cypress", "vitest", "jest", "mocha", "msw", "nock", "supertest", "testing-library",
             "storybook", "stryker", "testcontainers", "pytest", "pytest-playwright", "hypothesis", "mutmut"}
SCOPED_DEPS = {"@playwright/test": "playwright", "@storybook/test": "storybook"}
SCOPE_FAMILIES = {"@testing-library": "testing-library", "@stryker-mutator": "stryker"}
RULES_NAMES = {"CLAUDE.md", "AGENTS.md", ".cursorrules", "pytest.ini"}
RULES_PREFIXES = ("eslint.config.", ".eslintrc", "playwright.config.", "vitest.config.", "jest.config.",
                  "cypress.config.")


def mentions(text, phrase):
    """phrase occurs in text as a whole command or name: `pnpm test` is not in `pnpm test:e2e`, `web` not in `webpack`."""
    return re.search(rf"(?<![\w:.-]){re.escape(phrase)}(?![\w:.-])", text) is not None
YAML_KEY = re.compile(r"^-?\s*[\w-]+:(?:\s|$)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
PATH_LIKE = re.compile(r"^\.{0,2}/?[\w@.-]+(?:/[\w@.*-]*)+/?$|^[\w.-]+\.(?:ts|js|mjs|cjs|json|ya?ml|toml|ini|cfg|py)$")


def section(text, title):
    """Body of the `## <title>` section (up to the next `## ` heading), or ''."""
    m = re.search(rf"^##\s+{re.escape(title)}\b.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1) if m else ""


def table_rows(body):
    """Markdown table rows as lists of cells; the header row first, separator rows dropped."""
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def script_ref(command):
    """('pm' | 'make', script name) that a shell command runs, or None."""
    tokens = command.split()
    if not tokens:
        return None
    tool, rest = tokens[0], tokens[1:]
    if tool == "make":
        targets, i = [], 0
        while i < len(rest):
            t = rest[i]
            if t in ("-C", "-f", "--directory", "--file", "-I", "-j") and i + 1 < len(rest):
                i += 2
                continue
            if not t.startswith("-") and "=" not in t:
                targets.append(t)
            i += 1
        return ("make", targets[0]) if targets else None
    if tool not in PACKAGE_MANAGERS:
        return None
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        takes_value = rest[i] in PM_VALUE_FLAGS or (tool == "npm" and rest[i] == "-w")
        i += 2 if takes_value and "=" not in rest[i] else 1
    if i >= len(rest):
        return None
    word = rest[i]
    if tool == "yarn" and word == "workspace":  # yarn workspace <package> <script>
        return ("pm", rest[i + 2]) if len(rest) > i + 2 else None
    if word in ("run", "run-script"):
        names = [t for t in rest[i + 1:] if not t.startswith("-")]
        return ("pm", names[0]) if names else None
    if tool == "npm" and word in ("test", "t", "start"):
        return ("pm", "test" if word == "t" else word)
    if tool == "npm" or word in PM_BUILTINS:
        return None
    return ("pm", word)


def git_top(root):
    """The repository root that holds .git (CI config lives there in a monorepo), or root itself."""
    for path in (root, *root.parents):
        if (path / ".git").exists():
            return path
    return root


def repo_files(top):
    """Paths of the repo's files relative to top: tracked and untracked-not-ignored, or a pruned walk."""
    try:
        out = subprocess.run(["git", "-C", str(top), "ls-files", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, text=True, timeout=30, check=True).stdout
        return [Path(line) for line in out.splitlines() if line]
    except (OSError, subprocess.SubprocessError):
        files = []
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            files += [Path(dirpath, f).relative_to(top) for f in filenames]
        return files


def package_info(top, files):
    """(scripts, binaries): every package.json script, and the commands its dependencies install."""
    scripts, bins = {}, set(KNOWN_BINS)
    for rel in files:
        if rel.name != "package.json":
            continue
        try:
            data = json.loads((top / rel).read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        scripts.update(data.get("scripts") or {})
        for key in ("dependencies", "devDependencies"):
            bins.update(name.split("/")[-1] for name in data.get(key) or {})
    for path in (top / "node_modules" / ".bin", *(top / rel.parent / "node_modules" / ".bin"
                                                   for rel in files if rel.name == "package.json")):
        if path.is_dir():
            bins.update(p.name for p in path.iterdir())
    return scripts, bins


def make_targets(root):
    """Targets of the project's Makefile and of Makefiles one level down (`make -C web test`)."""
    targets = set()
    for path in [root / "Makefile", *sorted(root.glob("*/Makefile"))]:
        if path.is_file():
            targets |= set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", path.read_text(encoding="utf-8"), re.M))
    return targets


def manual_only(text):
    """True for a GitHub workflow that only runs when someone starts it by hand (`on: workflow_dispatch`)."""
    m = re.search(r"^on:[ \t]*(.*)$((?:\n[ \t]+.*|\n[ \t]*)*)", text, re.M)
    if not m:
        return False
    triggers = set(re.findall(r"[a-z_]+", m.group(1).split("#")[0]))
    if not triggers:
        keys = re.findall(r"^([ \t]+)([a-z_]+):", m.group(2), re.M)
        if keys:
            indent = min(len(k[0]) for k in keys)
            triggers = {name for space, name in keys if len(space) == indent}
    return triggers == {"workflow_dispatch"}


def ci_text(root, top):
    """(CI files, text of the automatic ones, text of the automatic ones about this project).

    Manual-only workflows are not CI. In a monorepo, a CI file is about this project when it lives under
    the project's dir or mentions it; the rest still counts when the profile names their commands.
    """
    files = sorted({p for base in {root, top} for g in CI_GLOBS for p in base.glob(g)})
    texts = [(p, p.read_text(encoding="utf-8", errors="replace")) for p in files]
    auto = [(p, t) for p, t in texts if not manual_only(t)]
    sub = root.relative_to(top).as_posix() if root != top else None
    own = [t for p, t in auto if sub is None or p.is_relative_to(root) or mentions(t, sub)]
    return files, "\n".join(t for _, t in auto), "\n".join(own)


def path_exists(snippet, root, top, names):
    """A profile path exists relative to the project or the repo root; a bare file name anywhere in the repo."""
    rel = snippet.removeprefix("./")
    if "*" in rel:
        return any(base.glob(rel) for base in (root, top))
    if "/" not in rel.rstrip("/"):
        return (root / rel).exists() or rel in names
    return (root / rel).exists() or (top / rel).exists()


def bare(command):
    """A command without env assignments and runner prefixes: `CI=1 pnpm exec playwright test` -> `playwright test`."""
    command = re.sub(r"(\s--?[\w-]+)=", r"\1 ", re.sub(r"^(?:\w+=\S*\s+)+", "", command.strip()))
    return re.sub(r"^(?:npx|bunx|pnpm exec|pnpm dlx|yarn exec|bun x|yarn|pnpm)\s+", "", command)


def ci_jobs(cell, ci):
    """Job ids the profile's CI cell names in inline code (`frontend-e2e`) that still exist in the CI text."""
    return [job for job in INLINE_CODE.findall(cell)
            if re.fullmatch(r"[\w-]+", job) and re.search(rf"^[ \t]+{re.escape(job)}:[ \t]*$", ci, re.M)]


def ci_runs(command, ref, ci, scripts):
    """Does the CI text run this command, directly, through a wrapper script, or by inlining its body?"""
    if mentions(ci, command):
        return True
    if ref and ref[0] == "pm" and re.search(rf"\b(?:{'|'.join(PACKAGE_MANAGERS)})\b[^\n]*\s{re.escape(ref[1])}{WORD_END}", ci, re.M):
        return True
    if ref and ref[0] == "make" and re.search(rf"\bmake\b[^\n]*\s{re.escape(ref[1])}{WORD_END}", ci, re.M):
        return True
    lines = [re.sub(r"^\s*(?:-\s*)?(?:run:\s*)?", "", line).strip().strip("'\"") for line in ci.splitlines()]
    # CI inlines the script: `pnpm exec playwright test --config=x` for "test:e2e": "playwright test --config=x".
    if ref and ref[0] == "pm" and ref[1] in scripts:
        parts = [bare(p) for p in re.split(r"&&|;", scripts[ref[1]]) if bare(p)]
        parts = [p for p in parts if TEST_TOOL.match(p)] or parts  # `pnpm build && playwright test`: the test part
        if parts and all(any(part in bare(line) for line in lines) for part in parts):
            return True
    # A tool command whose words all appear, in order, on one CI line: `./gradlew test` in `./gradlew :api:test`.
    if not ref:
        words = command.split()
        pattern = r"[^\n]*".join(rf"(?<![\w-]){re.escape(w)}(?![\w-])" for w in words)
        if words and re.search(pattern, ci):
            return True
    # One level of indirection: CI runs `npm run test:all`, whose body runs this command or script.
    for line in lines:
        outer = script_ref(line)
        if outer and outer[0] == "pm" and outer[1] in scripts:
            body = scripts[outer[1]]
            pm_call = rf"\b(?:{'|'.join(PACKAGE_MANAGERS)})\b[^&;\n]*\s{re.escape(ref[1])}(?:\s|$|&|;)" if ref else None
            if mentions(body, command) or (pm_call and re.search(pm_call, body)):
                return True
    return False


def ci_test_commands(ci):
    """Test-looking commands in the CI text: package scripts with a test word, and test tools."""
    found = set()
    for line in ci.splitlines():
        line = re.sub(r"^\s*(?:-\s*)?(?:run:\s*|script:\s*)?", "", line).strip().strip("'\"")
        if not line or line.startswith(("#", "//")) or YAML_KEY.match(line):
            continue
        ref = script_ref(line)
        if ref and ref[0] == "pm" and TEST_WORD.search(ref[1]):
            found.add(("pm", ref[1], line))
            continue
        m = TEST_TOOL.match(bare(line))
        if m:
            found.add(("tool", m.group(1), line))
    return found


def bare_dep(name):
    """A dependency name as a known test package's bare name (`@playwright/test` -> `playwright`), or None."""
    name = name.strip().lower().replace("_", "-")
    if name in SCOPED_DEPS:
        return SCOPED_DEPS[name]
    if name.startswith("@"):
        return SCOPE_FAMILIES.get(name.split("/")[0])
    return name if name in TEST_DEPS else None


def test_deps(top, files):
    """Bare names of the known test packages the repo depends on: package.json, requirements*.txt, pyproject.toml."""
    found = set()
    for rel in files:
        name = rel.name
        if not (name in ("package.json", "pyproject.toml") or re.fullmatch(r"requirements.*\.txt", name)):
            continue
        try:
            text = (top / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if name == "package.json":
            try:
                data = json.loads(text)
            except ValueError:
                continue
            for key in ("dependencies", "devDependencies"):
                found.update(filter(None, map(bare_dep, data.get(key) or {})))
        elif re.fullmatch(r"requirements.*\.txt", name):
            for line in text.splitlines():
                line = line.split("#")[0].strip()
                if line and not line.startswith("-"):
                    found.add(bare_dep(re.split(r"[\[<>=~!; ]", line)[0]))
        elif name == "pyproject.toml":
            for array in re.findall(r"=\s*\[(.*?)\]", text, re.S):
                for item in re.findall(r"""["']([^"']+)["']""", array):
                    found.add(bare_dep(re.split(r"[\[<>=~!; ]", item)[0]))
    found.discard(None)
    return found


def spaced(text):
    return re.sub(r"[-\s]+", " ", text.lower())


def last_commit(top, path):
    """Unix time of the last commit that touched path, or None (no git, untracked, not committed yet)."""
    try:
        out = subprocess.run(["git", "-C", str(top), "log", "-1", "--format=%ct", "--", str(path)],
                             capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return int(out) if out.isdigit() else None


def has_local_changes(top, path):
    try:
        out = subprocess.run(["git", "-C", str(top), "status", "--porcelain", "--", str(path)],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return True
    return out.returncode != 0 or bool(out.stdout.strip())


def is_rules_file(top, rel):
    name = rel.name
    if name == "pyproject.toml":
        try:
            return "[tool.pytest" in (top / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
    return name in RULES_NAMES or name.startswith(RULES_PREFIXES) or rel.as_posix().startswith(".cursor/rules/")


def rules_changed(top, files, profile_path, generated_date):
    """Details of project-rules files whose last commit is later than the profile (its commit or its Generated day)."""
    limit = last_commit(top, profile_path)
    if generated_date:
        try:
            day_end = datetime.strptime(generated_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59).timestamp()
            limit = max(limit or 0, day_end)
        except ValueError:  # a malformed date counts as absent
            pass
    if limit is None:
        return []
    details = []
    for rel in sorted(files):
        if not is_rules_file(top, rel) or has_local_changes(top, top / rel):
            continue
        changed = last_commit(top, top / rel)
        if changed and changed > limit:
            when, since = (datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in (changed, limit))
            details.append(f"{rel.as_posix()} changed on {when}, after the profile ({since})")
    return details


def lost_tests(root, top, names):
    """Details of coverage-matrix rows whose test file no longer exists."""
    matrix = root / "docs" / "qa" / "coverage-matrix.md"
    if not matrix.is_file():
        return []
    details = []
    for row in table_rows(matrix.read_text(encoding="utf-8", errors="replace"))[1:]:
        if len(row) < 3 or "(removed " in row[2]:
            continue
        spans = INLINE_CODE.findall(row[2])
        path = (spans[0] if spans else row[2].split(" \u203a")[0]).strip().split("::")[0]
        if PATH_LIKE.match(path) and not path_exists(path, root, top, names):
            details.append(f"{row[0]} / {row[1]}: test file `{path}` does not exist")
    return details


def check(root, profile_text, profile_path=None):
    drifts = []
    commands_body = section(profile_text, "Commands")
    layers_body = section(profile_text, "Test layers")
    top = git_top(root)
    files = repo_files(top)
    scripts, bins = package_info(top, files)
    targets, names = make_targets(root), {f.name for f in files}
    ci_files, ci, own_ci = ci_text(root, top)

    snippets = INLINE_CODE.findall(commands_body + "\n" + layers_body)
    seen = set()
    for snippet in snippets:
        snippet = snippet.strip()
        if snippet in seen:
            continue
        seen.add(snippet)
        ref = script_ref(snippet)
        if ref and ref[0] == "pm" and scripts and ref[1] not in scripts and ref[1] not in bins:
            drifts.append(("missing-script", f"`{snippet}`: no package.json has a script \"{ref[1]}\""))
        elif ref and ref[0] == "make" and ref[1] not in targets:
            drifts.append(("missing-script", f"`{snippet}`: the Makefile has no target \"{ref[1]}\""))
        elif not ref and " " not in snippet and "://" not in snippet and not snippet.startswith("@") \
                and PATH_LIKE.match(snippet):
            if not path_exists(snippet, root, top, names):
                drifts.append(("missing-path", f"`{snippet}` does not exist"))

    rows = table_rows(layers_body)
    if ci_files and len(rows) > 1:
        header = [c.lower() for c in rows[0]]
        ci_col = next((i for i, c in enumerate(header) if "ci" in re.findall(r"[a-z]+", c)), None)
        cmd_col = next((i for i, c in enumerate(header) if "command" in c or "команд" in c), None)
        for row in rows[1:]:
            if ci_col is None or cmd_col is None or max(ci_col, cmd_col) >= len(row):
                break
            layer = re.sub(r"[`*]", "", row[0]) or "?"
            for command in INLINE_CODE.findall(row[cmd_col]):
                ref = script_ref(command)
                runs = ci_runs(command, ref, ci, scripts)
                claims_ci = not NOT_IN_CI.match(re.sub(r"[*_`]", "", row[ci_col]))
                if claims_ci and not runs and not ci_jobs(row[ci_col], ci):
                    drifts.append(("left-ci", f"layer \"{layer}\": the profile says CI runs `{command}`, no CI file does"))
                elif not claims_ci and runs:
                    drifts.append(("joined-ci", f"layer \"{layer}\": the profile says CI does not run `{command}`, a CI file does now"))

    snippets = INLINE_CODE.findall(profile_text)
    mentioned = "\n".join(snippets)
    # Bodies of the scripts the profile names: CI may inline them (`pnpm exec playwright test …`).
    bodies = [bare(part) for ref in filter(None, map(script_ref, snippets)) if ref[0] == "pm" and ref[1] in scripts
              for part in re.split(r"&&|;", scripts[ref[1]]) if TEST_TOOL.match(bare(part))]
    for kind, name, line in sorted(ci_test_commands(own_ci)):
        if any(body in bare(line) for body in bodies):  # inlines a named script: `pnpm vitest --project x --run`
            continue
        if kind == "pm" and re.search(rf"(?<![\w:-]){re.escape(name)}(?![\w:-])", mentioned):
            continue
        if kind == "tool" and name in mentioned:
            continue
        drifts.append(("new-ci-command", f"CI runs `{line}`, the profile does not mention it"))

    profile_words = spaced(profile_text)
    for dep in sorted(test_deps(top, files)):
        if not re.search(rf"(?<![a-z0-9]){re.escape(spaced(dep))}(?![a-z0-9])", profile_words):
            drifts.append(("new-test-dep", f"`{dep}` is a dependency, the profile does not mention it"))
    if profile_path is not None:
        generated = re.search(r"on (\d{4}-\d{2}-\d{2})", profile_text)
        drifts += [("rules-changed", d) for d in
                   rules_changed(top, files, profile_path, generated.group(1) if generated else None)]
    drifts += [("lost-test", d) for d in lost_tests(root, top, names)]
    return drifts, len(ci_files)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default="docs/qa/project-profile.md")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv[1:])
    root = Path(args.root).resolve()
    profile = Path(args.profile) if Path(args.profile).is_absolute() else root / args.profile
    if not profile.exists():
        print(f"NO PROFILE: {profile}", file=sys.stderr)
        return 2
    text = profile.read_text(encoding="utf-8")
    drifts, ci_files = check(root, text, profile_path=profile)
    generated = re.search(r"on (\d{4}-\d{2}-\d{2})", text)
    since = f" (profile from {generated.group(1)})" if generated else ""
    if not drifts:
        print(f"OK: profile matches the repo{since}; {ci_files} CI file(s) checked")
        return 0
    print(f"DRIFT: {len(drifts)} difference(s){since}")
    for kind, detail in drifts:
        print(f"- {kind}: {detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
