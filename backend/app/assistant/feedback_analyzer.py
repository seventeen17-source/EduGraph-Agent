"""LLM 反馈分析引擎 —— 批量分析未处理的反馈，生成洞察并更新画像。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.assistant.feedback import FeedbackRepository
from app.core.config import Settings
from app.profile.schemas import ComprehensionGap, FeedbackInsight, PerNodeStrategy
from app.profile.service import ProfileService


class AnalysisOutput(BaseModel):
    """LLM 分析的输出结构。"""
    comprehension_gaps: list[dict] = Field(default_factory=list)
    # [{node_id, severity, inferred_root_cause, recommended_strategy}]
    effective_strategies: list[dict] = Field(default_factory=list)
    # [{node_id, best_approach, avoid_approach, confidence, reason}]
    insights: list[dict] = Field(default_factory=list)
    # [{key, description, category, actionable, confidence}]


ANALYSIS_SYSTEM_PROMPT = """你是 EduGraph-Agent 的学生学习行为分析师。

你的任务是分析学生对 AI 回复的反馈记录，推断学生的学习偏好、理解缺口和有效的教学策略。

## 反馈标签含义
- helpful/clear: 正向信号，该回复有效
- dont_get: 学生没看懂
- too_hard: 内容难度过高
- too_easy: 内容太简单
- too_vague: 不够具体
- want_examples/want_summary: 学生想要不同的内容形式

## 你的分析维度
1. comprehension_gaps: 哪些知识点学生反复反馈"没看懂"或"太难"？
   推断根因（前置知识不足？讲解风格不匹配？）并给出辅导策略
2. effective_strategies: 哪些教学方式对这个学生有效？哪些应该避免？
   例如："计算图演示→best_approach, 纯公式推导→avoid_approach"
3. insights: 整体洞察，如"该生偏好具体例子而非抽象理论"、"ml_chain_rule 需要前置补充"

