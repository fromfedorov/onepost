from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.storage.db as db_module
from app.api.schemas import (
    ConnectionsOut,
    LinkedInConnection,
    MediaOut,
    PlatformPostOut,
    PostListOut,
    PostOut,
    TelegramConnection,
)
from app.publishers.registry import PublisherRegistry
from app.services.publication import PublicationService
from app.storage.db import get_session
from app.storage.media import MediaError, MediaStorage
from app.storage.models import (
    Media,
    Platform,
    PlatformPost,
    PlatformPostStatus,
    Post,
    PostState,
)

router = APIRouter(prefix="/api")


def _media(request: Request) -> MediaStorage:
    return request.app.state.media


def _registry(request: Request) -> PublisherRegistry:
    return request.app.state.registry


async def _run_publish(
    post_id: str, registry: PublisherRegistry, media: MediaStorage
) -> None:
    async with db_module.async_session_factory() as session:
        svc = PublicationService(session, registry, media)
        await svc.publish(post_id)


async def _publish_one_pp(
    pp_id: str, registry: PublisherRegistry, media: MediaStorage
) -> None:
    async with db_module.async_session_factory() as session:
        pp = await session.get(PlatformPost, pp_id)
        if pp is None:
            return
        pp.attempts = 0
        pp.next_attempt_at = None
        pp.last_error = None
        pp.status = PlatformPostStatus.queued
        await session.commit()
        svc = PublicationService(session, registry, media)
        await svc.publish_platform_post(pp_id)


@router.get("/posts", response_model=PostListOut)
async def list_posts(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PostListOut:
    result = await session.execute(
        select(Post).order_by(Post.created_at.desc()).limit(50)
    )
    posts = result.scalars().all()
    return PostListOut(posts=[PostOut.model_validate(p) for p in posts])


@router.get("/posts/{post_id}", response_model=PostOut)
async def get_post(
    post_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PostOut:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostOut.model_validate(post)


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_202_ACCEPTED)
async def create_post(
    request: Request,
    background: BackgroundTasks,
    text: Annotated[str, Form()],
    session: Annotated[AsyncSession, Depends(get_session)],
    platforms: Annotated[str, Form()] = "telegram",
    text_override_telegram: Annotated[str | None, Form()] = None,
    text_override_linkedin: Annotated[str | None, Form()] = None,
    scheduled_at: Annotated[str | None, Form()] = None,
    image: Annotated[UploadFile | None, File()] = None,
) -> PostOut:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        platform_list = [Platform(p.strip()) for p in platforms.split(",") if p.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {exc}") from exc
    if not platform_list:
        raise HTTPException(status_code=400, detail="At least one platform required")

    scheduled_dt: datetime | None = None
    if scheduled_at:
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at") from exc

    media_id: str | None = None
    if image is not None and image.filename:
        data = await image.read()
        if data:
            try:
                local_path, mime, size = _media(request).save(data, image.filename)
            except MediaError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            m = Media(local_path=local_path, mime_type=mime, size_bytes=size)
            session.add(m)
            await session.flush()
            media_id = m.id

    overrides: dict[Platform, str | None] = {
        Platform.telegram: text_override_telegram or None,
        Platform.linkedin: text_override_linkedin or None,
    }

    initial_state = PostState.scheduled if scheduled_dt else PostState.publishing
    initial_pp_status = (
        PlatformPostStatus.scheduled if scheduled_dt else PlatformPostStatus.queued
    )

    post = Post(
        content=text,
        image_media_id=media_id,
        state=initial_state,
        scheduled_at=scheduled_dt,
    )
    session.add(post)
    await session.flush()

    for platform in platform_list:
        pp = PlatformPost(
            post_id=post.id,
            platform=platform,
            text_override=overrides.get(platform),
            status=initial_pp_status,
        )
        session.add(pp)
    await session.commit()
    await session.refresh(post, attribute_names=["platform_posts", "image"])

    if scheduled_dt is None:
        background.add_task(_run_publish, post.id, _registry(request), _media(request))

    return PostOut.model_validate(post)


@router.post(
    "/posts/{post_id}/retry/{platform}",
    response_model=PlatformPostOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_platform(
    post_id: str,
    platform: str,
    request: Request,
    background: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PlatformPostOut:
    try:
        platform_enum = Platform(platform)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unknown platform") from exc

    result = await session.execute(
        select(PlatformPost).where(
            PlatformPost.post_id == post_id, PlatformPost.platform == platform_enum
        )
    )
    pp = result.scalar_one_or_none()
    if pp is None:
        raise HTTPException(status_code=404, detail="Platform post not found")

    background.add_task(_publish_one_pp, pp.id, _registry(request), _media(request))
    return PlatformPostOut.model_validate(pp)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_post(
    post_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.state != PostState.scheduled:
        raise HTTPException(status_code=409, detail="Only scheduled posts can be cancelled")

    for pp in post.platform_posts:
        if pp.status == PlatformPostStatus.scheduled:
            pp.status = PlatformPostStatus.cancelled
    post.state = PostState.failed
    await session.commit()


@router.get("/connections", response_model=ConnectionsOut)
async def connections(request: Request) -> ConnectionsOut:
    registry: PublisherRegistry = request.app.state.registry
    telegram_pub = registry.get("telegram")
    telegram_healthy = await telegram_pub.healthcheck() if telegram_pub else False

    return ConnectionsOut(
        telegram=TelegramConnection(
            configured=telegram_pub is not None,
            healthy=telegram_healthy,
            channel_id=getattr(telegram_pub, "_channel_id", None) if telegram_pub else None,
        ),
        linkedin=LinkedInConnection(
            configured=False,  # Stage 2 will wire this up
            connected=False,
        ),
    )


@router.get("/media/{media_id}")
async def get_media(
    media_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileResponse:
    media = await session.get(Media, media_id)
    if media is None:
        raise HTTPException(status_code=404)
    path = _media(request).absolute_path(media.local_path)
    return FileResponse(path, media_type=media.mime_type)
