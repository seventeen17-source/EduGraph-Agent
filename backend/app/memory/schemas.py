"""记忆条目模型 —— 从对话中提取的结构化学习记忆。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MasterySignal(BaseModel):
    """掌握度信号。"""
    node_id: str
    level: Literal["none", "partial", "solid", "mastered"] = "partial"
    evidence: str = ""  # 支撑证据，如"学生能正确手推链式法则"


class MemoryEntry(BaseModel):
    """从单轮学习对话中提取的一条结构化记忆。

    每条记忆被嵌入为向量存入 ChromaDB，
    嵌入文本 = f"[{intent}] 学生:{student_question_summary} | 助教:{agent_response_summary} | 关键:{key_insight}"
    """

    # ── 标识 ──
    id: str = Field(default_factory=lambda: f"mem_{datetime.utcnow().timestamp():.0f}")
    student_id: str
    conversation_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # ── 知识点锚定（用于 ChromaDB 元数据过滤） ──
    node_ids: list[str] = Field(default_factory=list)      # 关联的知识点 UID
    intent: str = ""                                        # concept_explain / exercise_help / ...

    # ── 语义内容（拼接后做 embedding） ──
    student_question_summary: str = ""   # 学生问题的 1-2 句概括
    agent_response_summary: str = ""     # Agent 回复的 1-2 句概括
    key_insight: str = ""               # 最重要的发现

    # ── 学习信号 ──
    confusion_nodes: list[str] = Field(default_factory=list)   # 学生困惑的知识点
    mastery_signals: list[MasterySignal] = Field(default_factory=list)
    engagement_level: str = "medium"     # high / medium / low
    learning_preference_hint: str = ""   # "偏好图解，抗拒纯公式"

    # ── 可操作性指导 ──
    suggested_follow_up: str = ""        # 下次可以做什么
    caution_topics: list[str] = Field(default_factory=list)  # 需要特别留意的内容


class MemoryExtractionResult(BaseModel):
    """LLM 提取记忆条目的结构化输出。"""
    student_question_summary: str
    agent_response_summary: str
    key_insight: str
    confusion_nodes: list[str] = Field(default_factory=list)
    mastery_signals: list[MasterySignal] = Field(default_factory=list)
    engagement_level: str = "medium"
    learning_preference_hint: str = ""
    suggested_follow_up: str = ""
    caution_topics: list[str] = Field(default_factory=list)
    worth_remembering: bool = True


class MemorySearchResult(BaseModel):
    """检索结果。"""
    entry: MemoryEntry
    score: float               # 综合相似度 (0-1)
    semantic_score: float      # 向量余弦相似度
    metadata_bonus: float      # 元数据匹配加分
    graph_bonus: float         # 图谱扩展匹配加分
    time_decay: float          # 时间衰减因子


class MemoryStats(BaseModel):
    """记忆库统计。"""
    total_entries: int
    entries_by_intent: dict[str, int]
    top_confusion_nodes: list[tuple[str, int]]  # (node_id, count)
    oldest_entry: datetime | None
    newest_entry: datetime | None
