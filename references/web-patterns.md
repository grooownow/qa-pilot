# Web patterns and invariants

Generated from `knowledge/qa-pilot/rules/web-patterns.json` and `web-invariants.json` by `scripts/kb/render_web_patterns.py`. Edit the JSON, not this file.

Used by `spec-audit` (entity cards), `task-qa` (touched entities), `project-audit` and `plan-tests`. Must-check patterns are asked of **every entity with a lifecycle**; an empty cell means the run is not finished. Highlight-only patterns get one line when seen, never a card row.

## Entity card

One card per entity. Verdicts: OK · BUG · GAP · N/A (with evidence) · DECISION · SUPPRESSED (owner filter). Evidence: file:line, or the search command with its match count (untruncated).

| Pattern | Question | Verdict | Evidence |
|---|---|---|---|
| QAP-WEB-001 | Сохранение или действие над сущностью, которую уже удалили | | |
| QAP-WEB-002 | Двойная отправка и параллельный запуск одного действия | | |
| QAP-WEB-003 | Мутация без обработки ошибки | | |
| QAP-WEB-004 | Модальное окно закрывается раньше, чем завершится запрос | | |
| QAP-WEB-005 | Сбой фонового рефетча стирает уже показанные данные | | |
| QAP-WEB-006 | Конфликт уникальности (409) не доведён до пользователя | | |
| QAP-WEB-007 | Права проверены только в UI | | |
| QAP-WEB-008 | Вложенный id не сверяется с родителем или владельцем | | |
| QAP-WEB-009 | Сессия истекает посреди действия | | |
| QAP-WEB-010 | Маршруты и вкладки зависят от режима, флага или роли | | |

## Must-check patterns

### QAP-WEB-001 · Сохранение или действие над сущностью, которую уже удалили

Catalog severity `must` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: backend-integration · authority: industry-practice

Для каждой сущности с правкой и удалением определено и проверено, что происходит, когда пользователь сохраняет форму, запускает действие или открывает редактор, а сущность уже удалена (в другой вкладке, другим пользователем, фоновым процессом). Сервер отвечает 404 или 410, а не 500 и не воскрешает запись; UI показывает понятное сообщение, закрывает редактор или предлагает сохранить ввод и обновляет список.

**Check per entity:** Вопрос на сущность: «Что будет, если сохранить или запустить X, когда X уже удалён?». Найти PUT/PATCH/POST-действие и DELETE одной сущности. OK: бэкенд делает lookup и отвечает 404/410 (строка кода), фронт обрабатывает этот статус (строка кода), есть тест с моком 404 или backend-integration тест. BUG: findById без проверки даёт 500, upsert воскрешает запись, или UI показывает сырую ошибку/UUID, или редактор остаётся висеть. GAP: поведение верное по коду, но теста нет. N/A только с доказательством: у сущности нет удаления (grep по DELETE → 0).

**Triggers (where to look):** `rg -n "useMutation\(|axios\.(put|patch|delete)\(|method: *['\"](PUT|PATCH|DELETE)" src`, `rg -n "mutationFn: .*\$\{.*[iI]d\}" src`, `Spring: rg -n "@(Put|Patch|Delete)Mapping\(.*\{id\}|findById\(.*\)\.get\(\)"`, `Express: rg -n "router\.(put|patch|delete)\(['\"].*:id"`, `Django/Rails: rg -n "get_object_or_404|\.objects\.get\(|find\(params\[:id\]\)"`

**Why:** Мотивирующий промах колоквиума: сценарий «правка × удаление» не всплыл ни в одном прогоне, потому что агент сам выбирал места кода. Книга знает 404/500 на фронте (QAC-API-118) и 409 (QAC-API-025), но не связывает их с устаревшей сущностью.

**Book rules:** QAC-API-118, QAC-API-025

_Source: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.5 (404), §15.5.11 (410); qa-pilot TDK audit 2026-10_

### QAP-WEB-002 · Двойная отправка и параллельный запуск одного действия

