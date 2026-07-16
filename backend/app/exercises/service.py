import logging
import json
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.core.labels import choose_node_label, localize_text
from app.core.logging import log_business_metric
from app.exercises import models
from app.exercises.repository import ExerciseRepository
from app.exercises.review_recommender import ReviewRecommendationService
from app.exercises.schemas import (
    ExerciseActionResponse,
    ExerciseAttemptRecord,
    ExerciseAttemptSubmit,
    ExerciseMistakeListResponse,
    ExerciseSearchItem,
    ExerciseSearchRequest,
    ExerciseSearchResponse,
    ExerciseSessionListResponse,
    ExerciseSessionRecord,
    ExerciseSessionSubmitRequest,
    ExerciseSessionSubmitResponse,
    ExerciseStatsResponse,
)
from app.profile.schemas import ExerciseAttemptProfileUpdate, ExerciseRoundProfileUpdateRequest
from app.profile.service import ProfileService

if TYPE_CHECKING:
    from app.graphrag.service import GraphRAGService

logger = logging.getLogger(__name__)


def _parse_maybe_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _grade_choice(student_answer: dict, expected_answer: dict) -> bool:
    raw = student_answer.get("value")
    expected = expected_answer.get("correct") or expected_answer.get("reference_answer")
    if expected is None:
        return bool(student_answer.get("is_correct", False))
    return str(raw or "").strip() == str(expected).strip()


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        text = value.get("criterion") or value.get("point") or value.get("text") or value.get("description")
        return [str(text).strip()] if text else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_as_text_list(item))
        return [item for item in items if item]
    return [str(value).strip()] if str(value).strip() else []


