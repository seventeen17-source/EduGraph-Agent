from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.graphrag.schemas import StudentProfileInput
from app.profile.schemas import ProfileDashboardResponse, ProfileUpdateRecord, StudentProfile


ExerciseSourceType = Literal["all", "knowledge_base", "ai_generated", "mistake", "recommended"]


class ExerciseAttemptSubmit(BaseModel):
    exercise_id: str = ""
    exercise_title: str = ""
    exercise_type: str = ""
    related_node_id: str = ""
    related_node_name: str = ""
    exercise_snapshot: dict[str, Any] = Field(default_factory=dict)
    student_answer: dict[str, Any] = Field(default_factory=dict)
    expected_answer: dict[str, Any] = Field(default_factory=dict)
    is_correct: bool | None = None
    score: float | None = None
    difficulty: int = 3
    cognitive_level: str = "understand"
    used_hint: bool = False
    time_spent_seconds: int = 0
    feedback: dict[str, Any] = Field(default_factory=dict)
    misconception_tags: list[str] = Field(default_factory=list)
    source_uids: list[str] = Field(default_factory=list)
    mode: str = "practice"
    viewed_answer: bool = False
    grading_method: str | None = None
    grading_status: str | None = None
    grading_confidence: float | None = None
    profile_update_allowed: bool | None = None


class ExerciseSessionSubmitRequest(BaseModel):
    student_id: str
    round_id: str | None = None
    source_type: str = "exercise_page"
    source_id: str = ""
    target_node_id: str = ""
    target_node_name: str = ""
    title: str = ""
    mode: str = "practice"
    duration_seconds: int = 0
    started_at: datetime | None = None
    attempts: list[ExerciseAttemptSubmit]


class ExerciseSearchRequest(BaseModel):
    query: str = ""
    student_id: str | None = None
    source_type: ExerciseSourceType = "all"
    limit: int = Field(default=30, ge=1, le=100)
    node_id: str | None = None
    student_profile: StudentProfileInput | None = None


class ExerciseSearchItem(BaseModel):
    id: str
    source_type: Literal["knowledge_base", "ai_generated", "mistake", "recommended"]
    source_label: str = ""
    source_id: str = ""
    resource_record_id: str | None = None
    attempt_id: str | None = None
    title: str = ""
    type: str = "choice"
    related_node_id: str = ""
    related_node_name: str = ""
    difficulty: int = 3
    question: str = ""
    options: list[dict[str, Any]] = Field(default_factory=list)
    answer: dict[str, Any] = Field(default_factory=dict)
    adaptive_feedback: dict[str, Any] = Field(default_factory=dict)
    source_uids: list[str] = Field(default_factory=list)
    exercise_snapshot: dict[str, Any] = Field(default_factory=dict)
    rank_reason: list[str] = Field(default_factory=list)
    review_type: str | None = None
    review_score: float | None = None
    review_reasons: list[str] = Field(default_factory=list)
    recommended_node_id: str | None = None
    created_at: datetime | None = None


class ExerciseSearchResponse(BaseModel):
    query: str
    source_type: ExerciseSourceType
    total: int
    items: list[ExerciseSearchItem] = Field(default_factory=list)


class ExerciseAttemptRecord(BaseModel):
    id: str
    session_id: str
    student_id: str
    exercise_id: str
    exercise_title: str
    exercise_type: str
    related_node_id: str
    related_node_name: str
    exercise_snapshot: dict[str, Any]
    student_answer: dict[str, Any]
    expected_answer: dict[str, Any]
    is_correct: bool
    score: float
    difficulty: int
    cognitive_level: str
    used_hint: bool
    time_spent_seconds: int
    feedback: dict[str, Any]
    misconception_tags: list[str]
    source_uids: list[str]
    mode: str
    viewed_answer: bool
    grading_method: str
    grading_status: str = "graded"
    grading_confidence: float = 1.0
    profile_update_allowed: bool = True
    error_type: str | None = None
    created_at: datetime


class ExerciseSessionRecord(BaseModel):
    id: str
    student_id: str
    round_id: str
    source_type: str
    source_id: str
    target_node_id: str
    target_node_name: str
    title: str
    status: str
    total_count: int
    answered_count: int
    correct_count: int
    accuracy: float
    duration_seconds: int
    mastery_before: dict[str, float]
    mastery_after: dict[str, float]
    weak_nodes: list[str]
    summary: str
    started_at: datetime | None
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime
    attempts: list[ExerciseAttemptRecord] = Field(default_factory=list)


class ExerciseSessionListResponse(BaseModel):
    student_id: str
    total: int
    items: list[ExerciseSessionRecord]


class ExerciseMistakeListResponse(BaseModel):
    student_id: str
    total: int
    items: list[ExerciseAttemptRecord]


class ExerciseStatsResponse(BaseModel):
    student_id: str
    total_sessions: int
    total_attempts: int
    correct_attempts: int
    accuracy: float
    mistake_count: int
    practiced_nodes: int
    recent_accuracy: float
    weak_node_counts: dict[str, int]


class ExerciseSessionSubmitResponse(BaseModel):
    session: ExerciseSessionRecord
    profile: StudentProfile
    dashboard: ProfileDashboardResponse
    updated_node_mastery: list[str]
    update_event: ProfileUpdateRecord


class ExerciseBookmarkRequest(BaseModel):
    student_id: str
    tag: str = "review_later"
    note: str = ""


class ExerciseReviewRequest(BaseModel):
    student_id: str
    review_result: Literal["correct", "wrong", "partial", "skipped"]
    review_session_id: str = ""
    mastery_delta: float = 0.0
    notes: str = ""


class ExerciseActionResponse(BaseModel):
    ok: bool = True
    id: str = ""