Catalog severity `must` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: backend-integration · authority: industry-practice

Каждое создающее или запускающее действие (create, run, pay, send, import) защищено от повтора на двух уровнях: UI блокирует повторный клик на время запроса, а сервер не создаёт дубль и не запускает вторую копию процесса (уникальный ключ, Idempotency-Key, проверка «уже запущено»).

**Check per entity:** Вопрос на сущность: «Что будет, если действие X отправить дважды подряд или из двух вкладок?». OK: кнопка disabled по isPending (строка кода) И серверный guard (unique-индекс, idempotency key, статусная проверка в транзакции; строка кода). BUG: guard только в UI или его нет вовсе; повторный запуск долгой операции создаёт вторую копию. GAP: guard есть, но нет component-теста на блокировку или backend-integration теста на параллельный вызов.

**Triggers (where to look):** `rg -n "onClick=\{.*(mutate|submit|handle(Run|Create|Save))" src  # затем проверить disabled={isPending}`, `rg -n "isPending|isLoading|disabled=" src  # сверить с местами вызова mutate: кнопка без блокировки — триггер`, `rg -n "Idempotency-Key|idempotency" (front+back)`, `Spring: rg -n "@PostMapping\(.*(run|start|execute|pay)"`, `Express/Django/Rails: rg -n "post\(['\"].*/(run|start|execute)|def (run|start|execute)"`

**Why:** Блокировка кнопки не защищает от второй вкладки, ретрая сети и прямого вызова API. POST не идемпотентен по RFC 9110, поэтому защита на сервере обязательна. Уточняет QAC-FORM-026 и QAC-API-003: книга проверяет только двойной клик.

**Book rules:** QAC-FORM-026, QAC-API-003, QAC-PERF-014, QAC-UX-031, QAC-DB-024

_Source: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §9.2.2 (идемпотентные методы); IETF Internet-Draft draft-ietf-httpapi-idempotency-key-header, https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/; qa-pilot TDK audit 2026-10_

### QAP-WEB-003 · Мутация без обработки ошибки

Catalog severity `must` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: component · authority: industry-practice

Каждая операция записи имеет путь обработки сбоя: локальный onError/catch или глобальный обработчик, который реально покрывает статусы, возвращаемые этим эндпоинтом. Сбой записи не проглатывается молча и не оставляет пользователя в уверенности, что данные сохранены.

**Check per entity:** Вопрос на сущность: «Что увидит пользователь, если запись X вернёт 4xx/5xx или сеть оборвётся?». Перечислить мутации; для каждой найти onError/catch или глобальный MutationCache/interceptor и сверить, какие статусы он обрабатывает. OK: строка обработчика + статус эндпоинта входит в покрытые. BUG: `.then` без `.catch`, `mutate()` без onError при отсутствии глобального обработчика, catch с пустым телом или только console.log. GAP: обработчик есть, нет теста с замоканным сбоем.

**Triggers (where to look):** `rg -n "useMutation\(" src -A15  # в каждом окне искать onError; нет — мутация без локальной обработки`, `rg -n "new MutationCache\(|axios\.interceptors\.response" src  # глобальная обвязка`, `rg -n "\.then\(" src -A3  # кандидаты: проверить, есть ли .catch или try/await в цепочке`, `rg -n "catch \([a-z]*\) \{\s*\}|catch \{\s*\}|catch\(.*\) \{\s*console\." src`

**Why:** Молчаливый сбой записи — потеря данных с точки зрения пользователя. Глобальная обвязка часто ловит только 401/500, а 400/409/422 проходят мимо. Ожидаемый результат при молчании спеки — инвариант QAP-WINV-002.

**Book rules:** QAC-API-118, QAC-A11Y-060, QAC-MOB-016