def _extract_short_answer_rubric(expected_answer: dict, exercise_snapshot: dict, expected_text: str) -> list[str]:
    points: list[str] = []
    for source in (
        expected_answer.get("key_points"),
        expected_answer.get("knowledge_points"),
        expected_answer.get("rubric"),
        exercise_snapshot.get("key_points"),
        exercise_snapshot.get("rubric"),
        exercise_snapshot.get("grading_criteria"),
    ):
        points.extend(_as_text_list(source))

    if not points and expected_text:
        separators = ["\n", "；", ";", "。"]
        fragments = [expected_text]
        for separator in separators:
            if separator in expected_text:
                fragments = [part for part in expected_text.split(separator) if part.strip()]
                break
        points.extend(fragment.strip(" -0123456789.、") for fragment in fragments[:6] if fragment.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for point in points:
        normalized = " ".join(str(point).split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped[:8]


def _clamp_score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


async def _grade_short_answer(
    student_answer: dict,
    expected_answer: dict,
    exercise_snapshot: dict,
) -> tuple[bool, float, dict, str, str, float, bool]:
    """LLM + rubric 评分简答题"""
    from app.core.config import get_settings
    settings = get_settings()

    raw = student_answer.get("value", "")
    expected = expected_answer.get("correct") or expected_answer.get("reference_answer") or ""
    rubric = exercise_snapshot.get("rubric") or exercise_snapshot.get("grading_criteria") or ""
    rubric_points = _extract_short_answer_rubric(expected_answer, exercise_snapshot, expected)

    if settings.llm_api_key:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                temperature=0,
            )
            prompt = f"""请作为严格但公平的机器学习课程助教，按评分点评估以下简答题。

评分要求：
1. 不做逐字匹配，按语义和关键点覆盖评分。
2. 每个评分点都要判断是否命中，并给出 0.0-1.0 的 point score。
3. score 为总分，范围 0.0-1.0；score >= 0.75 才算整体正确，0.4-0.74 算部分正确但仍需复习。
4. 如果学生答非所问、空答、只写无关文字，score 必须低于 0.2。
5. 只返回 JSON，不要输出 Markdown。

题目: {exercise_snapshot.get('question', '')}
参考答案: {expected}
评分点: {rubric_points or rubric or '从参考答案中抽取核心语义点'}
原始评分标准: {rubric or '无'}
学生答案: {raw}

请返回 JSON:
{{
  "is_correct": bool,
  "score": 0.0,
  "confidence": 0.0,
  "hit_points": ["命中的评分点"],
  "missing_points": ["缺失或错误的评分点"],
  "point_scores": [
    {{"point": "评分点", "score": 0.0, "comment": "简短理由"}}
  ],
  "suggestions": ["下一步改进建议"],
  "feedback": "面向学生的一段总评"
}}"""
            from app.core.manual_json import parse_model
            from pydantic import BaseModel, Field

            class GradeResult(BaseModel):
                is_correct: bool = False
                score: float = 0.0
                confidence: float = 0.7
                hit_points: list[str] = Field(default_factory=list)
                missing_points: list[str] = Field(default_factory=list)
                point_scores: list[dict[str, Any]] = Field(default_factory=list)
                suggestions: list[str] = Field(default_factory=list)
                feedback: str = ""

            response = await llm.ainvoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            result = parse_model(text, GradeResult)
            score = _clamp_score(result.score)
            confidence = _clamp_score(result.confidence)
            is_correct = score >= 0.75
            profile_update_allowed = confidence >= 0.55
            point_scores: list[dict[str, Any]] = []
            for item in result.point_scores:
                point = str(item.get("point") or "").strip()
                if not point:
                    continue
                point_score = _clamp_score(item.get("score"))
                point_scores.append({
                    "point": point,
                    "score": point_score,
                    "comment": str(item.get("comment") or "").strip(),
                })
            if point_scores:
                hit_points = [item["point"] for item in point_scores if item["score"] >= 0.7]
                missing_points = [item["point"] for item in point_scores if item["score"] < 0.7]
            else:
                hit_points = result.hit_points
                missing_points = result.missing_points
            return (
                is_correct,
                score,
                {
                    "feedback": result.feedback,
                    "explanation": expected,
                    "grading": {
                        "score": score,
                        "is_correct": is_correct,
                        "raw_is_correct": bool(result.is_correct),
                        "threshold": 0.75,
                        "confidence": confidence,
                        "hit_points": hit_points,
                        "missing_points": missing_points,
                        "point_scores": point_scores,
                        "suggestions": result.suggestions,
                        "rubric_points": rubric_points,
                        "profile_update_allowed": profile_update_allowed,
                    },
                },
                "llm_rubric",
                "graded",
                confidence,
                profile_update_allowed,
            )
        except Exception as e:
            logger.warning(f"LLM grading failed; marking short answer for review: {e}")

    return (
        False,
        0.0,
        {
            "feedback": "简答题自动评分暂不可用，已标记为待复核。本题不会影响掌握度、错题统计或推荐结果。",
            "explanation": expected,
            "grading": {
                "score": 0.0,
                "is_correct": False,
                "threshold": 0.75,
                "confidence": 0.0,
                "hit_points": [],
                "missing_points": rubric_points,
                "point_scores": [],
                "suggestions": ["等待人工复核，或请学习助手先按参考答案讲解。"],
                "rubric_points": rubric_points,
                "profile_update_allowed": False,
            },
        },
        "manual_review",
        "pending_review",
        0.0,
        False,
    )


async def _grade_coding(
    student_answer: dict,
    expected_answer: dict,
    exercise_snapshot: dict,
) -> tuple[bool, float, dict, str, str, float, bool]:
    """代码题结构化评分"""
    from app.core.config import get_settings
    settings = get_settings()

    raw = student_answer.get("value", "") or student_answer.get("code", "")
    expected = expected_answer.get("correct") or expected_answer.get("reference_answer") or ""
    test_cases = exercise_snapshot.get("test_cases") or []

    if settings.llm_api_key:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                temperature=0,
            )
            prompt = f"""请评分以下代码题回答。

题目: {exercise_snapshot.get('question', '')}
参考答案: {expected}
测试用例: {test_cases}
学生代码: {raw}

请返回 JSON: {{"is_correct": bool, "score": 0.0-1.0, "feedback": "评分理由，包括代码正确性、风格、效率等"}}"""
            from app.core.manual_json import parse_model
            from pydantic import BaseModel

            class GradeResult(BaseModel):
                is_correct: bool
                score: float
                feedback: str

            response = await llm.ainvoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            result = parse_model(text, GradeResult)
            score = max(0.0, min(1.0, float(result.score)))
            return (
                result.is_correct,
                score,
                {"feedback": result.feedback, "explanation": expected},
                "llm_code_rubric",
                "graded",
                0.72,
                True,
            )
        except Exception as e:
            logger.warning(f"LLM code grading failed: {e}")

    return (
        False,
        0.0,
        {
            "feedback": "代码题自动评分暂不可用，已标记为暂不支持自动评分。本题已保存，但不会影响掌握度、错题统计或推荐结果。",
            "explanation": expected,
            "test_cases": test_cases,
        },
        "unsupported",
        "unsupported",
        0.0,
        False,
    )


