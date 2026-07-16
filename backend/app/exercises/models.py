from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.relational import Base


def new_id() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.utcnow()


class ExerciseSession(Base):
    __tablename__ = "exercise_sessions"
    __table_args__ = (
        Index("ix_exercise_sessions_student_submitted", "student_id", "submitted_at"),
        Index("ix_exercise_sessions_student_node", "student_id", "target_node_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    round_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    source_type: Mapped[str] = mapped_column(String(80), default="exercise_page")
    source_id: Mapped[str] = mapped_column(String(160), default="")
    target_node_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    target_node_name: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(240), default="")
    status: Mapped[str] = mapped_column(String(40), default="submitted")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    mastery_before_json: Mapped[dict] = mapped_column(JSON, default=dict)
    mastery_after_json: Mapped[dict] = mapped_column(JSON, default=dict)
    weak_nodes_json: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"
    __table_args__ = (
        Index("ix_exercise_attempts_student_node", "student_id", "related_node_id"),
        Index("ix_exercise_attempts_student_correct", "student_id", "is_correct"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("exercise_sessions.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(180), default="", index=True)
    exercise_title: Mapped[str] = mapped_column(String(260), default="")
    exercise_type: Mapped[str] = mapped_column(String(60), default="")
    related_node_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    related_node_name: Mapped[str] = mapped_column(String(200), default="")
    exercise_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    student_answer_json: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_answer_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_correct: Mapped[bool] = mapped_column(default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    cognitive_level: Mapped[str] = mapped_column(String(60), default="understand")
    used_hint: Mapped[bool] = mapped_column(default=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    feedback_json: Mapped[dict] = mapped_column(JSON, default=dict)
    misconception_tags_json: Mapped[list] = mapped_column(JSON, default=list)
    source_uids_json: Mapped[list] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String(40), default="practice")
    viewed_answer: Mapped[bool] = mapped_column(default=False)
    grading_method: Mapped[str] = mapped_column(String(40), default="rule")
    grading_status: Mapped[str] = mapped_column(String(40), default="graded")
    grading_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    profile_update_allowed: Mapped[bool] = mapped_column(default=True)
    error_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExerciseReview(Base):
    __tablename__ = "exercise_reviews"
    __table_args__ = (Index("ix_exercise_reviews_student_created", "student_id", "reviewed_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str] = mapped_column(String(64), ForeignKey("exercise_attempts.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    review_session_id: Mapped[str] = mapped_column(String(64), default="")
    review_result: Mapped[str] = mapped_column(String(40), default="")
    mastery_delta: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExerciseBookmark(Base):
    __tablename__ = "exercise_bookmarks"
    __table_args__ = (Index("ix_exercise_bookmarks_student_attempt", "student_id", "attempt_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str] = mapped_column(String(64), ForeignKey("exercise_attempts.id", ondelete="CASCADE"), index=True)
    tag: Mapped[str] = mapped_column(String(80), default="review_later")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
