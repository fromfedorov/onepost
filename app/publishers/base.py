from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublishRequest:
    text: str
    image_path: str | None
    idempotency_key: str


@dataclass(frozen=True)
class PublishResult:
    external_id: str
    external_url: str | None = None


class PublishError(Exception):
    def __init__(
        self,
        message: str,
        *,
        transient: bool,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.transient = transient
        self.retry_after = retry_after


class Publisher(Protocol):
    platform_id: str
    display_name: str

    async def publish(self, req: PublishRequest) -> PublishResult: ...

    async def healthcheck(self) -> bool: ...
