from __future__ import annotations

from pathlib import Path
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
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.storage.db as db_module
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

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _media(request: Request) -> MediaStorage:
    return request.app.state.media


def _registry(request: Request) -> PublisherRegistry:
    return request.app.state.registry


async def _run_publish(post_id: str, registry: PublisherRegistry, media: MediaStorage) -> None:
    async with db_module.async_session_factory() as session:
        svc = PublicationService(session, registry, media)
        await svc.publish(post_id)


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HTMLResponse:
    result = await session.execute(
        select(Post).order_by(Post.created_at.desc()).limit(20)
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"posts": posts, "active_statuses": _ACTIVE_STATUSES},
    )


_ACTIVE_STATUSES = {
    PlatformPostStatus.pending,
    PlatformPostStatus.queued,
    PlatformPostStatus.publishing,
    PlatformPostStatus.scheduled,
}


@router.post("/posts")
async def create_post(
    request: Request,
    background: BackgroundTasks,
    text: Annotated[str, Form()],
    session: Annotated[AsyncSession, Depends(get_session)],
    image: Annotated[UploadFile | None, File()] = None,
) -> RedirectResponse:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

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

    post = Post(content=text, image_media_id=media_id, state=PostState.publishing)
    session.add(post)
    await session.flush()

    pp = PlatformPost(
        post_id=post.id,
        platform=Platform.telegram,
        status=PlatformPostStatus.queued,
    )
    session.add(pp)
    await session.commit()

    background.add_task(_run_publish, post.id, _registry(request), _media(request))

    return RedirectResponse(url="/", status_code=303)


@router.get("/posts/{post_id}/status", response_class=HTMLResponse)
async def post_status(
    post_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HTMLResponse:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "partials/post_row.html",
        {"post": post, "active_statuses": _ACTIVE_STATUSES},
    )
