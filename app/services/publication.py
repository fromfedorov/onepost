from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.publishers.base import PublishError, PublishRequest
from app.publishers.registry import PublisherRegistry
from app.storage.media import MediaStorage
from app.storage.models import (
    PlatformPost,
    PlatformPostStatus,
    Post,
    PostState,
)

logger = logging.getLogger(__name__)


class PublicationService:
    def __init__(
        self,
        session: AsyncSession,
        registry: PublisherRegistry,
        media_storage: MediaStorage,
    ) -> None:
        self._session = session
        self._registry = registry
        self._media = media_storage

    async def publish(self, post_id: str) -> None:
        post = await self._session.get(Post, post_id)
        if post is None:
            logger.warning("publish: post %s not found", post_id)
            return

        image_path: str | None = None
        if post.image is not None:
            image_path = str(self._media.absolute_path(post.image.local_path))

        post.state = PostState.publishing
        await self._session.commit()

        await asyncio.gather(
            *(self._publish_one(pp, post.content, image_path) for pp in post.platform_posts),
            return_exceptions=False,
        )

        await self._session.refresh(post, attribute_names=["platform_posts"])
        statuses = {pp.status for pp in post.platform_posts}
        if statuses <= {PlatformPostStatus.succeeded}:
            post.state = PostState.done
        elif statuses & {
            PlatformPostStatus.succeeded,
            PlatformPostStatus.publishing,
            PlatformPostStatus.queued,
            PlatformPostStatus.scheduled,
        }:
            # mixed success / still-running
            post.state = (
                PostState.done
                if PlatformPostStatus.succeeded in statuses
                else PostState.publishing
            )
        else:
            post.state = PostState.failed
        await self._session.commit()

    async def publish_platform_post(self, pp_id: str) -> None:
        pp = await self._session.get(PlatformPost, pp_id)
        if pp is None:
            logger.warning("publish_platform_post: %s not found", pp_id)
            return
        post = await self._session.get(Post, pp.post_id)
        if post is None:
            return
        image_path = (
            str(self._media.absolute_path(post.image.local_path)) if post.image else None
        )
        await self._publish_one(pp, post.content, image_path)

    async def _publish_one(
        self, pp: PlatformPost, default_text: str, image_path: str | None
    ) -> None:
        publisher = self._registry.get(pp.platform.value)
        if publisher is None:
            pp.status = PlatformPostStatus.permanently_failed
            pp.last_error = f"No publisher registered for {pp.platform.value}"
            await self._session.commit()
            return

        pp.status = PlatformPostStatus.publishing
        pp.attempts += 1
        await self._session.commit()

        text = pp.text_override if pp.text_override else default_text
        req = PublishRequest(
            text=text,
            image_path=image_path,
            idempotency_key=pp.idempotency_key,
        )

        try:
            result = await publisher.publish(req)
        except PublishError as exc:
            pp.last_error = str(exc)
            pp.status = (
                PlatformPostStatus.failed if exc.transient else PlatformPostStatus.permanently_failed
            )
            logger.info(
                "publish %s failed (transient=%s): %s",
                pp.platform.value,
                exc.transient,
                exc,
            )
        except Exception as exc:  # defensive: never let one publisher crash the request
            pp.last_error = f"unexpected: {exc!r}"
            pp.status = PlatformPostStatus.failed
            logger.exception("publish %s unexpected error", pp.platform.value)
        else:
            pp.external_id = result.external_id
            pp.external_url = result.external_url
            pp.status = PlatformPostStatus.succeeded
            pp.last_error = None

        await self._session.commit()


def resolve_image_path(media_storage: MediaStorage, local_path: str | None) -> Path | None:
    if local_path is None:
        return None
    return media_storage.absolute_path(local_path)
