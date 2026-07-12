from __future__ import annotations

from app.graph.models import GraphNode
from app.graphrag.langgraph.state import EvidenceQualityReport, RepairAction
from app.graphrag.schemas import EvidencePackage, StudentProfileInput
from app.rag.schemas import CourseSemanticHit


def grade_evidence_package(
    *,
    evidence: EvidencePackage | None,
    semantic_hits: list[CourseSemanticHit],
    profile: StudentProfileInput,
    resolution_quality: str,
) -> EvidenceQualityReport:
    if evidence is None:
        return {
            "coverage_score": 0.0,
            "relevance_score": 0.0,
            "grounding_score": 0.0,
            "personal_fit_score": 0.0,
            "overall_score": 0.0,
            "missing_categories": ["center_node", "canonical_evidence"],
            "weak_reasons": ["没有形成可用证据包"],
            "repair_actions": ["ask_clarification"],
            "enough": False,
        }

    missing: list[str] = []
    weak_reasons: list[str] = []
    repair_actions: list[RepairAction] = []

    has_doc = bool(evidence.document_chunks)
    has_code = bool(evidence.code_cases)
    has_exercise = bool(evidence.exercises)
    has_faq = bool(evidence.misconceptions)
    has_prereq = bool(evidence.prerequisites or evidence.dependency_paths)
    coverage_parts = [has_doc, has_code, has_exercise, has_faq, has_prereq]
    coverage_score = sum(1 for item in coverage_parts if item) / len(coverage_parts)

    if not has_doc:
        missing.append("document_chunks")
        repair_actions.append("expand_related_nodes")
    if not has_faq:
        missing.append("misconceptions")
        repair_actions.append("global_semantic_search")
    if not has_code and _prefers(profile, "code_case", "code"):
        missing.append("code_cases")
        repair_actions.append("profile_guided_search")
    if not has_exercise:
        missing.append("exercises")
        repair_actions.append("expand_prerequisites")
    if not has_prereq:
        missing.append("prerequisites")
        repair_actions.append("expand_prerequisites")

    semantic_top = max((hit.semantic_score for hit in semantic_hits), default=0.0)
    relevance_score = max(float(getattr(evidence, "relevance_score", 0.0) or 0.0), semantic_top)
    if evidence.resolved_uid and evidence.resolved_uid in evidence.query:
        relevance_score = max(relevance_score, 0.75)
    if resolution_quality == "fallback":
        relevance_score = min(relevance_score, 0.68)
        weak_reasons.append("知识点定位为降级匹配，需要在回答中提示不确定性")
    if resolution_quality == "none":
        relevance_score = min(relevance_score, 0.35)
        weak_reasons.append("未定位到中心知识点")
        repair_actions.append("ask_clarification")

    grounded_nodes = [
        *evidence.document_chunks,
        *evidence.code_cases,
        *evidence.exercises,
        *evidence.misconceptions,
    ]
    grounding_score = _grounding_score(grounded_nodes, bool(evidence.sources))
    if grounding_score < 0.45:
        weak_reasons.append("证据来源链较弱，生成回答时应降低确定性")

    personal_fit_score = _personal_fit_score(evidence, semantic_hits, profile)
    if personal_fit_score < 0.35 and (profile.weak_points or profile.preferences):
        weak_reasons.append("证据与学生画像匹配度偏低")
        repair_actions.append("profile_guided_search")

    if coverage_score < 0.6:
        weak_reasons.append("证据类型覆盖不足")
    if relevance_score < 0.55:
        weak_reasons.append("语义相关性不足")
        repair_actions.append("global_semantic_search")

    overall_score = round(
        coverage_score * 0.30
        + relevance_score * 0.30
        + grounding_score * 0.20
        + personal_fit_score * 0.20,
        3,
    )
    repair_actions = _dedupe_actions(repair_actions)

    return {
        "coverage_score": round(coverage_score, 3),
        "relevance_score": round(relevance_score, 3),
        "grounding_score": round(grounding_score, 3),
        "personal_fit_score": round(personal_fit_score, 3),
        "overall_score": overall_score,
        "missing_categories": list(dict.fromkeys(missing)),
        "weak_reasons": list(dict.fromkeys(weak_reasons)),
        "repair_actions": repair_actions,
        "enough": overall_score >= 0.70 and resolution_quality != "none",
    }


def choose_repair_action(report: EvidenceQualityReport, attempts: int, max_attempts: int) -> RepairAction:
    if report.get("enough"):
        return "finalize_with_warning"
    if attempts >= max_attempts:
        return "finalize_with_warning"
    for action in report.get("repair_actions", []):
        if action != "ask_clarification":
            return action
    return "ask_clarification"


def _prefers(profile: StudentProfileInput, *values: str) -> bool:
    prefs = set(profile.preferences or [])
    return any(value in prefs for value in values)


def _grounding_score(nodes: list[GraphNode], has_sources: bool) -> float:
    if not nodes:
        return 0.0
    with_source = 0
    semantic_grounded = 0
    for node in nodes:
        props = node.properties or {}
        if props.get("source_ids") or props.get("source_uids"):
            with_source += 1
        if props.get("_semantic_match"):
            semantic_grounded += 1
    source_ratio = with_source / len(nodes)
    semantic_bonus = min(0.2, semantic_grounded * 0.05)
    base = 0.45 + source_ratio * 0.35 + semantic_bonus
    if has_sources:
        base += 0.15
    return round(min(1.0, base), 3)


def _personal_fit_score(
    evidence: EvidencePackage,
    semantic_hits: list[CourseSemanticHit],
    profile: StudentProfileInput,
) -> float:
    if not profile.weak_points and not profile.preferences and not profile.mastery:
        return 0.55

    score = 0.2
    weak_points = set(profile.weak_points or [])
    if weak_points:
        hit_nodes = set()
        for hit in semantic_hits:
            hit_nodes.update(hit.view.node_ids)
        for path in [*evidence.prerequisites, *evidence.related_nodes]:
            hit_nodes.update(node.uid for node in path.nodes)
        if weak_points.intersection(hit_nodes):
            score += 0.35

    if _prefers(profile, "code_case", "code") and evidence.code_cases:
        score += 0.18
    if _prefers(profile, "exercise") and evidence.exercises:
        score += 0.18
    if _prefers(profile, "document", "diagram", "mindmap") and evidence.document_chunks:
        score += 0.14

    low_mastery_nodes = {uid for uid, mastery in (profile.mastery or {}).items() if mastery < 0.5}
    if low_mastery_nodes:
        evidence_nodes = {hit.view.target_uid for hit in semantic_hits}
        if low_mastery_nodes.intersection(evidence_nodes):
            score += 0.15

    return round(min(1.0, score), 3)


def _dedupe_actions(actions: list[RepairAction]) -> list[RepairAction]:
    ordered = [
        "profile_guided_search",
        "global_semantic_search",
        "expand_related_nodes",
        "expand_prerequisites",
        "ask_clarification",
        "finalize_with_warning",
    ]
    present = set(actions)
    return [action for action in ordered if action in present]
