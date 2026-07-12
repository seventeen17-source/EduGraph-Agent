from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import Settings
from app.rag.schemas import CourseSemanticHit, CourseSemanticView


class CourseVectorStore:
    """Chroma-backed semantic index for course retrieval views."""

    COLLECTION_NAME = "course_semantic_views"

    def __init__(self, settings: Settings, embedding_dim: int = 1536) -> None:
        persist_dir = str(Path(settings.chroma_persist_dir).resolve())
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embedding_dim = embedding_dim
        self._collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine", "dim": embedding_dim},
        )

    async def replace_all(self, views: list[CourseSemanticView], embeddings: list[list[float]]) -> int:
        if len(views) != len(embeddings):
            raise ValueError("views and embeddings length mismatch")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.client.delete_collection(self.COLLECTION_NAME))
        self._collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine", "dim": self.embedding_dim},
        )
        if not views:
            return 0

        await loop.run_in_executor(
            None,
            lambda: self._collection.add(
                ids=[view.id for view in views],
                embeddings=embeddings,
                documents=[view.text for view in views],
                metadatas=[self._metadata(view) for view in views],
            ),
        )
        return len(views)

    async def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 12,
        candidate_node_ids: list[str] | None = None,
        weak_points: list[str] | None = None,
        preferences: list[str] | None = None,
    ) -> list[CourseSemanticHit]:
        count = await self.count()
        if count <= 0:
            return []
        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(
            None,
            lambda: self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(max(top_k * 4, top_k), count),
                include=["metadatas", "documents", "distances"],
            ),
        )
        hits = self._parse_results(raw)
        return self._rerank(
            hits,
            top_k=top_k,
            candidate_node_ids=candidate_node_ids or [],
            weak_points=weak_points or [],
            preferences=preferences or [],
        )

    async def count(self) -> int:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._collection.count)

    def _parse_results(self, raw: dict[str, Any]) -> list[CourseSemanticHit]:
        ids = raw.get("ids", [[]])[0] or []
        metadatas = raw.get("metadatas", [[]])[0] or []
        documents = raw.get("documents", [[]])[0] or []
        distances = raw.get("distances", [[]])[0] or []
        hits: list[CourseSemanticHit] = []
        for idx, view_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            text = documents[idx] if idx < len(documents) else ""
            distance = distances[idx] if idx < len(distances) else 1.0
            view = self._view_from_metadata(str(view_id), text, metadata or {})
            semantic_score = max(0.0, min(1.0, 1.0 - float(distance)))
            hits.append(
                CourseSemanticHit(
                    view=view,
                    score=semantic_score,
                    semantic_score=round(semantic_score, 4),
                    rank_reason=["语义相似度匹配"],
                )
            )
        return hits

    def _rerank(
        self,
        hits: list[CourseSemanticHit],
        *,
        top_k: int,
        candidate_node_ids: list[str],
        weak_points: list[str],
        preferences: list[str],
    ) -> list[CourseSemanticHit]:
        candidate_set = set(candidate_node_ids)
        weak_set = set(weak_points)
        prefer_code = "code_case" in preferences or "code" in preferences
        prefer_exercise = "exercise" in preferences
        prefer_document = "document" in preferences or "diagram" in preferences

        for hit in hits:
            view = hit.view
            node_overlap = candidate_set.intersection(view.node_ids)
            weak_overlap = weak_set.intersection(view.node_ids)
            graph_bonus = 0.0
            profile_bonus = 0.0
            if view.target_uid in candidate_set or node_overlap:
                graph_bonus += 0.22
                hit.rank_reason.append("命中图谱扩展节点范围")
            if weak_overlap:
                profile_bonus += 0.18
                hit.rank_reason.append("命中学生薄弱知识点")
            if prefer_code and view.view_type == "code_intent":
                profile_bonus += 0.08
                hit.rank_reason.append("匹配代码案例偏好")
            if prefer_exercise and view.view_type == "error_diagnosis":
                profile_bonus += 0.08
                hit.rank_reason.append("匹配练习/错题偏好")
            if prefer_document and view.view_type in {"concept_explanation", "raw_summary"}:
                profile_bonus += 0.05
                hit.rank_reason.append("匹配讲解资源偏好")

            hit.graph_bonus = round(graph_bonus, 4)
            hit.profile_bonus = round(profile_bonus, 4)
            hit.score = round(hit.semantic_score * 0.7 + graph_bonus + profile_bonus, 4)

        hits.sort(key=lambda item: (item.score, item.semantic_score), reverse=True)
        return hits[:top_k]

    @staticmethod
    def _metadata(view: CourseSemanticView) -> dict[str, Any]:
        return {
            "target_uid": view.target_uid,
            "target_type": view.target_type,
            "view_type": view.view_type,
            "node_ids": json.dumps(view.node_ids, ensure_ascii=False),
            "chapter_id": view.chapter_id,
            "source_uids": json.dumps(view.source_uids, ensure_ascii=False),
            "title": view.title,
            "difficulty": view.difficulty if view.difficulty is not None else "",
            "cognitive_level": view.cognitive_level,
            "tags": json.dumps(view.tags, ensure_ascii=False),
        }

    @staticmethod
    def _view_from_metadata(view_id: str, text: str, metadata: dict[str, Any]) -> CourseSemanticView:
        def _json_list(key: str) -> list[str]:
            raw = metadata.get(key, "[]")
            if isinstance(raw, list):
                return [str(item) for item in raw]
            try:
                return [str(item) for item in json.loads(str(raw or "[]"))]
            except Exception:
                return []

        raw_difficulty = metadata.get("difficulty")
        difficulty = int(raw_difficulty) if str(raw_difficulty).isdigit() else None
        return CourseSemanticView(
            id=view_id,
            text=text,
            target_uid=str(metadata.get("target_uid", "")),
            target_type=str(metadata.get("target_type", "KnowledgePoint")),  # type: ignore[arg-type]
            view_type=str(metadata.get("view_type", "raw_summary")),  # type: ignore[arg-type]
            node_ids=_json_list("node_ids"),
            chapter_id=str(metadata.get("chapter_id", "")),
            source_uids=_json_list("source_uids"),
            title=str(metadata.get("title", "")),
            difficulty=difficulty,
            cognitive_level=str(metadata.get("cognitive_level", "")),
            tags=_json_list("tags"),
        )