_Source: TanStack Query v5 docs, Guides: Mutations (onError; глобальные колбэки через MutationCache), https://tanstack.com/query/latest/docs/framework/react/guides/mutations; Nielsen Norman Group, 10 Usability Heuristics #1 и #9, https://www.nngroup.com/articles/ten-usability-heuristics/; qa-pilot TDK audit 2026-10_

### QAP-WEB-004 · Модальное окно закрывается раньше, чем завершится запрос

Catalog severity `should` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: component · authority: industry-practice

Диалог, который отправляет данные, закрывается только после успешного ответа. При ошибке он остаётся открытым, показывает причину и сохраняет введённое; на время запроса кнопки подтверждения заблокированы.

**Check per entity:** Вопрос на каждый диалог с записью: «Где вызывается закрытие относительно ответа?». OK: onClose/setOpen(false) только в onSuccess или после await с проверкой результата (строка кода). BUG: mutate() и закрытие подряд в одном обработчике; закрытие в onSettled; закрытие до await. GAP: код верный, но нет component-теста «ошибка → модалка открыта, ввод на месте».

**Triggers (where to look):** `rg -n "mutate\(.*\)[;,]?\s*$" src -A3 | rg "(onClose|setOpen\(false\)|close\(\)|onOpenChange\(false\))"`, `rg -n "onSettled:.*(close|setOpen)" src`, `rg -n "<(Dialog|Modal|Sheet|Drawer)" src -l  # список диалогов для перебора`

**Why:** Найдено в аудите TDK (G2): закрытие вызывалось в том же обработчике, что и mutate(), поэтому при ошибке ввод терялся, а пользователь видел закрытую модалку как успех. Книжного аналога нет.

**Book rules:** QAC-FORM-056, QAC-API-118

_Source: qa-pilot TDK audit 2026-10 (G2); TanStack Query v5 docs, https://tanstack.com/query/latest/docs/framework/react/overview (Mutations: mutate vs mutateAsync, onSuccess); Nielsen Norman Group, 10 Usability Heuristics #1 Visibility of system status, https://www.nngroup.com/articles/ten-usability-heuristics/_

### QAP-WEB-005 · Сбой фонового рефетча стирает уже показанные данные

Catalog severity `should` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: component · authority: industry-practice

Если данные уже загружены, а повторный запрос (поллинг, фокус окна, инвалидация) упал, экран продолжает показывать последние данные и рядом сообщает о сбое или пометке «устарело». Ошибка не заменяет весь контент.

**Check per entity:** Вопрос на каждое чтение с поллингом или долгим жизненным циклом: «Что видно, если рефетч упал после показа данных?». OK: ветка ошибки проверяет наличие data (или isLoadingError) и рендерит данные с баннером (строка кода). BUG: ранний return по isError/error без учёта data; setState([]) в catch поллинга. GAP: нет component-теста «успех → сбой рефетча → данные на месте».

**Triggers (where to look):** `rg -n "refetchInterval|refetchOnWindowFocus|setInterval\(.*fetch" src`, `rg -n "if \((isError|error|query\.isError)\)\s*(return|\{)" src  # затем проверить, учтена ли data`, `rg -n "isLoadingError|isRefetchError" src  # признаки правильной развилки`

**Why:** В TanStack Query v5 при сбое рефетча status становится 'error', а data от прошлого успешного ответа сохраняется (isRefetchError=true). Код вида `if (isError) return <Error/>` перед проверкой data стирает историю. Найдено в аудите TDK (G4); книжного аналога нет.

**Book rules:** QAC-API-118, QAC-API-123

_Source: TanStack Query v5 docs, https://tanstack.com/query/latest/docs/framework/react/overview; TanStack Query query-core types.ts (QueryObserverRefetchErrorResult: data сохраняется, isRefetchError), https://github.com/TanStack/query/blob/main/packages/query-core/src/types.ts; qa-pilot TDK audit 2026-10 (G4)_

### QAP-WEB-006 · Конфликт уникальности (409) не доведён до пользователя

Catalog severity `should` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: backend-integration · authority: industry-practice

