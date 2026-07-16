from pydantic import BaseModel, Field

from app.graphrag.schemas import StudentProfileInput


class RecommendationEvidence(BaseModel):
    source: str  # exercise_result/weak_points/forgetting_curve/mistake_history/goal_match
    detail: str
    mastery: float | None = None
    last_attempt: str | None = None


class RecommendationItem(BaseModel):
    node_id: str
    node_name: str
    recommendation_type: str  # weak_point/prerequisite/goal_related/forgetting_review/mistake_related
    reason: str
    score: float  # 0-1
    evidence: RecommendationEvidence | None = None
    # 保留原有字段
    prerequisites: list[str] = []
    difficulty: str | None = None
    chapter: str | None = None


class DiagnosisRecommendRequest(BaseModel):
    student_profile: StudentProfileInput
    top_k: int = 5
    node_mastery: dict[str, dict] = Field(default_factory=dict)  # uid -> {mastery_score, confidence, ...}
    student_id: str | None = None  # 可选，用于从画像和练习记录中获取掌握度与错题证据
    # 多目标支持：指定目标后，仅推荐与该目标相关的节点
    target_goal: str | None = None


class DiagnosisRecommendResponse(BaseModel):
    recommended_nodes: list[str] = Field(default_factory=list)
    recommended_exercises: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    node_priorities: dict[str, float] = Field(default_factory=dict)  # uid -> priority score
    sorted_by_prerequisites: bool = False
    # 新增：逐节点解释
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    current_node_id: str | None = None  # 当前建议节点（无进行中节点时取推荐队列首项）
