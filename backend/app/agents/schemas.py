from typing import Any, Literal

from pydantic import BaseModel, Field

from app.graph.models import GraphNode
from app.graphrag.schemas import EvidencePackage, StudentProfileInput


ResourceType = Literal["document", "mindmap", "exercise", "video_script", "code_case"]


class ResourceGenerateRequest(BaseModel):
    query: str = ""
    node_id: str | None = None
    student_id: str | None = None
    student_profile: StudentProfileInput | None = None
    exercise_count: int | None = Field(default=None, ge=1, le=20)
    exercise_type: Literal["choice", "short_answer", "coding", "case_analysis"] | None = None
    resource_types: list[ResourceType] = Field(
        default_factory=lambda: ["document", "mindmap", "exercise", "video_script", "code_case"],
    )


class GeneratedDocument(BaseModel):
    title: str = ""
    content: str = ""
    key_points: list[str] = Field(default_factory=list)
    source_uids: list[str] = Field(default_factory=list)


class GeneratedMindmap(BaseModel):
    title: str = ""
    format: Literal["mermaid"] = "mermaid"
    content: str = ""
    source_uids: list[str] = Field(default_factory=list)


class GeneratedExercise(BaseModel):
    title: str = ""
    type: Literal["choice", "short_answer", "coding", "case_analysis"] = "choice"
    related_node_id: str = ""
    difficulty: int = Field(default=3, ge=1, le=5)
    question: str = ""
    options: list[dict[str, str]] = Field(default_factory=list)
    answer: dict[str, Any] = Field(default_factory=dict)
    adaptive_feedback: dict[str, Any] = Field(default_factory=dict)
    source_uids: list[str] = Field(default_factory=list)


class GeneratedExercises(BaseModel):
    items: list[GeneratedExercise] = Field(default_factory=list)


class VideoScene(BaseModel):
    scene_no: int = Field(default=1, ge=1)
    title: str = ""
    visual: str = ""
    narration: str = ""
    animation_hint: str = ""


class GeneratedVideoScript(BaseModel):
    title: str = ""
    target_duration_seconds: int = Field(default=120, ge=30, le=600)
    scenes: list[VideoScene] = Field(default_factory=list)
    source_uids: list[str] = Field(default_factory=list)


class GeneratedCodeCase(BaseModel):
    title: str = ""
    language: Literal["python"] = "python"
    related_node_id: str = ""
    code: str = ""
    explanation: str = ""
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    source_uids: list[str] = Field(default_factory=list)


class GeneratedResources(BaseModel):
    document: GeneratedDocument | None = None
    mindmap: GeneratedMindmap | None = None
    exercises: list[GeneratedExercise] = Field(default_factory=list)
    video_script: GeneratedVideoScript | None = None
    code_case: GeneratedCodeCase | None = None


class QualityReport(BaseModel):
    grounded: bool = False
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    source_uids: list[str] = Field(default_factory=list)


class AgentTraceItem(BaseModel):
    agent: str
    status: Literal["done", "skipped", "failed"]
    summary: str = ""


class ResourceGenerateResponse(BaseModel):
    resource_record_id: str | None = None
    query: str
    resolved_uid: str | None = None
    center_node: GraphNode | None = None
    evidence: EvidencePackage
    resources: GeneratedResources
    quality_report: QualityReport
    agent_trace: list[AgentTraceItem] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    # 解析质量
    resolution_quality: str = Field(default="exact", description="exact=精确匹配, fallback=降级匹配, none=无匹配")
    suggested_alternatives: list[dict] = Field(default_factory=list, description="建议的备选知识点")
    resolution_notice: str = Field(default="", description="给用户的解析说明")


class ResourceCenterItem(BaseModel):
    id: str
    student_id: str = ""
    query: str = ""
    resolved_uid: str = ""
    center_node_name: str = ""
    resource_types: list[ResourceType] = Field(default_factory=list)
    quality_score: float = 0.0
    created_at: str


class ResourceCenterListResponse(BaseModel):
    items: list[ResourceCenterItem] = Field(default_factory=list)


class ResourceCenterDetail(BaseModel):
    id: str
    student_id: str = ""
    query: str = ""
    resolved_uid: str = ""
    center_node_name: str = ""
    resource_types: list[ResourceType] = Field(default_factory=list)
    resources: GeneratedResources
    evidence: EvidencePackage
    quality_report: QualityReport
    agent_trace: list[AgentTraceItem] = Field(default_factory=list)
    quality_score: float = 0.0
    created_at: str


class ResourceMindmapUpdateRequest(BaseModel):
    title: str | None = None
    content: str