Для каждого поля с ограничением уникальности (имя, slug, email) конфликт обрабатывается во всех путях записи — создание, переименование, импорт, копирование. Сервер отвечает 409 (или 422 с указанием поля), UI показывает ошибку у поля и не теряет ввод.

**Check per entity:** Вопрос на сущность: «Где задаётся уникальность и все ли пути записи доводят конфликт до поля?». Найти ограничение (unique-индекс, validator) и перечислить пути записи. OK: каждый путь отдаёт 409/422 с полем, фронт мапит его на поле (строки кода). BUG: DuplicateKey превращается в 500; rename не проверяет; UI показывает общий тост и сбрасывает форму. GAP: тест есть только на create.

**Triggers (where to look):** `Spring: rg -n "unique *= *true|@UniqueConstraint|DataIntegrityViolationException|DuplicateKeyException"`, `Django/Rails: rg -n "unique=True|UniqueConstraint|validates .*uniqueness|IntegrityError"`, `Express/Prisma: rg -n "@unique|P2002|ER_DUP_ENTRY|23505"`, `Front: rg -n "409|status === 409|Conflict" src`

**Why:** Обычно 409 обработан в create и забыт в rename/duplicate. Родитель — QAP-INV-001 (инвариант во всех путях записи); книга: QAC-API-025.

**Book rules:** QAC-API-025, QAC-DB-024

_Source: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.10 (409 Conflict); qa-pilot TDK audit 2026-10_

### QAP-WEB-007 · Права проверены только в UI

Catalog severity `must` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: backend-integration · authority: industry-practice

Каждое действие, которое UI скрывает или блокирует по роли или праву, защищено тем же правилом на сервере. Прямой вызов эндпоинта пользователем без права даёт 403 (или 404) и не меняет данные.

**Check per entity:** Вопрос на каждую UI-проверку прав: «Какой эндпоинт она прячет и где серверный guard?». OK: для эндпоинта есть @PreAuthorize/middleware/policy/RLS с тем же правом (строка кода) и тест, что пользователь без права получает 403. BUG: guard только в компоненте; сервер проверяет аутентификацию, но не роль. GAP: guard есть, теста на 403 нет.

**Triggers (where to look):** `rg -n "can\(|hasRole|hasPermission|isAdmin|permissions\.includes|role ===" src`, `rg -n "disabled=\{!.*(can|perm|role)" src`, `Spring: rg -n "@PreAuthorize|@Secured|@RolesAllowed"`, `Express: rg -n "(authorize|requireRole|checkPermission)\("`, `Django/Rails: rg -n "permission_classes|@permission_required|authorize! |Pundit|CanCan"`

**Why:** Скрытая кнопка не защищает API: это Broken Function Level Authorization (OWASP API5:2023). Книга проверяет 403 на уровне API (QAC-API-022), но не связывает его с UI-проверкой прав.

**Book rules:** QAC-API-022, QAC-API-089

_Source: OWASP API Security Top 10 2023 (CC BY-SA 4.0), https://owasp.org/API-Security/editions/2023/en/0x11-t10/ API5:2023 Broken Function Level Authorization; OWASP Authorization Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html_

### QAP-WEB-008 · Вложенный id не сверяется с родителем или владельцем

Catalog severity `must` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: backend-integration · authority: industry-practice

Для вложенных ресурсов (/projects/{pid}/items/{id}) и любых запросов по id сервер выбирает запись с учётом родителя и владельца или тенанта. Подставленный чужой id даёт 404 (или 403) и не раскрывает и не меняет чужие данные.

**Check per entity:** Вопрос на каждый маршрут с id: «Запрос к БД скоупится по родителю и владельцу?». OK: запрос вида findByIdAndProjectId / where(owner: current_user) / RLS-политика (строка кода) и тест с чужим id → 404. BUG: findById(id) без parentId; parentId из пути не используется; проверка владельца только для GET, но не для PATCH/DELETE. GAP: скоуп есть, нет теста с чужим id.

