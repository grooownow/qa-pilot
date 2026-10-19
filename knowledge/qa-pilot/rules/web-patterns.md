# web-patterns

Сгенерировано из `web-patterns.json` скриптом `scripts/kb/render_rules.py` — правьте JSON, не этот файл.
Собственные правила qa-pilot: источник каждого правила указан в поле «источник».

## Жёсткие правила (10)

### QAP-WEB-001 · Сохранение или действие над сущностью, которую уже удалили

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.5 (404), §15.5.11 (410); qa-pilot TDK audit 2026-10 · авторитет: industry-practice

Для каждой сущности с правкой и удалением определено и проверено, что происходит, когда пользователь сохраняет форму, запускает действие или открывает редактор, а сущность уже удалена (в другой вкладке, другим пользователем, фоновым процессом). Сервер отвечает 404 или 410, а не 500 и не воскрешает запись; UI показывает понятное сообщение, закрывает редактор или предлагает сохранить ввод и обновляет список.

**Почему:** Мотивирующий промах колоквиума: сценарий «правка × удаление» не всплыл ни в одном прогоне, потому что агент сам выбирал места кода. Книга знает 404/500 на фронте (SRK-API-118) и 409 (SRK-API-025), но не связывает их с устаревшей сущностью.

**Как проверить:** Вопрос на сущность: «Что будет, если сохранить или запустить X, когда X уже удалён?». Найти PUT/PATCH/POST-действие и DELETE одной сущности. OK: бэкенд делает lookup и отвечает 404/410 (строка кода), фронт обрабатывает этот статус (строка кода), есть тест с моком 404 или backend-integration тест. BUG: findById без проверки даёт 500, upsert воскрешает запись, или UI показывает сырую ошибку/UUID, или редактор остаётся висеть. GAP: поведение верное по коду, но теста нет. N/A только с доказательством: у сущности нет удаления (grep по DELETE → 0).

### QAP-WEB-002 · Двойная отправка и параллельный запуск одного действия

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §9.2.2 (идемпотентные методы); IETF Internet-Draft draft-ietf-httpapi-idempotency-key-header, https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/; qa-pilot TDK audit 2026-10 · авторитет: industry-practice

Каждое создающее или запускающее действие (create, run, pay, send, import) защищено от повтора на двух уровнях: UI блокирует повторный клик на время запроса, а сервер не создаёт дубль и не запускает вторую копию процесса (уникальный ключ, Idempotency-Key, проверка «уже запущено»).

**Почему:** Блокировка кнопки не защищает от второй вкладки, ретрая сети и прямого вызова API. POST не идемпотентен по RFC 9110, поэтому защита на сервере обязательна. Уточняет SRK-FORM-026 и SRK-API-003: книга проверяет только двойной клик.

**Как проверить:** Вопрос на сущность: «Что будет, если действие X отправить дважды подряд или из двух вкладок?». OK: кнопка disabled по isPending (строка кода) И серверный guard (unique-индекс, idempotency key, статусная проверка в транзакции; строка кода). BUG: guard только в UI или его нет вовсе; повторный запуск долгой операции создаёт вторую копию. GAP: guard есть, но нет component-теста на блокировку или backend-integration теста на параллельный вызов.

### QAP-WEB-003 · Мутация без обработки ошибки

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: TanStack Query v5 docs, Guides: Mutations (onError; глобальные колбэки через MutationCache), https://tanstack.com/query/latest/docs/framework/react/guides/mutations; Nielsen Norman Group, 10 Usability Heuristics #1 и #9, https://www.nngroup.com/articles/ten-usability-heuristics/; qa-pilot TDK audit 2026-10 · авторитет: industry-practice

Каждая операция записи имеет путь обработки сбоя: локальный onError/catch или глобальный обработчик, который реально покрывает статусы, возвращаемые этим эндпоинтом. Сбой записи не проглатывается молча и не оставляет пользователя в уверенности, что данные сохранены.

