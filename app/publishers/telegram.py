from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from app.publishers.base import PublishError, PublishRequest, PublishResult

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096


class TelegramPublisher:
    platform_id = "telegram"
    display_name = "Telegram"

    def __init__(
        self,
        bot_token: str,
        channel_id: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not bot_token:
            raise ValueError("Telegram bot token is empty")
        if not channel_id:
            raise ValueError("Telegram channel id is empty")
        self._bot_token = bot_token
        self._channel_id = channel_id
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=20.0, pool=5.0)
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _url(self, method: str) -> str:
        return f"{API_BASE}/bot{self._bot_token}/{method}"

    async def publish(self, req: PublishRequest) -> PublishResult:
        if req.image_path is None:
            return await self._send_text(req.text)

        if len(req.text) <= CAPTION_LIMIT:
            return await self._send_photo(req.image_path, caption=req.text)

        # Image + long text: photo first (anchors the post), then text follow-up.
        photo_result = await self._send_photo(req.image_path, caption=None)
        await self._send_text(req.text, reply_to=int(photo_result.external_id))
        return photo_result

    async def _send_text(self, text: str, reply_to: int | None = None) -> PublishResult:
        if len(text) > MESSAGE_LIMIT:
            raise PublishError(
                f"Text exceeds Telegram limit of {MESSAGE_LIMIT} characters",
                transient=False,
            )
        payload: dict[str, Any] = {"chat_id": self._channel_id, "text": text}
        if reply_to is not None:
            payload["reply_parameters"] = {"message_id": reply_to}
        data = await self._call("sendMessage", json=payload)
        return self._result_from_message(data["result"])

    async def _send_photo(self, image_path: str, caption: str | None) -> PublishResult:
        path = Path(image_path)
        mime, _ = mimetypes.guess_type(path.name)
        files = {"photo": (path.name, path.read_bytes(), mime or "image/jpeg")}
        form: dict[str, str] = {"chat_id": str(self._channel_id)}
        if caption:
            form["caption"] = caption
        data = await self._call("sendPhoto", data=form, files=files)
        return self._result_from_message(data["result"])

    async def _call(self, method: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.post(self._url(method), **kwargs)
        except httpx.RequestError as exc:
            raise PublishError(f"network error: {exc}", transient=True) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise PublishError(
                f"non-JSON response (status={response.status_code})",
                transient=response.status_code >= 500,
            ) from exc

        if body.get("ok") is True:
            return body

        description = str(body.get("description", "unknown error"))
        retry_after = self._extract_retry_after(body)
        is_rate_limited = response.status_code == 429
        is_server_error = response.status_code >= 500
        transient = is_rate_limited or is_server_error

        raise PublishError(
            f"Telegram API error {response.status_code}: {description}",
            transient=transient,
            retry_after=retry_after,
        )

    @staticmethod
    def _extract_retry_after(body: dict[str, Any]) -> float | None:
        params = body.get("parameters")
        if isinstance(params, dict):
            value = params.get("retry_after")
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def _result_from_message(self, message: dict[str, Any]) -> PublishResult:
        message_id = message["message_id"]
        chat = message.get("chat", {})
        url = self._build_url(chat, message_id)
        return PublishResult(external_id=str(message_id), external_url=url)

    @staticmethod
    def _build_url(chat: dict[str, Any], message_id: int) -> str | None:
        username = chat.get("username")
        if username:
            return f"https://t.me/{username}/{message_id}"
        chat_id = chat.get("id")
        if isinstance(chat_id, int) and chat_id < 0:
            # Private channel: -100xxxxxxxxxx → t.me/c/xxxxxxxxxx/<msg>
            short = str(chat_id).removeprefix("-100")
            if short and short.isdigit():
                return f"https://t.me/c/{short}/{message_id}"
        return None

    async def healthcheck(self) -> bool:
        try:
            await self._call("getMe", json={})
            return True
        except PublishError:
            return False
