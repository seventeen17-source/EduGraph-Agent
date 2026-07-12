from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.relational import Base


def new_id() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.utcnow()


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    profile: Mapped["StudentProfileRecord"] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        uselist=False,
    )


class StudentProfileRecord(Base):
    __tablename__ = "student_profiles"

    student_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("students.id", ondelete="CASCADE"),
        primary_key=True,
    )
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
    background_json: Mapped[dict] = mapped_column(JSON, default=dict)
    learning_goal_json: Mapped[dict] = mapped_column(JSON, default=dict)
    knowledge_base_json: Mapped[dict] = mapped_column(JSON, default=dict)
    progress_json: Mapped[dict] = mapped_column(JSON, default=dict)
    cognitive_style_json: Mapped[dict] = mapped_column(JSON, default=dict)
    weak_points_json: Mapped[dict] = mapped_column(JSON, default=dict)
    preferences_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ability_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    learning_behavior_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    student: Mapped[Student] = relationship(back_populates="profile")


class StudentNodeMastery(Base):
    __tablename__ = "student_node_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "node_id", name="uq_student_node_mastery"),
        Index("ix_student_node_mastery_student_chapter", "student_id", "chapter_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(120), index=True)
    node_name: Mapped[str] = mapped_column(String(200), default="")
    chapter_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    level: Mapped[str] = mapped_column(String(40), default="weak")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ProfileUpdateEvent(Base):
    __tablename__ = "profile_update_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[str] = mapped_column(String(80), default="system")
    trigger_detail: Mapped[str] = mapped_column(String(200), default="")
    updated_fields_json: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ProfileChatMessage(Base):
    __tablename__ = "profile_chat_messages"
    __table_args__ = (Index("ix_profile_chat_messages_student_created", "student_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    round_no: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MasteryEvidence(Base):
    __tablename__ = "mastery_evidence"
    __table_args__ = (Index("ix_mastery_evidence_student_node", "student_id", "node_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(120), index=True)
    source_type: Mapped[str] = mapped_column(String(80), default="")
    source_id: Mapped[str] = mapped_column(String(160), default="")
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_delta: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
