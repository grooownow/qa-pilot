# web-invariants

Сгенерировано из `web-invariants.json` скриптом `scripts/kb/render_rules.py` — правьте JSON, не этот файл.
Собственные правила qa-pilot: источник каждого правила указан в поле «источник».

## Жёсткие правила (6)

### QAP-WINV-001 · Нет сообщения об успехе после сбоя

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #1 Visibility of system status; qa-pilot TDK audit 2026-10 · авторитет: industry-practice · сверка со стандартом: aligned

Если операция не завершилась успешно, интерфейс не показывает признаков успеха: тоста «Сохранено», закрытия формы как при успехе, перехода на следующий шаг, обновлённого значения без отката.

**Почему:** Пользователь, увидевший успех, не повторит действие, и данные потеряются. Используется как ожидаемый результат, когда спека молчит; нарушение — BUG без вопроса продукту.

**Как проверить:** На спеке/тест-плане: у каждого сценария сбоя записи ожидаемый результат не допускает признаков успеха. На коде и продукте: при замоканном 4xx/5xx нет тоста успеха, форма/модалка не закрыта (см. QAP-WEB-004, -012, -013). Нарушение — BUG.

### QAP-WINV-002 · У каждой записи есть видимая реакция на сбой

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #9 Help users recognize, diagnose, and recover from errors; W3C WCAG 2.2 SC 3.3.1 Error Identification (A), https://www.w3.org/WAI/WCAG22/Understanding/error-identification; GOV.UK Design System, Error message (OGL v3), https://design-system.service.gov.uk/components/error-message/ · авторитет: industry-practice · сверка со стандартом: aligned

Любая операция записи при ошибке или обрыве сети даёт пользователю видимое и понятное сообщение: что не получилось и что делать. Сообщение связано с полем, если ошибка относится к полю, и доступно вспомогательным технологиям.

**Почему:** Молчаливый сбой — главный источник «сохранил, а ничего нет». WCAG 3.3.1 требует текстового описания обнаруженной ошибки ввода.

**Как проверить:** OK: для каждой мутации есть путь ошибки, ведущий к видимому тексту (QAP-WEB-003). BUG: сбой без сообщения, только console.error или только цвет. Сообщение конкретное и человеческое по GOV.UK, а не «Произошла ошибка».

### QAP-WINV-003 · Пользователю не показываются сырые id, стектрейсы и внутренние ошибки

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: OWASP Error Handling Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html; MITRE CWE-209 Generation of Error Message Containing Sensitive Information, https://cwe.mitre.org/data/definitions/209.html; GOV.UK Design System, Pages for problems with the service (OGL v3), https://design-system.service.gov.uk/patterns/problem-with-the-service-pages/ · авторитет: industry-practice · сверка со стандартом: aligned

Тексты ошибок и экраны не содержат стектрейсов, SQL, имён классов и исключений, внутренних кодов и сырых тел ответов сервера; вместо имени объекта не показывается его UUID. Детали уходят в логи, пользователь видит понятное сообщение.

**Почему:** Раскрытие внутренностей помогает атакующему и ничего не даёт пользователю. Развивает QAP-PRIV-001 (внутренние идентификаторы в публичных эндпоинтах) на уровень UI.

**Как проверить:** На продукте: вызвать 404/409/500 и проверить текст ошибки. BUG: в нём есть stack trace, Exception, SQL, «undefined», сырой JSON, или UUID стоит на месте имени объекта. UUID в адресной строке нарушением не считается. На коде: grep отображения error.message/response.data без маппинга. Нарушение — BUG.

### QAP-WINV-004 · Загруженные данные переживают сбой фонового обновления

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #1 Visibility of system status; TanStack Query v5 docs, https://tanstack.com/query/latest/docs/framework/react/overview; qa-pilot TDK audit 2026-10 (G4) · авторитет: industry-practice · сверка со стандартом: aligned

Если данные уже показаны, сбой повторной загрузки не стирает их: экран продолжает показывать последнее известное состояние и сообщает, что обновление не удалось или данные могут быть устаревшими.

**Почему:** Пользователь теряет контекст (историю запусков, список) из-за временного сбоя сети. Ожидаемый результат для QAP-WEB-005.

**Как проверить:** OK: после успешной загрузки и упавшего рефетча данные на месте, рядом баннер или пометка. BUG: экран заменяется ошибкой или пустым состоянием.

### QAP-WINV-005 · Разрушающее действие называет, что уничтожает, и требует подтверждения

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: W3C WCAG 2.2 SC 3.3.4 Error Prevention (Legal, Financial, Data) (AA), https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data; Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #5 Error prevention · авторитет: industry-practice · сверка со стандартом: aligned

Удаление, сброс, отмена запуска и другие необратимые действия называют конкретный объект и последствия (что ещё удалится) и требуют явного подтверждения либо дают отмену после выполнения. Кнопка подтверждения названа по действию.

**Почему:** WCAG 3.3.4 требует для удаления пользовательских данных обратимости, проверки или подтверждения. Название объекта защищает от удаления не того.

**Как проверить:** OK: диалог содержит имя объекта и последствия, кнопка «Удалить проект», а не «ОК»; или есть undo. BUG: удаление в один клик без отмены; диалог «Вы уверены?» без имени объекта.

### QAP-WINV-006 · Повтор предлагается, только когда он может помочь

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §9.2.2 (идемпотентные методы), §10.2.3 (Retry-After), §15.6.4 (503); GOV.UK Design System, Pages for problems with the service (OGL v3), https://design-system.service.gov.uk/patterns/problem-with-the-service-pages/ · авторитет: industry-practice · сверка со стандартом: aligned

Кнопка «Повторить» или совет «попробуйте ещё раз» показываются для временных сбоев (сеть, 5xx, 429, 503). Для постоянных ошибок (400, 403, 404, 409, 422) пользователю объясняют, что изменить, а не предлагают бесполезный повтор. Автоповтор неидемпотентной записи не создаёт дублей.

**Почему:** Бесполезный повтор раздражает и маскирует настоящую причину; автоповтор POST без idempotency key создаёт дубли (QAP-WEB-002).

**Как проверить:** OK: развилка по статусу или типу ошибки (строка кода): retry только для временных. BUG: «Повторить» на 403/404/409; retry-политика мутаций без идемпотентности.

<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
