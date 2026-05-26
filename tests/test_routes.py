from __future__ import annotations

import asyncio

from httpx import AsyncClient
from sqlalchemy import select

from app.publishers.base import PublishError, PublishRequest, PublishResult
from app.storage.models import PlatformPost, PlatformPostStatus, Post
from tests.test_publication_service import FakePublisher


async def _wait_status(
    session_factory, target: PlatformPostStatus, timeout: float = 1.0
) -> Post | None:
    iterations = max(1, int(timeout / 0.02))
    for _ in range(iterations):
        async with session_factory() as session:
            post = (await session.execute(select(Post))).scalar_one_or_none()
            if (
                post is not None
                and post.platform_posts
                and post.platform_posts[0].status == target
            ):
                return post
        await asyncio.sleep(0.02)
    return None


async def test_list_posts_empty(client: AsyncClient) -> None:
    response = await client.get("/api/posts")
    assert response.status_code == 200
    assert response.json() == {"posts": []}


async def test_create_post_returns_post_and_triggers_publish(
    client: AsyncClient, session_factory
) -> None:
    fake = FakePublisher(result=PublishResult(external_id="111", external_url="https://t.me/c/x/111"))
    from app.main import app

    app.state.registry.register(fake)

    response = await client.post(
        "/api/posts",
        data={"text": "hello json", "platforms": "telegram"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["content"] == "hello json"
    assert body["state"] in ("publishing", "done")
    assert len(body["platform_posts"]) == 1
    assert body["platform_posts"][0]["platform"] == "telegram"

    post = await _wait_status(session_factory, PlatformPostStatus.succeeded)
    assert post is not None
    pp = post.platform_posts[0]
    assert pp.external_id == "111"


async def test_get_single_post(client: AsyncClient, session_factory) -> None:
    fake = FakePublisher(result=PublishResult(external_id="1"))
    from app.main import app

    app.state.registry.register(fake)

    create = await client.post(
        "/api/posts", data={"text": "lookup test", "platforms": "telegram"}
    )
    post_id = create.json()["id"]
    await _wait_status(session_factory, PlatformPostStatus.succeeded)

    resp = await client.get(f"/api/posts/{post_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == post_id
    assert body["content"] == "lookup test"


async def test_empty_text_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/posts", data={"text": "   "})
    assert response.status_code == 400


async def test_unknown_platform_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/posts", data={"text": "x", "platforms": "mastodon"}
    )
    assert response.status_code == 400


async def test_retry_runs_publisher_again(client: AsyncClient, session_factory) -> None:
    fake = FakePublisher(error=PublishError("oops", transient=False))
    from app.main import app

    app.state.registry.register(fake)

    create = await client.post(
        "/api/posts", data={"text": "retry me", "platforms": "telegram"}
    )
    post_id = create.json()["id"]
    failed = await _wait_status(session_factory, PlatformPostStatus.permanently_failed)
    assert failed is not None
    assert len(fake.calls) == 1

    # Swap in a successful publisher and retry.
    success = FakePublisher(result=PublishResult(external_id="ok-2"))
    app.state.registry.register(success)

    retry = await client.post(f"/api/posts/{post_id}/retry/telegram")
    assert retry.status_code == 202

    succeeded = await _wait_status(session_factory, PlatformPostStatus.succeeded)
    assert succeeded is not None
    assert len(success.calls) == 1


async def test_retry_unknown_platform_returns_404(
    client: AsyncClient, session_factory
) -> None:
    fake = FakePublisher(result=PublishResult(external_id="1"))
    from app.main import app

    app.state.registry.register(fake)

    create = await client.post("/api/posts", data={"text": "x", "platforms": "telegram"})
    post_id = create.json()["id"]

    bad = await client.post(f"/api/posts/{post_id}/retry/twitter")
    assert bad.status_code == 404


async def test_connections_reports_telegram(client: AsyncClient) -> None:
    response = await client.get("/api/connections")
    assert response.status_code == 200
    body = response.json()
    assert "telegram" in body
    assert "linkedin" in body
    assert body["linkedin"]["connected"] is False


async def test_scheduled_post_does_not_publish_immediately(
    client: AsyncClient, session_factory
) -> None:
    fake = FakePublisher(result=PublishResult(external_id="never"))
    from app.main import app

    app.state.registry.register(fake)

    response = await client.post(
        "/api/posts",
        data={
            "text": "in the future",
            "platforms": "telegram",
            "scheduled_at": "2099-01-01T12:00:00",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["state"] == "scheduled"
    assert body["platform_posts"][0]["status"] == "scheduled"

    # Give a brief moment to confirm publisher is NOT called.
    await asyncio.sleep(0.1)
    assert fake.calls == []


async def test_cancel_scheduled_post(client: AsyncClient) -> None:
    response = await client.post(
        "/api/posts",
        data={
            "text": "to be cancelled",
            "platforms": "telegram",
            "scheduled_at": "2099-01-01T12:00:00",
        },
    )
    post_id = response.json()["id"]

    delete = await client.delete(f"/api/posts/{post_id}")
    assert delete.status_code == 204

    get = await client.get(f"/api/posts/{post_id}")
    assert get.status_code == 200
    body = get.json()
    assert body["platform_posts"][0]["status"] == "cancelled"
