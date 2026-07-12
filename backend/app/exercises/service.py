from datetime import datetime

from app.exercises import models
from app.exercises.repository import ExerciseRepository
from app.exercises.schemas import (
    ExerciseActionResponse,
    ExerciseAttemptRecord,
    ExerciseMistakeListResponse,
    ExerciseSessionListResponse,
    ExerciseSessionRecord,
    ExerciseSessionSubmitRequest,
    ExerciseSessionSubmitResponse,
    ExerciseStatsResponse,
)
from app.profile.schemas import ExerciseAttemptProfileUpdate, ExerciseRoundProfileUpdateRequest
from app.profile.service import ProfileService


def _answer_is_correct(student_answer: dict, expected_answer: dict) -> bool:
    raw = student_answer.get("value")
    expected = expected_answer.get("correct") or expected_answer.get("reference_answer")
    if expected is None:
        return bool(student_answer.get("is_correct", False))
    return str(raw or "").strip() == str(expected).strip()


class ExerciseRecordService:
    def __init__(self, repository: ExerciseRepository, profile_service: ProfileService) -> None:
        self.repository = repository
        self.profile_service = profile_service

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
        answered_count = 0

        for item in payload.attempts:
            expected = item.expected_answer or item.exercise_snapshot.get("answer") or {}
            answer_payload = item.student_answer or {}
            is_answered = any(str(v).strip() for v in answer_payload.values() if v is not None)
            is_correct = item.is_correct if item.is_correct is not None else _answer_is_correct(answer_payload, expected)
            score = item.score if item.score is not None else (1.0 if is_correct else 0.0)
            if is_answered:
                answered_count += 1
            if is_correct:
                correct_count += 1
            elif item.related_node_id:
                weak_nodes.append(item.related_node_id)

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
                    feedback_json=item.feedback,
                    misconception_tags_json=item.misconception_tags,
                    source_uids_json=item.source_uids,
                )
            )
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

        total_count = len(payload.attempts)
        accuracy = round(correct_count / total_count, 4) if total_count else 0.0
        target_name = payload.target_node_name or (payload.target_node_id or "练习")
        summary = f"完成「{target_name}」练习：{correct_count}/{total_count} 题正确。"

        session_row = models.ExerciseSession(
            id=session_id,
            student_id=payload.student_id,
            round_id=round_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            target_node_id=payload.target_node_id,
            target_node_name=payload.target_node_name,
            title=payload.title or f"{target_name}练习记录",
            status="submitted",
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

        profile_response = await self.profile_service.apply_exercise_round(
            ExerciseRoundProfileUpdateRequest(
                student_id=payload.student_id,
                round_id=round_id,
                attempts=profile_attempts,
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
    ) -> ExerciseMistakeListResponse:
        total, items = await self.repository.list_mistakes(student_id, limit=limit, offset=offset, node_id=node_id)
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
