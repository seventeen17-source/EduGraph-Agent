from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.graphrag.schemas import StudentProfileInput


KnowledgeLevel = Literal["weak", "basic", "intermediate", "advanced"]
AbilityLevel = Literal["weak", "basic", "intermediate", "advanced"]
ResourceType = Literal["document", "diagram", "exercise", "video_script", "code_case"]


class Background(BaseModel):
    major: str = ""
    grade: int | None = None
    school_type: str = "undergraduate"
    course_foundation: list[str] = Field(default_factory=list)
    source: str = ""
    confidence: float = 0.0
    last_updated: datetime | None = None


class LearningGoal(BaseModel):
    goal_type: list[str] = Field(default_factory=list)
    description: str = ""
    target_course: str = "ml_course"
    expected_hours_per_week: int | None = None
    source: str = ""
    confidence: float = 0.0
    last_updated: datetime | None = None


class KnownTopic(BaseModel):
    topic: str
    level: KnowledgeLevel = "basic"
    evidence: str = ""


class KnowledgeBase(BaseModel):
    known_topics: list[KnownTopic] = Field(default_factory=list)
    unknown_topics: list[str] = Field(default_factory=list)
    source: str = ""
    confidence: float = 0.0
    last_updated: datetime | None = None


class Progress(BaseModel):
    current_chapter_id: str | None = None
    completed_node_ids: list[str] = Field(default_factory=list)
    in_progress_node_ids: list[str] = Field(default_factory=list)
    completion_rate: float = 0.0
    last_active_at: datetime | None = None
    source: str = "system"
    confidence: float = 1.0


class CognitiveStyleInfo(BaseModel):
    primary: str = ""
    secondary: str = ""
    style_ranking: list[str] = Field(default_factory=list)
    source: str = ""
    confidence: float = 0.0
    last_updated: datetime | None = None


class SelfReportedWeakPoint(BaseModel):
    topic: str
    node_id: str | None = None
    description: str = ""


class DiagnosedWeakPoint(BaseModel):
    node_id: str
    error_rate: float = 0.0
    total_attempts: int = 0
    last_wrong_at: datetime | None = None


class WeakPoints(BaseModel):
    self_reported: list[SelfReportedWeakPoint] = Field(default_factory=list)
    diagnosed: list[DiagnosedWeakPoint] = Field(default_factory=list)
    source: str = ""
    confidence: float = 0.0
    last_updated: datetime | None = None


class Preferences(BaseModel):
    resource_ranking: list[ResourceType] = Field(default_factory=list)
    session_length: str = "medium"
    difficulty_preference: str = "gradual"
    source: str = ""
    confidence: float = 0.0
    last_updated: datetime | None = None


class AbilityState(BaseModel):
    programming: AbilityLevel = "basic"
    mathematics: AbilityLevel = "basic"
    reading_papers: AbilityLevel = "basic"
    application: AbilityLevel = "basic"
    source: str = ""
    confidence: float = 0.0
    last_updated: datetime | None = None


class KnowledgePointMastery(BaseModel):
    node_id: str
    node_name: str = ""
    chapter_id: str = ""
    mastery_score: float = Field(default=0.0, ge=0.0, le=1.0)
    level: KnowledgeLevel = "weak"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    attempts: int = 0
    correct_count: int = 0
    last_practiced_at: datetime | None = None
    updated_at: datetime | None = None


class ProfileUpdateRecord(BaseModel):
    id: str | None = None
    timestamp: datetime
    trigger: str
    trigger_detail: str = ""
    updated_fields: list[str] = Field(default_factory=list)
    summary: str = ""


class ProfileChatMessageRecord(BaseModel):
    id: str | None = None
    role: Literal["user", "assistant", "system"] = "user"
    content: str
    round_no: int = 1
    created_at: datetime


