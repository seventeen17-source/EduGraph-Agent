from typing import Protocol

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.graph.models import GraphNode


class QueryUnderstanding(BaseModel):
    normalized_query: str = ""
    intent: str = "unknown"
    possible_nodes: list[str] = Field(default_factory=list)
    reranked_nodes: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""


class LLMResolverClient(Protocol):
    async def understand_query(
        self,
        query: str,
        candidates: list[GraphNode],
        weak_points: list[str],
    ) -> QueryUnderstanding:
        """Rewrite, classify, and rerank a learning query."""


class HeuristicLLMResolverClient:
    """Local fallback that mirrors the intended LLM contract without network calls."""

    async def understand_query(
        self,
        query: str,
        candidates: list[GraphNode],
        weak_points: list[str],
    ) -> QueryUnderstanding:
        normalized_query = self._rewrite_query(query)
        intent = self._classify_intent(query)
        possible_nodes = self._infer_possible_nodes(query, normalized_query)
        reranked = self._rerank(query, normalized_query, candidates, weak_points, possible_nodes)
        return QueryUnderstanding(
            normalized_query=normalized_query,
            intent=intent,
            possible_nodes=list(dict.fromkeys(possible_nodes + [node.uid for node in candidates])),
            reranked_nodes=[node.uid for node in reranked],
            confidence=0.6 if reranked else 0.2,
            reason="heuristic_fallback",
        )

    def _rewrite_query(self, query: str) -> str:
        replacements = {
            "反复更新中心点": "K-Means 迭代过程与簇中心更新",
            "更新中心点": "K-Means 簇中心更新",
            "从后往前算梯度": "反向传播 梯度计算",
            "从后往前": "反向传播",
            "名字里有回归但实际在做分类": "逻辑回归 分类 线性模型",
            "回归但实际在做分类": "逻辑回归 分类",
        }
        for key, value in replacements.items():
            if key in query:
                return value
        return query.strip()

    def _classify_intent(self, query: str) -> str:
        if any(term in query for term in ["区别", "对比", "搞不清", "为什么"]):
            return "comparison" if "区别" in query or "对比" in query else "concept_explanation"
        if any(term in query for term in ["代码", "实现", "编程", "函数"]):
            return "implementation"
        if any(term in query for term in ["题", "练习", "答案", "错"]):
            return "exercise_help"
        if any(term in query for term in ["薄弱", "诊断", "不会", "总是"]):
            return "diagnosis"
        return "concept_explanation"

    def _infer_possible_nodes(self, query: str, normalized_query: str) -> list[str]:
        text = f"{query} {normalized_query}".lower()
        hints: list[str] = []
        if "k-means" in text or "kmeans" in text or "中心点" in text or "簇中心" in text:
            hints.extend(["ml_kmeans", "ml_clustering"])
        if "从后往前" in text or "反向传播" in text or "backprop" in text:
            hints.extend(["ml_backpropagation", "ml_gradient_descent"])
        if "逻辑回归" in text or "logistic" in text:
            hints.extend(["ml_logistic_regression", "ml_linear_regression"])
        if "梯度下降" in text or "gradient descent" in text:
            hints.extend(["ml_gradient_descent", "ml_gradient_optimization_basic"])
        return list(dict.fromkeys(hints))

    def _rerank(
        self,
        query: str,
        normalized_query: str,
        candidates: list[GraphNode],
        weak_points: list[str],
        possible_nodes: list[str],
    ) -> list[GraphNode]:
        text = f"{query} {normalized_query}".lower()

        def score(node: GraphNode) -> tuple[int, str]:
            props = node.properties
            value = 0
            if node.uid in possible_nodes:
                value += 80
            terms = [node.uid, str(props.get("name", ""))]
            terms.extend(str(item) for item in props.get("aliases", []))
            terms.extend(str(item) for item in props.get("keywords", []))
            for term in terms:
                lowered = term.lower()
                if lowered and lowered in text:
                    value += 20
            if node.uid in weak_points:
                value += 30
            return (-value, node.uid)

        return sorted(candidates, key=score)


class LangChainLLMResolverClient:
    """LangChain-backed resolver client with structured QueryUnderstanding output."""

    def __init__(self, settings: Settings, fallback: LLMResolverClient | None = None) -> None:
        self.settings = settings
        self.fallback = fallback or HeuristicLLMResolverClient()
        self._chain = None

    async def understand_query(
        self,
        query: str,
        candidates: list[GraphNode],
        weak_points: list[str],
    ) -> QueryUnderstanding:
        if not self.settings.llm_resolver_enabled or not self.settings.llm_api_key:
            return await self.fallback.understand_query(query, candidates, weak_points)
        try:
            chain = self._get_chain()
            payload = {
                "query": query,
                "weak_points": weak_points,
                "candidates": [
                    {
                        "uid": node.uid,
                        "name": node.properties.get("name"),
                        "aliases": node.properties.get("aliases", []),
                        "keywords": node.properties.get("keywords", []),
                        "summary": node.properties.get("summary", ""),
                    }
                    for node in candidates
                ],
            }
            result = await chain.ainvoke(payload)
            if not result.normalized_query:
                result.normalized_query = query.strip()
            return result
        except Exception as exc:
            fallback_result = await self.fallback.understand_query(query, candidates, weak_points)
            fallback_result.reason = f"heuristic_fallback_after_llm_error:{type(exc).__name__}:{exc}"
            return fallback_result

    def _get_chain(self):
        if self._chain is not None:
            return self._chain

        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        model_kwargs = {
            "model": self.settings.llm_model,
            "api_key": self.settings.llm_api_key,
            "temperature": 0,
        }
        if self.settings.llm_base_url:
            model_kwargs["base_url"] = self.settings.llm_base_url

        llm = ChatOpenAI(**model_kwargs)
        structured_method = "json_mode" if self.settings.llm_provider in ("deepseek", "qwen", "anthropic") else "function_calling"
        structured_llm = llm.with_structured_output(QueryUnderstanding, method=structured_method)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的知识点解析器。"
                    "你的任务不是回答学生问题，而是把问题改写为可检索表达、分类意图、"
                    "从候选知识点中选择 possible_nodes，并给出 reranked_nodes。"
                    "只能使用候选 uid 或你确信项目中存在的机器学习知识点 uid。"
                    "intent 只能是 concept_explanation, comparison, implementation, "
                    "exercise_help, diagnosis, learning_path, unknown 之一。"
                    "你必须返回一个 JSON 对象，且必须包含以下全部字段：\n"
                    '  "normalized_query": 将原始问题改写为适合检索的规范化表达（必填，不可为空字符串）\n'
                    '  "intent": 问题意图分类\n'
                    '  "possible_nodes": 你认为相关的知识点 uid 列表\n'
                    '  "reranked_nodes": 按相关性从高到低重排的知识点 uid 列表\n'
                    "务必确保 JSON 中 normalized_query 字段存在且有值。",
                ),
                (
                    "human",
                    "用户问题：{query}\n"
                    "学生薄弱点：{weak_points}\n"
                    "规则召回候选：{candidates}\n"
                    "请输出包含全部必填字段的 JSON 对象，特别注意 normalized_query 不可为空。",
                ),
            ]
        )
        self._chain = prompt | structured_llm
        return self._chain


def build_llm_resolver_client(settings: Settings) -> LLMResolverClient:
    fallback = HeuristicLLMResolverClient()
    if settings.llm_resolver_enabled:
        return LangChainLLMResolverClient(settings=settings, fallback=fallback)
    return fallback
