# onepost — План разработки MVP

Источник архитектурных решений: [ARCHITECTURE.md](./ARCHITECTURE.md).

## Принципы

- **Telegram сначала.** Бот добавляется в канал за 5 минут, нет апрува, есть видимый результат — это даёт быстрый work loop и проверяет каркас.
- **Каждый этап — самостоятельно ценная веха.** В конце этапа должно быть что-то, что можно показать или прогнать вручную, а не только «код написан».
- **Внешние зависимости (LinkedIn approval) — как можно позже.** До этого момента строим столько, сколько можно проверить локально.
- **Реальные API — только за фейками в тестах.** Юнит/интеграционные тесты не дёргают сеть.

## Оценки

- **S** = до полудня, **M** = 0.5–1 день, **L** = 1–2 дня, **XL** = 3+ дня. Один день — это 4–6 часов фокус-времени.
- Итог по MVP: ~7–10 рабочих дней без учёта ожидания апрува LinkedIn.

## Внешние блокеры (сделать параллельно, как можно раньше)

| # | Действие | Когда подаём | Ожидание |
|---|---|---|---|
| EXT-1 | Создать Telegram-бота через `@BotFather`, получить токен, добавить ботом-админом в свой канал | До этапа 1 | Минуты |
| EXT-2 | Создать приложение в LinkedIn Developer Portal, запросить продукт «Share on LinkedIn» (даёт `w_member_social`) | До этапа 2 (запросить сразу после этапа 0 на всякий случай) | Часы — дни |
| EXT-3 | Если потребуется доступ к Posts API v2 / image upload — проверить, что доступно с базовым продуктом; иначе запросить дополнительный | По мере прохождения этапа 3 | Часы — дни |

---

## Этап 0 — Скелет проекта и каркас (M)

**Цель:** Пустой, но настоящий проект: FastAPI поднимается, БД создаётся миграциями, тесты прогоняются, git инициализирован.

### Задачи
1. `git init` в `/Users/fedorov_s/Documents/VSCode/mvps/onepost/`.
2. `.gitignore`: `.env`, `*.db`, `*.db-journal`, `data/`, `__pycache__/`, `.venv/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.DS_Store`.
3. `pyproject.toml`: зависимости (FastAPI, uvicorn, jinja2, SQLAlchemy 2.x, alembic, httpx, pydantic-settings, cryptography, APScheduler, python-multipart, python-json-logger), dev-deps (pytest, pytest-asyncio, ruff, mypy).
4. `app/main.py`: создать FastAPI app, `GET /healthz` возвращает `{"ok": true}`.
5. `app/config.py`: pydantic-settings с полями `database_url`, `telegram_bot_token`, `telegram_channel_id`, `linkedin_client_id`, `linkedin_client_secret`, `linkedin_redirect_uri`, `encryption_key`, `app_base_url`.
6. `.env.example` со всеми ключами и пустыми значениями.
7. Сгенерировать Fernet-ключ, сохранить в локальном `.env` (`ONEPOST_ENCRYPTION_KEY=...`). В команду в README.
8. `app/storage/db.py`: SQLAlchemy engine и `async_session`.
9. Alembic init, первая пустая миграция.
10. `tests/conftest.py` + один тест `test_healthz` через `httpx.AsyncClient`.
11. Скрипты в README: запуск, миграции, тесты.

### DoD
- `uvicorn app.main:app --reload` поднимается, `GET /healthz` → `{"ok": true}`.
- `alembic upgrade head` создаёт `data/onepost.db` без ошибок.
- `pytest` зелёный (1 тест).
- `git log` содержит начальный коммит.

### Можно делать локально без внешних зависимостей? ✅ полностью.

### Риски
- Несовместимость зависимостей под Python 3.11/3.12 на macOS. Mitigation: использовать `uv` или `pip-tools`, зафиксировать версии в `pyproject.toml`.

---

## Этап 1 — Telegram publisher и минимальный compose-flow (L) ✅

Сделано на HTMX (см. ARCHITECTURE.md, до пивота). В Stage 1.5 UI перевели на React.

**Цель:** Можно открыть форму, набрать текст (опционально с картинкой), нажать «Опубликовать» — пост появляется в Telegram-канале. Статус виден в UI.

