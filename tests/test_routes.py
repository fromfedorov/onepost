from __future__ import annotations

import asyncio

from httpx import AsyncClient
from sqlalchemy import select

from app.publishers.base import PublishRequest, PublishResult
from app.publishers.registry import PublisherRegistry
from app.storage.models import PlatformPost, PlatformPostStatus, Post
from tests.test_publication_service import FakePublisher


async def test_index_renders_empty_state(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "Compose" in response.text
    assert "No posts yet" in response.text


async def test_create_post_creates_db_row_and_kicks_publisher(
    client: AsyncClient, session_factory
) -> None:
    fake = FakePublisher(result=PublishResult(external_id="999", external_url="https://t.me/c/x/9"))
    from app.main import app

    registry: PublisherRegistry = app.state.registry
    registry.register(fake)

    response = await client.post(
        "/posts",
        data={"text": "hello from test"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    # BackgroundTasks run after response; give the loop a chance
    for _ in range(50):
        async with session_factory() as session:
            pp = (await session.execute(select(PlatformPost))).scalar_one_or_none()
            if pp is not None and pp.status == PlatformPostStatus.succeeded:
                break
        await asyncio.sleep(0.02)

    async with session_factory() as session:
        post = (await session.execute(select(Post))).scalar_one()
        assert post.content == "hello from test"
        pp = (await session.execute(select(PlatformPost))).scalar_one()
        assert pp.status == PlatformPostStatus.succeeded
        assert pp.external_id == "999"

    assert len(fake.calls) == 1
    assert fake.calls[0].text == "hello from test"


async def test_post_status_partial(client: AsyncClient, session_factory) -> None:
    fake = FakePublisher(result=PublishResult(external_id="1"))
    from app.main import app

    app.state.registry.register(fake)

    create_resp = await client.post(
        "/posts", data={"text": "another"}, follow_redirects=False
    )
    assert create_resp.status_code == 303

    # Wait for the background publish to finish.
    post_id: str | None = None
    for _ in range(50):
        async with session_factory() as session:
            row = (await session.execute(select(Post))).scalar_one_or_none()
            if row is not None and row.platform_posts and row.platform_posts[0].status == PlatformPostStatus.succeeded:
                post_id = row.id
                break
        await asyncio.sleep(0.02)
    assert post_id is not None

    status_resp = await client.get(f"/posts/{post_id}/status")
    assert status_resp.status_code == 200
    assert "succeeded" in status_resp.text


async def test_empty_text_rejected(client: AsyncClient) -> None:
    response = await client.post("/posts", data={"text": "   "}, follow_redirects=False)
    assert response.status_code == 400
