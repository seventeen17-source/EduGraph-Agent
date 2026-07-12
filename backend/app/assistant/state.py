from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from app.agents.schemas import GeneratedResources
from app.assistant.schemas import (
    AssistantAction,
    AssistantIntent,
    AssistantPathPlan,
    AssistantTraceItem,
    ExerciseFeedback,
    SuggestedNextAction,
)
from app.graphrag.schemas import EvidencePackage, StudentProfileInput
from app.profile.schemas import StudentProfile


class AssistantState(TypedDict, total=False):
    student_id: str
    user_message: str
    conversation_id: str
    run_id: str
    started_at: datetime

    profile: StudentProfile | None
    lightweight_profile: StudentProfileInput | None
    history_messages: list[dict[str, Any]]

    intent: AssistantIntent | None
    intent_confidence: float
    intent_reasoning: str
    # 意图澄清相关
    needs_clarification: bool
    clarification_options: list[dict[str, Any]]
    clarification_question: str
    clarification_response: str | None

    entities: dict[str, Any]
    target_node_id: str | None
    requested_resource_types: list[str]

    evidence: EvidencePackage | None
    # Tool 效果评分
    evidence_quality_score: float
    evidence_evaluation_reason: str
    retry_evidence: bool

    resources: GeneratedResources | None
    # 资源质量评分
    resource_quality_score: float
    resource_evaluation_reason: str

    resource_record_id: str | None
    path_plan: AssistantPathPlan | None
    exercise_feedback: ExerciseFeedback | None
    profile_update: dict[str, Any]

    # 反思相关
    reflection: str
    needs_refinement: bool
    refinement_count: int

    # 错误恢复
    recovery_action: str  # "retry" | "compose" | "abort"
    recovery_message: str

    actions: list[AssistantAction]
    agent_trace: list[AssistantTraceItem]
    suggested_next_actions: list[SuggestedNextAction]
    # 语义记忆
    relevant_memories: list[dict[str, Any]]
    # 遗忘检测
    _forgetting_nodes: list[str]

    final_reply: str
    errors: list[str]
    llm_available: bool
    status: str