from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.publishers.base import PublishError, PublishRequest, PublishResult
from app.publishers.registry import PublisherRegistry
from app.services.publication import PublicationService
from app.storage.media import MediaStorage
from app.storage.models import (
    Platform,
    PlatformPost,
    PlatformPostStatus,
    Post,
    PostState,
)


class FakePublisher:
    platform_id = "telegram"
    display_name = "Telegram (fake)"

    def __init__(self, result: PublishResult | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.calls: list[PublishRequest] = []

    async def publish(self, req: PublishRequest) -> PublishResult:
        self.calls.append(req)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result

    async def healthcheck(self) -> bool:
        return True


async def _create_post(
    session: AsyncSession,
    text: str = "hello world",
    text_override: str | None = None,
) -> Post:
    post = Post(content=text, state=PostState.publishing)
    session.add(post)
    await session.flush()
    pp = PlatformPost(
        post_id=post.id,
        platform=Platform.telegram,
        text_override=text_override,
        status=PlatformPostStatus.queued,
    )
    session.add(pp)
    await session.commit()
    await session.refresh(post, attribute_names=["platform_posts"])
    return post


async def test_successful_publish_marks_succeeded(
    db_session: AsyncSession, media_storage: MediaStorage
) -> None:
    fake = FakePublisher(result=PublishResult(external_id="55", external_url="https://t.me/c/x/55"))
    registry = PublisherRegistry()
    registry.register(fake)
    post = await _create_post(db_session)

    svc = PublicationService(db_session, registry, media_storage)
    await svc.publish(post.id)

    refreshed = (
        await db_session.execute(select(Post).where(Post.id == post.id))
    ).scalar_one()
    pp = refreshed.platform_posts[0]
    assert pp.status == PlatformPostStatus.succeeded
    assert pp.external_id == "55"
    assert pp.external_url == "https://t.me/c/x/55"
    assert pp.attempts == 1
    assert refreshed.state == PostState.done


async def test_transient_failure_marks_failed(
    db_session: AsyncSession, media_storage: MediaStorage
) -> None:
    fake = FakePublisher(error=PublishError("network glitch", transient=True))
    registry = PublisherRegistry()
    registry.register(fake)
    post = await _create_post(db_session)

    svc = PublicationService(db_session, registry, media_storage)
    await svc.publish(post.id)

    pp = (await db_session.get(Post, post.id)).platform_posts[0]
    assert pp.status == PlatformPostStatus.failed
    assert "network glitch" in (pp.last_error or "")


async def test_permanent_failure_marks_permanently_failed(
    db_session: AsyncSession, media_storage: MediaStorage
) -> None:
    fake = FakePublisher(error=PublishError("bad request", transient=False))
    registry = PublisherRegistry()
    registry.register(fake)
    post = await _create_post(db_session)

    svc = PublicationService(db_session, registry, media_storage)
    await svc.publish(post.id)

    pp = (await db_session.get(Post, post.id)).platform_posts[0]
    assert pp.status == PlatformPostStatus.permanently_failed


async def test_unregistered_platform_is_permanently_failed(
    db_session: AsyncSession, media_storage: MediaStorage
) -> None:
    registry = PublisherRegistry()  # nothing registered
    post = await _create_post(db_session)

    svc = PublicationService(db_session, registry, media_storage)
    await svc.publish(post.id)

    pp = (await db_session.get(Post, post.id)).platform_posts[0]
    assert pp.status == PlatformPostStatus.permanently_failed
    assert "No publisher" in (pp.last_error or "")


async def test_text_override_takes_precedence(
    db_session: AsyncSession, media_storage: MediaStorage
) -> None:
    fake = FakePublisher(result=PublishResult(external_id="1"))
    registry = PublisherRegistry()
    registry.register(fake)
    post = await _create_post(db_session, text="default text", text_override="overridden")

    svc = PublicationService(db_session, registry, media_storage)
    await svc.publish(post.id)

    assert fake.calls[0].text == "overridden"