class ExerciseRecordService:
    def __init__(
        self,
        repository: ExerciseRepository,
        profile_service: ProfileService,
        graphrag_service: "GraphRAGService | None" = None,
    ) -> None:
        self.repository = repository
        self.profile_service = profile_service
        self.graphrag_service = graphrag_service

    async def search_exercises(self, payload: ExerciseSearchRequest) -> ExerciseSearchResponse:
        items: list[ExerciseSearchItem] = []
        source_filter = payload.source_type
        remaining = payload.limit

        def wants(source: str) -> bool:
            return source_filter == "all" or source_filter == source

        if wants("knowledge_base") and remaining > 0 and self.graphrag_service is not None:
            kb_items = await self._search_knowledge_base(payload, remaining)
            items.extend(kb_items)
            remaining = max(0, payload.limit - len(items))

        if wants("ai_generated") and remaining > 0:
            ai_items = await self._search_ai_generated(payload, remaining)
            items.extend(ai_items)
            remaining = max(0, payload.limit - len(items))

        if wants("mistake") and remaining > 0 and payload.student_id:
            mistake_items = await self._search_mistakes(payload, remaining)
            items.extend(mistake_items)
            remaining = max(0, payload.limit - len(items))

        if wants("recommended") and remaining > 0 and payload.student_id:
            recommended_items = await self._search_recommended(payload, remaining)
            items.extend(recommended_items)

        deduped: list[ExerciseSearchItem] = []
        seen: set[tuple[str, str, str]] = set()
        for item in items:
            key = (item.source_type, item.source_id, item.question[:120])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= payload.limit:
                break

        return ExerciseSearchResponse(
            query=payload.query,
            source_type=payload.source_type,
            total=len(deduped),
            items=deduped,
        )

    async def _search_knowledge_base(
        self,
        payload: ExerciseSearchRequest,
        limit: int,
    ) -> list[ExerciseSearchItem]:
        if self.graphrag_service is None:
            return []
        try:
            evidence = (
                await self.graphrag_service.build_evidence_by_uid(
                    payload.node_id,
                    payload.student_profile,
                    student_id=payload.student_id,
                )
                if payload.node_id
                else await self.graphrag_service.query(
                    payload.query or "练习",
                    payload.student_profile,
                    student_id=payload.student_id,
                )
            )
        except Exception as exc:
            logger.warning("knowledge-base exercise search failed: %s", exc)
            return []

        center_name = ""
        if evidence.center_node is not None:
            center_name = choose_node_label(evidence.center_node.properties.get("name"), evidence.resolved_uid, fallback="")

        results: list[ExerciseSearchItem] = []
        for node in evidence.exercises[:limit]:
            props = dict(node.properties or {})
            exercise = {
                "title": localize_text(props.get("title") or "练习题"),
                "type": props.get("type") or "choice",
                "related_node_id": props.get("related_node_id") or evidence.resolved_uid or payload.node_id or "",
                "related_node_name": center_name,
                "difficulty": props.get("difficulty") or 3,
                "question": props.get("question") or "",
                "options": _parse_maybe_json(props.get("options"), []),
                "answer": _parse_maybe_json(props.get("answer"), {}),
                "adaptive_feedback": _parse_maybe_json(props.get("adaptive_feedback"), {}),
                "source_uids": props.get("source_ids") or props.get("source_uids") or [],
            }
            results.append(self._search_item_from_exercise(
                exercise=exercise,
                source_type="knowledge_base",
                source_label="题库题",
                source_id=node.uid,
                rank_reason=["来自课程图谱配套题库", f"中心知识点：{center_name or choose_node_label(None, evidence.resolved_uid, '未定位')}"],
            ))
        return results

    async def _search_ai_generated(
        self,
        payload: ExerciseSearchRequest,
        limit: int,
    ) -> list[ExerciseSearchItem]:
        rows = await self.repository.search_ai_generated_exercises(
            student_id=payload.student_id,
            query=payload.query,
            limit=limit,
        )
        results: list[ExerciseSearchItem] = []
        for row in rows:
            record = row["record"]
            exercise = dict(row["exercise"] or {})
            if not exercise.get("related_node_id"):
                exercise["related_node_id"] = record.resolved_uid
            results.append(self._search_item_from_exercise(
                exercise=exercise,
                source_type="ai_generated",
                source_label="AI生成",
                source_id=f"{record.id}:{row['index']}",
                resource_record_id=record.id,
                created_at=record.created_at,
                related_node_name=record.center_node_name,
                rank_reason=["来自学习助手或资源生成台保存的题目"],
            ))
        return results

    async def _search_mistakes(
        self,
        payload: ExerciseSearchRequest,
        limit: int,
    ) -> list[ExerciseSearchItem]:
        if not payload.student_id:
            return []
        records = await self.repository.search_mistake_exercises(
            student_id=payload.student_id,
            query=payload.query,
            limit=limit,
        )
        return [self._search_item_from_attempt(record, "mistake", "我的错题") for record in records]

    async def _search_recommended(
        self,
        payload: ExerciseSearchRequest,
        limit: int,
    ) -> list[ExerciseSearchItem]:
        if not payload.student_id:
            return []
        recommender = ReviewRecommendationService(
            repository=self.repository,
            profile_service=self.profile_service,
            graphrag_service=self.graphrag_service,
        )
        return await recommender.recommend(payload, limit=limit)

    @staticmethod
    def _search_item_from_attempt(
        record: ExerciseAttemptRecord,
        source_type: str,
        source_label: str,
        rank_reason: list[str] | None = None,
    ) -> ExerciseSearchItem:
        snapshot = dict(record.exercise_snapshot or {})
        return ExerciseSearchItem(
            id=f"{source_type}:{record.id}",
            source_type=source_type,  # type: ignore[arg-type]
            source_label=source_label,
            source_id=record.session_id,
            attempt_id=record.id,
            title=record.exercise_title or snapshot.get("title") or record.exercise_id,
            type=record.exercise_type or snapshot.get("type") or "choice",
            related_node_id=record.related_node_id,
            related_node_name=record.related_node_name,
            difficulty=record.difficulty,
            question=snapshot.get("question") or "",
            options=list(snapshot.get("options") or []),
            answer=dict(record.expected_answer or snapshot.get("answer") or {}),
            adaptive_feedback=dict(snapshot.get("adaptive_feedback") or record.feedback or {}),
            source_uids=record.source_uids,
            exercise_snapshot=snapshot,
            rank_reason=rank_reason or ["来自历史错题记录"],
            created_at=record.created_at,
        )

    @staticmethod
    def _search_item_from_exercise(
        *,
        exercise: dict[str, Any],
        source_type: str,
        source_label: str,
        source_id: str,
        resource_record_id: str | None = None,
        created_at: datetime | None = None,
        related_node_name: str = "",
        rank_reason: list[str] | None = None,
    ) -> ExerciseSearchItem:
        snapshot = dict(exercise or {})
        return ExerciseSearchItem(
            id=f"{source_type}:{source_id}",
            source_type=source_type,  # type: ignore[arg-type]
            source_label=source_label,
            source_id=source_id,
            resource_record_id=resource_record_id,
            title=str(snapshot.get("title") or "练习题"),
            type=str(snapshot.get("type") or "choice"),
            related_node_id=str(snapshot.get("related_node_id") or ""),
            related_node_name=related_node_name or str(snapshot.get("related_node_name") or ""),
            difficulty=int(snapshot.get("difficulty") or 3),
            question=str(snapshot.get("question") or ""),
            options=list(snapshot.get("options") or []),
            answer=dict(snapshot.get("answer") or {}),
            adaptive_feedback=dict(snapshot.get("adaptive_feedback") or {}),
            source_uids=list(snapshot.get("source_uids") or snapshot.get("source_ids") or []),
            exercise_snapshot=snapshot,
            rank_reason=rank_reason or [],
            created_at=created_at,
        )

    async def _grade_attempt(self, item: ExerciseAttemptSubmit) -> tuple[bool, float, dict, str, str, float, bool]:
        """按题型分发评分，返回评分结果和是否允许写回画像。"""
        exercise_type = item.exercise_type or item.exercise_snapshot.get("type", "choice")

        if item.is_correct is not None and item.score is not None:
            # 前端已评分（choice 题型），直接使用
            return (
                item.is_correct,
                item.score,
                item.feedback,
                item.grading_method or "rule",
                item.grading_status or "graded",
                item.grading_confidence if item.grading_confidence is not None else 1.0,
                item.profile_update_allowed if item.profile_update_allowed is not None else True,
            )

        if exercise_type == "choice":
            is_correct = _grade_choice(item.student_answer, item.expected_answer or item.exercise_snapshot.get("answer", {}))
            return is_correct, 1.0 if is_correct else 0.0, item.feedback, "rule", "graded", 1.0, True
        elif exercise_type == "short_answer":
            return await _grade_short_answer(item.student_answer, item.expected_answer, item.exercise_snapshot)
        elif exercise_type == "coding":
            return await _grade_coding(item.student_answer, item.expected_answer, item.exercise_snapshot)
        elif exercise_type == "case_analysis":
            return await _grade_short_answer(item.student_answer, item.expected_answer, item.exercise_snapshot)
        else:
            is_correct = _grade_choice(item.student_answer, item.expected_answer or item.exercise_snapshot.get("answer", {}))
            return is_correct, 1.0 if is_correct else 0.0, item.feedback, "rule", "graded", 1.0, True

    @staticmethod
    def _classify_error_type(
        exercise_type: str,
        student_answer: dict,
        correct_answer: dict,
        exercise_snapshot: dict,
        had_previous_correct: bool = False,
    ) -> str:
        """根据题目类型和答案判断错误类型。"""
        if had_previous_correct:
            return "memory_lapse"

        if exercise_type == "choice":
            options = exercise_snapshot.get("options") or []
            if len(options) > 2:
                return "concept_confusion"
            return "application_failure"

        if exercise_type == "short_answer":
            return "application_failure"

        if exercise_type == "coding":
            return "application_failure"

        return "application_failure"

    async def submit_session(self, payload: ExerciseSessionSubmitRequest) -> ExerciseSessionSubmitResponse:
        profile_before = await self.profile_service.repository.ensure_profile(payload.student_id)
        mastery_before = {
            node_id: item.mastery_score
            for node_id, item in profile_before.node_mastery.items()
        }

        session_id = models.new_id()
        round_id = payload.round_id or f"exercise_round_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        attempts: list[models.ExerciseAttempt] = []
        profile_attempts: list[ExerciseAttemptProfileUpdate] = []
        weak_nodes: list[str] = []
        correct_count = 0
        graded_count = 0
        pending_count = 0
        answered_count = 0

        grading_start = time.monotonic()
        for item in payload.attempts:
            expected = item.expected_answer or item.exercise_snapshot.get("answer") or {}
            answer_payload = item.student_answer or {}
            is_answered = any(str(v).strip() for v in answer_payload.values() if v is not None)
            (
                is_correct,
                score,
                feedback,
                grading_method,
                grading_status,
                grading_confidence,
                profile_update_allowed,
            ) = await self._grade_attempt(item)
            if is_answered:
                answered_count += 1
            if grading_status == "graded" and profile_update_allowed:
                graded_count += 1
                if is_correct:
                    correct_count += 1
                elif item.related_node_id:
                    weak_nodes.append(item.related_node_id)
            else:
                pending_count += 1

            # 分类错误类型（仅对已评分的错题）
            error_type = None
            if (not is_correct and grading_status == "graded" and profile_update_allowed
                    and item.related_node_id):
                had_prev_correct = await self.repository.had_previous_correct(
                    payload.student_id, item.related_node_id
                )
                error_type = self._classify_error_type(
                    exercise_type=item.exercise_type or item.exercise_snapshot.get("type", "choice"),
                    student_answer=answer_payload,
                    correct_answer=expected,
                    exercise_snapshot=item.exercise_snapshot,
                    had_previous_correct=had_prev_correct,
                )

            exercise_id = item.exercise_id or item.exercise_title or f"exercise_{len(attempts) + 1}"
            attempts.append(
                models.ExerciseAttempt(
                    id=models.new_id(),
                    session_id=session_id,
                    student_id=payload.student_id,
                    exercise_id=exercise_id,
                    exercise_title=item.exercise_title or item.exercise_snapshot.get("title", ""),
                    exercise_type=item.exercise_type or item.exercise_snapshot.get("type", ""),
                    related_node_id=item.related_node_id,
                    related_node_name=item.related_node_name,
                    exercise_snapshot_json=item.exercise_snapshot,
                    student_answer_json=answer_payload,
                    expected_answer_json=expected,
                    is_correct=bool(is_correct),
                    score=float(score),
                    difficulty=item.difficulty,
                    cognitive_level=item.cognitive_level,
                    used_hint=item.used_hint,
                    time_spent_seconds=item.time_spent_seconds,
                    feedback_json=feedback,
                    misconception_tags_json=item.misconception_tags,
                    source_uids_json=item.source_uids,
                    mode=item.mode,
                    viewed_answer=item.viewed_answer,
                    grading_method=grading_method,
                    grading_status=grading_status,
                    grading_confidence=float(grading_confidence),
                    profile_update_allowed=bool(profile_update_allowed),
                    error_type=error_type,
                )
            )
            if profile_update_allowed and grading_status == "graded":
                profile_attempts.append(
                    ExerciseAttemptProfileUpdate(
                        exercise_id=exercise_id,
                        node_ids=[item.related_node_id] if item.related_node_id else [],
                        is_correct=bool(is_correct),
                        difficulty=item.difficulty,
                        cognitive_level=item.cognitive_level,
                        used_hint=item.used_hint,
                    )
                )

        grading_duration_ms = round((time.monotonic() - grading_start) * 1000, 2)
        log_business_metric(
            "exercise_grading_duration_ms",
            grading_duration_ms,
            attempt_count=len(payload.attempts),
        )

        total_count = len(payload.attempts)
        accuracy = round(correct_count / graded_count, 4) if graded_count else 0.0
        target_name = payload.target_node_name or (payload.target_node_id or "练习")
        summary = f"完成「{target_name}」练习：{correct_count}/{graded_count or total_count} 题正确。"
        if pending_count:
            summary += f" 另有 {pending_count} 题待复核或暂不支持自动评分，未写入掌握度。"

        session_row = models.ExerciseSession(
            id=session_id,
            student_id=payload.student_id,
            round_id=round_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            target_node_id=payload.target_node_id,
            target_node_name=payload.target_node_name,
            title=payload.title or f"{target_name}练习记录",
            status="submitted_pending_review" if pending_count and not graded_count else "submitted",
            total_count=total_count,
            answered_count=answered_count,
            correct_count=correct_count,
            accuracy=accuracy,
            duration_seconds=payload.duration_seconds,
            mastery_before_json=mastery_before,
            weak_nodes_json=list(dict.fromkeys(weak_nodes)),
            summary=summary,
            started_at=payload.started_at,
        )
        await self.repository.add_session(session_row, attempts)

        if profile_attempts:
            profile_response = await self.profile_service.apply_exercise_round(
                ExerciseRoundProfileUpdateRequest(
                    student_id=payload.student_id,
                    round_id=round_id,
                    attempts=profile_attempts,
                )
            )
        else:
            profile_response = await self.profile_service.apply_exercise_round(
                ExerciseRoundProfileUpdateRequest(
                    student_id=payload.student_id,
                    round_id=round_id,
                    attempts=[],
                )
            )
        mastery_after = {
            node_id: profile_response.profile.node_mastery[node_id].mastery_score
            for node_id in profile_response.updated_node_mastery
            if node_id in profile_response.profile.node_mastery
        }
        session_row.mastery_after_json = mastery_after
        session_row.summary = summary
        await self.repository.session.commit()

        session = await self.repository.get_session(payload.student_id, session_id)
        assert session is not None
        return ExerciseSessionSubmitResponse(
            session=session,
            profile=profile_response.profile,
            dashboard=profile_response.dashboard,
            updated_node_mastery=profile_response.updated_node_mastery,
            update_event=profile_response.update_event,
        )

    async def list_sessions(self, student_id: str, limit: int = 50, offset: int = 0) -> ExerciseSessionListResponse:
        total, items = await self.repository.list_sessions(student_id, limit=limit, offset=offset)
        return ExerciseSessionListResponse(student_id=student_id, total=total, items=items)

    async def get_session(self, student_id: str, session_id: str) -> ExerciseSessionRecord | None:
        return await self.repository.get_session(student_id, session_id)

    async def list_mistakes(
        self,
        student_id: str,
        limit: int = 100,
        offset: int = 0,
        node_id: str | None = None,
        error_type: str | None = None,
    ) -> ExerciseMistakeListResponse:
        total, items = await self.repository.list_mistakes(
            student_id, limit=limit, offset=offset, node_id=node_id, error_type=error_type
        )
        return ExerciseMistakeListResponse(student_id=student_id, total=total, items=items)

    async def bookmark_attempt(self, student_id: str, attempt_id: str, tag: str, note: str) -> ExerciseActionResponse:
        row = await self.repository.add_bookmark(student_id, attempt_id, tag, note)
        await self.repository.session.commit()
        return ExerciseActionResponse(id=row.id)

    async def review_attempt(
        self,
        student_id: str,
        attempt_id: str,
        session_id: str,
        review_session_id: str,
        review_result: str,
        mastery_delta: float,
        notes: str,
    ) -> ExerciseActionResponse:
        row = await self.repository.add_review(
            student_id=student_id,
            attempt_id=attempt_id,
            session_id=session_id,
            review_session_id=review_session_id,
            review_result=review_result,
            mastery_delta=mastery_delta,
            notes=notes,
        )
        await self.repository.session.commit()
        return ExerciseActionResponse(id=row.id)

    async def stats(self, student_id: str) -> ExerciseStatsResponse:
        data = await self.repository.stats(student_id)
        total = data["total_attempts"]
        correct = data["correct_attempts"]
        return ExerciseStatsResponse(
            student_id=student_id,
            total_sessions=data["total_sessions"],
            total_attempts=total,
            correct_attempts=correct,
            accuracy=round(correct / total, 4) if total else 0.0,
            mistake_count=data["mistake_count"],
            practiced_nodes=data["practiced_nodes"],
            recent_accuracy=round(data["recent_accuracy"], 4),
            weak_node_counts=data["weak_node_counts"],
        )
