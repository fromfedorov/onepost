# onepost

Cross-post to LinkedIn (personal profile) and Telegram (channel) from one place.

Single-user MVP. See [ARCHITECTURE.md](./ARCHITECTURE.md) and [DEV_PLAN.md](./DEV_PLAN.md).

## Stack

- Backend: Python 3.11+, FastAPI (JSON API), SQLAlchemy 2.x + Alembic, SQLite. Managed with [uv](https://docs.astral.sh/uv/).
- Frontend: React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui. Lives in `frontend/`.

## Setup

### Backend

```bash
# 1. Create venv and install deps
uv sync

# 2. Copy env template and fill it in
cp .env.example .env

# 3. Generate a Fernet encryption key (one-time; keep this safe)
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste into .env as ONEPOST_ENCRYPTION_KEY=...

# 4. Run database migrations
uv run alembic upgrade head
```

`ONEPOST_ENCRYPTION_KEY` encrypts OAuth tokens. If you lose or change it, stored
LinkedIn tokens become unreadable and you'll need to re-authorize. Back up `.env`.

### Frontend

```bash
cd frontend
npm install
```

Requires Node.js 20.19+ or 22.12+ (Vite 7).

## Run (development)

Two processes, two terminals:

```bash
# Terminal 1: backend
uv run uvicorn app.main:app --reload
# Listens on http://127.0.0.1:8000

# Terminal 2: frontend
npm --prefix frontend run dev
# Opens http://localhost:5173, proxies /api/* to the backend
```

Open http://localhost:5173 in a browser.

## Build (production)

```bash
npm --prefix frontend run build
uv run uvicorn app.main:app
```

When `frontend/dist` exists, FastAPI serves it as the SPA at `/`.

## Tests

```bash
uv run pytest                      # backend
npm --prefix frontend run lint     # frontend lint
npm --prefix frontend run build    # frontend type-check + build
```

## Database migrations

```bash
# Create a new migration after changing models
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head
```