**Почему:** Молчаливый сбой записи — потеря данных с точки зрения пользователя. Глобальная обвязка часто ловит только 401/500, а 400/409/422 проходят мимо. Ожидаемый результат при молчании спеки — инвариант QAP-WINV-002.

**Как проверить:** Вопрос на сущность: «Что увидит пользователь, если запись X вернёт 4xx/5xx или сеть оборвётся?». Перечислить мутации; для каждой найти onError/catch или глобальный MutationCache/interceptor и сверить, какие статусы он обрабатывает. OK: строка обработчика + статус эндпоинта входит в покрытые. BUG: `.then` без `.catch`, `mutate()` без onError при отсутствии глобального обработчика, catch с пустым телом или только console.log. GAP: обработчик есть, нет теста с замоканным сбоем.

### QAP-WEB-004 · Модальное окно закрывается раньше, чем завершится запрос

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: qa-pilot TDK audit 2026-10 (G2); TanStack Query v5 docs, https://tanstack.com/query/latest/docs/framework/react/overview (Mutations: mutate vs mutateAsync, onSuccess); Nielsen Norman Group, 10 Usability Heuristics #1 Visibility of system status, https://www.nngroup.com/articles/ten-usability-heuristics/ · авторитет: industry-practice

Диалог, который отправляет данные, закрывается только после успешного ответа. При ошибке он остаётся открытым, показывает причину и сохраняет введённое; на время запроса кнопки подтверждения заблокированы.

**Почему:** Найдено в аудите TDK (G2): закрытие вызывалось в том же обработчике, что и mutate(), поэтому при ошибке ввод терялся, а пользователь видел закрытую модалку как успех. Книжного аналога нет.

**Как проверить:** Вопрос на каждый диалог с записью: «Где вызывается закрытие относительно ответа?». OK: onClose/setOpen(false) только в onSuccess или после await с проверкой результата (строка кода). BUG: mutate() и закрытие подряд в одном обработчике; закрытие в onSettled; закрытие до await. GAP: код верный, но нет component-теста «ошибка → модалка открыта, ввод на месте».

### QAP-WEB-005 · Сбой фонового рефетча стирает уже показанные данные

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: TanStack Query v5 docs, https://tanstack.com/query/latest/docs/framework/react/overview; TanStack Query query-core types.ts (QueryObserverRefetchErrorResult: data сохраняется, isRefetchError), https://github.com/TanStack/query/blob/main/packages/query-core/src/types.ts; qa-pilot TDK audit 2026-10 (G4) · авторитет: industry-practice

Если данные уже загружены, а повторный запрос (поллинг, фокус окна, инвалидация) упал, экран продолжает показывать последние данные и рядом сообщает о сбое или пометке «устарело». Ошибка не заменяет весь контент.

**Почему:** В TanStack Query v5 при сбое рефетча status становится 'error', а data от прошлого успешного ответа сохраняется (isRefetchError=true). Код вида `if (isError) return <Error/>` перед проверкой data стирает историю. Найдено в аудите TDK (G4); книжного аналога нет.

**Как проверить:** Вопрос на каждое чтение с поллингом или долгим жизненным циклом: «Что видно, если рефетч упал после показа данных?». OK: ветка ошибки проверяет наличие data (или isLoadingError) и рендерит данные с баннером (строка кода). BUG: ранний return по isError/error без учёта data; setState([]) в catch поллинга. GAP: нет component-теста «успех → сбой рефетча → данные на месте».

### QAP-WEB-006 · Конфликт уникальности (409) не доведён до пользователя

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.10 (409 Conflict); qa-pilot TDK audit 2026-10 · авторитет: industry-practice

Для каждого поля с ограничением уникальности (имя, slug, email) конфликт обрабатывается во всех путях записи — создание, переименование, импорт, копирование. Сервер отвечает 409 (или 422 с указанием поля), UI показывает ошибку у поля и не теряет ввод.

