import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.storage.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PostState(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    publishing = "publishing"
    done = "done"
    failed = "failed"


class PlatformPostStatus(str, enum.Enum):
    pending = "pending"
    scheduled = "scheduled"
    queued = "queued"
    publishing = "publishing"
    succeeded = "succeeded"
    failed = "failed"
    permanently_failed = "permanently_failed"
    cancelled = "cancelled"


class Platform(str, enum.Enum):
    telegram = "telegram"
    linkedin = "linkedin"


class Media(Base):
    __tablename__ = "media"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_media_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media.id"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    state: Mapped[PostState] = mapped_column(
        SAEnum(PostState, name="post_state"), nullable=False, default=PostState.draft
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    image: Mapped[Media | None] = relationship("Media", lazy="selectin")
    platform_posts: Mapped[list["PlatformPost"]] = relationship(
        back_populates="post", lazy="selectin", cascade="all, delete-orphan"
    )


class PlatformPost(Base):
    __tablename__ = "platform_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id"), nullable=False)
    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform, name="platform"), nullable=False
    )
    text_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PlatformPostStatus] = mapped_column(
        SAEnum(PlatformPostStatus, name="platform_post_status"),
        nullable=False,
        default=PlatformPostStatus.pending,
    )
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, default=_uuid)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    post: Mapped[Post] = relationship(back_populates="platform_posts")