class StudentProfile(BaseModel):
    student_id: str
    display_name: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completeness: float = 0.0
    background: Background = Field(default_factory=Background)
    learning_goal: LearningGoal = Field(default_factory=LearningGoal)
    knowledge_base: KnowledgeBase = Field(default_factory=KnowledgeBase)
    progress: Progress = Field(default_factory=Progress)
    cognitive_style: CognitiveStyleInfo = Field(default_factory=CognitiveStyleInfo)
    weak_points: WeakPoints = Field(default_factory=WeakPoints)
    preferences: Preferences = Field(default_factory=Preferences)
    ability_state: AbilityState = Field(default_factory=AbilityState)
    node_mastery: dict[str, KnowledgePointMastery] = Field(default_factory=dict)
    learning_behavior: "LearningBehaviorProfile" = Field(default_factory=lambda: LearningBehaviorProfile())

    def to_graphrag_input(self) -> StudentProfileInput:
        weak_points = [item.topic for item in self.weak_points.self_reported]
        weak_points.extend(
            item.node_id for item in self.weak_points.diagnosed if item.error_rate >= 0.4
        )
        weak_points.extend(
            item.node_id
            for item in self.node_mastery.values()
            if item.mastery_score < 0.35 and item.confidence >= 0.3
        )
        return StudentProfileInput(
            weak_points=list(dict.fromkeys(weak_points)),
            preferences=list(self.preferences.resource_ranking),
            goal=self.learning_goal.description or None,
            mastery={key: value.mastery_score for key, value in self.node_mastery.items()},
        )


class ProfileChatRequest(BaseModel):
    student_id: str
    message: str
    display_name: str | None = None


class ProfileInitRequest(ProfileChatRequest):
    pass


class ProfileChatResponse(BaseModel):
    reply: str
    session_status: Literal["building", "completed"] = "building"
    current_round: int = 1
    profile: StudentProfile
    completeness: float
    updated_dimensions: list[str] = Field(default_factory=list)
    missing_dimensions: list[str] = Field(default_factory=list)


class ProfileDimensionView(BaseModel):
    key: str
    title: str
    icon: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source: str = ""
    last_updated: datetime | None = None
    status: Literal["filled", "missing", "inferred", "low_confidence"] = "missing"
    editable: bool = True


class MasteryOverviewItem(BaseModel):
    node_id: str
    node_name: str
    chapter_id: str = ""
    mastery_score: float
    level: KnowledgeLevel
    confidence: float


class WeakPointRankItem(BaseModel):
    label: str
    node_id: str | None = None
    source: Literal["self_reported", "diagnosed", "mastery"] = "self_reported"
    score: float = 0.0


class ProfileDashboardResponse(BaseModel):
    student_id: str
    display_name: str
    headline: str
    completeness: float
    missing_dimensions: list[str] = Field(default_factory=list)
    dimensions: list[ProfileDimensionView] = Field(default_factory=list)
    weak_point_rank: list[WeakPointRankItem] = Field(default_factory=list)
    mastery_overview: list[MasteryOverviewItem] = Field(default_factory=list)
    recent_updates: list[ProfileUpdateRecord] = Field(default_factory=list)
    personalization_reasons: list[str] = Field(default_factory=list)


class ManualProfilePatchRequest(BaseModel):
    dimension: str
    value: dict[str, Any]


class ExerciseResultProfileUpdateRequest(BaseModel):
    student_id: str
    exercise_id: str
    node_ids: list[str] = Field(default_factory=list)
    is_correct: bool
    score: float | None = None
    difficulty: int = Field(default=3, ge=1, le=5)
    cognitive_level: str = "understand"
    used_hint: bool = False


class ExerciseAttemptProfileUpdate(BaseModel):
    exercise_id: str
    node_ids: list[str] = Field(default_factory=list)
    is_correct: bool
    difficulty: int = Field(default=3, ge=1, le=5)
    cognitive_level: str = "understand"
    used_hint: bool = False


