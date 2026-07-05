# Quality Rules

Cross-cutting rules for every qa-pilot skill. Load this file at the start of any
phase that writes or changes code. These rules exist because AI-generated code
tends to fail in predictable ways: too much of it, too clever, confidently wrong.

## 1. Simplest solution first (complexity challenge)

Before writing any code, state (to yourself, in one or two sentences) the simplest
solution that could work. Then challenge every addition against it:

- Would a senior engineer call this over-engineered? Remove it.
- New abstraction (helper, wrapper, base class, config option) — is it used in
  ≥2 real places *today*? If not, inline it. YAGNI.
- New dependency — can the standard library / Playwright built-ins do it? Prefer them.
- If two designs both work, pick the one with fewer moving parts, even if the
  other is "more extensible".

After writing, re-read the diff and ask: "what can I delete without losing
behavior?" Delete it.

## 2. No junk output

- **Comments:** only for non-obvious constraints the code cannot express
  (why, not what). Never narrate ("// click the button"), never leave
  process notes ("// updated per review"), never restate the function name.
- **Dead code:** no commented-out blocks, no unused imports/variables/fixtures,
  no `console.log` leftovers.
- **Copy-paste:** if you are about to paste a third near-identical block,
  stop and extract — but only then (see rule 1).
- **Style:** match the surrounding file — its naming, its idioms, its comment
  density. The diff should look like the project's own author wrote it.

## 3. Evidence before claims

Never claim something works without having run it in this session:

- "Tests pass" requires a test run with visible output, in this session,
  after the last edit.
- A new test must be **proven able to fail**: break the assertion or the
  subject once, watch it fail for the right reason, restore it, watch it pass.
  A test that cannot fail is worse than no test.
- "Fixed" requires reproducing the failure first, then showing it gone.
- Watch for stale-green traps: cached typechecks, test runners reusing an old
  dev server, `.only` filters. When a result looks suspiciously easy, re-verify
  cold.

## 4. Mandatory self-review

Any change beyond a trivial one-liner goes through the review loop
(`review-loop.md`) before it is presented as done. No exceptions for
"small" changes — small changes are where sloppy patterns slip in.

## 5. Ask, don't guess

When product intent, credentials, environment URLs, or tracker access are
missing: stop and ask, listing exactly what you need and why. A wrong guess
costs more tokens than a question. Batch questions — ask everything you can
foresee in one message, not one at a time. If the user cannot answer
(e.g. no access yet), record the gap in the output document and mark dependent
work as blocked rather than improvising.

## 6. Project rules win

The target repo's own CLAUDE.md / AGENTS.md / docs / lint config override
anything in qa-pilot on conflict. qa-pilot supplies defaults, not law.
When you detect a conflict, follow the project and note the conflict in your
output document.

## Done checklist

Before declaring any task complete:

- [ ] Simplest-solution check passed; nothing deletable remains in the diff
- [ ] No junk comments / dead code / debug leftovers
- [ ] Project's own gates run and green (tests, typecheck, lint — whatever the
      profile lists), with output shown
- [ ] New tests proven able to fail
- [ ] Review loop completed (or explicitly waived as trivial one-liner)
- [ ] Output document updated (report / plan / session log)
