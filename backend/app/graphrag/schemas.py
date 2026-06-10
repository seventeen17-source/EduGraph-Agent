from typing import Any

from pydantic import BaseModel, Field

from app.graph.models import GraphNode, GraphPath


class StudentProfileInput(BaseModel):
    weak_points: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    goal: str | None = None
    mastery: dict[str, float] = Field(default_factory=dict)


class EvidenceQueryRequest(BaseModel):
    query: str
    student_profile: StudentProfileInput | None = None
    top_k: int = 8


class EvidencePackage(BaseModel):
    query: str
    resolved_uid: str | None = None
    center_node: GraphNode | None = None
    prerequisites: list[GraphPath] = Field(default_factory=list)
    related_nodes: list[GraphPath] = Field(default_factory=list)
    exercises: list[GraphNode] = Field(default_factory=list)
    document_chunks: list[GraphNode] = Field(default_factory=list)
    code_cases: list[GraphNode] = Field(default_factory=list)
    misconceptions: list[GraphNode] = Field(default_factory=list)
    graph_paths: list[GraphPath] = Field(default_factory=list)
    sources: list[GraphNode] = Field(default_factory=list)
    ranking_reason: list[str] = Field(default_factory=list)
    student_profile_adaptation: dict[str, Any] = Field(default_factory=dict)
    uncertainty: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
