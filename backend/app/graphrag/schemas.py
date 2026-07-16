from typing import Any

from pydantic import BaseModel, Field

from app.graph.models import DependencyPath, GraphNode, GraphPath, MultiHopSummary
from app.rag.schemas import CourseSemanticHit


class StudentProfileInput(BaseModel):
    weak_points: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    goal: str | None = None
    # 多目标支持：可携带多个学习目标，供诊断推荐按目标分别匹配
    goals: list[str] = Field(default_factory=list)
    mastery: dict[str, float] = Field(default_factory=dict)


class EvidenceQueryRequest(BaseModel):
    query: str
    student_profile: StudentProfileInput | None = None
    student_id: str | None = None
    top_k: int = 8


class SemanticSearchHitDebug(BaseModel):
    id: str
    target_uid: str
    target_type: str
    view_type: str
    title: str = ""
    text_preview: str = ""
    node_ids: list[str] = Field(default_factory=list)
    chapter_id: str = ""
    source_uids: list[str] = Field(default_factory=list)
    difficulty: int | None = None
    cognitive_level: str = ""
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0
    semantic_score: float = 0.0
    graph_bonus: float = 0.0
    profile_bonus: float = 0.0
    rank_reason: list[str] = Field(default_factory=list)


class SemanticSearchDebugResponse(BaseModel):
    query: str
    center_uid: str | None = None
    resolution_quality: str = "none"
    candidate_node_ids: list[str] = Field(default_factory=list)
    top_k: int = 10
    hits: list[SemanticSearchHitDebug] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CoverageStats(BaseModel):
    """证据包覆盖统计"""
    exercises_count: int = 0
    document_chunks_count: int = 0
    code_cases_count: int = 0
    misconceptions_count: int = 0
    prerequisites_count: int = 0
    related_nodes_count: int = 0
    sources_count: int = 0


class EvidenceCompleteness(BaseModel):
    """证据完整性评估"""
    has_document: bool = False
    has_code_case: bool = False
    has_exercises: bool = False
    has_misconceptions: bool = False
    has_prerequisites: bool = False
    completeness_score: float = 0.0  # 0-1
    missing_categories: list[str] = Field(default_factory=list)


class EvidencePackage(BaseModel):
    query: str
    resolved_uid: str | None = None
    center_node: GraphNode | None = None
    query_type: str = Field(default="general", description="查询类型：concept_explanation / exercise_help / path_plan / assessment_review / general")
    evidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="证据包质量评分，0-1")
    relation_summary: list[str] = Field(default_factory=list, description="关键关系摘要，每条一行描述一个核心关系")
    recommended_next_actions: list[str] = Field(default_factory=list, description="推荐的下一步学习动作")
    prerequisites: list[GraphPath] = Field(default_factory=list)
    related_nodes: list[GraphPath] = Field(default_factory=list)
    exercises: list[GraphNode] = Field(default_factory=list)
    document_chunks: list[GraphNode] = Field(default_factory=list)
    code_cases: list[GraphNode] = Field(default_factory=list)
    misconceptions: list[GraphNode] = Field(default_factory=list)
    semantic_hits: list[CourseSemanticHit] = Field(default_factory=list, description="课程语义入口命中，指向 Neo4j canonical evidence")
    graph_paths: list[GraphPath] = Field(default_factory=list)
    sources: list[GraphNode] = Field(default_factory=list)
    ranking_reason: list[str] = Field(default_factory=list)
    student_profile_adaptation: dict[str, Any] = Field(default_factory=dict)
    uncertainty: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    # 新增质量字段
    coverage_stats: CoverageStats = Field(default_factory=CoverageStats, description="各类型证据的数量统计")
    evidence_completeness: EvidenceCompleteness = Field(default_factory=EvidenceCompleteness, description="证据完整性评估")
    resource_diversity: float = Field(default=0.0, ge=0.0, le=1.0, description="资源多样性评分，0-1，衡量是否有多种类型的证据")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="与查询的相关性评分，0-1")
    # 多跳依赖
    multi_hop_summary: MultiHopSummary | None = Field(default=None, description="多跳依赖分析摘要")
    dependency_paths: list[DependencyPath] = Field(default_factory=list, description="多跳依赖路径列表")
    # 解析质量
    resolution_quality: str = Field(default="exact", description="解析质量：exact=精确匹配, fallback=降级匹配, none=无匹配")
    suggested_alternatives: list[dict] = Field(default_factory=list, description="建议的备选知识点 [{uid, name, reason}]")
