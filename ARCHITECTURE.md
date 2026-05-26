# onepost — Архитектура MVP

Кросс-постинг в LinkedIn (личный профиль) и Telegram-канал из единой точки.
Однопользовательский MVP. Локальный запуск сейчас, прицел на VPS в будущем.

## 1. Цели и нецели

**В скоупе MVP**
- Один пользователь (владелец).
- Пост = текст + опционально 1 изображение.
- Общий текст с возможностью per-platform override.
- Публикация «сейчас» и по расписанию (`scheduled_at`).
- Best-effort публикация на каждую платформу + автоматические ретраи с экспоненциальным backoff для транзиентных ошибок.
- Локальный запуск на macOS, OAuth через loopback на `127.0.0.1`.

**Вне скоупа MVP** (см. §11)
- Мультиюзерность, биллинг, команды, роли.
- Аналитика, метрики вовлечённости, ответы/комментарии.
- Все платформы кроме LinkedIn personal profile и Telegram channel.
- Видео, PDF-карусели, опросы.
- Полноценный деплой на VPS с CI/CD (архитектура его учитывает, но шаги — это уже после MVP).
- Откат публикации (rollback при частичном падении) — слишком хрупко.

## 2. Выбор стека

### Решение: Python 3.11+ / FastAPI / HTMX / SQLite / SQLAlchemy + Alembic

| Слой | Выбор | Почему |
|---|---|---|
| Язык | Python 3.11+ | Предпочтение пользователя; зрелые HTTP-клиенты; быстрый прототип. |
| Web | FastAPI | Минимум boilerplate, async-готов для httpx, Pydantic-валидация из коробки. |
| Frontend | Jinja2 (SSR) + HTMX + ванильный CSS (опц. Pico.css/Simple.css) | См. §2.1 ниже. Нет npm, нет сборки, нет SPA-фреймворка. |
| ORM / миграции | SQLAlchemy 2.x + Alembic | Стандарт; даёт возможность безболезненно перейти SQLite → Postgres при переезде на VPS. |
| БД | SQLite (файл) | Один пользователь, локально. Схема пишется так, чтобы быть совместимой с Postgres. |
| HTTP-клиент | httpx (async) | Параллельные вызовы LinkedIn/Telegram, тайм-ауты, ретраи. |
| Шифрование токенов | `cryptography` Fernet | Симметричное шифрование, ключ из `.env`. |
| Планировщик | APScheduler (in-process) | Один процесс, без Redis. Абстрагирован за интерфейс, чтобы заменить на Celery/RQ при переезде. |
| Конфиг | pydantic-settings + `.env` | Типизированная конфигурация. |
| Тесты | pytest + httpx MockTransport | Юнит и интеграционные тесты против фейковых LinkedIn/Telegram. |
| Линт/формат | ruff + mypy | Один тул для линта и формата + строгая типизация в core-слоях. |

### 2.1 Frontend подробнее

В MVP фронта как отдельной кодовой базы НЕТ. UI рендерится сервером и обновляется частичными HTML-фрагментами.

- **Jinja2** — серверный рендеринг страниц. Шаблоны в `app/web/templates/`. FastAPI отдаёт готовый HTML, не JSON.
- **HTMX** (~14 КБ, один `<script>` с CDN или в `app/web/static/`):
  - `hx-post="/posts"` — отправка compose-формы без перезагрузки.
  - `hx-get="/posts/{id}/status" hx-trigger="every 2s"` — polling статуса публикации, пока `publishing`/`queued`. Останавливаем `hx-trigger="every 2s [done]"` через ответный HTML без триггера.
  - `hx-swap` — точечная замена кусков DOM серверными partials (`templates/partials/platform_status.html`, `post_row.html`).
  - Загрузка файла — обычный `<form enctype="multipart/form-data">` с `hx-post`.
- **CSS** — ванильный + одна из classless библиотек (Pico.css / Simple.css) одним `<link>`. Без Tailwind, без PostCSS.
- **JS** — свой не пишем. Если понадобится мелочь (счётчик символов в textarea) — пара строк инлайн.

**Почему не React/Vue/Svelte:**
- Один пользователь, ~3 страницы, ~1 форма — SPA это паразитная сложность.
- Бэкенд и фронт в одном процессе, в одном репозитории, без отдельной сборки.
- HTMX покрывает 100% нужной интерактивности (polling, partial updates, форма с файлом).
- Если потом захочется отдельный SPA — JSON API уже есть в FastAPI; HTMX-роуты просто отдают `text/html` поверх той же логики, можно сосуществовать.