**Почему:** Обычно 409 обработан в create и забыт в rename/duplicate. Родитель — QAP-INV-001 (инвариант во всех путях записи); книга: SRK-API-025.

**Как проверить:** Вопрос на сущность: «Где задаётся уникальность и все ли пути записи доводят конфликт до поля?». Найти ограничение (unique-индекс, validator) и перечислить пути записи. OK: каждый путь отдаёт 409/422 с полем, фронт мапит его на поле (строки кода). BUG: DuplicateKey превращается в 500; rename не проверяет; UI показывает общий тост и сбрасывает форму. GAP: тест есть только на create.

### QAP-WEB-007 · Права проверены только в UI

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: OWASP API Security Top 10 2023 (CC BY-SA 4.0), https://owasp.org/API-Security/editions/2023/en/0x11-t10/ API5:2023 Broken Function Level Authorization; OWASP Authorization Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html · авторитет: industry-practice

Каждое действие, которое UI скрывает или блокирует по роли или праву, защищено тем же правилом на сервере. Прямой вызов эндпоинта пользователем без права даёт 403 (или 404) и не меняет данные.

**Почему:** Скрытая кнопка не защищает API: это Broken Function Level Authorization (OWASP API5:2023). Книга проверяет 403 на уровне API (SRK-API-022), но не связывает его с UI-проверкой прав.

**Как проверить:** Вопрос на каждую UI-проверку прав: «Какой эндпоинт она прячет и где серверный guard?». OK: для эндпоинта есть @PreAuthorize/middleware/policy/RLS с тем же правом (строка кода) и тест, что пользователь без права получает 403. BUG: guard только в компоненте; сервер проверяет аутентификацию, но не роль. GAP: guard есть, теста на 403 нет.

### QAP-WEB-008 · Вложенный id не сверяется с родителем или владельцем

`must` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: OWASP API Security Top 10 2023 (CC BY-SA 4.0), https://owasp.org/API-Security/editions/2023/en/0x11-t10/ API1:2023 Broken Object Level Authorization; OWASP Insecure Direct Object Reference Prevention Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html · авторитет: industry-practice

Для вложенных ресурсов (/projects/{pid}/items/{id}) и любых запросов по id сервер выбирает запись с учётом родителя и владельца или тенанта. Подставленный чужой id даёт 404 (или 403) и не раскрывает и не меняет чужие данные.

**Почему:** Это Broken Object Level Authorization (OWASP API1:2023), самая частая API-уязвимость. Типичный код делает findById(id) и игнорирует parentId из пути. Уточняет SRK-API-128: проверять надо именно скоуп запроса, а не только роль.

**Как проверить:** Вопрос на каждый маршрут с id: «Запрос к БД скоупится по родителю и владельцу?». OK: запрос вида findByIdAndProjectId / where(owner: current_user) / RLS-политика (строка кода) и тест с чужим id → 404. BUG: findById(id) без parentId; parentId из пути не используется; проверка владельца только для GET, но не для PATCH/DELETE. GAP: скоуп есть, нет теста с чужим id.

### QAP-WEB-009 · Сессия истекает посреди действия

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: OWASP Session Management Cheat Sheet (CC BY-SA 4.0), https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html; IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.2 (401); W3C WCAG 2.2 SC 2.2.5 Re-authenticating (AAA), https://www.w3.org/WAI/WCAG22/Understanding/re-authenticating · авторитет: industry-practice

Определено и проверено, что происходит, когда токен или сессия истекают во время заполнения формы или в момент записи: либо прозрачное обновление токена и повтор запроса, либо повторный вход без потери введённого. Несколько одновременных 401 дают один refresh, а не гонку.

**Почему:** Книга описывает истечение токена (SRK-API-036, SRK-API-110) и отправку формы после истечения сессии (SRK-TD-061), но не требует сохранения ввода и не учитывает параллельные 401. Если теряется длинный ввод, серьёзность поднимается до P1.