### Задачи
1. Модели SQLAlchemy: `Post`, `PlatformPost`, `Media`. Создать миграцию.
2. `MediaStorage` (local): сохранение файла в `data/media/<uuid>.<ext>`, чтение по id.
3. `app/publishers/base.py`: `Publisher` protocol, `PublishRequest`, `PublishResult`, `PublishError`.
4. `TelegramPublisher`:
   - `platform_id = "telegram"`.
   - `publish(req)`: если `image_path is None` → `sendMessage`; иначе → `sendPhoto` с `caption`. Используем httpx, тайм-ауты, парсинг ответа.
   - Маппинг ошибок: HTTP 5xx, 429 с `retry_after` → transient; 4xx → permanent.
   - `healthcheck`: `getMe`.
5. `PublicationService.publish(post_id)`:
   - Загружает `Post` + `PlatformPost`-ы.
   - Для каждого PP помечает `status='publishing'`, вызывает publisher, обновляет `external_id`/`last_error`, ставит финальный статус.
   - Пока только один publisher (telegram), но архитектура уже та самая.
6. Web routes:
   - `GET /` → compose-форма (Jinja2): текстовое поле, file-input для изображения, кнопка «Опубликовать сейчас».
   - `POST /posts`: multipart, создаёт `Post` + `PlatformPost(platform=telegram)`, вызывает publication service (in-process, `BackgroundTask`).
   - `GET /posts` → список последних постов с их статусами на платформах.
   - `GET /posts/{id}/status` → HTMX-partial со статусами PP.
7. UI: HTMX polling `/posts/{id}/status` каждые 2 секунды, пока есть `publishing`/`queued`.
8. Тесты:
   - `TelegramPublisher` против `httpx.MockTransport`: успешный sendMessage, успешный sendPhoto, 429 → transient, 400 → permanent.
   - `PublicationService` с фейковым Publisher: успех / transient / permanent сценарии.
   - End-to-end через `TestClient`: POST формы + проверка состояния в БД (без реальной сети).

### DoD
- Реальный пост уходит в Telegram-канал из локального UI (текст и текст+фото).
- Статус в UI меняется с `publishing` на `succeeded` без перезагрузки страницы.
- При искусственном падении (например, неверный chat_id) UI показывает `failed` и текст ошибки.
- Все тесты зелёные.

### Можно делать локально без внешних зависимостей? Почти — нужен токен Telegram-бота (EXT-1, минуты).

### Риски
- Telegram ограничивает длину caption до 1024 символов, а текста — до 4096. Mitigation: если есть и текст, и фото, и длина > 1024 → отправлять `sendPhoto` без caption + следом `sendMessage` с текстом (либо обрезать, но обрезать — плохо). Решение: для MVP — отправлять `sendPhoto` с урезанной caption и `sendMessage` с полным текстом, или ограничивать caption.
- Сетевая нестабильность при тестировании. Mitigation: ретраи будут в этапе 6.

---

## Этап 1.5 — Пивот фронта на React SPA (L)

**Цель:** Заменить HTMX UI на React + Vite + TS + Tailwind + shadcn/ui. Бэкенд начинает отдавать только JSON. UI закладывается под полный MVP-функционал (composer + preview + overrides + schedule + connections + history), даже если часть бэка ещё mock.

### Задачи
1. **Бэкенд → JSON:**
   - Удалить `app/web/templates/` + Jinja-роуты + статику.
   - `app/api/routes.py` под префиксом `/api`:
     - `POST /api/posts` (multipart: `text`, `image?`, `scheduled_at?`, `platforms`, `text_override_*?`).
     - `GET /api/posts`, `GET /api/posts/{id}`.
     - `POST /api/posts/{id}/retry/{platform}`.
     - `DELETE /api/posts/{id}` (отмена scheduled).
     - `GET /api/connections` — Telegram (через `getMe`), LinkedIn (заглушка `connected=false`, реализация в Stage 2).
     - `GET /api/media/{id}` — отдача загруженных изображений (для preview).
   - `app/api/schemas.py` — Pydantic-схемы.
   - `CORSMiddleware` для `http://localhost:5173` в dev.
   - В прод-режиме монтируется `frontend/dist` как статика + SPA fallback на `index.html`.
