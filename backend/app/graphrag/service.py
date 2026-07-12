from __future__ import annotations

from app.core.config import get_settings
from app.graph.expansion_policy import GraphExpansionPolicy
from app.graph.llm_resolver import build_llm_resolver_client
from app.graph.neo4j_store import Neo4jGraphStore
from app.graph.node_resolver import NodeResolver
from app.graphrag.evidence_retriever import EvidenceRetriever
from app.graphrag.langgraph import build_hybrid_rag_graph
from app.graphrag.langgraph.nodes import HybridRAGNodes
from app.graphrag.schemas import (
    EvidencePackage,
    SemanticSearchDebugResponse,
    SemanticSearchHitDebug,
    StudentProfileInput,
)
from app.memory.embedding import EmbeddingService
from app.memory.vector_store import MemoryVectorStore
from app.rag.course_retriever import CourseSemanticRetriever


class GraphRAGService:
    def __init__(self, graph_store: Neo4jGraphStore) -> None:
        settings = get_settings()
        embedding_service = EmbeddingService(settings)
        self.graph_store = graph_store
        self.embedding_service: EmbeddingService | None = embedding_service
        self.memory_store: MemoryVectorStore | None = None
        self.policy = GraphExpansionPolicy()
        self.node_resolver = NodeResolver(
            graph_store,
            llm_client=build_llm_resolver_client(settings),
        )
        self.evidence_retriever = EvidenceRetriever(
            graph_store,
            self.policy,
            semantic_retriever=CourseSemanticRetriever(
                settings,
                embedding_service=embedding_service,
            ),
        )
        self.hybrid_rag_nodes = HybridRAGNodes(
            graph_store=graph_store,
            node_resolver=self.node_resolver,
            evidence_retriever=self.evidence_retriever,
            embedding_service=self.embedding_service,
            memory_store=self.memory_store,
        )
        self.hybrid_rag_graph = build_hybrid_rag_graph(self.hybrid_rag_nodes)

    def set_memory_services(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        memory_store: MemoryVectorStore | None = None,
    ) -> None:
        if embedding_service is not None:
            self.embedding_service = embedding_service
            self.hybrid_rag_nodes.embedding_service = embedding_service
        self.memory_store = memory_store
        self.hybrid_rag_nodes.memory_store = memory_store

    async def build_evidence_by_uid(
        self,
        uid: str,
        student_profile: StudentProfileInput | None = None,
        *,
        student_id: str | None = None,
    ) -> EvidencePackage:
        return await self._run_hybrid_rag(
            query_text=uid,
            student_profile=student_profile,
            requested_center_uid=uid,
            student_id=student_id,
        )

    async def query(
        self,
        query_text: str,
        student_profile: StudentProfileInput | None = None,
        *,
        student_id: str | None = None,
    ) -> EvidencePackage:
        return await self._run_hybrid_rag(
            query_text=query_text,
            student_profile=student_profile,
            student_id=student_id,
        )

    async def _run_hybrid_rag(
        self,
        *,
        query_text: str,
        student_profile: StudentProfileInput | None = None,
        requested_center_uid: str | None = None,
        student_id: str | None = None,
    ) -> EvidencePackage:
        final_state = await self.hybrid_rag_graph.ainvoke({
            "query": query_text,
            "student_id": student_id,
            "student_profile": student_profile or StudentProfileInput(),
            "requested_center_uid": requested_center_uid,
            "repair_attempts": 0,
            "max_repair_attempts": 2,
            "warnings": [],
            "trace": [],
        })
        evidence = final_state.get("evidence_package")
        if evidence is None:
            return EvidencePackage(
                query=query_text,
                resolution_quality="none",
                uncertainty=final_state.get("warnings", []),
                missing_evidence=["evidence_package"],
                student_profile_adaptation={
                    "hybrid_rag_quality": final_state.get("quality_report", {}),
                    "hybrid_rag_trace": final_state.get("trace", []),
                },
            )
        return evidence

    async def semantic_search_debug(
        self,
        query_text: str,
        *,
        center_uid: str | None = None,
        student_profile: StudentProfileInput | None = None,
        top_k: int = 10,
    ) -> SemanticSearchDebugResponse:
        """Run course semantic retrieval and expose ranking details for inspection."""

        profile = student_profile or StudentProfileInput()
        warnings: list[str] = []
        resolution_quality = "exact" if center_uid else "none"
        resolved_uid = center_uid

        if not resolved_uid:
            try:
                resolution = await self.node_resolver.resolve(query_text, profile.weak_points)
                resolved_uid = resolution.resolved_uid
                resolution_quality = "exact" if resolved_uid else "none"
                warnings.extend(resolution.uncertainty)
            except Exception as exc:
                resolution_quality = "none"
                warnings.append(f"知识点解析失败，将执行全局语义检索：{type(exc).__name__}: {exc}")

        candidate_node_ids: list[str] = []
        if resolved_uid:
            try:
                center = await self.graph_store.get_node(resolved_uid)
            except Exception as exc:
                center = None
                warnings.append(f"读取中心知识点失败，将执行全局语义检索：{type(exc).__name__}: {exc}")

            if center is None:
                warnings.append(f"未找到中心知识点：{resolved_uid}")
                resolved_uid = None
            else:
                candidate_node_ids = await self._collect_semantic_candidate_nodes(resolved_uid)

        if not candidate_node_ids and profile.weak_points:
            candidate_node_ids = list(dict.fromkeys(profile.weak_points))
            resolution_quality = "fallback"
            warnings.append("未解析到中心知识点，临时使用学生薄弱点约束语义检索。")

        try:
            hits = await self.evidence_retriever.semantic_retriever.search(
                query_text,
                candidate_node_ids=candidate_node_ids,
                weak_points=profile.weak_points,
                preferences=profile.preferences,
                top_k=max(1, min(top_k, 30)),
            ) if self.evidence_retriever.semantic_retriever else []
        except Exception as exc:
            warnings.append(f"语义检索失败：{type(exc).__name__}: {exc}")
            hits = []

        return SemanticSearchDebugResponse(
            query=query_text,
            center_uid=resolved_uid,
            resolution_quality=resolution_quality,
            candidate_node_ids=candidate_node_ids,
            top_k=max(1, min(top_k, 30)),
            hits=[
                SemanticSearchHitDebug(
                    id=hit.view.id,
                    target_uid=hit.view.target_uid,
                    target_type=hit.view.target_type,
                    view_type=hit.view.view_type,
                    title=hit.view.title,
                    text_preview=hit.view.text[:240],
                    node_ids=hit.view.node_ids,
                    chapter_id=hit.view.chapter_id,
                    source_uids=hit.view.source_uids,
                    difficulty=hit.view.difficulty,
                    cognitive_level=hit.view.cognitive_level,
                    tags=hit.view.tags,
                    score=hit.score,
                    semantic_score=hit.semantic_score,
                    graph_bonus=hit.graph_bonus,
                    profile_bonus=hit.profile_bonus,
                    rank_reason=hit.rank_reason,
                )
                for hit in hits
            ],
            warnings=warnings,
        )

    async def _collect_semantic_candidate_nodes(self, center_uid: str) -> list[str]:
        candidate_node_ids: list[str] = [center_uid]
        try:
            prereq_tree = await self.graph_store.get_prerequisite_tree(
                center_uid,
                max_depth=self.policy.max_hop_depth,
                limit_per_level=self.policy.max_prerequisites,
            )
            for path in prereq_tree:
                candidate_node_ids.extend(node.uid for node in path.nodes)
        except Exception:
            pass

        try:
            related_nodes = await self.graph_store.get_related_nodes(
                center_uid,
                limit=self.policy.max_related_nodes,
            )
            for path in related_nodes:
                candidate_node_ids.extend(node.uid for node in path.nodes)
        except Exception:
            pass

        return list(dict.fromkeys([node_id for node_id in candidate_node_ids if node_id]))
