from pydantic import BaseModel, Field

from app.graphrag.schemas import StudentProfileInput


class DiagnosisRecommendRequest(BaseModel):
    student_profile: StudentProfileInput
    top_k: int = 5


class DiagnosisRecommendResponse(BaseModel):
    recommended_nodes: list[str] = Field(default_factory=list)
    recommended_exercises: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
