# База знаний: «Качество решает всё» (Р. Сурков)

Справочник и свод правил на основе книги Романа Суркова «Качество решает всё: полное руководство по тестированию ПО» (819 стр.). В книге описаны ручное тестирование и инженерия качества: теория, тест-дизайн, API, БД, нефункциональное тестирование, WCAG, мобильные приложения, гайдлайны Apple и Google, UX и ИИ в QA. Автоматизации тестов в книге нет.

Краткое содержание для человека лежит в [summary.md](summary.md).

## Что здесь лежит

| Файл | Что это | В git |
|---|---|---|
| `summary.md` | О чём книга, чем полезна qa-pilot, топ правил | да |
| `toc.json`, `toc.md` | Оглавление: раздел → глава → подраздел, `chunk_id`, страница, объём. Без текста книги | да |
| `topics.json` → `topics.md` | Темы: тема → файл правил → куски книги. Глубина извлечения | да |
| `rules/<topic>.json` | **Свод**: правила, рекомендации, советы, пункты чек-листов. Источник истины | да |
| `rules/<topic>.md` | То же для чтения, генерируется из JSON | да |
| `raw/` | Полный текст книги: постранично, кусками (`chunks/<id>.md`) и `chunks.jsonl` | **нет** (gitignore) |

Полный текст книги не публикуется, потому что книга защищена авторским правом, а репозиторий публичный. Все формулировки в `rules/` — пересказ. Чтобы получить `raw/` локально, нужен PDF книги:

```bash
python3 scripts/kb/build_chunks.py <путь к PDF> knowledge/surkov   # нужен poppler: brew install poppler
python3 scripts/kb/render_rules.py knowledge/surkov                # валидация свода + рендер .md + статистика ниже
python3 scripts/kb/check_overlap.py knowledge/surkov 10              # нет дословных кусков книги (≥10 слов подряд)
python3 -m unittest discover -s scripts/kb                         # тесты скриптов
```

Сборка детерминирована: повторный запуск даёт побайтно тот же результат. Отчёт о сборке пишется в `raw/build-report.txt`: сопоставление заголовков оглавления и покрытие текста.

## Как агенту пользоваться

1. Найти тему в [topics.md](topics.md), оттуда взять файл правил и список `chunk_id`.
2. Прочитать `rules/<topic>.md` целиком или отфильтровать `rules/<topic>.json` по полям:
   - `applies_to` — к какому артефакту применимо: `requirements`, `test-plan`, `test-code`, `live-product`, `test-cases`;
   - `check.mode` — `deterministic` (решает скрипт или инструмент), `heuristic` (суждение агента), `manual` (нужен человек);
   - `severity` — `must`, `should`, `nice`;
   - `kind` — `rule`, `recommendation`, `tip`, `checklist`.
3. Если нужна деталь из первоисточника, открыть `raw/chunks/<chunk_id>.md`, когда он есть. Если `raw/` нет, сослаться на страницу книги из `source.printed_pages`.

Пример: правила для тест-плана, которые проверяются без суждения агента:

```bash
jq '.[] | select((.applies_to|index("test-plan")) and .check.mode=="deterministic") | {id,title}' knowledge/surkov/rules/*.json
```

## Схема записи

```json
{
  "id": "SRK-FORM-001",
  "kind": "rule | recommendation | tip | checklist",
  "severity": "must | should | nice",
  "title": "Короткая формулировка",
  "statement": "Что требуется — пересказ",
  "rationale": "Почему (опц.)",
  "applies_to": ["requirements", "test-plan", "test-code", "live-product", "test-cases"],
  "check": { "mode": "deterministic | heuristic | manual", "how": "Как проверить при аудите" },
  "modern_note": "Что изменилось с тех пор (опц.)",
  "source": { "chunk_id": "s1-c07-01", "printed_pages": [43] },
  "tags": ["forms"],
  "verification": "ok | fixed | doubtful"
}
```

Поле `verification` проставляет проход сверки с первоисточником:
- `ok` — подтверждено;
- `fixed` — исправлено при сверке;
- `doubtful` — требует внимания человека.

## Статистика свода

<!-- stats -->
Всего записей: **1137**

| Тема | Всего | rule | recommendation | tip | checklist | deterministic |
|---|---|---|---|---|---|---|
| [accessibility](rules/accessibility.md) | 133 | 96 | 7 | 13 | 17 | 24 |
| [ai-in-qa](rules/ai-in-qa.md) | 38 | 5 | 13 | 6 | 14 | 6 |
| [api](rules/api.md) | 124 | 11 | 53 | 32 | 28 | 68 |
| [databases](rules/databases.md) | 32 | 4 | 11 | 17 | 0 | 2 |
| [forms](rules/forms.md) | 55 | 9 | 7 | 2 | 37 | 29 |
| [games](rules/games.md) | 17 | 3 | 0 | 1 | 13 | 0 |
| [gui](rules/gui.md) | 28 | 9 | 7 | 7 | 5 | 12 |
| [install-config](rules/install-config.md) | 57 | 5 | 8 | 11 | 33 | 0 |
| [localization](rules/localization.md) | 36 | 16 | 2 | 6 | 12 | 1 |
| [mobile](rules/mobile.md) | 76 | 3 | 4 | 18 | 51 | 3 |
| [mobile-hig](rules/mobile-hig.md) | 112 | 34 | 72 | 6 | 0 | 9 |
| [mobile-material](rules/mobile-material.md) | 92 | 52 | 40 | 0 | 0 | 20 |
| [performance](rules/performance.md) | 30 | 6 | 6 | 7 | 11 | 5 |
| [principles](rules/principles.md) | 12 | 7 | 4 | 1 | 0 | 0 |
| [process](rules/process.md) | 15 | 1 | 5 | 7 | 2 | 2 |
| [requirements](rules/requirements.md) | 30 | 4 | 10 | 8 | 8 | 5 |
| [test-artifacts](rules/test-artifacts.md) | 69 | 38 | 21 | 4 | 6 | 26 |
| [test-design](rules/test-design.md) | 56 | 13 | 10 | 4 | 29 | 2 |
| [test-strategy](rules/test-strategy.md) | 52 | 14 | 13 | 6 | 19 | 4 |
| [usability](rules/usability.md) | 35 | 14 | 9 | 2 | 10 | 11 |
| [ux-laws-dark-patterns](rules/ux-laws-dark-patterns.md) | 38 | 15 | 18 | 4 | 1 | 5 |

По severity: must — 272, should — 655, nice — 210

По способу проверки: deterministic — 234, heuristic — 702, manual — 201
<!-- /stats -->

## Ограничения

- Скриншоты из книги не извлекаются. Если смысл фрагмента держится на картинке, правило построено только по тексту (поле `images` в метаданных куска показывает, сколько картинок было).
- Номера страниц в оглавлении самой книги отстают от реальных на 5–6 страниц. Используйте `source.printed_pages` (номер в колонтитуле страницы) или `pdf_page` из `toc.json`.
- Из разделов «Об авторе», «Доступность в Беларуси» и «Карьерные рекомендации» правила не извлекались (см. `topics.md`, тема `index-only`).
