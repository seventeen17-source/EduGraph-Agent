from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.profile.schemas import ProfileDashboardResponse, ProfileUpdateRecord, StudentProfile


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


class ExerciseSessionSubmitRequest(BaseModel):
    student_id: str
    round_id: str | None = None
    source_type: str = "exercise_page"
    source_id: str = ""
    target_node_id: str = ""
    target_node_name: str = ""
    title: str = ""
    duration_seconds: int = 0
    started_at: datetime | None = None
    attempts: list[ExerciseAttemptSubmit]


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