**Структура `app/web/`:**
```
app/web/
├── routes.py
├── templates/
│   ├── base.html               # общий layout (header, nav, footer)
│   ├── compose.html            # GET /
│   ├── posts_list.html         # GET /posts
│   ├── settings.html           # GET /settings (подключения)
│   └── partials/
│       ├── platform_status.html  # фрагмент для GET /posts/{id}/status
│       └── post_row.html         # строка в списке постов
└── static/
    ├── htmx.min.js
    └── styles.css
```

### Альтернативы, которые рассматривались

- **Node/TypeScript (NestJS / Fastify)** — плюс: один язык на фронте и бэке если когда-нибудь будет SPA. Минус: пользователь предпочитает Python; для MVP меньше выигрыша.
- **Go (chi / echo)** — плюс: быстрый бинарь, дешёвый деплой. Минус: больше boilerplate для HTTP/JSON-структур LinkedIn, дольше прототипировать.
- **Django** — плюс: батарейки (admin, миграции, auth). Минус: тяжёлый под одного пользователя, async-стек у LinkedIn/Telegram идиоматичнее на FastAPI.
- **Flask** — плюс: проще FastAPI. Минус: нет встроенной валидации, async — через костыли.
- **HTMX vs React/SPA** — HTMX даёт ровно столько UI, сколько нужно, без отдельной сборки. SPA — оверкилл для одной формы и таблицы статусов.
- **APScheduler vs Celery+Redis vs cron** — для MVP нужна ровно одна задача с `scheduled_at`. APScheduler в том же процессе достаточно; Celery — лишняя инфраструктура; cron — менее гибко и плохо переживает миграцию состояния.

## 3. Компоненты системы

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI process                          │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │  Web layer   │───▶│  Publication     │───▶│  Publisher   │   │
│  │  (HTMX UI    │    │  Service         │    │  Registry    │   │
│  │   + JSON)    │    │  (orchestrator)  │    │              │   │
│  └──────────────┘    └────────┬─────────┘    └──────┬───────┘   │
│         │                     │                     │           │
│         │                     ▼                     ▼           │
│         │            ┌──────────────────┐  ┌────────────────┐   │
│         │            │  Scheduler       │  │ TelegramPub.   │   │
│         │            │  (APScheduler)   │  │ LinkedInPub.   │   │
│         │            └──────────────────┘  └────────┬───────┘   │
│         │                     │                     │           │
│         ▼                     ▼                     │           │
│  ┌──────────────────────────────────────┐           │           │
│  │  Storage layer                       │           │           │
│  │  ┌─────────┐ ┌──────────┐ ┌────────┐ │           │           │
│  │  │ Posts   │ │ Platform │ │ Tokens │ │◀──────────┘           │
│  │  │         │ │ Posts    │ │ (enc.) │ │                       │
│  │  └─────────┘ └──────────┘ └────────┘ │                       │
│  │            ┌────────────┐            │                       │
│  │            │ MediaStore │            │                       │
│  │            │ (FS)       │            │                       │
│  │            └────────────┘            │                       │
│  └──────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                              │ httpx
                              ▼
              ┌───────────────────────────────┐
              │  LinkedIn API   │  Telegram   │
              │  /rest/posts    │  Bot API    │
              └───────────────────────────────┘
