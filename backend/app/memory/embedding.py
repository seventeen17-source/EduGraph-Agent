"""Embedding 服务 —— 调用 OpenAI 兼容的 embedding API。"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import Settings


class EmbeddingService:
    """生成文本向量嵌入。

    优先使用专用的 embedding_api_key / embedding_base_url，
    若未配置则回退到 LLM 的 api_key / base_url。
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        api_key = settings.embedding_api_key or settings.llm_api_key
        base_url = settings.embedding_base_url or settings.llm_base_url or None
        self.client: AsyncOpenAI | None = None
        if api_key:
            kwargs: dict = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = AsyncOpenAI(**kwargs)  # type: ignore[arg-type]
        self.model = settings.embedding_model

    async def embed(self, text: str) -> list[float]:
        """将文本嵌入为向量。"""
        if self.client is None:
            raise RuntimeError("Embedding API key is not configured; semantic retrieval is disabled.")
        text = text.strip()
        if not text:
            return [0.0] * self.embedding_dim()
        # 截断过长文本（embedding 模型通常有 token 上限）
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars]
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入。"""
        if self.client is None:
            raise RuntimeError("Embedding API key is not configured; semantic retrieval is disabled.")
        if not texts:
            return []
        texts = [t.strip()[:8000] for t in texts]
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embedding_dim(self) -> int:
        """返回当前模型的向量维度。"""
        dims: dict[str, int] = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "BAAI/bge-m3": 1024,
            "Pro/BAAI/bge-m3": 1024,
            "BAAI/bge-large-zh-v1.5": 1024,
            "BAAI/bge-large-en-v1.5": 1024,
            "Qwen/Qwen3-Embedding-0.6B": 1024,
            "Qwen/Qwen3-Embedding-4B": 2560,
            "Qwen/Qwen3-Embedding-8B": 4096,
            "Qwen/Qwen3-VL-Embedding-8B": 4096,
        }
        return dims.get(self.model, 1536)
