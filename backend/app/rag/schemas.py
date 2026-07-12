from typing import Literal

from pydantic import BaseModel, Field


SemanticTargetType = Literal[
    "KnowledgePoint",
    "DocumentChunk",
    "Misconception",
    "Exercise",
    "CodeCase",
]

SemanticViewType = Literal[
    "student_confusion",
    "concept_explanation",
    "error_diagnosis",
    "code_intent",
    "learning_action",
    "raw_summary",
]


class CourseSemanticView(BaseModel):
    """A semantic retrieval view that points back to canonical Neo4j evidence."""

    id: str
    text: str
    target_uid: str
    target_type: SemanticTargetType
    view_type: SemanticViewType
    node_ids: list[str] = Field(default_factory=list)
    chapter_id: str = ""
    source_uids: list[str] = Field(default_factory=list)
    title: str = ""
    difficulty: int | None = None
    cognitive_level: str = ""
    tags: list[str] = Field(default_factory=list)


class CourseSemanticHit(BaseModel):
    view: CourseSemanticView
    score: float = 0.0
    semantic_score: float = 0.0
    graph_bonus: float = 0.0
    profile_bonus: float = 0.0
    rank_reason: list[str] = Field(default_factory=list)