class ExerciseRoundProfileUpdateRequest(BaseModel):
    student_id: str
    round_id: str | None = None
    attempts: list[ExerciseAttemptProfileUpdate] = Field(default_factory=list)


class LearningProgressUpdateRequest(BaseModel):
    student_id: str
    completed_node_ids: list[str] = Field(default_factory=list)
    in_progress_node_ids: list[str] = Field(default_factory=list)
    current_chapter_id: str | None = None
    completion_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class ProfileEventResponse(BaseModel):
    profile: StudentProfile
    dashboard: ProfileDashboardResponse
    updated_node_mastery: list[str] = Field(default_factory=list)
    update_event: ProfileUpdateRecord


# ═══════════════════════════════════════════════════════════════
# 学习行为画像（从反馈和练习结果中推断）
# ═══════════════════════════════════════════════════════════════


class FormatEffectiveness(BaseModel):
    """某种内容格式对该学生的实际有效性（从反馈推断）。"""
    format: str                         # "diagram" | "code" | "formula" | "analogy" | "step_by_step"
    effectiveness_score: float = 0.5    # 0-1，越高越有效
    positive_count: int = 0             # "有帮助"次数
    negative_count: int = 0             # "没看懂"次数
    last_updated: datetime | None = None


class DepthPreference(BaseModel):
    """讲解深度的最佳区间。"""
    too_shallow_count: int = 0          # "太简单"次数
    just_right_count: int = 0           # "有帮助"+"很清楚"
    too_deep_count: int = 0             # "太难"+"没看懂"
    preferred_level: str = "intermediate"  # "basic" | "intermediate" | "advanced"


class ComprehensionGap(BaseModel):
    """一个被检测到的理解缺口 —— 看了但没懂的知识点。"""
    node_id: str
    signals: list[dict] = Field(default_factory=list)
    # [{source: "feedback", type: "没看懂", count: 3},
    #  {source: "exercise", type: "概念错误", count: 2},
    #  {source: "behavior", type: "反复提问", count: 1}]
    severity: float = 0.0               # 0-1，综合信号强度
    inferred_root_cause: str = ""        # LLM 推断的根因
    recommended_strategy: str = ""       # LLM 建议的辅导策略
    detected_at: datetime | None = None
    resolved: bool = False


class PerNodeStrategy(BaseModel):
    """按知识点定制的辅导策略。"""
    node_id: str
    best_approach: str = ""             # "计算图优先 + 避免公式开场"
    avoid_approach: str = ""            # "一次性给完整推导链"
    confidence: float = 0.0             # 策略可信度（反馈越多越高）
    evidence_count: int = 0
    last_updated: datetime | None = None


class EngagementPattern(BaseModel):
    """从交互中推断的学习行为模式。"""
    total_interactions: int = 0
    total_feedback_given: int = 0
    follow_up_rate: float = 0.0         # 追问频率
    clarification_rate: float = 0.0     # 需要澄清的频率
    avg_dwell_seconds: float = 0.0      # 阅读回复的平均停留时间
    preferred_hours: list[int] = Field(default_factory=list)  # 活跃时段
    hint_usage_rate: float = 0.0        # 做题时使用提示的频率