2. **Тесты бэка:** переписать `tests/test_routes.py` под JSON, добавить тесты на retry endpoint + connections.
3. **Frontend scaffold:**
   - `frontend/` через `npm create vite@latest -- --template react-ts`.
   - `vite.config.ts` с `server.proxy = { '/api': 'http://127.0.0.1:8000' }`.
   - Tailwind init + shadcn/ui init. Темы light/dark через `next-themes` или ручной toggle.
4. **Frontend код:**
   - `src/lib/types.ts` — `Post`, `PlatformPost`, `Platform`, `PlatformPostStatus`, `Connection`.
   - `src/lib/mockApi.ts` — моки с искусственной задержкой и dev-контролем (success/error toggle, не random).
   - `src/lib/api.ts` — реальные `fetch /api/*`.
   - Компоненты: `App`, `PostComposer`, `PlatformToggle`, `PostPreview` (LinkedIn + Telegram), `PublishStatus`, `OverridesAccordion`, `ScheduleSheet`, `ConnectionsCard`, `History`, `ThemeToggle`.
5. **Wire-up:** переключить импорт в `App.tsx` с `mockApi` на `api`.

### DoD
- `uv run uvicorn app.main:app` + `npm --prefix frontend run dev`: React UI на `:5173` шлёт `/api/posts`, тестовый пост уходит в Telegram-канал.
- Backend-тесты зелёные.
- `npm --prefix frontend run build` собирается без ошибок.
- `npm --prefix frontend run lint`/`tsc --noEmit` без ошибок.

### Можно делать локально без внешних зависимостей? ✅ полностью.

### Риски
- Тонкости shadcn CLI (path aliases `@/*` в `tsconfig.json` + `vite.config.ts`). Mitigation: следовать официальной инструкции «shadcn/Vite» шаг в шаг.
- Дрейф контракта между mockApi и реальным API. Mitigation: оба используют один и тот же `types.ts`; функциональная сигнатура совпадает.
- LinkedIn `Connect` пока не работает (Stage 2). UI показывает «Coming in Stage 2» в `ConnectionsCard`.

---

## Этап 2 — LinkedIn OAuth + posting только текста (L)

**Цель:** Можно подключить свой LinkedIn-аккаунт через UI, и при публикации поста (без картинки) он появляется в личном профиле.

### Предусловие: EXT-2 одобрен (или хотя бы клиент создан с базовым продуктом).

### Задачи
1. Миграция: таблица `oauth_tokens`.
2. `app/auth/token_store.py`: Fernet-шифрование, get/save, авто-refresh при `expires_at < now + 7 days`.
3. `app/auth/linkedin_oauth.py`:
   - `authorize_url()` — формирует URL `/oauth/v2/authorization` с `scope=w_member_social`, `state` (CSRF).
   - `exchange_code(code)` — `POST /oauth/v2/accessToken`, парсит access/refresh/expires_in.
   - `refresh(refresh_token)` — аналогично.
4. API routes (JSON):
   - `GET /api/connections` теперь возвращает `linkedin: { connected, member_name? }`.
   - `GET /api/oauth/linkedin/start` → `{ authorize_url }`.
   - `GET /api/oauth/linkedin/callback` → обмен code, сохранение токенов, **302 на frontend** (`/?connected=linkedin`).
   - В `ConnectionsCard` (Stage 1.5) кнопка «Connect LinkedIn» делает `window.location.assign(authorize_url)`.
5. `LinkedInPublisher`:
   - `platform_id = "linkedin"`.
   - `publish(req)` для текста: `POST /rest/posts` с `author=urn:li:person:{member_urn}`, заголовки `LinkedIn-Version`, `X-Restli-Protocol-Version: 2.0.0`. Парсит `external_id` из заголовка `x-restli-id`/тела.
   - Узнаём свой member URN один раз через `/v2/userinfo` (OIDC `sub` поле) — сохраняем в `oauth_tokens.account_identifier`.
   - Маппинг ошибок: 401 → попытка refresh + 1 ретрай; 429 → transient с retry_after; 5xx → transient; остальное 4xx → permanent.
   - `healthcheck`: `/v2/userinfo`.
