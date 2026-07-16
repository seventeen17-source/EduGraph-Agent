from __future__ import annotations

import base64
import email.utils
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.image_generation.schemas import ImageGenerationPayload


class XunfeiTTIClient:
    """Client for Xunfei Spark text-to-image WebAPI."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(
            self.settings.xunfei_tti_enabled
            and self.settings.xunfei_tti_app_id
            and self.settings.xunfei_tti_api_key
            and self.settings.xunfei_tti_api_secret
            and self.settings.xunfei_tti_endpoint
        )

    async def generate_base64(self, payload: ImageGenerationPayload) -> str:
        if not self.is_configured():
            raise ServiceUnavailableError(
                "XUNFEI_TTI_APP_ID / XUNFEI_TTI_API_KEY / XUNFEI_TTI_API_SECRET are required for image generation."
            )

        signed_url = self._signed_url()
        request_body = self._request_body(payload)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(signed_url, json=request_body)
        response.raise_for_status()
        data = response.json()
        code = _extract_code(data)
        if code not in (None, 0, "0"):
            message = _extract_message(data)
            raise ServiceUnavailableError(f"Xunfei image generation failed: {message or code}")
        image_base64 = _extract_image_base64(data)
        if not image_base64:
            raise ServiceUnavailableError("Xunfei image generation returned no image payload.")
        return image_base64

    def _signed_url(self) -> str:
        endpoint = self.settings.xunfei_tti_endpoint
        parsed = urlparse(endpoint)
        host = parsed.netloc
        path = parsed.path or "/"
        date = email.utils.format_datetime(datetime.now(timezone.utc), usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
        signature_sha = hmac.new(
            str(self.settings.xunfei_tti_api_secret).encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.settings.xunfei_tti_api_key}", '
            'algorithm="hmac-sha256", headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        query = urlencode(
            {
                "authorization": authorization,
                "date": date,
                "host": host,
            },
            quote_via=quote,
        )
        return f"{endpoint}?{query}"

    def _request_body(self, payload: ImageGenerationPayload) -> dict[str, Any]:
        prompt = payload.prompt
        if payload.negative_prompt:
            prompt = f"{prompt}\n\n负面约束：{payload.negative_prompt}"
        return {
            "header": {
                "app_id": self.settings.xunfei_tti_app_id,
                "uid": "edugraph-agent",
            },
            "parameter": {
                "chat": {
                    "domain": "general",
                    "width": payload.width,
                    "height": payload.height,
                }
            },
            "payload": {
                "message": {
                    "text": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ]
                }
            },
        }


def _extract_code(data: dict[str, Any]) -> Any:
    header = data.get("header")
    if isinstance(header, dict):
        return header.get("code")
    return data.get("code")


def _extract_message(data: dict[str, Any]) -> str:
    header = data.get("header")
    if isinstance(header, dict):
        return str(header.get("message") or header.get("sid") or "")
    return str(data.get("message") or data.get("error") or "")


def _extract_image_base64(data: Any) -> str:
    if isinstance(data, str):
        text = data.strip()
        if text.startswith("data:image/") or _looks_like_base64_image(text):
            return text
        return ""
    if isinstance(data, list):
        for item in data:
            found = _extract_image_base64(item)
            if found:
                return found
        return ""
    if not isinstance(data, dict):
        return ""

    preferred_keys = (
        "image",
        "image_base64",
        "base64",
        "content",
        "data",
        "url",
    )
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, str) and (value.startswith("data:image/") or _looks_like_base64_image(value)):
            return value
    for value in data.values():
        found = _extract_image_base64(value)
        if found:
            return found
    return ""


def _looks_like_base64_image(value: str) -> bool:
    text = value.strip()
    if len(text) < 200:
        return False
    if text.startswith(("http://", "https://")):
        return False
    sample = text[:120]
    return all(ch.isalnum() or ch in "+/=\n\r" for ch in sample)