```

### 3.1 Web layer (`app/web`)
- Роуты для compose-формы, списка постов, страницы статусов, OAuth-callback.
- HTMX-фрагменты для динамического обновления статусов без full page reload.
- В MVP — никакой auth: слушает только `127.0.0.1`. При переезде на VPS — basic auth / cookie session (см. §11).

### 3.2 Publication Service (`app/services/publication.py`)
- Оркестратор. Принимает `Post`, разворачивает в N `PlatformPost` (по одной на платформу), вызывает соответствующие `Publisher`-ы параллельно через `asyncio.gather(return_exceptions=True)`.
- Не знает о конкретных платформах — только об интерфейсе `Publisher`.
- Записывает статусы и `external_id` в БД. Падение одной платформы не отменяет другую.

### 3.3 Publisher Registry + платформенные реализации (`app/publishers/`)
- `Publisher` — protocol (см. §4).
- Реализации: `TelegramPublisher`, `LinkedInPublisher`.
- Registry — простой dict `{platform_id: Publisher}`. Добавление новой платформы = одна реализация + регистрация.

### 3.4 Auth / Token layer (`app/auth/`)
- `LinkedInOAuth`: запуск flow, callback, обмен code→token, refresh-сценарий.
- `TokenStore`: чтение/запись зашифрованных токенов в БД.
- Refresh: проверка `expires_at` перед каждым вызовом; если осталось <7 дней — refresh; если refresh-токен мёртв — UI показывает баннер «требуется реавторизация».
- Telegram — просто bot token + chat_id в `.env`/конфиге; не требует refresh.

### 3.5 Storage layer (`app/storage/`)
- SQLAlchemy-модели + Alembic.
- `MediaStorage` — тонкий интерфейс с одной реализацией `LocalMediaStorage` (запись в `data/media/<uuid>.<ext>`). Абстракция позволяет позже подключить S3/MinIO без изменений в publication service.

### 3.6 Scheduler (`app/scheduler/`)
- APScheduler `AsyncIOScheduler`, поднимается в lifespan FastAPI.
- Один периодический job (раз в 30с): «забрать `PlatformPost`-ы с `status='scheduled'` и `scheduled_at <= now`, перевести в `queued`, вызвать publication service».
- Также используется для backoff-ретраев (см. §8).

## 4. Абстракция платформы

```python
# app/publishers/base.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class PublishRequest:
    text: str
    image_path: str | None        # абсолютный путь на локальный файл, или None
    idempotency_key: str          # для дедупликации при ретраях

@dataclass
class PublishResult:
    external_id: str              # ID поста на платформе
    external_url: str | None      # ссылка на пост, если доступна

class PublishError(Exception):
    transient: bool               # True → стоит ретраить; False → постоянная ошибка

class Publisher(Protocol):
    platform_id: str              # "telegram" | "linkedin" | ...
    display_name: str

    async def publish(self, req: PublishRequest) -> PublishResult: ...
    async def healthcheck(self) -> bool: ...   # для UI "соединение ок"
```

Контракт:
- `publish` либо возвращает `PublishResult`, либо бросает `PublishError(transient=True/False)`.
- Реализация сама занимается своими «причудами» (LinkedIn — отдельный upload media шаг и `urn:li:image:...`; Telegram — выбор между `sendMessage`/`sendPhoto`).
- Реализация сама знает про свои rate limits и подсказывает scheduler-у retry-after через атрибут на исключении.

Добавление третьей платформы (X, Mastodon, Bluesky) = создать класс, реализующий `Publisher`, и зарегистрировать его. Никаких изменений в Publication Service.

## 5. Модель данных

Используются UUID-ы как первичные ключи (PG-совместимо).

### `posts`
| Поле | Тип | Назначение |
|---|---|---|
| id | UUID | PK |
| content | TEXT | Базовый текст |
| image_media_id | UUID? | FK → media.id |
| scheduled_at | TIMESTAMP? | Если NULL — публикация немедленная |
| created_at | TIMESTAMP | |
| state | ENUM(`draft`, `scheduled`, `publishing`, `done`, `failed`) | Агрегат над PlatformPost |

### `platform_posts`
| Поле | Тип | Назначение |
|---|---|---|
| id | UUID | PK |
| post_id | UUID | FK → posts.id |
| platform | ENUM(`telegram`, `linkedin`) | |
| text_override | TEXT? | Если NULL — берём `posts.content` |
| status | ENUM(`pending`, `scheduled`, `queued`, `publishing`, `succeeded`, `failed`, `permanently_failed`) | |
| external_id | TEXT? | ID поста на платформе |
| external_url | TEXT? | URL опубликованного поста |
| attempts | INTEGER | Сколько попыток сделано |
| next_attempt_at | TIMESTAMP? | Когда вторая/третья попытка |
| last_error | TEXT? | Сообщение последней ошибки (для UI) |
| idempotency_key | TEXT | UUID, генерируется при создании |
| updated_at | TIMESTAMP | |

### `media`
| Поле | Тип | Назначение |
|---|---|---|
| id | UUID | PK |
| local_path | TEXT | Путь относительно `data/media/` |
| mime_type | TEXT | |
| size_bytes | INTEGER | |
| created_at | TIMESTAMP | |

### `oauth_tokens`
| Поле | Тип | Назначение |
|---|---|---|
| id | UUID | PK |
| platform | ENUM(`linkedin`) | (Telegram сюда не пишется) |
| access_token_encrypted | BLOB | Зашифровано Fernet |
| refresh_token_encrypted | BLOB? | |
| access_expires_at | TIMESTAMP | |
| refresh_expires_at | TIMESTAMP? | |
| scope | TEXT | |
| account_identifier | TEXT? | LinkedIn member URN, для отображения |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `audit_log` (опционально, но рекомендую сразу)
| Поле | Тип | Назначение |
|---|---|---|
| id | UUID | PK |
| at | TIMESTAMP | |
| platform_post_id | UUID? | |
| event | TEXT | `attempt`, `success`, `transient_fail`, `permanent_fail`, `token_refresh`, ... |
| detail | JSON | |

## 6. Секреты и OAuth-токены

### Чувствительные данные

| Что | Где | Защита |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `.env` | `.env` в `.gitignore`, не логируется |
| `TELEGRAM_CHANNEL_ID` | `.env` | — |
| `LINKEDIN_CLIENT_ID` / `CLIENT_SECRET` | `.env` | `.env` в `.gitignore` |
| `ONEPOST_ENCRYPTION_KEY` | `.env` | 32-байтовый Fernet-ключ; генерируется на этапе 0 и больше не меняется (иначе токены расшифровать нельзя) |
| LinkedIn access/refresh токены | таблица `oauth_tokens`, BLOB | Fernet поверх `ONEPOST_ENCRYPTION_KEY` |

### Правила
- Никаких токенов в коде, в логах, в shell history.
- При логировании HTTP ответов LinkedIn — маскировать заголовок `Authorization` и поля `access_token`/`refresh_token`.
- `.env.example` коммитится с пустыми значениями; `.env` — никогда.
- При переезде на VPS — `ONEPOST_ENCRYPTION_KEY` берётся из секрет-менеджера (например, Doppler / 1Password / Fly secrets / Railway env), не из файла.

### OAuth flow (LinkedIn)
1. Пользователь жмёт «Connect LinkedIn» в UI.
2. Редирект на `https://www.linkedin.com/oauth/v2/authorization?...&redirect_uri=http://127.0.0.1:8000/oauth/linkedin/callback`.
3. LinkedIn возвращает `code` на callback.
4. Сервер обменивает `code` на access + refresh токены (`POST /oauth/v2/accessToken`).
5. Токены шифруются и пишутся в `oauth_tokens`.
6. Перед каждой публикацией `LinkedInPublisher` запрашивает у `TokenStore` валидный access-токен; если близок к истечению — TokenStore сам делает refresh.

