from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profile import models
from app.profile.schemas import (
    AbilityState,
    Background,
    CognitiveStyleInfo,
    KnowledgeBase,
    KnowledgePointMastery,
    LearningBehaviorProfile,
    LearningGoal,
    Preferences,
    ProfileChatMessageRecord,
    ProfileUpdateRecord,
    Progress,
    StudentProfile,
    WeakPoints,
)


_TZ_UTC8 = timezone(timedelta(hours=8))


def _to_local(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(_TZ_UTC8)
    return dt.astimezone(_TZ_UTC8)


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile(self, student_id: str) -> StudentProfile | None:
        if not student_id or not student_id.strip():
            return None
        student = await self.session.get(models.Student, student_id)
        if student is None:
            return None

        record = await self.session.get(models.StudentProfileRecord, student_id)
        if record is None:
            return None

        mastery_rows = await self.session.scalars(
            select(models.StudentNodeMastery).where(models.StudentNodeMastery.student_id == student_id)
        )
        node_mastery = {
            item.node_id: KnowledgePointMastery(
                node_id=item.node_id,
                node_name=item.node_name,
                chapter_id=item.chapter_id,
                mastery_score=item.mastery_score,
                level=item.level,  # type: ignore[arg-type]
                confidence=item.confidence,
                attempts=item.attempts,
                correct_count=item.correct_count,
                last_practiced_at=_to_local(item.last_practiced_at),
                updated_at=_to_local(item.updated_at),
            )
            for item in mastery_rows
        }

        return StudentProfile(
            student_id=student.id,
            display_name=student.display_name,
            created_at=_to_local(record.created_at),
            updated_at=_to_local(record.updated_at),
            completeness=record.completeness,
            background=Background(**(record.background_json or {})),
            learning_goal=LearningGoal(**(record.learning_goal_json or {})),
            knowledge_base=KnowledgeBase(**(record.knowledge_base_json or {})),
            progress=Progress(**(record.progress_json or {})),
            cognitive_style=CognitiveStyleInfo(**(record.cognitive_style_json or {})),
            weak_points=WeakPoints(**(record.weak_points_json or {})),
            preferences=Preferences(**(record.preferences_json or {})),
            ability_state=AbilityState(**(record.ability_state_json or {})),
            learning_behavior=LearningBehaviorProfile(**(record.learning_behavior_json or {})),
            node_mastery=node_mastery,
        )

    async def ensure_profile(self, student_id: str, display_name: str | None = None) -> StudentProfile:
        if not student_id or not student_id.strip():
            raise ValueError("student_id 不能为空")
        profile = await self.get_profile(student_id)
        if profile is not None:
            return profile

        student = models.Student(id=student_id, display_name=display_name or student_id)
        record = models.StudentProfileRecord(student_id=student_id)
        self.session.add(student)
        self.session.add(record)
        await self.session.flush()
        return (await self.get_profile(student_id)) or StudentProfile(
            student_id=student_id,
            display_name=display_name or student_id,
        )

    async def save_profile(self, profile: StudentProfile) -> None:
        student = await self.session.get(models.Student, profile.student_id)
        if student is None:
            student = models.Student(id=profile.student_id, display_name=profile.display_name or profile.student_id)
            self.session.add(student)
        elif profile.display_name:
            student.display_name = profile.display_name

        record = await self.session.get(models.StudentProfileRecord, profile.student_id)
        if record is None:
            record = models.StudentProfileRecord(student_id=profile.student_id)
            self.session.add(record)

        record.completeness = profile.completeness
        record.background_json = profile.background.model_dump(mode="json")
        record.learning_goal_json = profile.learning_goal.model_dump(mode="json")
        record.knowledge_base_json = profile.knowledge_base.model_dump(mode="json")
        record.progress_json = profile.progress.model_dump(mode="json")
        record.cognitive_style_json = profile.cognitive_style.model_dump(mode="json")
        record.weak_points_json = profile.weak_points.model_dump(mode="json")
        record.preferences_json = profile.preferences.model_dump(mode="json")
        record.ability_state_json = profile.ability_state.model_dump(mode="json")
        record.learning_behavior_json = profile.learning_behavior.model_dump(mode="json")
        record.updated_at = datetime.now(timezone.utc).replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
        for mastery in profile.node_mastery.values():
            await self.upsert_node_mastery(profile.student_id, mastery)

    async def save_learning_behavior(
        self,
        student_id: str,
        behavior: LearningBehaviorProfile,
    ) -> None:
        """仅更新 learning_behavior 字段（轻量更新，不重写整个 profile）。"""
        record = await self.session.get(models.StudentProfileRecord, student_id)
        if record is None:
            return
        record.learning_behavior_json = behavior.model_dump(mode="json")
        record.updated_at = datetime.now(timezone.utc).replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
        await self.session.flush()

    async def upsert_node_mastery(self, student_id: str, mastery: KnowledgePointMastery) -> None:
        result = await self.session.scalars(
            select(models.StudentNodeMastery).where(
                models.StudentNodeMastery.student_id == student_id,
                models.StudentNodeMastery.node_id == mastery.node_id,
            )
        )
        row = result.first()
        if row is None:
            row = models.StudentNodeMastery(student_id=student_id, node_id=mastery.node_id)
            self.session.add(row)

        row.node_name = mastery.node_name
        row.chapter_id = mastery.chapter_id
        row.mastery_score = mastery.mastery_score
        row.level = mastery.level
        row.confidence = mastery.confidence
        row.attempts = mastery.attempts
        row.correct_count = mastery.correct_count
        row.last_practiced_at = mastery.last_practiced_at
        row.updated_at = mastery.updated_at or datetime.now(timezone.utc).replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))

    async def add_update_event(
        self,
        student_id: str,
        trigger: str,
        trigger_detail: str,
        updated_fields: list[str],
        summary: str,
    ) -> None:
        self.session.add(
            models.ProfileUpdateEvent(
                student_id=student_id,
                trigger=trigger,
                trigger_detail=trigger_detail,
                updated_fields_json=updated_fields,
                summary=summary,
            )
        )

    async def add_chat_message(
        self,
        student_id: str,
        role: str,
        content: str,
        round_no: int,
    ) -> None:
        self.session.add(
            models.ProfileChatMessage(
                student_id=student_id,
                role=role,
                content=content,
                round_no=round_no,
            )
        )

    async def add_mastery_evidence(
        self,
        student_id: str,
        node_id: str,
        source_type: str,
        source_id: str,
        score_delta: float,
        confidence_delta: float,
        summary: str,
    ) -> None:
        self.session.add(
            models.MasteryEvidence(
                student_id=student_id,
                node_id=node_id,
                source_type=source_type,
                source_id=source_id,
                score_delta=score_delta,
                confidence_delta=confidence_delta,
                summary=summary,
            )
        )

    async def list_mastery_evidence(
        self,
        student_id: str,
        node_id: str,
        limit: int = 50,
    ) -> list[models.MasteryEvidence]:
        rows = await self.session.scalars(
            select(models.MasteryEvidence)
            .where(
                models.MasteryEvidence.student_id == student_id,
                models.MasteryEvidence.node_id == node_id,
            )
            .order_by(models.MasteryEvidence.created_at.desc())
            .limit(limit)
        )
        return list(rows)

    async def list_chat_messages(self, student_id: str, limit: int = 100) -> list[ProfileChatMessageRecord]:
        rows = await self.session.scalars(
            select(models.ProfileChatMessage)
            .where(models.ProfileChatMessage.student_id == student_id)
            .order_by(models.ProfileChatMessage.created_at.asc())
            .limit(limit)
        )
        return [
            ProfileChatMessageRecord(
                id=row.id,
                role=row.role,  # type: ignore[arg-type]
                content=row.content,
                round_no=row.round_no,
                created_at=_to_local(row.created_at),
            )
            for row in rows
        ]

    async def list_update_history(self, student_id: str, limit: int = 20) -> list[ProfileUpdateRecord]:
        rows = await self.session.scalars(
            select(models.ProfileUpdateEvent)
            .where(models.ProfileUpdateEvent.student_id == student_id)
            .order_by(models.ProfileUpdateEvent.created_at.desc())
            .limit(limit)
        )
        return [
            ProfileUpdateRecord(
                id=row.id,
                timestamp=_to_local(row.created_at),
                trigger=row.trigger,
                trigger_detail=row.trigger_detail,
                updated_fields=list(row.updated_fields_json or []),
                summary=row.summary,
            )
            for row in rows
        ]
