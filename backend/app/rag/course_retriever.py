from __future__ import annotations

from app.core.config import Settings
from app.memory.embedding import EmbeddingService
from app.rag.course_vector_store import CourseVectorStore
from app.rag.schemas import CourseSemanticHit


class CourseSemanticRetriever:
    """Semantic entry retriever for course evidence views."""

    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService | None = None,
        vector_store: CourseVectorStore | None = None,
    ) -> None:
        self.settings = settings
        self.embedding_service = embedding_service or EmbeddingService(settings)
        self.vector_store = vector_store or CourseVectorStore(
            settings,
            embedding_dim=self.embedding_service.embedding_dim(),
        )

    async def search(
        self,
        query: str,
        *,
        candidate_node_ids: list[str] | None = None,
        weak_points: list[str] | None = None,
        preferences: list[str] | None = None,
        top_k: int = 10,
    ) -> list[CourseSemanticHit]:
        if not query.strip():
            return []
        embedding = await self.embedding_service.embed(query)
        if not any(embedding):
            return []
        return await self.vector_store.query(
            embedding,
            top_k=top_k,
            candidate_node_ids=candidate_node_ids or [],
            weak_points=weak_points or [],
            preferences=preferences or [],
        )
