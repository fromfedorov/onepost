from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.storage.db as db_module
from app.publishers.registry import PublisherRegistry
from app.storage import models  # noqa: F401  ensure tables registered
from app.storage.db import Base
from app.storage.media import MediaStorage


@pytest.fixture
async def db_engine(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def db_session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def media_storage(tmp_path: Path) -> MediaStorage:
    return MediaStorage(tmp_path / "media")


@pytest.fixture
async def client(
    db_engine,
    session_factory,
    media_storage: MediaStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setattr(db_module, "engine", db_engine)
    monkeypatch.setattr(db_module, "async_session_factory", session_factory)

    from app.main import app

    app.state.media = media_storage
    app.state.registry = PublisherRegistry()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