**Triggers (where to look):** `rg -n "Mapping\(.*\{\w+Id\}.*\{id\}|router\.\w+\(['\"].*/:\w+Id/.*/:id"`, `rg -n "findById\(|findByPk\(|\.objects\.get\(pk=|\.find\(params\[:id\]\)"  # затем проверить скоуп`, `Supabase: rg -n "\.from\(['\"]\w+['\"]\)\.(update|delete|select)" src + проверить RLS-политики в миграциях`

**Why:** Это Broken Object Level Authorization (OWASP API1:2023), самая частая API-уязвимость. Типичный код делает findById(id) и игнорирует parentId из пути. Уточняет QAC-API-128: проверять надо именно скоуп запроса, а не только роль.

**Book rules:** QAC-API-128, QAC-DB-029

_Source: OWASP API Security Top 10 2023 (CC BY-SA 4.0), https://owasp.org/API-Security/editions/2023/en/0x11-t10/ API1:2023 Broken Object Level Authorization; OWASP Insecure Direct Object Reference Prevention Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html_

### QAP-WEB-009 · Сессия истекает посреди действия

Catalog severity `should` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: e2e · authority: industry-practice

Определено и проверено, что происходит, когда токен или сессия истекают во время заполнения формы или в момент записи: либо прозрачное обновление токена и повтор запроса, либо повторный вход без потери введённого. Несколько одновременных 401 дают один refresh, а не гонку.

**Check per entity:** Вопрос на сущность с формой: «Что будет, если на сохранении X придёт 401?». OK: interceptor обновляет токен и повторяет исходный запрос, очередь параллельных 401 (строка кода), или черновик сохраняется перед редиректом на вход. BUG: редирект на /login без сохранения ввода; бесконечный цикл refresh; мутация молча падает. GAP: нет e2e/@ui-contract теста с одноразовым 401 на мутации.

**Triggers (where to look):** `rg -n "status === 401|401\b|refreshToken|refresh_token|getSession|onAuthStateChange" src`, `rg -n "interceptors\.response\.use" src -A20`, `rg -n "navigate\(['\"]/login|window\.location.*login" src`

**Why:** Книга описывает истечение токена (QAC-API-036, QAC-API-110) и отправку формы после истечения сессии (QAC-TD-061), но не требует сохранения ввода и не учитывает параллельные 401. Если теряется длинный ввод, серьёзность поднимается до P1.

**Book rules:** QAC-API-036, QAC-API-110, QAC-TD-061, QAC-A11Y-066

_Source: OWASP Session Management Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html; IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.2 (401); W3C WCAG 2.2 SC 2.2.5 Re-authenticating (AAA), https://www.w3.org/WAI/WCAG22/Understanding/re-authenticating_

### QAP-WEB-010 · Маршруты и вкладки зависят от режима, флага или роли

