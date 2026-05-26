# Echo

Cross-post to LinkedIn (personal profile) and Telegram (channel) from one place.

Single-user MVP. See [ARCHITECTURE.md](./ARCHITECTURE.md) and [DEV_PLAN.md](./DEV_PLAN.md).

## Stack

- Python 3.11+, FastAPI, HTMX, SQLAlchemy 2.x + Alembic, SQLite (PG-compatible schema).
- Managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
# 1. Create venv and install deps
uv sync

# 2. Copy env template and fill it in
cp .env.example .env

# 3. Generate a Fernet encryption key (one-time; keep this safe)
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste into .env as ECHO_ENCRYPTION_KEY=...

# 4. Run database migrations
uv run alembic upgrade head
```

**Important:** `ECHO_ENCRYPTION_KEY` encrypts OAuth tokens. If you lose or change it, stored
LinkedIn tokens become unreadable and you'll need to re-authorize. Back up `.env`.

## Run

```bash
uv run uvicorn app.main:app --reload
```

The app listens on http://127.0.0.1:8000. Health check: http://127.0.0.1:8000/healthz

## Tests

```bash
uv run pytest
```

## Database migrations

```bash
# Create a new migration after changing models
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head
```
