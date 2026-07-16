from __future__ import annotations

import asyncio
import base64
import email.utils
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.image_generation.schemas import ImageGenerationPayload


class XunfeiHiDreamClient:
    """Client for Xunfei HiDream async image generation API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(
            self.settings.xunfei_hidream_enabled
            and self._app_id
            and self._api_key
            and self._api_secret
            and self.settings.xunfei_hidream_create_endpoint
            and self.settings.xunfei_hidream_query_endpoint
        )

    async def generate_base64(self, payload: ImageGenerationPayload) -> str:
        if not self.is_configured():
            raise ServiceUnavailableError(
                "XUNFEI_HIDREAM_APP_ID / XUNFEI_HIDREAM_API_KEY / XUNFEI_HIDREAM_API_SECRET are required for HiDream image generation."
            )

        async with httpx.AsyncClient(timeout=120) as client:
            task_id = await self._create_task(client, payload)
            result = await self._poll_result(client, task_id)
            image_ref = _extract_image_reference(result)
            if not image_ref:
                raise ServiceUnavailableError("HiDream query returned no image url or base64 payload.")
            return await self._resolve_image_base64(client, image_ref)

    @property
    def _app_id(self) -> str | None:
        return self.settings.xunfei_hidream_app_id or self.settings.xunfei_tti_app_id

    @property
    def _api_key(self) -> str | None:
        return self.settings.xunfei_hidream_api_key or self.settings.xunfei_tti_api_key

    @property
    def _api_secret(self) -> str | None:
        return self.settings.xunfei_hidream_api_secret or self.settings.xunfei_tti_api_secret

    async def _create_task(self, client: httpx.AsyncClient, payload: ImageGenerationPayload) -> str:
        response = await client.post(
            self._signed_url(self.settings.xunfei_hidream_create_endpoint),
            json=self._create_request_body(payload),
        )
        response.raise_for_status()
        data = response.json()
        self._raise_for_error(data, stage="create")
        task_id = _extract_header(data).get("task_id")
        if not task_id:
            raise ServiceUnavailableError("HiDream create response did not include task_id.")
        return str(task_id)

    async def _poll_result(self, client: httpx.AsyncClient, task_id: str) -> Any:
        attempts = max(1, int(self.settings.xunfei_hidream_poll_attempts or 25))
        interval = max(0.5, float(self.settings.xunfei_hidream_poll_interval_seconds or 2.0))

        last_data: dict[str, Any] | None = None
        for attempt in range(attempts):
            response = await client.post(
                self._signed_url(self.settings.xunfei_hidream_query_endpoint),
                json={
                    "header": {
                        "app_id": self._app_id,
                        "task_id": task_id,
                    }
                },
            )
            response.raise_for_status()
            data = response.json()
            last_data = data
            self._raise_for_error(data, stage="query")
            header = _extract_header(data)
            task_status = str(header.get("task_status") or "")
            if task_status in {"3", "4"}:
                return _decode_query_result(data)
            if attempt < attempts - 1:
                await asyncio.sleep(interval)

        status = ""
        if last_data:
            status = str(_extract_header(last_data).get("task_status") or "")
        raise ServiceUnavailableError(f"HiDream task timed out before completion. task_id={task_id}, status={status}")

    def _signed_url(self, endpoint: str) -> str:
        parsed = urlparse(endpoint)
        host = parsed.netloc
        path = parsed.path or "/"
        date = email.utils.format_datetime(datetime.now(timezone.utc), usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
        signature_sha = hmac.new(
            str(self._api_secret).encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self._api_key}", '
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

    def _create_request_body(self, payload: ImageGenerationPayload) -> dict[str, Any]:
        text_payload = {
            "image": [],
            "prompt": payload.prompt,
            "aspect_ratio": self.settings.xunfei_hidream_aspect_ratio or "1:1",
            "negative_prompt": payload.negative_prompt or "",
            "img_count": 1,
            "resolution": self.settings.xunfei_hidream_resolution or "2k",
        }
        text = base64.b64encode(
            json.dumps(text_payload, ensure_ascii=False).encode("utf-8")
        ).decode("utf-8")
        return {
            "header": {
                "app_id": self._app_id,
                "status": 3,
                "channel": "default",
                "callback_url": "default",
            },
            "parameter": {
                "oig": {
                    "result": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json",
                    }
                }
            },
            "payload": {
                "oig": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "json",
                    "status": 3,
                    "text": text,
                }
            },
        }

    async def _resolve_image_base64(self, client: httpx.AsyncClient, image_ref: str) -> str:
        text = image_ref.strip()
        if text.startswith("data:image/") or _looks_like_base64_image(text):
            return text
        if text.startswith(("http://", "https://")):
            response = await client.get(text)
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "image/png").split(";", 1)[0]
            encoded = base64.b64encode(response.content).decode("utf-8")
            return f"data:{mime_type};base64,{encoded}"
        raise ServiceUnavailableError("HiDream image result is neither URL nor base64 image data.")

    @staticmethod
    def _raise_for_error(data: dict[str, Any], *, stage: str) -> None:
        header = _extract_header(data)
        code = header.get("code")
        if code not in (None, 0, "0"):
            message = header.get("message") or header.get("sid") or code
            raise ServiceUnavailableError(f"HiDream {stage} failed: {message}")


def _extract_header(data: dict[str, Any]) -> dict[str, Any]:
    header = data.get("header")
    return header if isinstance(header, dict) else {}


def _decode_query_result(data: dict[str, Any]) -> Any:
    payload = data.get("payload") or {}
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        raise ServiceUnavailableError("HiDream query response missing payload.result.")
    text = str(result.get("text") or "").strip()
    if not text:
        raise ServiceUnavailableError("HiDream query response payload.result.text is empty.")
    decoded = base64.b64decode(text, validate=False).decode("utf-8", errors="replace")
    decoded = decoded.strip()
    try:
        return json.loads(decoded)
    except json.JSONDecodeError:
        return decoded


def _extract_image_reference(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("http://", "https://", "data:image/")) or _looks_like_base64_image(text):
            return text
        return ""
    if isinstance(value, list):
        for item in value:
            found = _extract_image_reference(item)
            if found:
                return found
        return ""
    if not isinstance(value, dict):
        return ""

    preferred_keys = (
        "url",
        "image_url",
        "imageUrl",
        "image",
        "image_base64",
        "base64",
        "content",
        "data",
        "result",
        "images",
    )
    for key in preferred_keys:
        if key not in value:
            continue
        found = _extract_image_reference(value.get(key))
        if found:
            return found
    for nested in value.values():
        found = _extract_image_reference(nested)
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
