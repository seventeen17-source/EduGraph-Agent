"""ChromaDB 向量存储封装 —— 记忆条目的写入与混合检索。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import Settings
from app.memory.schemas import MemoryEntry, MemorySearchResult


def _make_where(student_id: str, node_ids: list[str] | None = None) -> dict[str, Any]:
    """构建 ChromaDB where 过滤条件。

    ChromaDB 0.5.x 仅支持简单的单字段过滤。
    多条件过滤在 Python 侧完成（见 _filter_by_node_ids）。
    """
    return {"student_id": student_id}


def _filter_by_node_ids(
    results: dict,
    node_ids: list[str],
) -> dict:
    """在 Python 侧按 node_ids 过滤 ChromaDB 结果。

    node_ids 在 metadata 中以 JSON 字符串存储，
    匹配任意一个 node_id 即视为命中。
    """
    if not node_ids:
        return results
    metadatas = results.get("metadatas", [[]])[0] or []
    ids = results.get("ids", [[]])[0] or []
    distances = results.get("distances", [[]])[0] or []
    documents = results.get("documents", [[]])[0] or []

    filtered_ids, filtered_metas, filtered_dists, filtered_docs = [], [], [], []
    for i, meta in enumerate(metadatas):
        node_ids_str = meta.get("node_ids", "[]") if meta else "[]"
        try:
            stored_ids: list[str] = json.loads(node_ids_str)
        except (json.JSONDecodeError, TypeError):
            stored_ids = []
        if any(nid in stored_ids for nid in node_ids):
            filtered_ids.append(ids[i] if i < len(ids) else "")
            filtered_metas.append(meta)
            if i < len(distances):
                filtered_dists.append(distances[i])
            if i < len(documents):
                filtered_docs.append(documents[i])

    return {
        "ids": [filtered_ids],
        "metadatas": [filtered_metas],
        "distances": [filtered_dists],
        "documents": [filtered_docs],
    }


class MemoryVectorStore:
    """ChromaDB 记忆向量存储。

    每个 collection 对应一个模型维度（由 embedding model 决定）。
    所有学生的记忆存入同一个 collection，通过 metadata.student_id 隔离。
    """

    COLLECTION_NAME = "learning_memories"

    def __init__(self, settings: Settings, embedding_dim: int = 1536) -> None:
        persist_dir = str(Path(settings.chroma_persist_dir).resolve())
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # 如果维度变了（切换了 embedding 模型），删除旧 collection 重建
        self.embedding_dim = embedding_dim
        self._collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine", "dim": embedding_dim},
        )

    # ── 写入 ──

    async def insert(self, entry: MemoryEntry, embedding: list[float]) -> str:
        """插入一条记忆。"""
        metadata = self._entry_metadata(entry)
        # ChromaDB 的 add 是同步的，用线程池避免阻塞事件循环
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._collection.add(
                ids=[entry.id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[self._format_document(entry)],
            ),
        )
        return entry.id

    async def insert_batch(self, entries: list[MemoryEntry], embeddings: list[list[float]]) -> list[str]:
        """批量插入。"""
        if not entries:
            return []
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._collection.add(
                ids=[e.id for e in entries],
                embeddings=embeddings,
                metadatas=[self._entry_metadata(e) for e in entries],
                documents=[self._format_document(e) for e in entries],
            ),
        )
        return [e.id for e in entries]

    # ── 检索 ──

    async def search_semantic(
        self,
        query_embedding: list[float],
        student_id: str,
        top_k: int = 10,
    ) -> list[MemorySearchResult]:
        """纯语义检索（向量相似度）。"""
        where = _make_where(student_id)
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self._collection.count()),
                where=where,
                include=["metadatas", "documents", "distances"],
            ),
        )
        return self._parse_results(results, semantic_only=True)

    async def search_by_nodes(
        self,
        query_embedding: list[float],
        student_id: str,
        node_ids: list[str],
        top_k: int = 5,
    ) -> list[MemorySearchResult]:
        """按知识点 ID 精确过滤 + 向量相似度排序。

        先用 ChromaDB 做向量检索（仅按 student_id 过滤），
        再在 Python 侧按 node_ids 过滤。
        """
        if not node_ids:
            return []
        where = _make_where(student_id)
        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(
            None,
            lambda: self._collection.query(
                query_embeddings=[query_embedding],
                n_results=max(top_k * 3, 15),
                where=where,
                include=["metadatas", "documents", "distances"],
            ),
        )
        # Python 侧按 node_ids 过滤
        filtered = _filter_by_node_ids(raw, node_ids)
        return self._parse_results(filtered, graph_match=True)[:top_k]

    async def hybrid_search(
        self,
        query_embedding: list[float],
        student_id: str,
        node_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[MemorySearchResult]:
        """混合检索：语义 + 知识点过滤 → 合并去重 → 时间衰减排序。"""
        # 并行执行语义检索和精确检索
        semantic_task = self.search_semantic(query_embedding, student_id, top_k=top_k * 2)

        exact_results: list[MemorySearchResult] = []
        if node_ids:
            exact_results = await self.search_by_nodes(query_embedding, student_id, node_ids, top_k=top_k)

        semantic_results = await semantic_task

        # 合并去重
        seen: set[str] = set()
        merged: list[MemorySearchResult] = []
        for r in exact_results:
            if r.entry.id not in seen:
                seen.add(r.entry.id)
                r.metadata_bonus = 0.3   # 知识点精确匹配 → 高加分
                merged.append(r)

        for r in semantic_results:
            if r.entry.id not in seen:
                seen.add(r.entry.id)
                merged.append(r)

        # 综合重排序
        for r in merged:
            r.score = self._final_score(r)
            r.time_decay = self._time_decay_factor(r.entry.timestamp)

        merged.sort(key=lambda r: r.score, reverse=True)
        return merged[:top_k]

    # ── 维护 ──

    async def delete_stale(self, student_id: str, before: datetime) -> int:
        """删除指定学生指定日期之前的记忆。"""
        where = {"student_id": student_id}
        loop = asyncio.get_running_loop()
        # 先查出所有符合 student_id 的记录
        results = await loop.run_in_executor(
            None,
            lambda: self._collection.get(where=where, include=["metadatas"]),
        )
        to_delete: list[str] = []
        for i, meta in enumerate(results.get("metadatas", []) or []):
            if meta and meta.get("timestamp", ""):
                try:
                    ts = datetime.fromisoformat(meta["timestamp"])
                    if ts < before:
                        to_delete.append(results["ids"][i])
                except (ValueError, IndexError):
                    pass
        if to_delete:
            await loop.run_in_executor(None, lambda: self._collection.delete(ids=to_delete))
        return len(to_delete)

    async def count(self, student_id: str | None = None) -> int:
        """统计记忆数量。"""
        loop = asyncio.get_running_loop()
        if student_id:
            result = await loop.run_in_executor(
                None,
                lambda: self._collection.get(
                    where={"student_id": student_id}, include=[]
                ),
            )
        else:
            result = await loop.run_in_executor(
                None,
                lambda: self._collection.get(include=[]),
            )
        return len(result.get("ids", []) or [])

    # ── 内部工具 ──

    def _format_document(self, entry: MemoryEntry) -> str:
        """生成嵌入文本 — 这是向量相似度判断的依据。"""
        parts = [
            f"[{entry.intent}] 学生问题：{entry.student_question_summary}",
            f"助教回复：{entry.agent_response_summary}",
        ]
        if entry.key_insight:
            parts.append(f"关键发现：{entry.key_insight}")
        if entry.confusion_nodes:
            parts.append(f"困惑点：{', '.join(entry.confusion_nodes)}")
        if entry.learning_preference_hint:
            parts.append(f"偏好：{entry.learning_preference_hint}")
        return " | ".join(parts)

    def _entry_metadata(self, entry: MemoryEntry) -> dict[str, Any]:
        return {
            "student_id": entry.student_id,
            "conversation_id": entry.conversation_id,
            "timestamp": entry.timestamp.isoformat(),
            "intent": entry.intent,
            "node_ids": json.dumps(entry.node_ids, ensure_ascii=False),
            "confusion_nodes": json.dumps(entry.confusion_nodes, ensure_ascii=False),
            "engagement_level": entry.engagement_level,
            # 关键摘要字段（供 _meta_to_entry 恢复）
            "student_question_summary": entry.student_question_summary[:200] if entry.student_question_summary else "",
            "agent_response_summary": entry.agent_response_summary[:200] if entry.agent_response_summary else "",
            "key_insight": entry.key_insight[:200] if entry.key_insight else "",
            "learning_preference_hint": entry.learning_preference_hint[:200] if entry.learning_preference_hint else "",
            "suggested_follow_up": entry.suggested_follow_up[:200] if entry.suggested_follow_up else "",
            "caution_topics": json.dumps(entry.caution_topics, ensure_ascii=False),
        }

    def _parse_results(
        self,
        raw: dict,
        semantic_only: bool = False,
        graph_match: bool = False,
    ) -> list[MemorySearchResult]:
        results: list[MemorySearchResult] = []
        ids = raw.get("ids", [[]])[0] or []
        distances = raw.get("distances", [[]])[0] or []
        metadatas = raw.get("metadatas", [[]])[0] or []
        documents = raw.get("documents", [[]])[0] or []

        for i, mem_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            semantic_score = 1.0 - distance  # cosine distance → similarity

            entry = self._meta_to_entry(mem_id, meta)
            results.append(MemorySearchResult(
                entry=entry,
                score=semantic_score,
                semantic_score=round(semantic_score, 4),
                metadata_bonus=0.0 if semantic_only else 0.15,
                graph_bonus=0.2 if graph_match else 0.0,
                time_decay=self._time_decay_factor(entry.timestamp),
            ))
        return results

    def _meta_to_entry(self, mem_id: str, meta: dict) -> MemoryEntry:
        def _parse_json(raw, default=None):
            if default is None:
                default = []
            if isinstance(raw, list):
                return raw
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    return default
            return raw if raw else default

        node_ids = _parse_json(meta.get("node_ids", "[]"))
        confusion_nodes = _parse_json(meta.get("confusion_nodes", "[]"))
        caution_topics = _parse_json(meta.get("caution_topics", "[]"))

        ts_str = meta.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()

        return MemoryEntry(
            id=mem_id,
            student_id=meta.get("student_id", ""),
            conversation_id=meta.get("conversation_id", ""),
            timestamp=timestamp,
            node_ids=node_ids or [],
            intent=meta.get("intent", ""),
            confusion_nodes=confusion_nodes or [],
            engagement_level=meta.get("engagement_level", "medium"),
            student_question_summary=meta.get("student_question_summary", ""),
            agent_response_summary=meta.get("agent_response_summary", ""),
            key_insight=meta.get("key_insight", ""),
            learning_preference_hint=meta.get("learning_preference_hint", ""),
            suggested_follow_up=meta.get("suggested_follow_up", ""),
            caution_topics=caution_topics or [],
        )

    def _time_decay_factor(self, timestamp: datetime) -> float:
        """时间衰减因子：越旧的记忆权重越低。"""
        days = (datetime.utcnow() - timestamp).total_seconds() / 86400.0
        return round(0.9 ** days, 4)

    def _final_score(self, result: MemorySearchResult) -> float:
        """综合评分：语义相似度 0.5 + 元数据匹配 0.3 + 图谱匹配 0.2，再乘以时间衰减。"""
        base = (
            result.semantic_score * 0.5
            + result.metadata_bonus * 1.0   # 元数据加分按原值
            + result.graph_bonus * 1.0      # 图谱加分按原值
        )
        return round(base * result.time_decay, 4)
