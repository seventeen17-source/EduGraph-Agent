from pydantic import BaseModel, Field

from app.graph.llm_resolver import HeuristicLLMResolverClient, LLMResolverClient, QueryUnderstanding
from app.graph.models import GraphNode
from app.graph.neo4j_store import Neo4jGraphStore


class NodeResolution(BaseModel):
    query: str
    normalized_query: str | None = None
    intent: str = "unknown"
    resolved_uid: str | None = None
    candidates: list[GraphNode] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    llm_understanding: QueryUnderstanding | None = None


class NodeResolver:
    """Two-layer resolver: rule recall first, LLM-style rewrite/classification/rerank second."""

    def __init__(
        self,
        graph_store: Neo4jGraphStore,
        llm_client: LLMResolverClient | None = None,
    ) -> None:
        self.graph_store = graph_store
        self.llm_client = llm_client or HeuristicLLMResolverClient()

    async def resolve(
        self,
        query: str,
        weak_points: list[str] | None = None,
    ) -> NodeResolution:
        normalized = query.strip()
        weak_points = weak_points or []
        if not normalized:
            return NodeResolution(query=query, uncertainty=["empty_query"])

        direct_node = await self.graph_store.get_node(normalized)
        if direct_node and "KnowledgePoint" in direct_node.labels:
            return NodeResolution(
                query=query,
                normalized_query=normalized,
                intent="direct_uid_lookup",
                resolved_uid=direct_node.uid,
                candidates=[direct_node],
            )

        candidates = await self._rule_recall(normalized, limit=10)
        candidates = self._rank_candidates(normalized, candidates, weak_points)
        understanding = await self.llm_client.understand_query(normalized, candidates, weak_points)
        if not candidates and understanding.normalized_query != normalized:
            candidates = await self._rule_recall(understanding.normalized_query, limit=10)
            candidates = self._rank_candidates(understanding.normalized_query, candidates, weak_points)
            understanding = await self.llm_client.understand_query(normalized, candidates, weak_points)
        if not candidates and understanding.possible_nodes:
            candidates = await self._nodes_from_possible_uids(understanding.possible_nodes)
            candidates = self._rank_candidates(understanding.normalized_query, candidates, weak_points)
            understanding = await self.llm_client.understand_query(normalized, candidates, weak_points)

        candidates = self._apply_llm_rerank(candidates, understanding.reranked_nodes)
        if not candidates:
            return NodeResolution(
                query=query,
                normalized_query=understanding.normalized_query,
                intent=understanding.intent,
                uncertainty=["no_matching_knowledge_point"],
                llm_understanding=understanding,
            )

        return NodeResolution(
            query=query,
            normalized_query=understanding.normalized_query,
            intent=understanding.intent,
            resolved_uid=candidates[0].uid,
            candidates=candidates,
            uncertainty=["multiple_candidates"] if len(candidates) > 1 else [],
            llm_understanding=understanding,
        )

    async def _rule_recall(self, query: str, limit: int) -> list[GraphNode]:
        return await self.graph_store.search_knowledge_points(query, limit=limit)

    async def _nodes_from_possible_uids(self, possible_uids: list[str]) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        for uid in possible_uids:
            node = await self.graph_store.get_node(uid)
            if node and "KnowledgePoint" in node.labels:
                nodes.append(node)
        return nodes

    def _rank_candidates(
        self,
        query: str,
        candidates: list[GraphNode],
        weak_points: list[str],
    ) -> list[GraphNode]:
        lowered = query.lower()

        def score(node: GraphNode) -> tuple[int, str]:
            props = node.properties
            value = 0
            if node.uid in weak_points:
                value += 20
            if lowered == node.uid.lower():
                value += 100
            if lowered in str(props.get("name", "")).lower():
                value += 50
            if any(lowered in str(alias).lower() for alias in props.get("aliases", [])):
                value += 40
            if any(str(keyword).lower() in lowered for keyword in props.get("keywords", [])):
                value += 30
            return (-value, node.uid)

        return sorted(candidates, key=score)

    def _apply_llm_rerank(
        self,
        candidates: list[GraphNode],
        reranked_uids: list[str],
    ) -> list[GraphNode]:
        if not candidates or not reranked_uids:
            return candidates
        by_uid = {node.uid: node for node in candidates}
        ordered = [by_uid[uid] for uid in reranked_uids if uid in by_uid]
        remaining = [node for node in candidates if node.uid not in reranked_uids]
        return ordered + remaining
