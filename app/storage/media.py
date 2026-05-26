from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MiB


class MediaError(Exception):
    pass


class MediaStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, original_filename: str | None) -> tuple[str, str, int]:
        if len(data) > MAX_BYTES:
            raise MediaError(f"Image exceeds {MAX_BYTES} bytes")
        mime = self._guess_mime(original_filename, data)
        if mime not in ALLOWED_MIME:
            raise MediaError(f"Unsupported mime type: {mime}")
        ext = mimetypes.guess_extension(mime) or ".bin"
        rel = f"{uuid.uuid4()}{ext}"
        (self.root / rel).write_bytes(data)
        return rel, mime, len(data)

    def absolute_path(self, local_path: str) -> Path:
        return self.root / local_path

    @staticmethod
    def _guess_mime(filename: str | None, data: bytes) -> str:
        if filename:
            mime, _ = mimetypes.guess_type(filename)
            if mime:
                return mime
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        return "application/octet-stream"
