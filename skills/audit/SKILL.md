---
name: audit
description: "The big-picture qa-pilot command: `/qa-pilot:audit [nothing | feature/spec/ticket | \"tests\"]`. With nothing, it audits the whole project. It rates how mature the test framework is, confirms the critical flows, audits each flow for must-check web failure patterns, and writes one roadmap. With a feature, spec or ticket, it audits the requirements against the code and tests and lists missing test cases (Must / Should / Highlight), bugs and product questions. With \"tests\", \"flaky\" or \"test code\", it audits the test suite itself for false greens, flakiness and duplication. Use for \"аудит\", \"общая картина\", \"проверь требования\", \"каких тестов не хватает во флоу\", \"что с тестами в целом\", \"почему тесты флакают\". Requires docs/qa/project-profile.md (else it runs qa-pilot:onboard first)."
---

# Audit

The one command for stepping back and looking at the whole thing. **You** pick the audit from what the user wrote after the command. The audits are hidden skills: invoke the one you pick with the Skill tool and follow it.

| Audit | Skill | When |
|---|---|---|
| **Project** | `qa-pilot:project-audit` | Nothing after the command, or "проект", "общая картина", "после большой фичи", "новый проект" |
| **Feature / requirements** | `qa-pilot:spec-audit` | A feature or flow name, a spec path, a ticket, "требования", "AC", "каких тестов не хватает во флоу X" |
| **Test code** | `qa-pilot:test-code-audit` | "тесты", "флаки", "test code", "suite", "почему тесты падают", "рефакторинг тестов" |

`docs/qa/project-profile.md` must exist. If it doesn't, say so in one line and run `qa-pilot:onboard` first.

**Is the profile still true?** Run, from the project root (`SKILL_DIR` is this skill's base directory, shown when it loads):

```bash
SKILL_DIR=<absolute base directory of this skill>   # shown when the skill loads
python3 "$SKILL_DIR/../onboard/scripts/profile_drift.py"
```

It compares the profile's commands, test paths and CI claims with `package.json`, the Makefile and the CI files, in well under a second.
- **Exit 0:** say nothing and go on.
- **Exit 1:** show its lines as they are, then ask once: "Профиль разошёлся с репо: (1) обновить только эти строки через `qa-pilot:onboard` (refresh) — рекомендую, (2) продолжить как есть". Do not block. If the user goes on, use the repo's real commands for the drifted items, not the profile's, and say so.
- **Any other exit** (the script could not run or crashed): say so in one line and go on. The check never blocks the run.

## Deciding

1. **Explicit words win.** Before starting, say the choice and its cost in one line. Example: "Аудит требований флоу «Workflows» — около 250–450k токенов, начинаю".
2. **No words: start with the project audit.** It states its own cost estimate, and you pick the flows before anything expensive runs.
3. **Ask once,** when the words fit two audits. Example: "проверь тесты флоу оплаты" can mean the requirements coverage of the flow or the quality of its test code. Use one question with the options and your recommendation first.
4. **The user doesn't know which audit they need.** Start with the project audit: its roadmap points at the next audit worth running.

The audits are read-only for product code. They write reports under `docs/qa/` and propose actions. For implementing the action lists, point the user to `/qa-pilot:test` with the list (it writes tests from a plan).
