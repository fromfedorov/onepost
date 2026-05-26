from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from app.publishers.base import PublishError, PublishRequest
from app.publishers.telegram import TelegramPublisher

Handler = Callable[[httpx.Request], httpx.Response]


def make_publisher(handler: Handler) -> TelegramPublisher:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return TelegramPublisher(bot_token="TEST_TOKEN", channel_id="@chan", client=client)


async def test_send_text_only_calls_send_message() -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 42,
                    "chat": {"id": -1001234567890, "type": "channel", "username": "chan"},
                },
            },
        )

    pub = make_publisher(handler)
    result = await pub.publish(PublishRequest(text="hello", image_path=None, idempotency_key="k"))

    assert result.external_id == "42"
    assert result.external_url == "https://t.me/chan/42"
    assert len(seen) == 1
    assert seen[0].url.path.endswith("/sendMessage")


async def test_send_photo_with_short_caption(tmp_path: Path) -> None:
    image = tmp_path / "pic.jpg"
    image.write_bytes(b"\xff\xd8\xff fake jpg")

    methods: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        methods.append(req.url.path.rsplit("/", 1)[-1])
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 7,
                    "chat": {"id": -1001234567890, "type": "channel", "username": "chan"},
                },
            },
        )

    pub = make_publisher(handler)
    result = await pub.publish(
        PublishRequest(text="short caption", image_path=str(image), idempotency_key="k")
    )

    assert result.external_id == "7"
    assert methods == ["sendPhoto"]


async def test_long_text_with_photo_splits_into_two_calls(tmp_path: Path) -> None:
    image = tmp_path / "pic.jpg"
    image.write_bytes(b"\xff\xd8\xff fake jpg")
    long_text = "x" * 1500

    methods: list[str] = []
    counter = iter(range(100, 200))

    def handler(req: httpx.Request) -> httpx.Response:
        methods.append(req.url.path.rsplit("/", 1)[-1])
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": next(counter),
                    "chat": {"id": -1001234567890, "type": "channel", "username": "chan"},
                },
            },
        )

    pub = make_publisher(handler)
    result = await pub.publish(
        PublishRequest(text=long_text, image_path=str(image), idempotency_key="k")
    )

    assert methods == ["sendPhoto", "sendMessage"]
    assert result.external_id == "100"  # anchored on the photo message


async def test_429_with_retry_after_is_transient() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests",
                "parameters": {"retry_after": 17},
            },
        )

    pub = make_publisher(handler)
    with pytest.raises(PublishError) as exc_info:
        await pub.publish(PublishRequest(text="t", image_path=None, idempotency_key="k"))

    assert exc_info.value.transient is True
    assert exc_info.value.retry_after == 17.0


async def test_400_is_permanent() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"ok": False, "error_code": 400, "description": "Bad Request"}
        )

    pub = make_publisher(handler)
    with pytest.raises(PublishError) as exc_info:
        await pub.publish(PublishRequest(text="t", image_path=None, idempotency_key="k"))

    assert exc_info.value.transient is False


async def test_text_above_telegram_message_limit_is_permanent() -> None:
    pub = make_publisher(lambda req: httpx.Response(200, json={"ok": True}))
    with pytest.raises(PublishError) as exc_info:
        await pub.publish(
            PublishRequest(text="x" * 5000, image_path=None, idempotency_key="k")
        )
    assert exc_info.value.transient is False


async def test_private_channel_builds_url_via_c_prefix() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 9,
                    "chat": {"id": -1001234567890, "type": "channel"},  # no username
                },
            },
        )

    pub = make_publisher(handler)
    result = await pub.publish(PublishRequest(text="x", image_path=None, idempotency_key="k"))
    assert result.external_url == "https://t.me/c/1234567890/9"