6. Регистрация publisher-а; при создании `Post` создаются ОБА `PlatformPost`-а (telegram + linkedin).
7. Тесты:
   - OAuth: фейковые ответы LinkedIn для exchange/refresh, проверка шифрования.
   - `LinkedInPublisher` против `httpx.MockTransport`: успех текста, 401 → refresh → успех, 429 → transient.
8. README: как создать LinkedIn-приложение, какие redirect URL заводить, как пройти первый OAuth.

### DoD
- В карточке Connections (UI Stage 1.5) можно нажать «Connect LinkedIn», пройти OAuth, увидеть «Connected as <имя>».
- При публикации текстового поста через основную форму он реально появляется в моём LinkedIn-профиле И в Telegram-канале.
- Статусы обеих платформ независимо отображаются в UI.
- Перезапуск приложения через сутки не требует повторного OAuth (токен жив 60 дней, refresh работает).

### Можно делать локально? Логику OAuth и обмен токенов можно покрыть тестами без сети. Реальный flow требует одобренного приложения LinkedIn.

### Риски
- **LinkedIn approval может затянуться.** Mitigation: запросить EXT-2 в этапе 0; пока ждём — можно делать всё, кроме фактических вызовов LinkedIn API, против фейков.
- LinkedIn Posts API меняется (`/rest/posts` vs старый `/v2/ugcPosts`). Mitigation: фиксируем `LinkedIn-Version` (формат `YYYYMM`), сверяемся с актуальной документацией на момент разработки.
- `r_liteprofile` / `r_emailaddress` устарели; нужно использовать OIDC `profile`/`email` + `openid` для получения member URN. Mitigation: использовать `/v2/userinfo` после OAuth — это OIDC endpoint, возвращает `sub` (URN-совместимый).
- 401 после refresh может оказаться концом refresh_token. Mitigation: помечаем в UI «требуется реавторизация», не пытаемся бесконечно ретраить permanent-ошибки.

---

## Этап 3 — LinkedIn изображения (M)

**Цель:** Кросс-публикация поста с одной картинкой работает в обе платформы.

### Задачи
1. `LinkedInPublisher.publish` для случая `image_path is not None`:
   - Шаг 1: `POST /rest/images?action=initializeUpload` → получаем `uploadUrl` и `image` URN.
   - Шаг 2: `PUT uploadUrl` с бинарником.
   - Шаг 3: `POST /rest/posts` с `content.media.id = image_urn`.
2. Хэндлинг: тайм-аут на upload (30с), валидация mime/размера.
3. Тесты: 3-шаговый flow против `httpx.MockTransport`; кейсы падения на каждом шаге.
4. Ручная проверка: реальный пост с реальной картинкой в LinkedIn-профиль.

### DoD
- Пост с картинкой публикуется в обе платформы из одной формы.
- В случае падения на upload-шаге — `permanently_failed` для LinkedIn PP, Telegram PP не страдает.

### Можно делать локально? Логика — да; реальная проверка — нет.

### Риски
- Размер картинки и форматы (LinkedIn принимает JPEG/PNG; ограничения на размер). Mitigation: валидация на входе формы, понятная ошибка в UI.

---

## Этап 4 — Per-platform overrides (S, бэк-только)

UI готов в Stage 1.5 (`OverridesAccordion`). Тут — только бэк-валидация и тесты, если в 1.5 это не было полностью покрыто.

**Цель:** Бэк корректно принимает и применяет per-platform overrides.

### Задачи
1. `POST /api/posts` принимает `text_override_telegram` и `text_override_linkedin`.
2. `PublicationService` уже умеет (`text_override or post.content`) — убедиться тестом.
3. Бэк-валидация: длина overrides под лимиты платформ (LinkedIn ~3000, Telegram 4096).
4. Тесты: override применяется только к нужной платформе; пустой override = базовый текст.

### DoD
- Можно опубликовать пост, в котором Telegram-версия содержит хештеги, а LinkedIn-версия — без, проверено вручную.

### Можно делать локально? ✅ полностью.

### Риски
- Минимальные. Чистая UI-логика.

---

## Этап 5 — Запланированная публикация (M)

UI Sheet «Отложить» сделан в Stage 1.5. Здесь только бэк + scheduler.

