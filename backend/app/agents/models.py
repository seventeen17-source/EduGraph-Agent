from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.relational import Base
from app.profile.models import new_id, utcnow


class GeneratedResourceRecord(Base):
    __tablename__ = "generated_resource_records"
    __table_args__ = (
        Index("ix_generated_resources_student_created", "student_id", "created_at"),
        Index("ix_generated_resources_node_created", "resolved_uid", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    query: Mapped[str] = mapped_column(Text, default="")
    resolved_uid: Mapped[str] = mapped_column(String(120), default="", index=True)
    center_node_name: Mapped[str] = mapped_column(String(200), default="")
    resource_types_json: Mapped[list] = mapped_column(JSON, default=list)
    resources_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    agent_trace_json: Mapped[list] = mapped_column(JSON, default=list)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
