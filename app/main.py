from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.publishers.registry import PublisherRegistry
from app.publishers.telegram import TelegramPublisher
from app.storage.media import MediaStorage
from app.web.routes import router as web_router

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "web" / "static"
MEDIA_DIR = Path(__file__).parent.parent / "data" / "media"


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
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(web_router)


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