**Цель:** Можно выбрать дату/время — пост уходит без участия пользователя.

### Задачи
1. UI готов: `ScheduleSheet` с datetime-picker, отправка `scheduled_at` в `POST /api/posts`.
2. `POST /api/posts` пишет `scheduled_at` и ставит `PlatformPost.status='scheduled'`.
3. `app/scheduler/runner.py`: APScheduler `AsyncIOScheduler`, поднимается в FastAPI lifespan. Один job каждые 30с: выбирает `PlatformPost`-ы со `status='scheduled'` и `next_attempt_at <= now()` (или `scheduled_at <= now()` если попыток ещё не было), атомарно переводит в `queued`, вызывает publication service для каждого.
4. UI: в `History` (Stage 1.5) уже есть отображение `scheduled_at` и кнопка «Cancel» → вызывает `DELETE /api/posts/{id}`.
5. Конкурентность: атомарная смена `scheduled → queued` через `UPDATE ... WHERE status='scheduled'` с проверкой `rowcount=1`. Защита от двойного запуска scheduler-а (он один на процесс).

6. Тесты:
   - Создание поста с `scheduled_at` в будущем → не публикуется немедленно.
   - Тик scheduler-а при `scheduled_at <= now` → публикация запускается.
   - Отмена scheduled-поста → publisher не вызывается.

### DoD
- Создаю пост с `scheduled_at = +2 минуты`, закрываю вкладку, через ~2 минуты пост появляется в обеих платформах.
- Отмена scheduled-поста через UI работает.

### Можно делать локально? ✅ полностью (с фейковыми publisher-ами).

### Риски
- Часовой пояс. Mitigation: храним всё в UTC, отображаем в local time; на форме `datetime-local` — конвертация в UTC на сервере по `Settings.timezone`.
- Если процесс упал в момент scheduled-времени — пост опубликуется при следующем старте (потому что `status='scheduled'` всё ещё). Это приемлемое поведение; если задержка критична — это не для MVP.
- Drift у APScheduler в long-running процессе. Mitigation: периодический job на 30с не требует точности; для `scheduled_at` точность ±30с в MVP приемлема.

---

## Этап 6 — Авторетраи с backoff (M)

**Цель:** Транзиентные ошибки (network blip, 429, 5xx) не превращаются в `failed`, а автоматически повторяются до 5 раз с экспоненциальным backoff.

### Задачи
1. `PublicationService`: при `PublishError(transient=True)` — увеличить `attempts`, посчитать `next_attempt_at = now + min(60 * 2^attempts, 30*60) + jitter`, поставить `status='scheduled'` (тот же ретрай-механизм, что и для запланированных). После 5 попыток → `permanently_failed`.
2. Учёт `retry_after` от Telegram/LinkedIn (если есть в ответе) — использовать как минимум для `next_attempt_at`.
3. Scheduler job (из этапа 5) уже подхватит PP с `scheduled` + `next_attempt_at <= now` — изменений в нём почти не нужно.
4. UI: `PublishStatus` (Stage 1.5) уже разворачивает строку попыток («Attempt 2 of 5 — failed: 429, next retry at …»). Источник — `attempts`/`last_error`/`next_attempt_at` из `GET /api/posts/{id}`.
5. UI: кнопка «Retry now» на `permanently_failed` PP — вызывает `POST /api/posts/{id}/retry/{platform}` (endpoint появился в 1.5; здесь — реальная логика сброса `attempts` и `next_attempt_at = now`).
6. Тесты:
   - Mock publisher, который бросает transient 2 раза, потом успешный → итог `succeeded`, `attempts=3`.
   - 5 transient подряд → `permanently_failed`.
   - Permanent сразу → `permanently_failed`, `attempts=1`.

### DoD
- При искусственно симулированной транзиентной ошибке (`MockTransport`, отключение сети) система сама дожимает публикацию, без участия пользователя.
- UI показывает осмысленную историю попыток.

### Можно делать локально? ✅ полностью.

### Риски
- Двойная публикация при race condition (`publishing` параллельно). Mitigation: атомарная смена статуса + блокировка по idempotency_key + проверка `external_id`.

---

## Этап 7 — Финальная полировка (M)

**Цель:** Готовность к ежедневному использованию.

