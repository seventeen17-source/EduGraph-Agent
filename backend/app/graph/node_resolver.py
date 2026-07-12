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

    _QUERY_HINT_ROUTES: tuple[tuple[tuple[str, ...], str, str], ...] = (
        (
            ("常见术语", "基础术语", "基本术语", "机器学习术语", "入门术语", "术语表",
             "基础概念", "基本概念", "机器学习基础", "ML基础", "机器学习入门", "ML入门"),
            "ml_basic_terms",
            "query_hint_lookup",
        ),
        (
            ("训练集", "验证集", "测试集", "数据集划分", "数据划分"),
            "ml_dataset_split",
            "query_hint_lookup",
        ),
        (
            ("有监督", "无监督", "监督学习", "无监督学习"),
            "ml_supervised_unsupervised",
            "query_hint_lookup",
        ),
        (
            ("机器学习的应用", "机器学习应用", "ML应用", "AI应用",
             "深度学习的应用", "深度学习应用", "应用场景", "应用领域"),
            "ml_basic_terms",  # 广域查询 → 引导到基础术语节点查看概述
            "query_hint_lookup",
        ),
    )

    # 宽泛查询关键词 — 匹配到这些的直接返回无匹配（不强制指定知识点）
    _BROAD_QUERY_MARKERS: tuple[str, ...] = (
        "是什么", "能做什么", "有什么用", "概述", "综述", "介绍",
        "入门", "初学者", "新手", "科普", "简介",
    )

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

        # 宽泛查询检测：纯概述性问题不走精确匹配
        is_broad = self._is_broad_query(normalized)

        hinted_uid, hinted_intent = self._route_by_query_hint(normalized)
        if hinted_uid:
            # 宽泛查询命中 hint route 时（如"机器学习的应用" → ml_basic_terms），仍然返回
            hinted_node = await self.graph_store.get_node(hinted_uid)
            if hinted_node and "KnowledgePoint" in hinted_node.labels:
                understanding = QueryUnderstanding(
                    normalized_query=normalized,
                    intent="concept_explanation" if is_broad else hinted_intent,
                    possible_nodes=[hinted_uid],
                    reranked_nodes=[hinted_uid],
                    confidence=0.7 if is_broad else 0.95,
                    reason="broad_query_hint" if is_broad else "query_hint_route",
                )
                return NodeResolution(
                    query=query,
                    normalized_query=normalized,
                    intent=hinted_intent,
                    resolved_uid=hinted_node.uid,
                    candidates=[hinted_node],
                    uncertainty=(
                        ["broad_query_matched_to_general_node"]
                        if is_broad
                        else []
                    ),
                    llm_understanding=understanding,
                )
        elif is_broad:
            # 宽泛查询 + 无 hint route → 不强制匹配，返回空
            return NodeResolution(
                query=query,
                normalized_query=normalized,
                intent="general_learning_chat",
                uncertainty=["broad_query_no_specific_node"],
            )
            hinted_node = await self.graph_store.get_node(hinted_uid)
            if hinted_node and "KnowledgePoint" in hinted_node.labels:
                understanding = QueryUnderstanding(
                    normalized_query=normalized,
                    intent=hinted_intent,
                    possible_nodes=[hinted_uid],
                    reranked_nodes=[hinted_uid],
                    confidence=0.95,
                    reason="query_hint_route",
                )
                return NodeResolution(
                    query=query,
                    normalized_query=normalized,
                    intent=hinted_intent,
                    resolved_uid=hinted_node.uid,
                    candidates=[hinted_node],
                    llm_understanding=understanding,
                )

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

    def _is_broad_query(self, query: str) -> bool:
        """检测查询是否为宽泛的概述性问题（不应强制匹配特定知识点）。"""
        lowered = query.lower()
        # 短查询 + 宽泛标记
        if len(query) < 20:
            for marker in self._BROAD_QUERY_MARKERS:
                if marker in lowered:
                    return True
        # 明显的宽泛短语
        broad_phrases = [
            "机器学习是什么", "深度学习是什么", "AI 是什么",
            "能做什么", "有什么用", "应用场景", "应用领域",
            "怎么学", "如何入门", "新手", "初学者",
            "的应用", "应用有哪些", "应用案例", "应用举例",
            "有哪些算法", "有哪些模型", "有哪些方法",
            "前景", "发展趋势", "前沿",
        ]
        for phrase in broad_phrases:
            if phrase in lowered:
                return True
        # 纯问句且无具体算法名 → 宽泛
        if any(q in lowered for q in ["什么是", "是什么", "有哪些", "怎么做"]):
            # 没有具体算法关键词 → 宽泛
            specific_terms = [
                "梯度", "反向传播", "CNN", "RNN", "SVM", "KNN", "PCA",
                "决策树", "随机森林", "正则化", "过拟合", "激活函数",
                "backprop", "gradient", "transformer", "attention",
            ]
            if not any(t.lower() in lowered for t in specific_terms):
                return True
        return False

    def _route_by_query_hint(self, query: str) -> tuple[str | None, str]:
        lowered = query.lower()
        for terms, uid, intent in self._QUERY_HINT_ROUTES:
            if any(term.lower() in lowered for term in terms):
                return uid, intent
        return None, "unknown"

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
