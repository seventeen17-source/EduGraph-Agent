from pydantic import BaseModel, Field


class ImageGenerationPayload(BaseModel):
    """Provider-neutral image generation request."""

    title: str
    prompt: str
    negative_prompt: str = ""
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)


class StoredImage(BaseModel):
    """Saved image asset returned to resource generation."""

    image_url: str
    local_path: str
    mime_type: str = "image/png"
    width: int | None = None
    height: int | None = None

