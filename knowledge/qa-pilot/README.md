# Собственные правила qa-pilot

Правила, которых нет в книге «Качество решает всё» (`../catalog/`), но которые доказали ценность на реальных аудитах. Схема та же, что у свода книги (см. `../catalog/README.md`), с двумя отличиями:
- id имеет вид `QAP-<TOPIC>-NNN`;
- вместо `source.chunk_id` указывается `source.origin`: откуда взялось правило.

Дополнительно:
- `authority` обязателен по смыслу: каждое собственное правило указывает, на чём держится (см. `../catalog/README.md`);
- записи `QAP-WEB-…` (веб-паттерны) несут объект `pattern`: `{tier: must-check | highlight, triggers: [...], level: unit | component | backend-integration | e2e, book_refs: [...]}`. Паттерны и инварианты (`QAP-WINV-…`) не попадают в пакеты правил: агенты получают их из `references/web-patterns.md` (генерируется `scripts/kb/render_web_patterns.py`);
- `drafts/` — черновики новых доменов до проверки; `rules_pack.py` и `render_rules.py` их не читают.

Правила конкретного проекта (`PRJ-…`) живут не здесь, а в `docs/qa/rule-overrides.json` самого проекта.

```bash
python3 scripts/kb/render_rules.py knowledge/qa-pilot   # валидация + рендер rules/*.md
```

<!-- stats -->
Всего записей: **176**

| Тема | Всего | rule | recommendation | tip | checklist | deterministic |
|---|---|---|---|---|---|---|
| [ai-systems](rules/ai-systems.md) | 15 | 14 | 1 | 0 | 0 | 0 |
| [api-http](rules/api-http.md) | 23 | 20 | 2 | 0 | 1 | 13 |
| [auth](rules/auth.md) | 14 | 13 | 0 | 0 | 1 | 3 |
| [pilot](rules/pilot.md) | 10 | 10 | 0 | 0 | 0 | 1 |
| [security](rules/security.md) | 38 | 37 | 0 | 0 | 1 | 6 |
| [test-code](rules/test-code.md) | 30 | 30 | 0 | 0 | 0 | 10 |
| [test-strategy](rules/test-strategy.md) | 22 | 17 | 3 | 1 | 1 | 0 |
| [web-invariants](rules/web-invariants.md) | 6 | 6 | 0 | 0 | 0 | 0 |
| [web-patterns](rules/web-patterns.md) | 18 | 10 | 8 | 0 | 0 | 0 |

По severity: must — 70, should — 95, nice — 11

По способу проверки: deterministic — 33, heuristic — 141, manual — 2
<!-- /stats -->