## 输出要求
以 JSON 格式输出，包含 comprehension_gaps、effective_strategies、insights 三个数组。
每个数组元素必须包含所述字段。不要输出分析过程，只输出 JSON。"""


class FeedbackAnalyzer:
    """LLM 驱动的反馈批量分析引擎。"""

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
        llm = ChatOpenAI(**kwargs)
        method = "json_mode" if self.settings.llm_provider in ("deepseek", "qwen", "anthropic") else "function_calling"
        structured = llm.with_structured_output(AnalysisOutput, method=method)
        prompt = ChatPromptTemplate.from_messages([
            ("system", ANALYSIS_SYSTEM_PROMPT),
            ("human", "{context}"),
        ])
        self._chain = prompt | structured
        return self._chain

    async def analyze_and_update_profile(
        self,
        student_id: str,
        *,
        feedback_repo: FeedbackRepository,
        profile_service: ProfileService,
    ) -> dict:
        """分析未处理的反馈并更新学生画像。

        调用时机：extract_memory 节点中检测到未分析反馈 >= 8 条时异步触发。
        """
        if not self.settings.llm_api_key:
            return {"status": "skipped", "reason": "no_llm"}

        # 1. 获取未分析的反馈
        unanalyzed = await feedback_repo.list_unanalyzed(student_id, limit=50)
        if len(unanalyzed) < 5:
            return {"status": "skipped", "reason": f"only_{len(unanalyzed)}_unanalyzed"}

        # 2. 构建分析上下文
        context = self._build_context(unanalyzed)

        # 3. LLM 分析
        try:
            chain = self._get_chain()
            result: AnalysisOutput = await chain.ainvoke({"context": context})
        except Exception as exc:
            # LLM 失败 → 标记为已分析（避免反复重试），但不更新画像
            await feedback_repo.mark_analyzed([fb.id for fb in unanalyzed])
            return {"status": "llm_error", "error": str(exc)}

        # 4. 更新画像
        profile = await profile_service.get_profile(student_id)
        behavior = profile.learning_behavior

        # 更新 comprehension_gaps
        for gap_dict in result.comprehension_gaps:
            node_id = gap_dict.get("node_id", "")
            if not node_id:
                continue
            existing = next(
                (g for g in behavior.comprehension_gaps if g.node_id == node_id and not g.resolved),
                None,
            )
            if existing:
                existing.severity = max(existing.severity, float(gap_dict.get("severity", 0.3)))
                existing.inferred_root_cause = str(gap_dict.get("inferred_root_cause", existing.inferred_root_cause))
                existing.recommended_strategy = str(gap_dict.get("recommended_strategy", existing.recommended_strategy))
            else:
                behavior.comprehension_gaps.append(ComprehensionGap(
                    node_id=node_id,
                    severity=float(gap_dict.get("severity", 0.3)),
                    inferred_root_cause=str(gap_dict.get("inferred_root_cause", "")),
                    recommended_strategy=str(gap_dict.get("recommended_strategy", "")),
                    detected_at=datetime.utcnow(),
                ))

        # 更新 effective_strategies
        for st_dict in result.effective_strategies:
            node_id = st_dict.get("node_id", "")
            if not node_id:
                continue
            if node_id not in behavior.effective_strategies:
                behavior.effective_strategies[node_id] = PerNodeStrategy(node_id=node_id)
            st = behavior.effective_strategies[node_id]
            if st_dict.get("best_approach"):
                st.best_approach = str(st_dict["best_approach"])
            if st_dict.get("avoid_approach"):
                st.avoid_approach = str(st_dict["avoid_approach"])
            st.confidence = max(st.confidence, float(st_dict.get("confidence", 0.5)))
            st.last_updated = datetime.utcnow()

        # 新增 insights
        for ins_dict in result.insights:
            key = ins_dict.get("key", "")
            # 避免重复
            if any(i.key == key for i in behavior.insights):
                continue
            behavior.insights.append(FeedbackInsight(
                key=str(key),
                description=str(ins_dict.get("description", "")),
                category=str(ins_dict.get("category", "general")),
                confidence=float(ins_dict.get("confidence", 0.5)),
                actionable=str(ins_dict.get("actionable", "")),
                created_at=datetime.utcnow(),
            ))

        behavior.last_analyzed_at = datetime.utcnow()
        behavior.last_updated = datetime.utcnow()

        # 持久化
        await profile_service.save_learning_behavior(student_id, behavior)

        # 5. 标记反馈为已分析
        await feedback_repo.mark_analyzed([fb.id for fb in unanalyzed])

        return {
            "status": "ok",
            "analyzed_count": len(unanalyzed),
            "new_gaps": len(result.comprehension_gaps),
            "new_strategies": len(result.effective_strategies),
            "new_insights": len(result.insights),
        }

    def _build_context(self, feedbacks: list) -> str:
        """构建 LLM 分析上下文。"""
        lines = []
        for fb in feedbacks[:30]:
            tags_str = ", ".join(fb.tags) if fb.tags else "无标签"
            node = fb.target_node_id or "未知"
            intent = fb.intent or "未知"
            features = fb.reply_features or {}
            style = features.get("style", "未知")
            text = fb.free_text or ""
            lines.append(
                f"[{fb.created_at.isoformat()}] intent={intent}, node={node}, "
                f"tags=[{tags_str}], style={style}"
                + (f", free_text=\"{text}\"" if text else "")
            )
        return "\n".join(lines)

    # ── 反馈闭环：根据反馈类型触发对应动作 ──

    # 负反馈标签 → 动作映射
    _FEEDBACK_ACTIONS: dict[str, dict] = {
        "dont_get": {
            "action": "re_explain",
            "label": "重新解释",
            "prompt": "请用更简单的方式重新解释，并补充具体例子",
            "user_message": "已根据你的反馈重新解释，降低了理解难度并补充了例子",
        },
        "too_hard": {
            "action": "simplify",
            "label": "降低难度",
            "prompt": "请降低难度，推荐前置知识，用更基础的方式讲解",
            "user_message": "已根据你的反馈降低了难度，并推荐了前置知识",
        },
        "too_easy": {
            "action": "advance",
            "label": "提高难度",
            "prompt": "请推荐更高难度内容，增加推导、对比或综合题",
            "user_message": "已根据你的反馈提高了挑战度，推荐了更高难度内容",
        },
        "incorrect": {
            "action": "regenerate",
            "label": "重新生成",
            "prompt": "内容有误，请重新生成正确的内容",
            "user_message": "已标记内容待审核，并尝试重新生成",
        },
        "too_vague": {
            "action": "add_detail",
            "label": "补充细节",
            "prompt": "请给出更具体的步骤、依据和可执行建议",
            "user_message": "已根据你的反馈补充了更具体的步骤和建议",
        },
        "want_examples": {
            "action": "generate_example",
            "label": "补充例子",
            "prompt": "请补充例题、代码或具体场景",
            "user_message": "已根据你的反馈补充了例子和具体场景",
        },
        "want_summary": {
            "action": "generate_summary",
            "label": "补充总结",
            "prompt": "请在结尾给出更清晰的要点总结",
            "user_message": "已根据你的反馈补充了要点总结",
        },
    }

    def trigger_feedback_action(
        self,
        feedback_tags: list[str],
        message_content: str = "",
        student_id: str = "",
    ) -> dict:
        """根据反馈标签触发对应动作。

        Args:
            feedback_tags: 反馈标签列表（如 ["dont_get", "too_hard"]）
            message_content: 原始助手回复内容（供生成新回复时参考）
            student_id: 学生 ID

        Returns:
            {
                "action": 动作标识（re_explain/simplify/advance/...）,
                "label": 动作中文名,
                "prompt": 重新生成的提示词,
                "user_message": 展示给用户的系统响应消息,
                "feedback_tag": 触发该动作的反馈标签,
            }
            如果没有匹配的负反馈，返回 {"action": "none", ...}
        """
        # 按优先级匹配：incorrect > dont_get > too_hard > too_vague > want_examples > want_summary > too_easy
        priority = [
            "incorrect", "dont_get", "too_hard", "too_vague",
            "want_examples", "want_summary", "too_easy",
        ]
        tag_set = set(feedback_tags or [])
        for tag in priority:
            if tag in tag_set:
                action = self._FEEDBACK_ACTIONS[tag]
                return {
                    "action": action["action"],
                    "label": action["label"],
                    "prompt": action["prompt"],
                    "user_message": action["user_message"],
                    "feedback_tag": tag,
                }
        return {
            "action": "none",
            "label": "",
            "prompt": "",
            "user_message": "反馈已记录，会用于后续个性化调整",
            "feedback_tag": "",
        }