## 7. Поток данных

### Немедленная публикация

```mermaid
sequenceDiagram
    actor U as User
    participant W as Web (HTMX)
    participant P as Publication Service
    participant TG as TelegramPublisher
    participant LI as LinkedInPublisher
    participant DB as Storage

    U->>W: POST /compose (text, image, "publish now")
    W->>DB: create Post + 2 PlatformPosts (status=queued)
    W-->>U: 200 + HTMX partial (статус "publishing...")
    par
        W->>P: publish(post_id)
        P->>TG: publish(req)
        TG-->>P: PublishResult or PublishError
        P->>DB: update telegram PlatformPost
    and
        P->>LI: publish(req)
        LI-->>P: PublishResult or PublishError
        P->>DB: update linkedin PlatformPost
    end
    U->>W: GET /posts/{id}/status (HTMX poll)
    W->>DB: read PlatformPosts
    W-->>U: HTML с реальными статусами
```

### Запланированная публикация

```mermaid
sequenceDiagram
    actor U as User
    participant W as Web
    participant S as Scheduler (APScheduler)
    participant P as Publication Service
    participant DB as Storage

    U->>W: POST /compose (text, scheduled_at=2026-05-27T10:00)
    W->>DB: create Post(state=scheduled) + PlatformPosts(status=scheduled)
    loop каждые 30с
        S->>DB: SELECT * FROM platform_posts WHERE status='scheduled' AND scheduled_at <= now()
        S->>DB: UPDATE ... SET status='queued'
        S->>P: publish_due()
        P->>P: ... (как в немедленном сценарии)
    end
```

## 8. Обработка ошибок и ретраев

### Классификация ошибок (на стороне Publisher-а)
- **Transient**: HTTP 5xx, сетевые таймауты, LinkedIn 429 (rate limit), Telegram `retry_after`. Бросаем `PublishError(transient=True, retry_after=...)`.
- **Permanent**: HTTP 400/401/403 после refresh-попытки, валидационные ошибки (текст слишком длинный), ошибки контента. Бросаем `PublishError(transient=False)`.

