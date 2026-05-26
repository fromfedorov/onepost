from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import get_settings
from app.publishers.registry import PublisherRegistry
from app.publishers.telegram import TelegramPublisher
from app.storage.media import MediaStorage

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
MEDIA_DIR = PROJECT_ROOT / "data" / "media"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.media = MediaStorage(MEDIA_DIR)

    registry = PublisherRegistry()
    telegram: TelegramPublisher | None = None
    if settings.telegram_bot_token and settings.telegram_channel_id:
        telegram = TelegramPublisher(
            bot_token=settings.telegram_bot_token,
            channel_id=settings.telegram_channel_id,
        )
        registry.register(telegram)
    else:
        logger.warning("Telegram credentials missing — publisher not registered")
    app.state.registry = registry

    try:
        yield
    finally:
        if telegram is not None:
            await telegram.aclose()


app = FastAPI(title="onepost", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


# Serve React build in production. In dev, Vite runs separately on :5173.
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def spa_fallback(spa_path: str) -> FileResponse:
        index = FRONTEND_DIST / "index.html"
        return FileResponse(index)
