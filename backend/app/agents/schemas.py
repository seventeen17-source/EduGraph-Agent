from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.graph.models import GraphNode
from app.graphrag.schemas import EvidencePackage, StudentProfileInput


ResourceType = Literal["document", "mindmap", "exercise", "video_script", "code_case", "image"]
ResourceGenerationStatus = Literal["success", "partial_success", "failed"]


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
    illustrations: list["GeneratedImage"] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_container(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in ("document", "generated_document", "resource"):
                nested = value.get(key)
                if isinstance(nested, dict):
                    return nested
        return value


class GeneratedMindmap(BaseModel):
    title: str = ""
    format: Literal["mermaid"] = "mermaid"
    content: str = ""
    source_uids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_container(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in ("mindmap", "diagram", "generated_mindmap", "resource"):
                nested = value.get(key)
                if isinstance(nested, dict):
                    return nested
        return value


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

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: Any) -> str:
        text = str(value or "choice").strip().lower()
        mapping = {
            "single_choice": "choice",
            "multiple_choice": "choice",
            "单选题": "choice",
            "选择题": "choice",
            "简答题": "short_answer",
            "问答题": "short_answer",
            "编程题": "coding",
            "代码题": "coding",
            "案例题": "case_analysis",
            "案例分析": "case_analysis",
        }
        return mapping.get(text, text)

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, value: Any) -> int:
        if isinstance(value, (int, float)):
            return max(1, min(int(value), 5))
        text = str(value or "").strip().lower()
        mapping = {
            "easy": 2,
            "simple": 2,
            "basic": 2,
            "low": 2,
            "简单": 2,
            "基础": 2,
            "middle": 3,
            "medium": 3,
            "normal": 3,
            "中等": 3,
            "hard": 4,
            "difficult": 4,
            "advanced": 4,
            "困难": 4,
            "较难": 4,
        }
        if text in mapping:
            return mapping[text]
        try:
            return max(1, min(int(float(text)), 5))
        except (TypeError, ValueError):
            return 3

    @field_validator("answer", mode="before")
    @classmethod
    def normalize_answer(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        text = str(value or "").strip()
        if text.upper() in {"A", "B", "C", "D"}:
            return {"correct": text.upper(), "explanation": ""}
        return {"reference_answer": text} if text else {}

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, value: Any) -> list[dict[str, str]]:
        if isinstance(value, dict):
            return [
                {"label": str(label).strip().upper(), "text": str(text).strip()}
                for label, text in value.items()
            ]
        return value or []


class GeneratedExercises(BaseModel):
    items: list[GeneratedExercise] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_items_container(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, list):
            return {"items": value}
        if isinstance(value, dict):
            for key in ("questions", "exercises", "problems"):
                if key in value and "items" not in value:
                    return {"items": value.get(key) or []}
        return value


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

    @model_validator(mode="before")
    @classmethod
    def unwrap_container(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in ("video_script", "script", "generated_video_script", "resource"):
                nested = value.get(key)
                if isinstance(nested, dict):
                    return nested
        return value


class GeneratedCodeCase(BaseModel):
    title: str = ""
    language: Literal["python"] = "python"
    related_node_id: str = ""
    code: str = ""
    explanation: str = ""
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    source_uids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_container(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in ("code_case", "case", "generated_code_case", "resource"):
                nested = value.get(key)
                if isinstance(nested, dict):
                    return nested
        return value


class GeneratedImage(BaseModel):
    title: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    image_url: str = ""
    local_path: str = ""
    mime_type: str = "image/png"
    width: int | None = None
    height: int | None = None
    provider: str = "xunfei_tti"
    source_uids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_container(cls, value: Any) -> Any:
        if isinstance(value, dict):
            for key in ("image", "illustration", "generated_image", "resource"):
                nested = value.get(key)
                if isinstance(nested, dict):
                    return nested
        return value


class GeneratedResources(BaseModel):
    document: GeneratedDocument | None = None
    mindmap: GeneratedMindmap | None = None
    exercises: list[GeneratedExercise] = Field(default_factory=list)
    video_script: GeneratedVideoScript | None = None
    code_case: GeneratedCodeCase | None = None
    image: GeneratedImage | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_nulls(cls, value: Any) -> Any:
        if isinstance(value, dict):
            normalized = dict(value)
            if normalized.get("exercises") is None:
                normalized["exercises"] = []
            return normalized
        return value


class QualityReport(BaseModel):
    grounded: bool = False
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    grounding_score: float = Field(default=0.0, ge=0.0, le=1.0)
    personal_fit_score: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    weak_reasons: list[str] = Field(default_factory=list)
    repair_actions: list[str] = Field(default_factory=list)
    source_uids: list[str] = Field(default_factory=list)
    fallback_used: bool = False


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
    generation_status: ResourceGenerationStatus = "success"
    success_types: list[ResourceType] = Field(default_factory=list)
    failed_types: list[ResourceType] = Field(default_factory=list)
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
    related_nodes: list[str] = Field(default_factory=list)
    is_practiced: bool = False
    practice_accuracy: float | None = None
    source: str = "resource_generation"


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


class RetryRequest(BaseModel):
    """单独重试某类资源的请求。"""
    resource_id: str
    resource_type: ResourceType
    student_id: str = ""