class FeedbackInsight(BaseModel):
    """LLM 分析反馈后生成的洞察。"""
    key: str                            # 唯一标识
    description: str                    # 人类可读的描述
    category: str = "general"           # "format" | "depth" | "pace" | "strategy" | "gap"
    confidence: float = 0.0
    actionable: str = ""                # 可操作建议
    related_nodes: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class LearningBehaviorProfile(BaseModel):
    """从反馈和练习中推断的学习行为画像 —— 揭示式偏好。

    与声明式画像（StudentProfile.preferences/cognitive_style）互补。
    当行为画像置信度足够时，优先使用行为画像驱动个性化。
    """

    # 内容格式有效性
    format_effectiveness: dict[str, FormatEffectiveness] = Field(default_factory=dict)

    # 讲解深度偏好
    depth_preference: DepthPreference = Field(default_factory=DepthPreference)

    # 理解缺口
    comprehension_gaps: list[ComprehensionGap] = Field(default_factory=list)

    # 按知识点定制策略
    effective_strategies: dict[str, PerNodeStrategy] = Field(default_factory=dict)

    # 交互行为模式
    engagement: EngagementPattern = Field(default_factory=EngagementPattern)

    # LLM 生成的洞察
    insights: list[FeedbackInsight] = Field(default_factory=list)

    # 节奏偏好
    pace_preference: str = "balanced"   # "step_by_step" | "quick_overview" | "balanced"

    # 推断的认知水平
    inferred_cognitive_level: str = ""  # "beginner" | "intermediate" | "advanced"

    # 元数据
    total_feedback_count: int = 0
    last_analyzed_at: datetime | None = None
    last_updated: datetime | None = None

    def is_reliable(self) -> bool:
        """行为画像是否足够可靠。"""
        return self.total_feedback_count >= 5


# ═══════════════════════════════════════════════════════════════
# 成长时间轴
# ═══════════════════════════════════════════════════════════════


class TimelineEvent(BaseModel):
    """成长时间轴中的单个事件。"""
    date: str                                    # "2026-07-05"
    time: str | None = None                      # "14:32"
    type: str                                    # mastery_gain | mastery_milestone |
                                                 # exercise_done | concept_started |
                                                 # profile_created | question_asked |
                                                 # resource_generated | feedback_given |
                                                 # streak_milestone | forgetting_warning
    icon: str = "●"
    title: str = ""
    description: str = ""
    node_id: str | None = None
    node_name: str | None = None
    score_before: float | None = None
    score_after: float | None = None
    chapter_id: str | None = None


class DailySummary(BaseModel):
    """单日学习摘要。"""
    date: str
    active_score: int = 0                         # 0-6 复合活跃度
    event_count: int = 0
    top_event: TimelineEvent | None = None
    events: list[TimelineEvent] = Field(default_factory=list)


class WeeklySummary(BaseModel):
    """单周学习摘要。"""
    week_start: str
    week_label: str                               # "7月第一周"
    active_days: int = 0
    total_score: int = 0
    days: list[DailySummary] = Field(default_factory=list)


class MonthlySummary(BaseModel):
    """单月学习摘要。"""
    month: str                                    # "2026-07"
    month_label: str                              # "2026年7月"
    active_days: int = 0
    weeks: list[WeeklySummary] = Field(default_factory=list)
    # 当月统计
    new_concepts: int = 0
    exercises_done: int = 0
    questions_asked: int = 0


class ForgettingNode(BaseModel):
    """即将遗忘的知识点预警。"""
    node_id: str
    node_name: str
    mastery_score: float
    days_since_review: int
    estimated_forgetting_rate: float              # 估算遗忘比例 (0-1)
    threshold_days: int                           # 该知识点的遗忘阈值天数
    urgency: str                                  # "low" | "medium" | "high"


class LearningStats(BaseModel):
    """学习统计概览。"""
    total_active_days: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    mastered_concepts: int = 0                    # mastery >= 0.6
    strong_concepts: int = 0                      # mastery >= 0.8
    total_exercises: int = 0
    total_questions: int = 0
    total_feedback: int = 0
    # 趋势
    this_week_days: int = 0
    last_week_days: int = 0
    week_trend: str = "stable"                    # "up" | "down" | "stable"


class TimelineResponse(BaseModel):
    """成长时间轴完整响应。"""
    student_id: str
    months: list[MonthlySummary] = Field(default_factory=list)
    stats: LearningStats = Field(default_factory=LearningStats)
    forgetting_soon: list[ForgettingNode] = Field(default_factory=list)
    generated_at: str = ""
