# Собственные правила qa-pilot

Правила, которых нет в книге Суркова (`../surkov/`), но которые доказали ценность на реальных аудитах. Схема та же, что у свода книги (см. `../surkov/README.md`), с двумя отличиями:
- id имеет вид `QAP-<TOPIC>-NNN`;
- вместо `source.chunk_id` указывается `source.origin`: откуда взялось правило.

Правила конкретного проекта (`PRJ-…`) живут не здесь, а в `docs/qa/rule-overrides.json` самого проекта.

```bash
python3 scripts/kb/render_rules.py knowledge/qa-pilot   # валидация + рендер rules/*.md
```

<!-- stats -->
Всего записей: **8**

| Тема | Всего | rule | recommendation | tip | checklist | deterministic |
|---|---|---|---|---|---|---|
| [pilot](rules/pilot.md) | 8 | 8 | 0 | 0 | 0 | 1 |

По severity: must — 2, should — 6, nice — 0

По способу проверки: deterministic — 1, heuristic — 7, manual — 0
<!-- /stats -->
