import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.errors import NotFoundError
from app.profile.completeness import compute_completeness, missing_dimensions
from app.profile.extractor import ExtractionMode, ProfileExtractionResult, ProfileExtractor
from app.profile.repository import ProfileRepository
from app.profile.schemas import (
    Background,
    CognitiveStyleInfo,
    DiagnosedWeakPoint,
    ExerciseAttemptProfileUpdate,
    ExerciseResultProfileUpdateRequest,
    ExerciseRoundProfileUpdateRequest,
    KnowledgePointMastery,
    LearningProgressUpdateRequest,
    KnownTopic,
    LearningGoal,
    ManualProfilePatchRequest,
    Preferences,
    ProfileChatMessageRecord,
    ProfileChatResponse,
    ProfileDashboardResponse,
    ProfileDimensionView,
    ProfileEventResponse,
    ProfileUpdateRecord,
    SelfReportedWeakPoint,
    StudentProfile,
    WeakPointRankItem,
    WeakPoints,
    MasteryOverviewItem,
)


NODE_HINTS: dict[str, tuple[str, str, str]] = {
    "梯度下降": ("ml_gradient_descent", "梯度下降", "ch03"),
    "随机梯度": ("ml_sgd_minibatch", "随机梯度下降与 Mini-batch", "ch03"),
    "mini-batch": ("ml_sgd_minibatch", "随机梯度下降与 Mini-batch", "ch03"),
    "反向传播": ("ml_backpropagation", "反向传播", "ch06"),
    "bp": ("ml_backpropagation", "反向传播", "ch06"),
    "神经网络": ("ml_multilayer_neural_network", "多层神经网络", "ch06"),
    "k-means": ("ml_kmeans", "K-Means", "ch05"),
    "聚类": ("ml_clustering", "聚类", "ch05"),
    "逻辑回归": ("ml_logistic_regression", "逻辑回归", "ch03"),
}

RESOURCE_LABELS: dict[str, str] = {
    "document": "讲解文档",
    "diagram": "图解",
    "mindmap": "思维导图",
    "exercise": "练习题",
    "video_script": "视频脚本",
    "code_case": "代码案例",
}

VALID_RESOURCE_TYPES = {"document", "diagram", "exercise", "video_script", "code_case"}

RESOURCE_TYPE_ALIASES: dict[str, str] = {
    "article": "document",
    "doc": "document",
    "docs": "document",
    "explanation": "document",
    "lecture": "document",
    "note": "document",
    "notes": "document",
    "reading": "document",
    "text": "document",
    "文本": "document",
    "文档": "document",
    "文章": "document",
    "讲义": "document",
    "阅读": "document",
    "diagram": "diagram",
    "graph": "diagram",
    "image": "diagram",
    "mind_map": "diagram",
    "mindmap": "diagram",
    "visual": "diagram",
    "图": "diagram",
    "图解": "diagram",
    "图示": "diagram",
    "图谱": "diagram",
    "思维导图": "diagram",
    "可视化": "diagram",
    "exercise": "exercise",
    "exercises": "exercise",
    "practice": "exercise",
    "problem": "exercise",
    "problems": "exercise",
    "quiz": "exercise",
    "question": "exercise",
    "questions": "exercise",
    "test": "exercise",
    "做题": "exercise",
    "刷题": "exercise",
    "练习": "exercise",
    "练习题": "exercise",
    "题": "exercise",
    "题目": "exercise",
    "习题": "exercise",
    "测验": "exercise",
    "video": "video_script",
    "animation": "video_script",
    "script": "video_script",
    "video_script": "video_script",
    "视频": "video_script",
    "动画": "video_script",
    "视频脚本": "video_script",
    "code": "code_case",
    "coding": "code_case",
    "code_case": "code_case",
    "programming": "code_case",
    "case": "code_case",
    "代码": "code_case",
    "代码案例": "code_case",
    "编程": "code_case",
    "实战": "code_case",
}

KNOWLEDGE_LEVEL_ALIASES: dict[str, str] = {
    "weak": "weak",
    "low": "weak",
    "poor": "weak",
    "unknown": "weak",
    "not_started": "weak",
    "beginner": "basic",
    "beginning": "basic",
    "basic": "basic",
    "foundation": "basic",
    "intro": "basic",
    "intermediate": "intermediate",
    "medium": "intermediate",
    "familiar": "intermediate",
    "advanced": "advanced",
    "strong": "advanced",
    "expert": "advanced",
    "薄弱": "weak",
    "不会": "weak",
    "不了解": "weak",
    "入门": "basic",
    "基础": "basic",
    "一般": "basic",
    "熟悉": "intermediate",
    "掌握": "intermediate",
    "较好": "intermediate",
    "精通": "advanced",
}

GRADE_PATTERNS: list[tuple[str, int]] = [
    ("大一", 1),
    ("一年级", 1),
    ("一年級", 1),
    ("大二", 2),
    ("二年级", 2),
    ("二年級", 2),
    ("大三", 3),
    ("三年级", 3),
    ("三年級", 3),
    ("大四", 4),
    ("四年级", 4),
    ("四年級", 4),
]

