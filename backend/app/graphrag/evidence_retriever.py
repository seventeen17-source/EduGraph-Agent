from app.graph.expansion_policy import GraphExpansionPolicy
from app.graph.models import GraphNode
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.ranking import rank_nodes_by_profile
from app.graphrag.schemas import EvidencePackage, StudentProfileInput


class EvidenceRetriever:
    """Collects explainable graph evidence around one resolved KnowledgePoint."""

    def __init__(self, graph_store: Neo4jGraphStore, policy: GraphExpansionPolicy) -> None:
        self.graph_store = graph_store
        self.policy = policy

    async def retrieve(
        self,
        query: str,
        center_uid: str,
        student_profile: StudentProfileInput | None = None,
    ) -> EvidencePackage:
        profile = student_profile or StudentProfileInput()
        center = await self.graph_store.get_node(center_uid)
        if center is None:
            return EvidencePackage(
                query=query,
                resolved_uid=center_uid,
                uncertainty=["center_node_not_found"],
                missing_evidence=["center_node"],
            )

        prerequisites = await self.graph_store.get_prerequisites(
            center_uid,
            depth=self.policy.clamp_depth(),
            limit=self.policy.max_prerequisites,
        )
        related_nodes = await self.graph_store.get_related_nodes(
            center_uid,
            limit=self.policy.max_related_nodes,
        )
        exercises = await self.graph_store.get_exercises_for_node(
            center_uid,
            limit=self.policy.max_exercises,
        )
        document_chunks = await self.graph_store.get_document_chunks_for_node(
            center_uid,
            limit=self.policy.max_document_chunks,
        )
        code_cases = await self.graph_store.get_code_cases_for_node(
            center_uid,
            limit=self.policy.max_code_cases,
        )
        misconceptions = await self.graph_store.get_misconceptions_for_node(center_uid)
        sources = await self._collect_sources(center, exercises, document_chunks, code_cases)
        subgraph = await self.graph_store.get_subgraph(
            center_uid,
            relation_types=self.policy.graphrag_relations,
            depth=self.policy.clamp_depth(),
            limit=self.policy.max_subgraph_items,
        )

        exercises = rank_nodes_by_profile(exercises, profile.weak_points)
        missing = []
        if not document_chunks:
            missing.append("document_chunks")
        if not code_cases:
            missing.append("code_cases")
        if not misconceptions:
            missing.append("misconceptions")

        return EvidencePackage(
            query=query,
            resolved_uid=center_uid,
            center_node=center,
            prerequisites=prerequisites,
            related_nodes=related_nodes,
            exercises=exercises,
            document_chunks=document_chunks,
            code_cases=code_cases,
            misconceptions=misconceptions,
            graph_paths=subgraph.paths,
            sources=sources,
            ranking_reason=self._ranking_reason(profile, exercises, document_chunks),
            student_profile_adaptation={
                "weak_points": profile.weak_points,
                "preferences": profile.preferences,
                "goal": profile.goal,
            },
            missing_evidence=missing,
        )

    async def _collect_sources(
        self,
        center: GraphNode,
        exercises: list[GraphNode],
        document_chunks: list[GraphNode],
        code_cases: list[GraphNode],
    ) -> list[GraphNode]:
        seen: dict[str, GraphNode] = {}
        for node in [center, *exercises, *document_chunks, *code_cases]:
            for source in await self.graph_store.get_sources_for_entity(node.uid, limit=self.policy.max_sources):
                seen[source.uid] = source
        return list(seen.values())

    def _ranking_reason(
        self,
        profile: StudentProfileInput,
        exercises: list[GraphNode],
        document_chunks: list[GraphNode],
    ) -> list[str]:
        reasons = ["使用 Neo4j 图谱中的知识关系、资源关系和来源关系构建证据包。"]
        if profile.weak_points:
            reasons.append("根据 weak_points 对练习题和相关证据进行优先排序。")
        if not document_chunks:
            reasons.append("当前 DocumentChunk 数量较少，MVP 阶段更依赖题目、前置链和来源链。")
        elif document_chunks:
            reasons.append("已纳入 SUPPORTS 文档块作为知识解释证据。")
        if exercises:
            reasons.append("已纳入 ASSESSES 题目用于诊断和练习推荐。")
        return reasons
