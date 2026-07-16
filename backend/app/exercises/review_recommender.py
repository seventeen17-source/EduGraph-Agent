from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.labels import choose_node_label, localize_text
from app.exercises.repository import ExerciseRepository
from app.exercises.schemas import ExerciseAttemptRecord, ExerciseSearchItem, ExerciseSearchRequest
from app.profile.schemas import KnowledgePointMastery, StudentProfile
from app.profile.service import ProfileService
from app.profile.timeline import ForgettingDetector


def _normalize(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


def _parse_maybe_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


@dataclass
class ReviewCandidate:
    node_id: str
    node_name: str = ""
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    review_types: set[str] = field(default_factory=set)
    mistake_attempts: list[ExerciseAttemptRecord] = field(default_factory=list)
    mastery_score: float | None = None
    query_matched: bool = False

    def add(self, points: float, review_type: str, reason: str) -> None:
        self.score += points
        self.review_types.add(review_type)
        if reason and reason not in self.reasons:
            self.reasons.append(reason)

    @property
    def primary_type(self) -> str:
        order = ["mistake_retry", "forgetting_review", "weak_point_review", "prereq_repair", "query_review"]
        for item in order:
            if item in self.review_types:
                return item
        return "weak_point_review"


class ReviewRecommendationService:
    """Builds explainable review exercise recommendations from real student signals."""

    def __init__(
        self,
        repository: ExerciseRepository,
        profile_service: ProfileService,
        graphrag_service: Any | None = None,
    ) -> None:
        self.repository = repository
        self.profile_service = profile_service
        self.graphrag_service = graphrag_service

    async def recommend(self, payload: ExerciseSearchRequest, limit: int) -> list[ExerciseSearchItem]:
        if not payload.student_id:
            return []

        profile = await self.profile_service.repository.ensure_profile(payload.student_id)
        candidates: dict[str, ReviewCandidate] = {}
        query = payload.query or ""
        normalized_query = _normalize(query)

        def candidate(node_id: str, node_name: str = "", *, query_matched: bool = False) -> ReviewCandidate:
            row = candidates.get(node_id)
            if row is None:
                row = ReviewCandidate(node_id=node_id, node_name=choose_node_label(node_name, node_id), query_matched=query_matched)
                candidates[node_id] = row
            if node_name and (not row.node_name or row.node_name == row.node_id):
                row.node_name = choose_node_label(node_name, node_id)
            row.query_matched = row.query_matched or query_matched
            return row

        def query_matches(node_id: str, node_name: str = "") -> bool:
            if not normalized_query:
                return True
            return normalized_query in _normalize(f"{node_id} {node_name}")

        # 1. Historical wrong answers: most concrete review signal.
        mistake_records = await self.repository.search_mistake_exercises(
            student_id=payload.student_id,
            query=query,
            limit=200,
        )
        mistakes_by_node: dict[str, list[ExerciseAttemptRecord]] = {}
        for record in mistake_records:
            if not record.related_node_id:
                continue
            mistakes_by_node.setdefault(record.related_node_id, []).append(record)

        for node_id, records in mistakes_by_node.items():
            node_name = choose_node_label(records[0].related_node_name, node_id)
            row = candidate(node_id, node_name, query_matched=bool(normalized_query))
            row.mistake_attempts = records
            severity = min(1.0, len(records) / 3)
            latest = records[0].created_at.strftime("%m-%d") if records[0].created_at else "最近"
            row.add(
                0.30 * severity,
                "mistake_retry",
                f"{latest} 做错过该知识点相关题目，共 {len(records)} 道错题待复盘。",
            )

        # 2. Profile weak points and low mastery nodes.
        await self._add_profile_candidates(profile, candidate, query_matches)

        # 3. Forgetting curve risk.
        detector = ForgettingDetector()
        for forgetting in detector.detect(profile.node_mastery, top_k=20):
            if not query_matches(forgetting.node_id, forgetting.node_name):
                continue
            urgency_weight = {"high": 1.0, "medium": 0.7, "low": 0.45}.get(forgetting.urgency, 0.45)
            row = candidate(forgetting.node_id, choose_node_label(forgetting.node_name, forgetting.node_id))
            row.mastery_score = forgetting.mastery_score
            row.add(
                0.20 * urgency_weight,
                "forgetting_review",
                (
                    f"距离上次练习已 {forgetting.days_since_review} 天，超过 {forgetting.threshold_days} 天复习阈值，"
                    f"预计遗忘风险 {forgetting.estimated_forgetting_rate:.0%}。"
                ),
            )

        # 4. Explicit query target: useful for students searching a topic before enough history exists.
        await self._add_query_candidates(query, candidate)

        # 5. Prerequisite repair candidates for the highest-risk nodes.
        await self._add_prerequisite_candidates(candidates, profile)

        ranked = sorted(
            [row for row in candidates.values() if row.score > 0 and self._allowed_by_query(row, normalized_query)],
            key=lambda row: (-row.score, row.node_name, row.node_id),
        )

        items: list[ExerciseSearchItem] = []
        seen_questions: set[str] = set()
        for row in ranked:
            if len(items) >= limit:
                break
            node_items = await self._items_for_candidate(payload, row, limit - len(items), seen_questions)
            items.extend(node_items)

        return items[:limit]

    async def _add_profile_candidates(self, profile: StudentProfile, candidate, query_matches) -> None:
        for weak in profile.weak_points.self_reported:
            node_id = weak.node_id
            node_name = weak.topic
            if not node_id and self.graphrag_service is not None and weak.topic:
                try:
                    nodes = await self.graphrag_service.graph_store.search_knowledge_points(weak.topic, limit=1)
                    if nodes:
                        node_id = nodes[0].uid
                        node_name = str(nodes[0].properties.get("name") or weak.topic)
                except Exception:
                    node_id = None
            if not node_id or not query_matches(node_id, node_name):
                continue
            candidate(node_id, node_name).add(
                0.15,
                "weak_point_review",
                "该知识点来自你主动反馈的薄弱点，建议安排针对性复习。",
            )

        for weak in profile.weak_points.diagnosed:
            mastery = profile.node_mastery.get(weak.node_id)
            node_name = choose_node_label(mastery.node_name if mastery else None, weak.node_id)
            if not query_matches(weak.node_id, node_name):
                continue
            severity = min(1.0, max(weak.error_rate, weak.total_attempts / 4))
            candidate(weak.node_id, node_name).add(
                0.18 * severity,
                "weak_point_review",
                f"练习诊断显示该知识点错误率约 {weak.error_rate:.0%}，需要优先巩固。",
            )

        for node_id, mastery in profile.node_mastery.items():
            if not query_matches(node_id, mastery.node_name):
                continue
            need = max(0.0, 1.0 - mastery.mastery_score)
            if mastery.mastery_score < 0.65 and mastery.confidence >= 0.2:
                row = candidate(node_id, choose_node_label(mastery.node_name, node_id))
                row.mastery_score = mastery.mastery_score
                row.add(
                    0.25 * need,
                    "weak_point_review",
                    f"当前掌握度约 {mastery.mastery_score:.0%}，低于稳定掌握阈值。",
                )

    async def _add_query_candidates(self, query: str, candidate) -> None:
        if not query.strip() or self.graphrag_service is None:
            return
        try:
            nodes = await self.graphrag_service.graph_store.search_knowledge_points(query, limit=5)
        except Exception:
            return
        for node in nodes:
            name = choose_node_label(node.properties.get("name"), node.uid)
            candidate(node.uid, name, query_matched=True).add(
                0.08,
                "query_review",
                f"与你搜索的“{query}”直接相关，可作为本次复习主题。",
            )

    async def _add_prerequisite_candidates(self, candidates: dict[str, ReviewCandidate], profile: StudentProfile) -> None:
        if self.graphrag_service is None:
            return
        roots = sorted(candidates.values(), key=lambda row: -row.score)[:5]
        for root in roots:
            if root.primary_type == "query_review":
                continue
            try:
                paths = await self.graphrag_service.graph_store.get_prerequisites(root.node_id, depth=1, limit=3)
            except Exception:
                continue
            for path in paths:
                for node in path.nodes:
                    if node.uid == root.node_id:
                        continue
                    mastery = profile.node_mastery.get(node.uid)
                    mastery_score = mastery.mastery_score if mastery else 0.35
                    if mastery_score >= 0.75:
                        continue
                    name = choose_node_label(node.properties.get("name") or (mastery.node_name if mastery else None), node.uid)
                    row = candidates.get(node.uid)
                    if row is None:
                        row = ReviewCandidate(node_id=node.uid, node_name=name)
                        candidates[node.uid] = row
                    row.mastery_score = mastery_score
                    row.add(
                        0.12 * (1.0 - mastery_score),
                        "prereq_repair",
                        f"它是「{root.node_name}」的前置知识，补齐后更容易修复当前薄弱点。",
                    )

    def _allowed_by_query(self, row: ReviewCandidate, normalized_query: str) -> bool:
        if not normalized_query:
            return True
        if row.query_matched:
            return True
        return normalized_query in _normalize(f"{row.node_id} {row.node_name}")

    async def _items_for_candidate(
        self,
        payload: ExerciseSearchRequest,
        row: ReviewCandidate,
        limit: int,
        seen_questions: set[str],
    ) -> list[ExerciseSearchItem]:
        items: list[ExerciseSearchItem] = []

        def add_item(item: ExerciseSearchItem) -> None:
            key = _normalize(item.question or item.title)
            if not key or key in seen_questions:
                return
            seen_questions.add(key)
            items.append(item)

        # Prefer one original wrong question when available.
        for attempt in row.mistake_attempts[:1]:
            if len(items) >= limit:
                break
            add_item(self._item_from_attempt(attempt, row))

        # Add canonical question-bank exercises.
        if self.graphrag_service is not None and len(items) < limit:
            try:
                graph_exercises = await self.graphrag_service.graph_store.get_exercises_for_node(row.node_id, limit=3)
            except Exception:
                graph_exercises = []
            for node in graph_exercises:
                if len(items) >= limit:
                    break
                add_item(self._item_from_graph_exercise(node, row))

        # Add previously saved AI-generated variants.
        if len(items) < limit:
            rows = await self.repository.search_ai_generated_exercises(
                student_id=payload.student_id,
                query=row.node_name or row.node_id,
                limit=3,
            )
            for ai_row in rows:
                if len(items) >= limit:
                    break
                record = ai_row["record"]
                exercise = dict(ai_row["exercise"] or {})
                related = str(exercise.get("related_node_id") or record.resolved_uid or "")
                if related and related != row.node_id and _normalize(row.node_name) not in _normalize(exercise.get("question", "")):
                    continue
                add_item(self._item_from_ai_exercise(record, ai_row["index"], exercise, row))

        return items

    def _review_metadata(self, row: ReviewCandidate) -> dict[str, Any]:
        return {
            "review_type": row.primary_type,
            "review_score": round(row.score, 4),
            "review_reasons": [localize_text(reason) for reason in row.reasons[:4]],
            "recommended_node_id": row.node_id,
        }

    def _item_from_attempt(self, record: ExerciseAttemptRecord, row: ReviewCandidate) -> ExerciseSearchItem:
        snapshot = dict(record.exercise_snapshot or {})
        meta = self._review_metadata(row)
        return ExerciseSearchItem(
            id=f"recommended:mistake:{record.id}",
            source_type="recommended",
            source_label="推荐复习 · 原错题",
            source_id=record.session_id,
            attempt_id=record.id,
            title=localize_text(record.exercise_title or snapshot.get("title") or "练习题"),
            type=record.exercise_type or snapshot.get("type") or "choice",
            related_node_id=record.related_node_id or row.node_id,
            related_node_name=choose_node_label(record.related_node_name, record.related_node_id or row.node_id),
            difficulty=record.difficulty,
            question=snapshot.get("question") or "",
            options=list(snapshot.get("options") or []),
            answer=dict(record.expected_answer or snapshot.get("answer") or {}),
            adaptive_feedback=dict(snapshot.get("adaptive_feedback") or record.feedback or {}),
            source_uids=record.source_uids,
            exercise_snapshot=snapshot,
            rank_reason=meta["review_reasons"],
            created_at=record.created_at,
            **meta,
        )

    def _item_from_graph_exercise(self, node: Any, row: ReviewCandidate) -> ExerciseSearchItem:
        props = dict(node.properties or {})
        answer = _parse_maybe_json(props.get("answer"), {})
        options = _parse_maybe_json(props.get("options"), [])
        adaptive_feedback = _parse_maybe_json(props.get("adaptive_feedback"), {})
        exercise = {
            "title": localize_text(props.get("title") or "练习题"),
            "type": props.get("type") or "choice",
            "related_node_id": props.get("related_node_id") or row.node_id,
            "related_node_name": row.node_name,
            "difficulty": props.get("difficulty") or 3,
            "question": props.get("question") or "",
            "options": options,
            "answer": answer,
            "adaptive_feedback": adaptive_feedback,
            "source_uids": props.get("source_ids") or props.get("source_uids") or [],
        }
        meta = self._review_metadata(row)
        return ExerciseSearchItem(
            id=f"recommended:knowledge_base:{node.uid}",
            source_type="recommended",
            source_label="推荐复习 · 题库题",
            source_id=node.uid,
            title=str(exercise["title"] or "练习题"),
            type=str(exercise["type"] or "choice"),
            related_node_id=str(exercise["related_node_id"] or row.node_id),
            related_node_name=choose_node_label(row.node_name, row.node_id),
            difficulty=int(exercise["difficulty"] or 3),
            question=str(exercise["question"] or ""),
            options=list(exercise["options"] or []),
            answer=dict(exercise["answer"] or {}),
            adaptive_feedback=dict(exercise["adaptive_feedback"] or {}),
            source_uids=list(exercise["source_uids"] or []),
            exercise_snapshot=exercise,
            rank_reason=meta["review_reasons"],
            **meta,
        )

    def _item_from_ai_exercise(self, record: Any, index: int, exercise: dict[str, Any], row: ReviewCandidate) -> ExerciseSearchItem:
        snapshot = dict(exercise or {})
        if not snapshot.get("related_node_id"):
            snapshot["related_node_id"] = record.resolved_uid or row.node_id
        meta = self._review_metadata(row)
        return ExerciseSearchItem(
            id=f"recommended:ai_generated:{record.id}:{index}",
            source_type="recommended",
            source_label="推荐复习 · AI变式题",
            source_id=f"{record.id}:{index}",
            resource_record_id=record.id,
            title=localize_text(snapshot.get("title") or "练习题"),
            type=str(snapshot.get("type") or "choice"),
            related_node_id=str(snapshot.get("related_node_id") or row.node_id),
            related_node_name=choose_node_label(row.node_name or record.center_node_name, row.node_id or record.resolved_uid),
            difficulty=int(snapshot.get("difficulty") or 3),
            question=str(snapshot.get("question") or ""),
            options=list(snapshot.get("options") or []),
            answer=dict(snapshot.get("answer") or {}),
            adaptive_feedback=dict(snapshot.get("adaptive_feedback") or {}),
            source_uids=list(snapshot.get("source_uids") or snapshot.get("source_ids") or []),
            exercise_snapshot=snapshot,
            rank_reason=meta["review_reasons"],
            created_at=record.created_at,
            **meta,
        )