PROFILE_FIELD_LABELS: dict[str, str] = {
    "background": "专业背景",
    "learning_goal": "学习目标",
    "knowledge_base": "知识掌握",
    "progress": "学习进度",
    "cognitive_style": "认知风格",
    "weak_points": "薄弱点",
    "preferences": "学习偏好",
    "ability_state": "能力水平",
    "node_mastery": "知识点掌握度",
}


def _now() -> datetime:
    return datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))


def _level_from_score(score: float) -> str:
    if score < 0.25:
        return "weak"
    if score < 0.55:
        return "basic"
    if score < 0.80:
        return "intermediate"
    return "advanced"


def _resource_label(resource_type: str) -> str:
    return RESOURCE_LABELS.get(resource_type, resource_type)


def _field_label(field: str) -> str:
    return PROFILE_FIELD_LABELS.get(field, field)


def _normalized_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_resource_type(value: Any) -> str | None:
    key = _normalized_key(value)
    if not key:
        return None
    mapped = RESOURCE_TYPE_ALIASES.get(key, key)
    if mapped in VALID_RESOURCE_TYPES:
        return mapped
    return None


def _normalize_resource_ranking(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    normalized = [
        mapped
        for mapped in (_normalize_resource_type(value) for value in values)
        if mapped is not None
    ]
    return list(dict.fromkeys(normalized))


def _normalize_knowledge_level(value: Any, default: str = "basic") -> str:
    key = _normalized_key(value)
    mapped = KNOWLEDGE_LEVEL_ALIASES.get(key, key)
    if mapped in {"weak", "basic", "intermediate", "advanced"}:
        return mapped
    return default


def _grade_label(grade: int | None) -> str:
    if grade is None:
        return "未确认年级"
    labels = {1: "大一", 2: "大二", 3: "大三", 4: "大四"}
    return labels.get(grade, f"大{grade}")


class ProfileService:
    def __init__(self, repository: ProfileRepository, extractor: ProfileExtractor | None = None) -> None:
        self.repository = repository
        self.extractor = extractor

    async def get_profile(self, student_id: str) -> StudentProfile:
        profile = await self.repository.get_profile(student_id)
        if profile is None:
            raise NotFoundError(f"Student profile not found: {student_id}")
        return profile

    async def save_learning_behavior(
        self,
        student_id: str,
        behavior: "LearningBehaviorProfile",
    ) -> None:
        """仅更新行为画像（不重写整个 profile）。"""
        from app.profile.schemas import LearningBehaviorProfile

        await self.repository.save_learning_behavior(student_id, behavior)

    async def initialize_profile(
        self,
        student_id: str,
        message: str,
        display_name: str | None = None,
    ) -> ProfileChatResponse:
        return await self._apply_dialogue(
            student_id=student_id,
            message=message,
            display_name=display_name,
            trigger="init_dialogue",
            trigger_detail="profile_init",
            extraction_mode="initialization",
        )

    async def chat(self, student_id: str, message: str, display_name: str | None = None) -> ProfileChatResponse:
        return await self._apply_dialogue(
            student_id=student_id,
            message=message,
            display_name=display_name,
            trigger="update_dialogue",
            trigger_detail="profile_chat",
            extraction_mode="update",
        )

    async def _apply_dialogue(
        self,
        student_id: str,
        message: str,
        display_name: str | None,
        trigger: str,
        trigger_detail: str,
        extraction_mode: ExtractionMode,
    ) -> ProfileChatResponse:
        profile = await self.repository.ensure_profile(student_id, display_name)
        previous_profile = profile.model_copy(deep=True)
        updated_fields = await self._apply_extraction_or_fallback(
            profile=profile,
            message=message,
            mode=extraction_mode,
        )
        profile.completeness = compute_completeness(profile)
        now_dt = _now()
        profile.updated_at = now_dt

        await self.repository.save_profile(profile)
        next_round = len(await self.repository.list_chat_messages(student_id, limit=1000)) // 2 + 1
        if updated_fields:
            await self.repository.add_update_event(
                student_id=student_id,
                trigger=trigger,
                trigger_detail=trigger_detail,
                updated_fields=updated_fields,
                summary=f"从对话中更新画像字段：{'、'.join(_field_label(field) for field in updated_fields)}",
            )
            for mastery in profile.node_mastery.values():
                if mastery.mastery_score < 0.35:
                    await self.repository.add_mastery_evidence(
                        student_id=student_id,
                        node_id=mastery.node_id,
                        source_type=trigger,
                        source_id=trigger_detail,
                        score_delta=mastery.mastery_score,
                        confidence_delta=mastery.confidence,
                        summary=f"学生自述相关薄弱点：{mastery.node_name or mastery.node_id}",
                    )
        missing = missing_dimensions(profile)
        completed = profile.completeness >= 0.75 and not any(
            key in missing for key in ["background", "learning_goal", "knowledge_base"]
        )
        reply = self._next_reply(
            profile=profile,
            missing=missing,
            completed=completed,
            updated_fields=updated_fields,
            message=message,
            previous_profile=previous_profile,
        )
        await self.repository.add_chat_message(
            student_id=student_id,
            role="user",
            content=message,
            round_no=next_round,
        )
        await self.repository.add_chat_message(
            student_id=student_id,
            role="assistant",
            content=reply,
            round_no=next_round,
        )
        await self.repository.session.commit()
        return ProfileChatResponse(
            reply=reply,
            session_status="completed" if completed else "building",
            current_round=next_round,
            profile=profile,
            completeness=profile.completeness,
            updated_dimensions=updated_fields,
            missing_dimensions=missing,
        )

    async def patch_profile(self, student_id: str, payload: ManualProfilePatchRequest) -> StudentProfile:
        profile = await self.get_profile(student_id)
        value = payload.value
        now = _now()
        if payload.dimension == "background":
            profile.background = Background(**value)
            profile.background.source = "manual"
            profile.background.last_updated = now
        elif payload.dimension == "learning_goal":
            profile.learning_goal = LearningGoal(**value)
            profile.learning_goal.source = "manual"
            profile.learning_goal.last_updated = now
        elif payload.dimension == "preferences":
            data = dict(value)
            if "resource_ranking" in data:
                data["resource_ranking"] = _normalize_resource_ranking(data["resource_ranking"])
            profile.preferences = Preferences(**data)
            profile.preferences.source = "manual"
            profile.preferences.last_updated = now
        elif payload.dimension == "cognitive_style":
            profile.cognitive_style = CognitiveStyleInfo(**value)
            profile.cognitive_style.source = "manual"
            profile.cognitive_style.last_updated = now
        else:
            raise NotFoundError(f"Unsupported profile dimension: {payload.dimension}")

        profile.completeness = compute_completeness(profile)
        await self.repository.save_profile(profile)
        await self.repository.add_update_event(
            student_id=student_id,
            trigger="manual_patch",
            trigger_detail=payload.dimension,
            updated_fields=[payload.dimension],
            summary=f"手动修正画像字段：{_field_label(payload.dimension)}",
        )
        await self.repository.session.commit()
        return profile

    async def apply_exercise_result(
        self,
        payload: ExerciseResultProfileUpdateRequest,
    ) -> ProfileEventResponse:
        profile = await self.repository.ensure_profile(payload.student_id)
        now = _now()
        updated_nodes = await self._apply_exercise_attempt(
            profile=profile,
            attempt=ExerciseAttemptProfileUpdate(
                exercise_id=payload.exercise_id,
                node_ids=payload.node_ids,
                is_correct=payload.is_correct,
                difficulty=payload.difficulty,
                cognitive_level=payload.cognitive_level,
                used_hint=payload.used_hint,
            ),
            now=now,
        )
        return await self._commit_exercise_profile_update(
            profile=profile,
            trigger_detail=payload.exercise_id,
            summary="根据单题练习结果更新知识点掌握度。",
            updated_nodes=updated_nodes,
            now=now,
        )

    async def apply_exercise_round(
        self,
        payload: ExerciseRoundProfileUpdateRequest,
    ) -> ProfileEventResponse:
        profile = await self.repository.ensure_profile(payload.student_id)
        updated_nodes: list[str] = []
        now = _now()
        for attempt in payload.attempts:
            updated_nodes.extend(
                await self._apply_exercise_attempt(
                    profile=profile,
                    attempt=attempt,
                    now=now,
                )
            )
        round_id = payload.round_id or f"exercise_round_{now.strftime('%Y%m%d%H%M%S')}"
        correct_count = sum(1 for attempt in payload.attempts if attempt.is_correct)
        summary = f"完成一轮练习：{correct_count}/{len(payload.attempts)} 题正确，已统一更新知识点掌握度。"
        return await self._commit_exercise_profile_update(
            profile=profile,
            trigger_detail=round_id,
            summary=summary,
            updated_nodes=list(dict.fromkeys(updated_nodes)),
            now=now,
        )

    async def _apply_exercise_attempt(
        self,
        profile: StudentProfile,
        attempt: ExerciseAttemptProfileUpdate,
        now: datetime,
    ) -> list[str]:
        updated_nodes: list[str] = []
        for node_id in attempt.node_ids:
            if not node_id or not node_id.strip():
                continue
            existing = profile.node_mastery.get(node_id)
            node_name = existing.node_name if existing else node_id
            chapter_id = existing.chapter_id if existing else ""
            current_score = existing.mastery_score if existing else 0.35
            delta = self._exercise_delta(
                is_correct=attempt.is_correct,
                difficulty=attempt.difficulty,
                cognitive_level=attempt.cognitive_level,
                used_hint=attempt.used_hint,
            )
            new_score = max(0.0, min(1.0, current_score + delta))
            attempts = (existing.attempts if existing else 0) + 1
            correct_count = (existing.correct_count if existing else 0) + (1 if attempt.is_correct else 0)
            confidence = min(1.0, (existing.confidence if existing else 0.3) + 0.08)
            mastery = KnowledgePointMastery(
                node_id=node_id,
                node_name=node_name,
                chapter_id=chapter_id,
                mastery_score=round(new_score, 4),
                level=_level_from_score(new_score),  # type: ignore[arg-type]
                confidence=round(confidence, 4),
                attempts=attempts,
                correct_count=correct_count,
                last_practiced_at=now,
            )
            profile.node_mastery[node_id] = mastery
            updated_nodes.append(node_id)

            await self.repository.add_mastery_evidence(
                student_id=profile.student_id,
                node_id=node_id,
                source_type="exercise_result",
                source_id=attempt.exercise_id,
                score_delta=round(delta, 4),
                confidence_delta=0.08,
                summary=f"练习 {attempt.exercise_id} {'答对' if attempt.is_correct else '答错'}，更新 {node_name} 掌握度。",
            )

            if not attempt.is_correct:
                self._upsert_diagnosed_weak_point(profile, node_id, now)

        return updated_nodes

    async def _commit_exercise_profile_update(
        self,
        profile: StudentProfile,
        trigger_detail: str,
        summary: str,
        updated_nodes: list[str],
        now: datetime,
    ) -> ProfileEventResponse:
        profile.progress.in_progress_node_ids = list(
            dict.fromkeys([*profile.progress.in_progress_node_ids, *updated_nodes])
        )
        profile.progress.last_active_at = now
        profile.completeness = compute_completeness(profile)
        profile.updated_at = now
        await self.repository.save_profile(profile)
        await self.repository.add_update_event(
            student_id=profile.student_id,
            trigger="exercise_result",
            trigger_detail=trigger_detail,
            updated_fields=["node_mastery", "weak_points", "progress"],
            summary=summary,
        )
        await self.repository.session.commit()
        dashboard = await self.get_dashboard(profile.student_id)
        return ProfileEventResponse(
            profile=profile,
            dashboard=dashboard,
            updated_node_mastery=updated_nodes,
            update_event=ProfileUpdateRecord(
                timestamp=now,
                trigger="exercise_result",
                trigger_detail=trigger_detail,
                updated_fields=["node_mastery", "weak_points", "progress"],
                summary=summary,
            ),
        )

    async def apply_learning_progress(
        self,
        payload: LearningProgressUpdateRequest,
    ) -> ProfileEventResponse:
        profile = await self.repository.ensure_profile(payload.student_id)
        now = _now()
        profile.progress.completed_node_ids = list(
            dict.fromkeys([*profile.progress.completed_node_ids, *payload.completed_node_ids])
        )
        profile.progress.in_progress_node_ids = list(dict.fromkeys(payload.in_progress_node_ids))
        if payload.current_chapter_id is not None:
            profile.progress.current_chapter_id = payload.current_chapter_id
        if payload.completion_rate is not None:
            profile.progress.completion_rate = payload.completion_rate
        profile.progress.last_active_at = now
        profile.completeness = compute_completeness(profile)
        profile.updated_at = now

        await self.repository.save_profile(profile)
        summary = "更新学习进度。"
        await self.repository.add_update_event(
            student_id=payload.student_id,
            trigger="learning_progress",
            trigger_detail=payload.current_chapter_id or "progress_update",
            updated_fields=["progress"],
            summary=summary,
        )
        await self.repository.session.commit()
        dashboard = await self.get_dashboard(payload.student_id)
        return ProfileEventResponse(
            profile=profile,
            dashboard=dashboard,
            updated_node_mastery=[],
            update_event=ProfileUpdateRecord(
                timestamp=now,
                trigger="learning_progress",
                trigger_detail=payload.current_chapter_id or "progress_update",
                updated_fields=["progress"],
                summary=summary,
            ),
        )

    async def get_dashboard(self, student_id: str) -> ProfileDashboardResponse:
        profile = await self.get_profile(student_id)
        history = await self.repository.list_update_history(student_id, limit=8)
        missing = missing_dimensions(profile)
        dimensions = self._build_dimension_views(profile, missing)
        weak_points = self._build_weak_points(profile)
        mastery = [
            MasteryOverviewItem(
                node_id=item.node_id,
                node_name=item.node_name,
                chapter_id=item.chapter_id,
                mastery_score=item.mastery_score,
                level=item.level,
                confidence=item.confidence,
            )
            for item in sorted(profile.node_mastery.values(), key=lambda row: row.mastery_score)
        ]
        return ProfileDashboardResponse(
            student_id=profile.student_id,
            display_name=profile.display_name or profile.student_id,
            headline=self._headline(profile),
            completeness=profile.completeness,
            missing_dimensions=missing,
            dimensions=dimensions,
            weak_point_rank=weak_points,
            mastery_overview=mastery,
            recent_updates=history,
            personalization_reasons=self._personalization_reasons(profile),
        )

    async def list_history(self, student_id: str) -> list[ProfileUpdateRecord]:
        _ = await self.get_profile(student_id)
        return await self.repository.list_update_history(student_id)

    async def list_chat_messages(self, student_id: str) -> list[ProfileChatMessageRecord]:
        _ = await self.get_profile(student_id)
        return await self.repository.list_chat_messages(student_id)

    async def _apply_extraction_or_fallback(
        self,
        profile: StudentProfile,
        message: str,
        mode: ExtractionMode,
    ) -> list[str]:
        updated_fields: list[str] = []
        if self.extractor is not None:
            extraction = await self.extractor.extract(message=message, existing_profile=profile, mode=mode)
            if extraction.has_updates():
                updated_fields.extend(self._merge_llm_extraction(profile, extraction, message))

        # Deterministic rules supplement partial LLM output and remain the fallback
        # when the extractor is disabled, unavailable, or returns no usable fields.
        updated_fields.extend(self._apply_rule_extraction(profile, message))
        updated_fields.extend(self._normalize_profile_text(profile, message))
        return list(dict.fromkeys(updated_fields))

    def _merge_llm_extraction(
        self,
        profile: StudentProfile,
        extraction: ProfileExtractionResult,
        source_message: str,
    ) -> list[str]:
        now = _now()
        updated: list[str] = []

        if extraction.background:
            data = {**profile.background.model_dump(), **extraction.background}
            profile.background = Background(**data)
            profile.background.source = "llm_profile_extractor"
            profile.background.confidence = max(profile.background.confidence, extraction.confidence or 0.65)
            profile.background.last_updated = now
            updated.append("background")

        if extraction.learning_goal:
            data = {**profile.learning_goal.model_dump(), **extraction.learning_goal}
            profile.learning_goal = LearningGoal(**data)
            profile.learning_goal.source = "llm_profile_extractor"
            profile.learning_goal.confidence = max(profile.learning_goal.confidence, extraction.confidence or 0.65)
            profile.learning_goal.last_updated = now
            updated.append("learning_goal")

        if extraction.known_topics or extraction.unknown_topics:
            existing_topics = {item.topic for item in profile.knowledge_base.known_topics}
            for item in extraction.known_topics:
                if item.topic and item.topic not in existing_topics:
                    profile.knowledge_base.known_topics.append(
                        KnownTopic(
                            topic=item.topic,
                            level=_normalize_knowledge_level(item.level),
                            evidence=item.evidence or "LLM 从学生对话中抽取",
                        )
                    )
            profile.knowledge_base.unknown_topics = list(
                dict.fromkeys([*profile.knowledge_base.unknown_topics, *extraction.unknown_topics])
            )
            profile.knowledge_base.source = "llm_profile_extractor"
            profile.knowledge_base.confidence = max(profile.knowledge_base.confidence, extraction.confidence or 0.6)
            profile.knowledge_base.last_updated = now
            updated.append("knowledge_base")

        if extraction.preferences:
            data = {**profile.preferences.model_dump(), **extraction.preferences}
            if "resource_ranking" in data and data["resource_ranking"]:
                data["resource_ranking"] = _normalize_resource_ranking(data["resource_ranking"])
            profile.preferences = Preferences(**data)
            profile.preferences.source = "llm_profile_extractor"
            profile.preferences.confidence = max(profile.preferences.confidence, extraction.confidence or 0.65)
            profile.preferences.last_updated = now
            updated.append("preferences")

        if extraction.cognitive_style:
            data = {**profile.cognitive_style.model_dump(), **extraction.cognitive_style}
            profile.cognitive_style = CognitiveStyleInfo(**data)
            profile.cognitive_style.source = "llm_profile_extractor"
            profile.cognitive_style.confidence = max(
                profile.cognitive_style.confidence,
                extraction.confidence or 0.65,
            )
            profile.cognitive_style.last_updated = now
            updated.append("cognitive_style")

        if extraction.self_reported_weak_points:
            for item in extraction.self_reported_weak_points:
                for node_id, node_name, chapter_id in self._extract_node_hints(item.topic):
                    self._add_weak_node(
                        profile=profile,
                        node_id=node_id,
                        node_name=node_name,
                        chapter_id=chapter_id,
                        message=item.description or source_message,
                    )
                if not self._extract_node_hints(item.topic) and item.topic:
                    if not any(existing.topic == item.topic for existing in profile.weak_points.self_reported):
                        profile.weak_points.self_reported.append(
                            SelfReportedWeakPoint(topic=item.topic, description=item.description or source_message)
                        )
            profile.weak_points.source = "llm_profile_extractor"
            profile.weak_points.confidence = max(profile.weak_points.confidence, extraction.confidence or 0.65)
            profile.weak_points.last_updated = now
            updated.extend(["weak_points", "knowledge_base"])

        if extraction.ability_signals:
            for key, value in extraction.ability_signals.items():
                if hasattr(profile.ability_state, key) and value in {"weak", "basic", "intermediate", "advanced"}:
                    setattr(profile.ability_state, key, value)
            profile.ability_state.source = "llm_profile_extractor"
            profile.ability_state.confidence = max(profile.ability_state.confidence, extraction.confidence or 0.5)
            profile.ability_state.last_updated = now
            updated.append("ability_state")

        return list(dict.fromkeys(updated))

    def _apply_rule_extraction(self, profile: StudentProfile, message: str) -> list[str]:
        msg = message.lower()
        now = _now()
        updated: list[str] = []

        if "计算机" in message and not profile.background.major:
            profile.background.major = "计算机科学与技术"
            profile.background.source = "dialogue_rule"
            profile.background.confidence = 0.75
            profile.background.last_updated = now
            updated.append("background")

        parsed_grade = self._extract_grade(message)
        if parsed_grade is not None and profile.background.grade != parsed_grade:
            profile.background.grade = parsed_grade
            profile.background.source = "dialogue_rule"
            profile.background.confidence = max(profile.background.confidence, 0.75)
            profile.background.last_updated = now
            if "background" not in updated:
                updated.append("background")

        foundations: list[str] = []
        for keyword, label in [("python", "Python"), ("高数", "高等数学"), ("线代", "线性代数"), ("概率", "概率统计")]:
            if keyword in msg or keyword in message:
                foundations.append(label)
        if foundations:
            merged = list(dict.fromkeys([*profile.background.course_foundation, *foundations]))
            profile.background.course_foundation = merged
            profile.background.source = "dialogue_rule"
            profile.background.confidence = max(profile.background.confidence, 0.7)
            profile.background.last_updated = now
            existing = {item.topic for item in profile.knowledge_base.known_topics}
            for label in foundations:
                if label not in existing:
                    profile.knowledge_base.known_topics.append(
                        KnownTopic(topic=label, level="basic", evidence="学生在画像对话中提到已学过")
                    )
            profile.knowledge_base.source = "dialogue_rule"
            profile.knowledge_base.confidence = max(profile.knowledge_base.confidence, 0.7)
            profile.knowledge_base.last_updated = now
            for key in ["background", "knowledge_base"]:
                if key not in updated:
                    updated.append(key)

        if self._has_goal_signal(message):
            profile.learning_goal.description = self._extract_goal_description(message) or message
            if "课程项目" in message:
                profile.learning_goal.goal_type = ["course_project"]
            elif "竞赛" in message or "比赛" in message:
                profile.learning_goal.goal_type = ["competition"]
            elif "找工作" in message:
                profile.learning_goal.goal_type = ["employment"]
            else:
                profile.learning_goal.goal_type = profile.learning_goal.goal_type or ["interest"]
            profile.learning_goal.source = "dialogue_rule"
            profile.learning_goal.confidence = 0.65
            profile.learning_goal.last_updated = now
            updated.append("learning_goal")

        resource_ranking: list[str] = []
        if "图解" in message or "图" in message:
            resource_ranking.append("diagram")
        if "代码" in message or "编程" in message:
            resource_ranking.append("code_case")
        if "练习" in message or "题" in message:
            resource_ranking.append("exercise")
        if "视频" in message or "动画" in message:
            resource_ranking.append("video_script")
        if "文字" in message or "讲义" in message:
            resource_ranking.append("document")
        if resource_ranking:
            profile.preferences.resource_ranking = list(dict.fromkeys(resource_ranking))
            profile.preferences.source = "dialogue_rule"
            profile.preferences.confidence = 0.75
            profile.preferences.last_updated = now
            profile.cognitive_style.primary = "diagram" if "diagram" in resource_ranking else resource_ranking[0]
            profile.cognitive_style.secondary = "code" if "code_case" in resource_ranking else ""
            profile.cognitive_style.style_ranking = profile.preferences.resource_ranking
            profile.cognitive_style.source = "dialogue_rule"
            profile.cognitive_style.confidence = 0.7
            profile.cognitive_style.last_updated = now
            updated.extend(["preferences", "cognitive_style"])

        weak_markers = ["不懂", "不会", "薄弱", "吃力", "搞不清", "不太懂", "不太理解", "困难"]
        if any(marker in message for marker in weak_markers):
            weak_labels = self._extract_node_hints(message)
            for node_id, node_name, chapter_id in weak_labels:
                self._add_weak_node(profile, node_id, node_name, chapter_id, message)
            if weak_labels:
                profile.weak_points.source = "dialogue_rule"
                profile.weak_points.confidence = 0.75
                profile.weak_points.last_updated = now
                updated.extend(["weak_points", "knowledge_base"])

        return list(dict.fromkeys(updated))

    def _extract_grade(self, message: str) -> int | None:
        for pattern, grade in GRADE_PATTERNS:
            if pattern in message:
                return grade
        match = re.search(r"大\s*([1-4一二三四])", message)
        if not match:
            return None
        raw = match.group(1)
        return {"1": 1, "2": 2, "3": 3, "4": 4, "一": 1, "二": 2, "三": 3, "四": 4}.get(raw)

    def _has_goal_signal(self, message: str) -> bool:
        goal_markers = ["想学", "想要学", "目标", "课程项目", "比赛", "竞赛", "找工作", "想理解", "希望理解", "掌握", "搞懂"]
        return any(word in message for word in goal_markers)

    def _extract_goal_description(self, message: str) -> str:
        text = message.strip()
        text = re.sub(r"^我(是|其实是)?[^，。；;]*?(专业)?大[一二三四1-4](的)?(学生)?[，。；;、\s]*", "", text)
        text = re.sub(r"^学过[^，。；;]*(Python|高数|线代|概率)[^，。；;]*[，。；;、\s]*", "", text, flags=re.IGNORECASE)
        text = text.replace("我想", "想").replace("我希望", "希望").strip("，。；;、 ")
        if not text:
            return ""
        parts = re.split(r"[。；;]", text)
        goal_parts = [
            part.strip("，, ")
            for part in parts
            if self._has_goal_signal(part)
        ]
        return "；".join(goal_parts or [text])

    def _normalize_profile_text(self, profile: StudentProfile, message: str) -> list[str]:
        updated: list[str] = []
        normalized_goal = self._extract_goal_description(profile.learning_goal.description)
        if normalized_goal and normalized_goal != profile.learning_goal.description:
            profile.learning_goal.description = normalized_goal
            profile.learning_goal.last_updated = _now()
            if not profile.learning_goal.source:
                profile.learning_goal.source = "dialogue_rule"
            updated.append("learning_goal")

        # When a later utterance is only correcting background information, keep the
        # learning goal stable instead of treating the correction itself as a goal.
        if self._extract_grade(message) is not None and not self._has_goal_signal(message):
            correction_text = self._extract_goal_description(message)
            if correction_text == profile.learning_goal.description:
                profile.learning_goal.description = ""
                updated.append("learning_goal")
        return updated

    def _extract_node_hints(self, message: str) -> list[tuple[str, str, str]]:
        lowered = message.lower()
        hits: list[tuple[str, str, str]] = []
        for keyword, node in NODE_HINTS.items():
            if keyword in lowered or keyword in message:
                hits.append(node)
        return list(dict.fromkeys(hits))

    def _add_weak_node(
        self,
        profile: StudentProfile,
        node_id: str,
        node_name: str,
        chapter_id: str,
        message: str,
    ) -> None:
        if not any(item.node_id == node_id for item in profile.weak_points.self_reported):
            profile.weak_points.self_reported.append(
                SelfReportedWeakPoint(topic=node_name, node_id=node_id, description=message)
            )
        profile.node_mastery[node_id] = KnowledgePointMastery(
            node_id=node_id,
            node_name=node_name,
            chapter_id=chapter_id,
            mastery_score=0.2,
            level="weak",
            confidence=0.65,
        )

    def _upsert_diagnosed_weak_point(self, profile: StudentProfile, node_id: str, now: datetime) -> None:
        for item in profile.weak_points.diagnosed:
            if item.node_id == node_id:
                item.total_attempts += 1
                item.error_rate = min(1.0, round((item.error_rate + 1.0) / 2, 4))
                item.last_wrong_at = now
                return
        profile.weak_points.diagnosed.append(
            DiagnosedWeakPoint(
                node_id=node_id,
                error_rate=1.0,
                total_attempts=1,
                last_wrong_at=now,
            )
        )

    def _exercise_delta(
        self,
        is_correct: bool,
        difficulty: int,
        cognitive_level: str,
        used_hint: bool,
    ) -> float:
        difficulty_weight = 0.02 + difficulty * 0.01
        task_weight = {
            "remember": 0.6,
            "understand": 0.8,
            "apply": 1.0,
            "analyze": 1.2,
            "create": 1.3,
        }.get(cognitive_level, 1.0)
        hint_penalty = 0.5 if used_hint else 1.0
        if is_correct:
            return difficulty_weight * task_weight * hint_penalty
        return -difficulty_weight * 1.2

    def _next_reply(
        self,
        profile: StudentProfile,
        missing: list[str],
        completed: bool,
        updated_fields: list[str],
        message: str,
        previous_profile: StudentProfile,
    ) -> str:
        acknowledgements: list[str] = []
        if "background" in updated_fields:
            background_bits = []
            if profile.background.major:
                background_bits.append(profile.background.major)
            if profile.background.grade:
                background_bits.append(_grade_label(profile.background.grade))
            if previous_profile.background.grade and previous_profile.background.grade != profile.background.grade:
                acknowledgements.append(
                    f"好的，我已把年级从{_grade_label(previous_profile.background.grade)}修正为{_grade_label(profile.background.grade)}。"
                )
            else:
                acknowledgements.append(f"收到，我已把你的专业背景更新为：{' · '.join(background_bits) or '已补充背景信息'}。")
        if "learning_goal" in updated_fields and profile.learning_goal.description:
            acknowledgements.append(f"学习目标我整理为：{profile.learning_goal.description}")
        if "knowledge_base" in updated_fields:
            known = "、".join(item.topic for item in profile.knowledge_base.known_topics[:4])
            if known:
                acknowledgements.append(f"知识基础里已记录：{known}。")
        if "weak_points" in updated_fields:
            weak = "、".join(item.topic for item in profile.weak_points.self_reported[:3])
            if weak:
                acknowledgements.append(f"薄弱点我会优先关注：{weak}。")
        if "preferences" in updated_fields:
            preferences = "、".join(_resource_label(item) for item in profile.preferences.resource_ranking)
            if preferences:
                acknowledgements.append(f"资源偏好已更新为：{preferences}。")

        if not acknowledgements:
            acknowledgements.append("我收到这条补充了，会结合前面的画像一起判断。")

        if completed:
            next_step = self._next_profile_question(profile, missing)
            if next_step:
                return "\n".join([*acknowledgements, next_step])
            return "\n".join(
                [
                    *acknowledgements,
                    self._ready_summary(profile),
                ]
            )
        next_step = self._next_profile_question(profile, missing)
        if next_step:
            return "\n".join([*acknowledgements, next_step])
        return "\n".join([*acknowledgements, self._ready_summary(profile)])

    def _ready_summary(self, profile: StudentProfile) -> str:
        parts = ["现在画像已经比较完整。"]
        if profile.learning_goal.description:
            parts.append(f"目标按“{profile.learning_goal.description}”处理。")
        weak = "、".join(item.topic for item in profile.weak_points.self_reported[:2])
        if weak:
            parts.append(f"后续会优先补强 {weak}。")
        if profile.preferences.resource_ranking:
            labels = "、".join(_resource_label(item) for item in profile.preferences.resource_ranking[:2])
            parts.append(f"资源会优先用{labels}的形式呈现。")
        parts.append("你也可以继续修正画像，或者点“已完成”进入学习路径和资源生成。")
        return "".join(parts)

    def _next_profile_question(self, profile: StudentProfile, missing: list[str]) -> str:
        if "background" in missing:
            return "我还需要了解你的专业、年级，以及之前学过哪些编程或数学课程。"
        if "learning_goal" in missing:
            return "你学习这门课主要是为了课程项目、考试、竞赛，还是就业准备？"
        if "knowledge_base" in missing:
            return "接下来我想确认你的知识基础：除了 Python 和高数，你对线性代数、概率统计、损失函数或梯度这些内容熟悉吗？"
        if "preferences" in missing or "cognitive_style" in missing:
            return "你更喜欢图解、代码案例、练习题、视频脚本，还是文字讲义？"
        if profile.weak_points.self_reported:
            return "如果你愿意，可以再补一句：这些薄弱点里你最想先解决哪一个？"
        return ""

    def _build_dimension_views(self, profile: StudentProfile, missing: list[str]) -> list[ProfileDimensionView]:
        def status(key: str, confidence: float) -> str:
            if key in missing:
                return "missing"
            if confidence and confidence < 0.6:
                return "low_confidence"
            return "filled"

        return [
            ProfileDimensionView(
                key="background",
                title="专业背景",
                icon="User",
                summary=f"{profile.background.major or '未填写'} · 大{profile.background.grade or '?'}",
                tags=profile.background.course_foundation,
                confidence=profile.background.confidence,
                source=profile.background.source,
                last_updated=profile.background.last_updated,
                status=status("background", profile.background.confidence),
            ),
            ProfileDimensionView(
                key="learning_goal",
                title="学习目标",
                icon="Target",
                summary=profile.learning_goal.description or "未填写学习目标",
                tags=profile.learning_goal.goal_type,
                confidence=profile.learning_goal.confidence,
                source=profile.learning_goal.source,
                last_updated=profile.learning_goal.last_updated,
                status=status("learning_goal", profile.learning_goal.confidence),
            ),
            ProfileDimensionView(
                key="knowledge_base",
                title="知识掌握",
                icon="BookOpen",
                summary=f"{len(profile.node_mastery)} 个知识点有掌握度记录",
                tags=[item.topic for item in profile.knowledge_base.known_topics],
                confidence=profile.knowledge_base.confidence,
                source=profile.knowledge_base.source,
                last_updated=profile.knowledge_base.last_updated,
                status=status("knowledge_base", profile.knowledge_base.confidence),
            ),
            ProfileDimensionView(
                key="weak_points",
                title="薄弱点",
                icon="AlertTriangle",
                summary=f"{len(profile.weak_points.self_reported) + len(profile.weak_points.diagnosed)} 个薄弱点",
                tags=[item.topic for item in profile.weak_points.self_reported],
                confidence=profile.weak_points.confidence,
                source=profile.weak_points.source,
                last_updated=profile.weak_points.last_updated,
                status=status("weak_points", profile.weak_points.confidence),
            ),
            ProfileDimensionView(
                key="preferences",
                title="学习偏好",
                icon="SlidersHorizontal",
                summary=" > ".join(_resource_label(item) for item in profile.preferences.resource_ranking) or "未填写偏好",
                tags=[_resource_label(item) for item in profile.preferences.resource_ranking],
                confidence=profile.preferences.confidence,
                source=profile.preferences.source,
                last_updated=profile.preferences.last_updated,
                status=status("preferences", profile.preferences.confidence),
            ),
        ]

    def _build_weak_points(self, profile: StudentProfile) -> list[WeakPointRankItem]:
        items = [
            WeakPointRankItem(
                label=item.topic,
                node_id=item.node_id,
                source="self_reported",
                score=0.8,
            )
            for item in profile.weak_points.self_reported
        ]
        for mastery in profile.node_mastery.values():
            if mastery.mastery_score < 0.35:
                items.append(
                    WeakPointRankItem(
                        label=mastery.node_name or mastery.node_id,
                        node_id=mastery.node_id,
                        source="mastery",
                        score=round(1.0 - mastery.mastery_score, 4),
                    )
                )
        return sorted(items, key=lambda item: item.score, reverse=True)

    def _headline(self, profile: StudentProfile) -> str:
        major = profile.background.major or "未填写专业"
        goal = profile.learning_goal.description or "待明确学习目标"
        return f"{major}学生，目标：{goal[:40]}"

    def _personalization_reasons(self, profile: StudentProfile) -> list[str]:
        reasons: list[str] = []
        if profile.preferences.resource_ranking:
            labels = [_resource_label(item) for item in profile.preferences.resource_ranking]
            reasons.append(f"资源生成会优先匹配偏好：{' > '.join(labels)}。")
        weak = [item.node_name or item.node_id for item in profile.node_mastery.values() if item.mastery_score < 0.35]
        if weak:
            reasons.append(f"路径规划会优先补强薄弱知识点：{', '.join(weak[:3])}。")
        if profile.learning_goal.description:
            reasons.append("图谱增强检索会结合当前学习目标调整证据排序。")
        return reasons