### Задачи
1. README: установка, OAuth-setup для обеих платформ, типичные ошибки.
2. Структурированные логи (`python-json-logger`), маскирование `Authorization`-заголовка и токенов.
3. Sanity-проверки на старте: проверить наличие всех env-ключей, валидность Telegram токена, существование `ECHO_ENCRYPTION_KEY`; падать с понятной ошибкой, если что-то не так.
4. Простой banner в React UI: «LinkedIn refresh token истекает через X дней» (когда останется <14 дней до `refresh_expires_at`).
5. Дамп истории публикаций в JSON (`GET /api/export`) — для бэкапа на случай потери `.db`.
6. Smoke-тест: один пост-пайплайн от формы до базы, прогоняется в CI (если CI заведём; иначе руками перед коммитом).

### DoD
- Запускаю Echo, публикую пост с картинкой по расписанию через 1 минуту, закрываю ноут, открываю снова — статус `succeeded` на обеих платформах, лог чистый, изменений в схеме БД не потребовалось.

### Можно делать локально? ✅ полностью.

---

## Этап 8 (post-MVP, не входит в исходный план) — Подготовка к VPS

Архитектура к этому готова, но в этапы MVP это не входит. Что нужно будет сделать:
- Postgres вместо SQLite (заменой `database_url`; миграции Alembic должны быть PG-совместимы — мы это уже учитываем).
- HTTPS-домен, обновлённый `linkedin_redirect_uri` в LinkedIn-приложении.
- Секреты из секрет-менеджера, не из `.env`.
- Basic auth / cookie-сессия для всего веба.
- Systemd unit / Docker image + автозапуск.
- Rotation `ECHO_ENCRYPTION_KEY` — продумать процедуру (re-encrypt all tokens), либо принципиально не ротировать.

---

## Сводный список рисков

| Риск | Этап | Mitigation |
|---|---|---|
| LinkedIn approval задерживается | 2 | Запросить EXT-2 на этапе 0; пока ждём — всё кроме реальных вызовов LinkedIn можно делать на фейках |
| `r_liteprofile` deprecated | 2 | Использовать OIDC `/v2/userinfo` для получения member URN |
| LinkedIn API меняет версию | 2, 3 | Фиксируем `LinkedIn-Version` в коде; добавляем в smoke-тест проверку 401/410, чтобы сразу заметить |
| Refresh token умер раньше 365 дней | 2, 6 | UI показывает «требуется реавторизация», не уходим в бесконечный ретрай |
| Telegram caption limit 1024 vs текст до 4096 | 1 | Договариваемся о поведении (skip caption / split — решить при реализации, дефолт: текст идёт отдельным sendMessage если > 1024) |
| Двойная публикация при ретраях | 1, 6 | Атомарная смена статуса `queued→publishing`, проверка `external_id` |
| Утечка `.env` или `.db` | все | Шифрование токенов, `.gitignore`, README предупреждение |
| `ECHO_ENCRYPTION_KEY` потерян | все | README предупреждает: ключ = доступ к токенам; backup из `.env` |
| APScheduler не стартует или job задвоился | 5 | Один job, одна реплика процесса; защита через атомарный `UPDATE` |
| LinkedIn rate limit 100/день | 2, 3 | Не критично для одного человека; учитываем `429` как transient |

## Что строить первым — резюме

1. **EXT-1 (Telegram bot)** ✅ — готов.
2. **EXT-2 (LinkedIn app)** — отправить заявку в Developer Portal как можно раньше, чтобы апрув не блокировал.
3. **Этап 0** ✅ — каркас.
4. **Этап 1** ✅ — Telegram publisher + HTMX UI (заменён в 1.5).
5. **Этап 1.5** — пивот на React SPA. UI закладывается полностью; backend-моки заменяются по мере прохождения следующих этапов.
6. **Этап 2 (LinkedIn OAuth + текст)** — как только EXT-2 одобрен.
7. **Этап 3 → 4 → 5 → 6 → 7** — далее по порядку.

Параллелизация: пока ждём апрув LinkedIn, можно делать этап 5 (планировщик) и этап 6 (авторетраи) против Telegram publisher — они от LinkedIn не зависят. UI для этих фич готов с 1.5.
