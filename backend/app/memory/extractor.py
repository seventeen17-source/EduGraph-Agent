"""记忆提取器 —— 用 LLM 从对话轮次中提取结构化记忆条目。"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.memory.schemas import MemoryEntry, MemoryExtractionResult


EXTRACTION_SYSTEM_PROMPT = """你是 EduGraph-Agent 的「学习记忆提取器」。你的任务是从每一轮师生对话中提取结构化记忆，用于后续个性化教学。

## 提取原则
1. **只提取有学习价值的内容**：纯寒暄/导航/系统操作不提取，`worth_remembering` 设为 false
2. **困惑点要精确**：尽量映射到具体的知识点 ID（如 `ml_backpropagation`、`ml_chain_rule`），不要泛泛而谈
3. **掌握信号要有证据**：不要猜，只记录对话中明确体现的理解程度
4. **偏好要具体**：如"对计算图可视化反应积极"而非"喜欢图片"
5. **建议要有可操作性**：如"下次准备 sigmoid 梯度消失的可视化练习"

## 知识点 ID 参考（提取 confusion_nodes 和 mastery_signals 时优先使用）
常见知识点 ID：ml_backpropagation, ml_gradient_descent, ml_activation_function, ml_chain_rule,
ml_overfitting_underfitting, ml_regularization, ml_cross_validation, ml_cnn, ml_rnn,
ml_neural_network, ml_loss_function, ml_optimizer, ml_batch_normalization, ml_dropout,
ml_logistic_regression, ml_svm, ml_decision_tree, ml_random_forest, ml_kmeans, ml_pca

## 输出格式
严格按照 JSON 格式输出，不要输出其他内容：
{
  "student_question_summary": "…",
  "agent_response_summary": "…",
  "key_insight": "…",
  "confusion_nodes": ["ml_xxx"],
  "mastery_signals": [{"node_id": "ml_xxx", "level": "partial", "evidence": "…"}],
  "engagement_level": "medium",
  "learning_preference_hint": "…",
  "suggested_follow_up": "…",
  "caution_topics": ["…"],
  "worth_remembering": true
}"""


class MemoryExtractor:
    """用 LLM 从对话轮次中提取 MemoryEntry。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chain = None

    def _get_chain(self):
        if self._chain is not None:
            return self._chain
        kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "api_key": self.settings.llm_api_key,
            "temperature": 0,
        }
        if self.settings.llm_base_url:
            kwargs["base_url"] = self.settings.llm_base_url
        llm = ChatOpenAI(**kwargs)  # type: ignore[arg-type]
        method = "json_mode" if self.settings.llm_provider in ("deepseek", "qwen", "anthropic") else "function_calling"
        structured = llm.with_structured_output(MemoryExtractionResult, method=method)
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("human", "{context}"),
        ])
        self._chain = prompt | structured
        return self._chain

    async def extract(
        self,
        *,
        user_message: str,
        agent_reply: str,
        intent: str,
        target_node_id: str | None,
        agent_trace: list[dict] | None = None,
    ) -> MemoryEntry | None:
        """从一轮对话中提取记忆条目。如果 LLM 不可用或内容无价值，返回 None。"""
        if not self.settings.llm_api_key:
            return None

        # 构建提取上下文
        trace_summary = ""
        if agent_trace:
            trace_items = [
                t if isinstance(t, dict) else t.model_dump(mode="json") if hasattr(t, "model_dump") else {}
                for t in agent_trace
            ]
            nodes = [t.get("node", "") for t in trace_items if t.get("status") == "done"]
            trace_summary = f"Agent 执行路径：{' → '.join(nodes[:8])}"

        context = f"""本轮意图：{intent}
目标知识点：{target_node_id or '未明确'}
学生消息：{user_message[:800]}
助教回复：{agent_reply[:1200]}
{trace_summary}"""

        try:
            chain = self._get_chain()
            result: MemoryExtractionResult = await chain.ainvoke({"context": context})
        except Exception:
            return None

        if not result.worth_remembering:
            return None

        return MemoryEntry(
            student_id="",  # 由调用方填充
            conversation_id="",  # 由调用方填充
            node_ids=[target_node_id] if target_node_id else [],
            intent=intent,
            student_question_summary=result.student_question_summary,
            agent_response_summary=result.agent_response_summary,
            key_insight=result.key_insight,
            confusion_nodes=result.confusion_nodes,
            mastery_signals=[s.model_dump() for s in result.mastery_signals],
            engagement_level=result.engagement_level,
            learning_preference_hint=result.learning_preference_hint,
            suggested_follow_up=result.suggested_follow_up,
            caution_topics=result.caution_topics,
        )

    async def extract_from_state(self, state: dict) -> MemoryEntry | None:
        """从 LangGraph state 中提取记忆。"""
        # 判断是否值得记忆
        intent = state.get("intent") or ""
        skip_intents = {"navigation_help", "clarify_intent"}
        if intent in skip_intents:
            return None
        user_msg = state.get("user_message", "")
        if len(user_msg) < 10:
            return None
        if not state.get("target_node_id") and intent not in {
            "profile_update", "general_learning_chat", "concept_explain",
        }:
            # 没有知识点锚定的操作类意图不记忆
            if intent in {"progress_update"}:
                pass  # 仍可记忆
            elif not state.get("evidence"):
                return None

        return await self.extract(
            user_message=user_msg,
            agent_reply=state.get("final_reply", ""),
            intent=intent,
            target_node_id=state.get("target_node_id"),
            agent_trace=state.get("agent_trace"),
        )
