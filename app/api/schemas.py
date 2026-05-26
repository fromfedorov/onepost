from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PlatformId = Literal["telegram", "linkedin"]

PlatformPostStatusId = Literal[
    "pending",
    "scheduled",
    "queued",
    "publishing",
    "succeeded",
    "failed",
    "permanently_failed",
    "cancelled",
]

PostStateId = Literal["draft", "scheduled", "publishing", "done", "failed"]


class PlatformPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: PlatformId
    status: PlatformPostStatusId
    text_override: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    attempts: int
    next_attempt_at: datetime | None = None
    last_error: str | None = None
    updated_at: datetime


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mime_type: str
    size_bytes: int


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    state: PostStateId
    scheduled_at: datetime | None = None
    created_at: datetime
    image: MediaOut | None = None
    platform_posts: list[PlatformPostOut] = Field(default_factory=list)


class PostListOut(BaseModel):
    posts: list[PostOut]


class TelegramConnection(BaseModel):
    configured: bool
    healthy: bool
    channel_id: str | None = None


class LinkedInConnection(BaseModel):
    configured: bool
    connected: bool
    member_name: str | None = None
    refresh_expires_at: datetime | None = None


class ConnectionsOut(BaseModel):
    telegram: TelegramConnection
    linkedin: LinkedInConnection


class ErrorOut(BaseModel):
    error: str
