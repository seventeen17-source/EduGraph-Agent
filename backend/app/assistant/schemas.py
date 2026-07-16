from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.schemas import GeneratedResources
from app.graphrag.schemas import EvidencePackage
from app.profile.schemas import StudentProfile

AssistantIntent = Literal[
    "profile_update",
    "concept_explain",
    "resource_generate",
    "exercise_help",
    "path_plan",
    "progress_update",
    "assessment_review",
    "navigation_help",
    "general_learning_chat",
    "clarify_intent",
]

AssistantStatus = Literal["ok", "degraded", "unavailable", "error"]
PathMode = Literal[
    "current_goal",
    "gap_filling",
    "exam_review",
    "project_practice",
    "free_exploration",
]
PathNodeStatus = Literal[
    "recommended",
    "in_progress",
    "mastered",
    "needs_review",
    "added_by_mistake",
    "skipped_by_student",
]


class AssistantChatRequest(BaseModel):
    student_id: str
    message: str
    conversation_id: str | None = None


class ClarifyOption(BaseModel):
    value: str
    label: str
    description: str = ""
    intent: AssistantIntent | None = None
    target_node_id: str | None = None


class ClarifyIntentResult(BaseModel):
    question: str
    options: list[ClarifyOption]
    reasoning: str = ""


class AssistantIntentResult(BaseModel):
    intent: AssistantIntent = "general_learning_chat"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    target_topic: str | None = None
    target_node_id: str | None = None
    resource_types: list[str] = Field(default_factory=list)
    exercise_count: int | None = Field(default=None, ge=1, le=20)
    exercise_type: Literal["choice", "short_answer", "coding", "case_analysis"] | None = None
    profile_update_hint: str | None = None
    exercise_context: str | None = None
    path_goal: str | None = None
    user_constraints: list[str] = Field(default_factory=list)
    reasoning: str = ""
    clarification: ClarifyIntentResult | None = None


class AssistantAction(BaseModel):
    type: str
    label: str
    description: str = ""
    route: str = ""
    query: dict[str, Any] = Field(default_factory=dict)
    node_id: str | None = None
    resource_record_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SuggestedNextAction(BaseModel):
    label: str
    description: str = ""
    action_type: str = "navigation"
    priority: int = 3
    route: str = ""
    query: dict[str, Any] = Field(default_factory=dict)


class AssistantTraceItem(BaseModel):
    node: str
    status: Literal["started", "done", "skipped", "failed"] = "done"
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PathPlanNode(BaseModel):
    node_id: str
    label: str = ""
    status: PathNodeStatus = "recommended"
    reason: str = ""
    recommended_resource_types: list[str] = Field(default_factory=list)


class AssistantPathPlan(BaseModel):
    mode: PathMode = "current_goal"
    title: str = ""
    goal: str = ""
    nodes: list[PathPlanNode] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ExerciseFeedback(BaseModel):
    summary: str = ""
    likely_causes: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    related_node_ids: list[str] = Field(default_factory=list)


class AssistantResponse(BaseModel):
    reply: str
    intent: AssistantIntent | None = None
    intent_confidence: float = 0.0
    conversation_id: str
    assistant_message_id: str = ""  # 真实 DB message id，用于反馈绑定
    status: AssistantStatus = "ok"
    # 语义记忆
    relevant_memories: list[dict] = Field(default_factory=list)
    # 意图澄清相关
    needs_clarification: bool = False
    clarification_options: list[ClarifyOption] = Field(default_factory=list)
    clarification_question: str = ""
    # Tool 效果评分
    evidence_quality_score: float | None = None
    resource_quality_score: float | None = None
    # 反思结果
    reflection: str = ""
    needs_refinement: bool = False
    # 原有字段
    actions: list[AssistantAction] = Field(default_factory=list)
    suggested_next_actions: list[SuggestedNextAction] = Field(default_factory=list)
    profile_delta: dict[str, Any] = Field(default_factory=dict)
    evidence: EvidencePackage | None = None
    resource_record_id: str | None = None
    resource_has_exercises: bool = False
    resources: GeneratedResources | None = None
    path_plan: AssistantPathPlan | None = None
    exercise_feedback: ExerciseFeedback | None = None
    agent_trace: list[AssistantTraceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AssistantMessageRecord(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    intent: str = ""
    target_node_id: str = ""
    resource_record_id: str | None = None
    actions: list[AssistantAction] = Field(default_factory=list)
    agent_trace: list[AssistantTraceItem] = Field(default_factory=list)
    created_at: datetime


class AssistantConversationRecord(BaseModel):
    id: str
    student_id: str
    title: str = ""
    last_intent: str = ""
    updated_at: datetime
    created_at: datetime


class AssistantHistoryResponse(BaseModel):
    student_id: str
    conversations: list[AssistantConversationRecord] = Field(default_factory=list)
    messages: list[AssistantMessageRecord] = Field(default_factory=list)


class AssistantContextSummary(BaseModel):
    profile: StudentProfile | None = None
    lightweight_profile: dict[str, Any] = Field(default_factory=dict)
    recent_messages: list[AssistantMessageRecord] = Field(default_factory=list)
