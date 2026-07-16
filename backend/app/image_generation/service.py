from __future__ import annotations

from app.agents.schemas import GeneratedImage
from app.core.config import Settings
from app.image_generation.schemas import ImageGenerationPayload
from app.image_generation.storage import save_base64_image
from app.image_generation.xunfei_hidream import XunfeiHiDreamClient
from app.image_generation.xunfei_tti import XunfeiTTIClient


class ImageGenerationService:
    """Generate and persist educational image assets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = settings.xunfei_image_provider
        self.client = XunfeiHiDreamClient(settings) if self.provider == "hidream" else XunfeiTTIClient(settings)

    async def generate(self, draft: GeneratedImage) -> GeneratedImage:
        payload = ImageGenerationPayload(
            title=draft.title or "学习示意图",
            prompt=draft.prompt,
            negative_prompt=draft.negative_prompt,
            width=draft.width or 1024,
            height=draft.height or 1024,
        )
        image_base64 = await self.client.generate_base64(payload)
        stored = save_base64_image(
            settings=self.settings,
            image_base64=image_base64,
            width=payload.width,
            height=payload.height,
        )
        return GeneratedImage(
            title=draft.title,
            prompt=draft.prompt,
            negative_prompt=draft.negative_prompt,
            image_url=stored.image_url,
            local_path=stored.local_path,
            mime_type=stored.mime_type,
            width=stored.width,
            height=stored.height,
            provider=f"xunfei_{self.provider}",
            source_uids=draft.source_uids,
        )
