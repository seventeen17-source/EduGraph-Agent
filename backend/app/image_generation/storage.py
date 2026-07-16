from __future__ import annotations

import base64
import re
import uuid
from pathlib import Path

from app.core.config import PROJECT_ROOT, Settings
from app.image_generation.schemas import StoredImage


_DATA_URL_RE = re.compile(r"^data:(?P<mime>[-\w.]+/[-\w.+]+);base64,(?P<data>.+)$", re.S)


def resolve_assets_dir(settings: Settings) -> Path:
    raw = Path(settings.generated_assets_dir)
    if raw.is_absolute():
        return raw
    return (PROJECT_ROOT / raw).resolve()


def save_base64_image(
    *,
    settings: Settings,
    image_base64: str,
    prefix: str = "xunfei",
    width: int | None = None,
    height: int | None = None,
) -> StoredImage:
    mime_type = "image/png"
    payload = image_base64.strip()
    match = _DATA_URL_RE.match(payload)
    if match:
        mime_type = match.group("mime")
        payload = match.group("data").strip()

    ext = _mime_to_ext(mime_type)
    binary = base64.b64decode(payload, validate=False)
    image_dir = resolve_assets_dir(settings) / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    file_path = image_dir / file_name
    file_path.write_bytes(binary)

    base_url = settings.generated_assets_base_url.rstrip("/")
    return StoredImage(
        image_url=f"{base_url}/images/{file_name}",
        local_path=str(file_path),
        mime_type=mime_type,
        width=width,
        height=height,
    )


def _mime_to_ext(mime_type: str) -> str:
    mapping = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
    }
    return mapping.get(mime_type.lower(), "png")

