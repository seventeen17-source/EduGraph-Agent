from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exercises import models
from app.exercises.schemas import ExerciseAttemptRecord, ExerciseSessionRecord


class ExerciseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_session(
        self,
        session_row: models.ExerciseSession,
        attempts: list[models.ExerciseAttempt],
    ) -> None:
        self.session.add(session_row)
        for attempt in attempts:
            self.session.add(attempt)
        await self.session.flush()

    async def get_session(self, student_id: str, session_id: str) -> ExerciseSessionRecord | None:
        row = await self.session.get(models.ExerciseSession, session_id)
        if row is None or row.student_id != student_id:
            return None
        attempts = await self.list_attempts_for_session(session_id)
        return self._session_record(row, attempts)

    async def list_sessions(
        self,
        student_id: str,
        limit: int = 50,
        offset: int = 0,
        include_attempts: bool = False,
    ) -> tuple[int, list[ExerciseSessionRecord]]:
        total = await self.session.scalar(
            select(func.count()).select_from(models.ExerciseSession).where(
                models.ExerciseSession.student_id == student_id
            )
        )
        rows = await self.session.scalars(
            select(models.ExerciseSession)
            .where(models.ExerciseSession.student_id == student_id)
            .order_by(desc(models.ExerciseSession.submitted_at))
            .offset(offset)
            .limit(limit)
        )
        records: list[ExerciseSessionRecord] = []
        for row in rows:
            attempts = await self.list_attempts_for_session(row.id) if include_attempts else []
            records.append(self._session_record(row, attempts))
        return int(total or 0), records

    async def list_attempts_for_session(self, session_id: str) -> list[ExerciseAttemptRecord]:
        rows = await self.session.scalars(
            select(models.ExerciseAttempt)
            .where(models.ExerciseAttempt.session_id == session_id)
            .order_by(models.ExerciseAttempt.created_at.asc())
        )
        return [self._attempt_record(row) for row in rows]

    async def list_mistakes(
        self,
        student_id: str,
        limit: int = 100,
        offset: int = 0,
        node_id: str | None = None,
    ) -> tuple[int, list[ExerciseAttemptRecord]]:
        conditions = [
            models.ExerciseAttempt.student_id == student_id,
            models.ExerciseAttempt.is_correct.is_(False),
        ]
        if node_id:
            conditions.append(models.ExerciseAttempt.related_node_id == node_id)
        total = await self.session.scalar(
            select(func.count()).select_from(models.ExerciseAttempt).where(*conditions)
        )
        rows = await self.session.scalars(
            select(models.ExerciseAttempt)
            .where(*conditions)
            .order_by(desc(models.ExerciseAttempt.created_at))
            .offset(offset)
            .limit(limit)
        )
        return int(total or 0), [self._attempt_record(row) for row in rows]

    async def add_bookmark(self, student_id: str, attempt_id: str, tag: str, note: str) -> models.ExerciseBookmark:
        row = models.ExerciseBookmark(
            student_id=student_id,
            attempt_id=attempt_id,
            tag=tag,
            note=note,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_review(
        self,
        student_id: str,
        attempt_id: str,
        session_id: str,
        review_session_id: str,
        review_result: str,
        mastery_delta: float,
        notes: str,
    ) -> models.ExerciseReview:
        row = models.ExerciseReview(
            student_id=student_id,
            attempt_id=attempt_id,
            session_id=session_id,
            review_session_id=review_session_id,
            review_result=review_result,
            mastery_delta=mastery_delta,
            notes=notes,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def stats(self, student_id: str) -> dict:
        session_count = await self.session.scalar(
            select(func.count()).select_from(models.ExerciseSession).where(
                models.ExerciseSession.student_id == student_id
            )
        )
        total_attempts = await self.session.scalar(
            select(func.count()).select_from(models.ExerciseAttempt).where(
                models.ExerciseAttempt.student_id == student_id
            )
        )
        correct_attempts = await self.session.scalar(
            select(func.count()).select_from(models.ExerciseAttempt).where(
                models.ExerciseAttempt.student_id == student_id,
                models.ExerciseAttempt.is_correct.is_(True),
            )
        )
        mistake_count = await self.session.scalar(
            select(func.count()).select_from(models.ExerciseAttempt).where(
                models.ExerciseAttempt.student_id == student_id,
                models.ExerciseAttempt.is_correct.is_(False),
            )
        )
        practiced_nodes = await self.session.scalar(
            select(func.count(func.distinct(models.ExerciseAttempt.related_node_id))).where(
                models.ExerciseAttempt.student_id == student_id,
                models.ExerciseAttempt.related_node_id != "",
            )
        )
        recent_rows = await self.session.scalars(
            select(models.ExerciseAttempt)
            .where(models.ExerciseAttempt.student_id == student_id)
            .order_by(desc(models.ExerciseAttempt.created_at))
            .limit(20)
        )
        recent = list(recent_rows)
        weak_rows = await self.session.execute(
            select(models.ExerciseAttempt.related_node_id, func.count())
            .where(
                models.ExerciseAttempt.student_id == student_id,
                models.ExerciseAttempt.is_correct.is_(False),
                models.ExerciseAttempt.related_node_id != "",
            )
            .group_by(models.ExerciseAttempt.related_node_id)
            .order_by(desc(func.count()))
            .limit(20)
        )
        return {
            "total_sessions": int(session_count or 0),
            "total_attempts": int(total_attempts or 0),
            "correct_attempts": int(correct_attempts or 0),
            "mistake_count": int(mistake_count or 0),
            "practiced_nodes": int(practiced_nodes or 0),
            "recent_accuracy": (
                sum(1 for item in recent if item.is_correct) / len(recent)
                if recent else 0.0
            ),
            "weak_node_counts": {node_id: count for node_id, count in weak_rows if node_id},
        }

    @staticmethod
    def _session_record(
        row: models.ExerciseSession,
        attempts: list[ExerciseAttemptRecord],
    ) -> ExerciseSessionRecord:
        return ExerciseSessionRecord(
            id=row.id,
            student_id=row.student_id,
            round_id=row.round_id,
            source_type=row.source_type,
            source_id=row.source_id,
            target_node_id=row.target_node_id,
            target_node_name=row.target_node_name,
            title=row.title,
            status=row.status,
            total_count=row.total_count,
            answered_count=row.answered_count,
            correct_count=row.correct_count,
            accuracy=row.accuracy,
            duration_seconds=row.duration_seconds,
            mastery_before=dict(row.mastery_before_json or {}),
            mastery_after=dict(row.mastery_after_json or {}),
            weak_nodes=list(row.weak_nodes_json or []),
            summary=row.summary,
            started_at=row.started_at,
            submitted_at=row.submitted_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            attempts=attempts,
        )

    @staticmethod
    def _attempt_record(row: models.ExerciseAttempt) -> ExerciseAttemptRecord:
        return ExerciseAttemptRecord(
            id=row.id,
            session_id=row.session_id,
            student_id=row.student_id,
            exercise_id=row.exercise_id,
            exercise_title=row.exercise_title,
            exercise_type=row.exercise_type,
            related_node_id=row.related_node_id,
            related_node_name=row.related_node_name,
            exercise_snapshot=dict(row.exercise_snapshot_json or {}),
            student_answer=dict(row.student_answer_json or {}),
            expected_answer=dict(row.expected_answer_json or {}),
            is_correct=row.is_correct,
            score=row.score,
            difficulty=row.difficulty,
            cognitive_level=row.cognitive_level,
            used_hint=row.used_hint,
            time_spent_seconds=row.time_spent_seconds,
            feedback=dict(row.feedback_json or {}),
            misconception_tags=list(row.misconception_tags_json or []),
            source_uids=list(row.source_uids_json or []),
            created_at=row.created_at,
        )