**Как проверить:** Вопрос на сущность с формой: «Что будет, если на сохранении X придёт 401?». OK: interceptor обновляет токен и повторяет исходный запрос, очередь параллельных 401 (строка кода), или черновик сохраняется перед редиректом на вход. BUG: редирект на /login без сохранения ввода; бесконечный цикл refresh; мутация молча падает. GAP: нет e2e/@ui-contract теста с одноразовым 401 на мутации.

### QAP-WEB-010 · Маршруты и вкладки зависят от режима, флага или роли

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: OWASP API Security Top 10 2023 API5 Broken Function Level Authorization, https://owasp.org/API-Security/editions/2023/en/0x11-t10/; Pete Hodgson, Feature Toggles (aka Feature Flags), martinfowler.com, https://martinfowler.com/articles/feature-toggles.html; qa-pilot TDK audit 2026-10 · авторитет: industry-practice

Если видимость маршрута, вкладки или действия зависит от режима, feature flag, тарифа или роли, решение принимает одна функция, и она же используется для навигации, прямого URL и сервера. Прямой переход на скрытый маршрут ведёт себя предсказуемо (404, редирект или сообщение), а не показывает полу-рабочий экран.

**Почему:** Условия, размазанные по меню, роутеру и компонентам, расходятся: вкладка скрыта, но URL открывается, или флаг выключен в UI, а эндпоинт работает. При обходе прав серьёзность P2 и связь с QAP-WEB-007.

**Как проверить:** Вопрос на каждое условие видимости: «Где принимается решение, и что даёт прямой URL при выключенном условии?». OK: одна решающая функция или конфиг (строка кода), unit-тест на неё по всем режимам, guard маршрута использует её же. BUG: разные условия в меню и роутере; прямой URL открывает экран, эндпоинт которого отвечает 403/500. GAP: нет unit-теста решающей функции.

## Рекомендации (8)

### QAP-WEB-011 · Потерянное обновление при одновременной правке

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §13.1.1 (If-Match), §15.5.13 (412 Precondition Failed), §15.5.10 (409) · авторитет: industry-practice

Для сущностей, которые правят несколько человек, либо есть оптимистическая блокировка (version, ETag/If-Match → 412 или 409), сверяемая во всех путях записи, либо last-write-wins явно принят в спеке.

**Почему:** Тихая перезапись чужих правок — потеря данных, но встречается реже, чем удаление; поэтому подсветка, а не обязательная клетка. Связано с SRK-DB-024.

**Как проверить:** Вопрос: «Две вкладки правят X: что с правкой первой?». OK: @Version/etag сверяется в update (строка кода) или решение last-write-wins в спеке. BUG: версия есть в DTO, но не проверяется. Одна строка в «Highlighted».

### QAP-WEB-012 · Оптимистичное обновление без отката

`nice` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: TanStack Query v5 docs, Guides: Optimistic Updates, https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates · авторитет: industry-practice

Если UI меняет кэш до ответа сервера, при ошибке он восстанавливает прежнее состояние и затем синхронизируется с сервером.

**Почему:** Без отката UI показывает несохранённое как сохранённое (нарушение QAP-WINV-001).

**Как проверить:** Вопрос: «Что видно после ошибки оптимистичной мутации?». OK: onMutate сохраняет snapshot, onError его возвращает, onSettled инвалидирует; или оптимизм только через variables мутации / useOptimistic (кэш не меняется, откат автоматический). BUG: setQueryData в onMutate без отката в onError.

### QAP-WEB-013 · Успех показан до ответа или при сбое второго шага

`nice` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: qa-pilot TDK audit 2026-10; Nielsen Norman Group, 10 Usability Heuristics #1 Visibility of system status, https://www.nngroup.com/articles/ten-usability-heuristics/ · авторитет: industry-practice

Сообщение об успехе и переход дальше происходят только после успешного завершения всех шагов операции. Сбой второго шага многошагового действия (создать, затем привязать или загрузить) виден пользователю.