### Поведение Publication Service
- Параллельная отправка на обе платформы (`asyncio.gather(return_exceptions=True)`).
- Каждый PlatformPost живёт своей жизнью — статус одного не зависит от другого.
- При transient → планируем повтор: `next_attempt_at = now + backoff(attempts)`, `status='scheduled'`. Тот же periodic-job планировщика подхватит её снова.
- Backoff: `min(60 * 2^attempts, 30*60)` секунд + jitter. Максимум 5 попыток. После 5 — `permanently_failed`.
- При permanent → сразу `permanently_failed`, причина в `last_error`, UI показывает кнопку «Попробовать снова» (сбрасывает счётчик).

### Идемпотентность
- В `idempotency_key` PlatformPost'а — UUID, генерируемый при создании.
- TelegramPublisher: bot API не поддерживает идемпотентность; защищаемся атомарной сменой статуса `queued → publishing` (если кто-то опередил — пропускаем).
- LinkedInPublisher: передаём `X-RestLi-Method: CREATE` и заголовок `LinkedIn-Version`. Если получили `external_id` от прошлой попытки и текущая попытка получит дубль-успех — обновляем `external_id` на последнем (вряд ли случится при правильной блокировке статусов, но всё равно безопасно).

### Что НЕ делаем
- Не делаем rollback успешной публикации, если упала вторая платформа. Это нежелательно для личного бренда (удаление поста = неконсистентность для подписчиков, которые уже увидели).
- Не делаем cross-platform transactions.

## 9. Логирование и наблюдаемость

- Стандартный `logging` с JSON-форматтером (`python-json-logger`). Готово к чтению `journalctl`/Loki при переезде.
- Уровни: INFO для каждой попытки публикации, WARN для transient-ошибок, ERROR для permanent.
- Никаких токенов и тел запросов в логи.
- На UI — таблица последних 50 постов со статусами на платформу + раскрывающаяся история попыток (из `audit_log`).

## 10. Безопасность (минимум для локального MVP)

- FastAPI слушает только `127.0.0.1`.
- `.gitignore` покрывает `.env`, `*.db`, `data/`, `__pycache__/`, `.venv/`.
- Шифрование токенов даже локально — чтобы кража БД-файла не раскрыла LinkedIn-аккаунт.
- Все исходящие HTTP-вызовы — с тайм-аутами (connect 5с, read 15с).
- Валидация входных данных через Pydantic; ограничения на размер изображения (например, 5 МБ).
- При будущем переезде на VPS — добавить HTTPS, basic auth или OAuth-вход для самого приложения, rate-limit на `/compose`. В коде — оставить hook для middleware.

## 11. Что НЕ входит в MVP

- Многопользовательский режим, команды, RBAC.
- Биллинг.
- Более одного Telegram-канала / нескольких LinkedIn-аккаунтов.
- Видео, PDF-карусели, опросы, статьи (`/rest/originalArticles`).
- Перепост чужих постов, шаринг ссылок с превью-карточками за пределами того, что LinkedIn/Telegram делают сами.
- Аналитика (просмотры, реакции, клики).
- Inbox: ответы и комментарии.
- AI-генерация / переписывание контента под платформу.
- Превью «как пост будет выглядеть» в стиле LinkedIn/Telegram — отложено.
- Rollback при частичном падении публикации.
- Деплой на VPS, CI/CD, мониторинг, alerts — отдельный пост-MVP трек.
- Тесты против реального LinkedIn (только против фейков; реальная проверка — ручная при апруве приложения).

## 12. Структура репозитория (целевая)

```
onepost/
├── ARCHITECTURE.md
├── DEV_PLAN.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── alembic.ini
├── migrations/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, lifespan, scheduler bootstrap
│   ├── config.py               # pydantic-settings
│   ├── deps.py                 # DI helpers
│   ├── web/
│   │   ├── routes.py
│   │   ├── templates/
│   │   └── static/
│   ├── services/
│   │   └── publication.py
│   ├── publishers/
│   │   ├── base.py             # Publisher protocol + dataclasses
│   │   ├── telegram.py
│   │   └── linkedin.py
│   ├── auth/
│   │   ├── linkedin_oauth.py
│   │   └── token_store.py
│   ├── storage/
│   │   ├── db.py               # engine, session
│   │   ├── models.py
│   │   └── media.py            # MediaStorage
│   └── scheduler/
│       └── runner.py
├── tests/
│   ├── conftest.py
│   ├── test_telegram_publisher.py
│   ├── test_linkedin_publisher.py
│   ├── test_publication_service.py
│   └── test_scheduler.py
└── data/                       # gitignored: SQLite файл + медиа
    ├── onepost.db
    └── media/
```
