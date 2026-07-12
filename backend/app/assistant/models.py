from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.relational import Base


def new_id() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.utcnow()


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"
    __table_args__ = (Index("ix_assistant_conversations_student_updated", "student_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="学习助手会话")
    last_intent: Mapped[str] = mapped_column(String(80), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    messages: Mapped[list["AssistantMessage"]] = relationship(back_populates="conversation")


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    __table_args__ = (Index("ix_assistant_messages_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    intent: Mapped[str] = mapped_column(String(80), default="")
    target_node_id: Mapped[str] = mapped_column(String(120), default="")
    agent_trace_json: Mapped[list] = mapped_column(JSON, default=list)
    actions_json: Mapped[list] = mapped_column(JSON, default=list)
    resource_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[AssistantConversation] = relationship(back_populates="messages")


class AssistantRun(Base):
    __tablename__ = "assistant_runs"
    __table_args__ = (Index("ix_assistant_runs_student_created", "student_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(40), default="running")
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    agent_trace_json: Mapped[list] = mapped_column(JSON, default=list)
    actions_json: Mapped[list] = mapped_column(JSON, default=list)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssistantActionRecord(Base):
    __tablename__ = "assistant_actions"
    __table_args__ = (Index("ix_assistant_actions_run", "run_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    action_type: Mapped[str] = mapped_column(String(80), default="navigation")
    label: Mapped[str] = mapped_column(String(160), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssistantFeedback(Base):
    """学生对助手回复的反馈。

    每条反馈关联到一条 assistant 消息。
    标签可多选（如同时选"有帮助"+"想要例子"）。
    """

    __tablename__ = "assistant_feedback"
    __table_args__ = (
        Index("ix_feedback_student_created", "student_id", "created_at"),
        Index("ix_feedback_message", "message_id"),
        Index("ix_feedback_intent", "intent"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("assistant_messages.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[str] = mapped_column(String(64), default="")
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")

    # 反馈内容
    tags: Mapped[list] = mapped_column(JSON, default=list)
    # ["helpful", "clear", "dont_get", "too_hard", "too_easy",
    #  "too_vague", "want_examples", "want_summary", "incorrect"]
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 冗余字段（加速聚合）
    intent: Mapped[str] = mapped_column(String(80), default="")
    target_node_id: Mapped[str] = mapped_column(String(120), default="")

    # 回复特征（写入时从消息中提取，便于分析）
    reply_features: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"length": 850, "has_code": true, "has_formula": true,
    #  "has_diagram": false, "style": "公式推导+代码示例"}

    # 分析状态
    analyzed: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)