**Почему:** Обычная ошибка кода, сгенерированного агентами: toast.success до await или navigate сразу после mutate(). Ожидаемый результат — QAP-WINV-001.

**Как проверить:** Вопрос: «Где показывается успех относительно ответа?». OK: успех в onSuccess последнего шага. BUG: toast/navigate до await; второй вызов в onSuccess без собственной обработки ошибки.

### QAP-WEB-014 · Ошибка загрузки выглядит как пустой список

`nice` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: TanStack Query v5 docs, Guides: Queries (status 'error' отдельно от данных), https://tanstack.com/query/latest/docs/framework/react/guides/queries; Nielsen Norman Group, heuristic #1 Visibility of system status, https://www.nngroup.com/articles/ten-usability-heuristics/ · авторитет: industry-practice

Состояние ошибки чтения отличимо от пустого состояния: пользователь не видит «здесь пока ничего нет», когда данные просто не загрузились.

**Почему:** Пользователь, решивший, что данных нет, может создать дубль; тогда серьёзность растёт до P2.

**Как проверить:** OK: isError обрабатывается отдельно от data.length === 0. BUG: `data ?? []` при неиспользуемом isError; `catch { return [] }`.

### QAP-WEB-015 · После мутации связанные данные не обновились

`nice` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: TanStack Query v5 docs, Guides: Invalidations from Mutations, https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations · авторитет: industry-practice

После записи все экраны, показывающие затронутые данные (список, деталь, счётчики), обновляются без перезагрузки страницы.

**Почему:** Типовая причина «сохранилось только после F5».

**Как проверить:** OK: invalidateQueries/refetch/revalidatePath для всех затронутых ключей. BUG: мутация без инвалидации, или инвалидируется только деталь, а не список.

### QAP-WEB-016 · Прямой URL на несуществующую или чужую сущность

`nice` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.5 (404), §15.5.4 (403) · авторитет: industry-practice

Открытие по прямой ссылке удалённой, несуществующей или недоступной сущности даёт понятную страницу «не найдено», без бесконечного лоадера, сырого id и стектрейса.

**Почему:** Серверная часть (чужой id) — QAP-WEB-008; здесь только реакция UI.

**Как проверить:** OK: роут обрабатывает 404/403 отдельной страницей. BUG: вечный спиннер, пустой экран, сырой текст ошибки.

### QAP-WEB-017 · Несохранённые изменения теряются при уходе

`nice` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: MDN Web Docs, Window: beforeunload event, https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event · авторитет: vendor-guideline

При закрытии формы с изменениями (крестик, Cancel, клик по фону, смена маршрута, закрытие вкладки) пользователь предупреждён или черновик сохранён.

**Почему:** Подсветка: потеря ввода раздражает, но обычно не портит сохранённые данные.

**Как проверить:** OK: проверка isDirty перед закрытием и beforeunload/route-blocker. BUG: dirty-форма закрывается молча.

### QAP-WEB-018 · Действие над сущностью во время долгой операции

`should` · проверка: эвристика агента · для: requirements, test-plan, test-code, live-product · источник: qa-pilot TDK audit 2026-10; IETF RFC 9110 HTTP Semantics (2022), https://www.rfc-editor.org/rfc/rfc9110 §15.5.10 (409 Conflict: конфликт с текущим состоянием ресурса) · авторитет: industry-practice

Для сущностей со статусами выполнения (run, import, job) определено, что происходит с правкой, удалением и повторным запуском, пока операция идёт; поллинг останавливается на финальном статусе.

**Почему:** В аудите TDK фильтр «удаление во время запуска не тестируем» вырезал ровно этот класс. Полная модель состояний — SRK-TD-039/040.

**Как проверить:** Вопрос: «Можно ли удалить, править или перезапустить X, пока он выполняется?». OK: сервер проверяет статус (строка кода), UI блокирует действия. BUG: удаление во время run оставляет висячую задачу; поллинг не останавливается.
