from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.graph.models import GraphNode, GraphPath
from app.graphrag.schemas import EvidencePackage, StudentProfileInput
from app.rag.schemas import CourseSemanticHit


RepairAction = Literal[
    "expand_related_nodes",
    "expand_prerequisites",
    "global_semantic_search",
    "profile_guided_search",
    "ask_clarification",
    "finalize_with_warning",
]


class HybridRAGTraceItem(TypedDict, total=False):
    node: str
    status: str
    summary: str
    metadata: dict[str, Any]


class EvidenceQualityReport(TypedDict, total=False):
    coverage_score: float
    relevance_score: float
    grounding_score: float
    personal_fit_score: float
    overall_score: float
    missing_categories: list[str]
    weak_reasons: list[str]
    repair_actions: list[RepairAction]
    enough: bool


class GraphContext(TypedDict, total=False):
    center_node: GraphNode | None
    prerequisites: list[GraphPath]
    related_nodes: list[GraphPath]
    dependency_paths: list[Any]
    document_chunks: list[GraphNode]
    exercises: list[GraphNode]
    code_cases: list[GraphNode]
    misconceptions: list[GraphNode]
    sources: list[GraphNode]
    candidate_node_ids: list[str]


class HybridRAGState(TypedDict, total=False):
    query: str
    normalized_query: str
    student_id: str | None
    student_profile: StudentProfileInput
    requested_center_uid: str | None

    intent: str
    query_type: str
    target_uid: str | None
    resolution_quality: str
    candidate_nodes: list[dict[str, Any]]
    suggested_alternatives: list[dict[str, Any]]

    graph_context: GraphContext
    semantic_hits: list[CourseSemanticHit]
    memory_hits: list[dict[str, Any]]
    merge_report: dict[str, Any]

    evidence_package: EvidencePackage | None
    quality_report: EvidenceQualityReport
    repair_attempts: int
    max_repair_attempts: int
    repair_actions: list[RepairAction]
    pending_repair_action: RepairAction | None

    warnings: list[str]
    trace: list[HybridRAGTraceItem]
