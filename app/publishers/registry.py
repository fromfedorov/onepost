from __future__ import annotations

from app.publishers.base import Publisher


class PublisherRegistry:
    def __init__(self) -> None:
        self._publishers: dict[str, Publisher] = {}

    def register(self, publisher: Publisher) -> None:
        self._publishers[publisher.platform_id] = publisher

    def get(self, platform_id: str) -> Publisher | None:
        return self._publishers.get(platform_id)

    def all(self) -> list[Publisher]:
        return list(self._publishers.values())