Catalog severity `should` (not a bucket: the cell's P1/P2 follows `severity-calibration.md`) · test level: unit · authority: industry-practice

Если видимость маршрута, вкладки или действия зависит от режима, feature flag, тарифа или роли, решение принимает одна функция, и она же используется для навигации, прямого URL и сервера. Прямой переход на скрытый маршрут ведёт себя предсказуемо (404, редирект или сообщение), а не показывает полу-рабочий экран.

**Check per entity:** Вопрос на каждое условие видимости: «Где принимается решение, и что даёт прямой URL при выключенном условии?». OK: одна решающая функция или конфиг (строка кода), unit-тест на неё по всем режимам, guard маршрута использует её же. BUG: разные условия в меню и роутере; прямой URL открывает экран, эндпоинт которого отвечает 403/500. GAP: нет unit-теста решающей функции.

**Triggers (where to look):** `rg -n "isEnabled\(|featureFlag|useFlag|useFeature|flags\.|mode ===|plan ===" src`, `rg -n "tabs\.filter\(|routes\.filter\(|\{.*&& <(Route|Tab)" src`, `Back: rg -n "FeatureFlag|@ConditionalOn|feature_enabled|Flipper"`

**Why:** Условия, размазанные по меню, роутеру и компонентам, расходятся: вкладка скрыта, но URL открывается, или флаг выключен в UI, а эндпоинт работает. При обходе прав серьёзность P2 и связь с QAP-WEB-007.

**Book rules:** QAC-INST-024, QAC-API-089

_Source: OWASP API Security Top 10 2023 API5 Broken Function Level Authorization, https://owasp.org/API-Security/editions/2023/en/0x11-t10/; Pete Hodgson, Feature Toggles (aka Feature Flags), martinfowler.com, https://martinfowler.com/articles/feature-toggles.html; qa-pilot TDK audit 2026-10_

## Highlight-only patterns

Mention as one line in *Highlighted, not drilled* when you see one.

- **QAP-WEB-011** Потерянное обновление при одновременной правке — Вопрос: «Две вкладки правят X: что с правкой первой?». OK: @Version/etag сверяется в update (строка кода) или решение last-write-wins в спеке. BUG: версия есть в DTO, но не проверяется. Одна строка в «Highlighted». _(triggers: `rg -n "@Version|lock_version|ETag|If-Match|optimistic.?lock|(where|WHERE).*(version|updated_at) *="`)_
- **QAP-WEB-012** Оптимистичное обновление без отката — Вопрос: «Что видно после ошибки оптимистичной мутации?». OK: onMutate сохраняет snapshot, onError его возвращает, onSettled инвалидирует; или оптимизм только через variables мутации / useOptimistic (кэш не меняется, откат автоматический). BUG: setQueryData в onMutate без отката в onError. _(triggers: `rg -n "onMutate|setQueryData|useOptimistic" src`)_
- **QAP-WEB-013** Успех показан до ответа или при сбое второго шага — Вопрос: «Где показывается успех относительно ответа?». OK: успех в onSuccess последнего шага. BUG: toast/navigate до await; второй вызов в onSuccess без собственной обработки ошибки. _(triggers: `rg -n "toast\.success|notify.*success" src -B5  # проверить порядок относительно await`, `rg -n "mutate\(.*\);\s*(navigate|router\.push)" src`)_
- **QAP-WEB-014** Ошибка загрузки выглядит как пустой список — OK: isError обрабатывается отдельно от data.length === 0. BUG: `data ?? []` при неиспользуемом isError; `catch { return [] }`. _(triggers: `rg -n "data \?\? \[\]|\?\.length === 0|catch.*return \[\]" src`)_
- **QAP-WEB-015** После мутации связанные данные не обновились — OK: invalidateQueries/refetch/revalidatePath для всех затронутых ключей. BUG: мутация без инвалидации, или инвалидируется только деталь, а не список. _(triggers: `rg -n "useMutation\(" src -A20  # в каждом окне искать invalidateQueries|refetch|setQueryData|revalidatePath|router.refresh`)_
- **QAP-WEB-016** Прямой URL на несуществующую или чужую сущность — OK: роут обрабатывает 404/403 отдельной страницей. BUG: вечный спиннер, пустой экран, сырой текст ошибки. _(triggers: `rg -n "useParams\(|path: ['\"].*:\w*[iI]d" src`, `rg --files | rg "\[\w*[iI]d\]"  # Next.js/Remix: динамические маршруты по имени файла`)_
- **QAP-WEB-017** Несохранённые изменения теряются при уходе — OK: проверка isDirty перед закрытием и beforeunload/route-blocker. BUG: dirty-форма закрывается молча. _(triggers: `rg -n "isDirty|formState\.dirty|beforeunload|useBlocker|unstable_usePrompt" src`)_
- **QAP-WEB-018** Действие над сущностью во время долгой операции — Вопрос: «Можно ли удалить, править или перезапустить X, пока он выполняется?». OK: сервер проверяет статус (строка кода), UI блокирует действия. BUG: удаление во время run оставляет висячую задачу; поллинг не останавливается. _(triggers: `rg -n "status === ['\"](running|pending|in_progress)|enum .*Status|RUNNING|IN_PROGRESS"`)_

## Web invariants (expected-result sources)

When a spec is silent, these are valid sources for a scenario's expected result (cite the id). A violation on a user-visible path is a BUG, not a product question.

- **QAP-WINV-001 · Нет сообщения об успехе после сбоя.** Если операция не завершилась успешно, интерфейс не показывает признаков успеха: тоста «Сохранено», закрытия формы как при успехе, перехода на следующий шаг, обновлённого значения без отката. _(source: Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #1 Visibility of system status; qa-pilot TDK audit 2026-10)_
- **QAP-WINV-002 · У каждой записи есть видимая реакция на сбой.** Любая операция записи при ошибке или обрыве сети даёт пользователю видимое и понятное сообщение: что не получилось и что делать. Сообщение связано с полем, если ошибка относится к полю, и доступно вспомогательным технологиям. _(source: Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #9 Help users recognize, diagnose, and recover from errors; W3C WCAG 2.2 SC 3.3.1 Error Identification (A), https://www.w3.org/WAI/WCAG22/Understanding/error-identification; GOV.UK Design System, Error message (OGL v3), https://design-system.service.gov.uk/components/error-message/)_
- **QAP-WINV-003 · Пользователю не показываются сырые id, стектрейсы и внутренние ошибки.** Тексты ошибок и экраны не содержат стектрейсов, SQL, имён классов и исключений, внутренних кодов и сырых тел ответов сервера; вместо имени объекта не показывается его UUID. Детали уходят в логи, пользователь видит понятное сообщение. _(source: OWASP Error Handling Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html; MITRE CWE-209 Generation of Error Message Containing Sensitive Information, https://cwe.mitre.org/data/definitions/209.html; GOV.UK Design System, Pages for problems with the service (OGL v3), https://design-system.service.gov.uk/patterns/problem-with-the-service-pages/)_
- **QAP-WINV-004 · Загруженные данные переживают сбой фонового обновления.** Если данные уже показаны, сбой повторной загрузки не стирает их: экран продолжает показывать последнее известное состояние и сообщает, что обновление не удалось или данные могут быть устаревшими. _(source: Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #1 Visibility of system status; TanStack Query v5 docs, https://tanstack.com/query/latest/docs/framework/react/overview; qa-pilot TDK audit 2026-10 (G4))_
- **QAP-WINV-005 · Разрушающее действие называет, что уничтожает, и требует подтверждения.** Удаление, сброс, отмена запуска и другие необратимые действия называют конкретный объект и последствия (что ещё удалится) и требуют явного подтверждения либо дают отмену после выполнения. Кнопка подтверждения названа по действию. _(source: W3C WCAG 2.2 SC 3.3.4 Error Prevention (Legal, Financial, Data) (AA), https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data; Nielsen Norman Group, 10 Usability Heuristics for User Interface Design, https://www.nngroup.com/articles/ten-usability-heuristics/ #5 Error prevention)_
- **QAP-WINV-006 · Повтор предлагается, только когда он может помочь.** Кнопка «Повторить» или совет «попробуйте ещё раз» показываются для временных сбоев (сеть, 5xx, 429, 503). Для постоянных ошибок (400, 403, 404, 409, 422) пользователю объясняют, что изменить, а не предлагают бесполезный повтор. Автоповтор неидемпотентной записи не создаёт дублей. _(source: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §9.2.2 (идемпотентные методы), §10.2.3 (Retry-After), §15.6.4 (503); GOV.UK Design System, Pages for problems with the service (OGL v3), https://design-system.service.gov.uk/patterns/problem-with-the-service-pages/)_

<!-- qa-pilot · © 2026 Ekaterina Pustovaia (Ludvik4) · https://ludvik4.dev · PolyForm-Noncommercial-1.0.0 · ref qp-l4-7f3a9c -->
