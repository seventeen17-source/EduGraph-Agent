from pydantic import BaseModel, Field

from app.graphrag.schemas import StudentProfileInput


class DiagnosisRecommendRequest(BaseModel):
    student_profile: StudentProfileInput
    top_k: int = 5
    node_mastery: dict[str, dict] = Field(default_factory=dict)  # uid -> {mastery_score, confidence, ...}


class DiagnosisRecommendResponse(BaseModel):
    recommended_nodes: list[str] = Field(default_factory=list)
    recommended_exercises: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    node_priorities: dict[str, float] = Field(default_factory=dict)  # uid -> priority score
    sorted_by_prerequisites: bool = False
