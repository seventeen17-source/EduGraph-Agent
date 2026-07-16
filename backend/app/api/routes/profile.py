from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_profile_service
from app.profile.schemas import (
    ExerciseResultProfileUpdateRequest,
    ExerciseRoundProfileUpdateRequest,
    LearningProgressUpdateRequest,
    ManualProfilePatchRequest,
    MasteryEvidenceRecord,
    ProfileChatMessageRecord,
    ProfileChatRequest,
    ProfileChatResponse,
    ProfileDashboardResponse,
    ProfileEventResponse,
    ProfileInitRequest,
    ProfileUpdateRecord,
    StudentProfile,
    WeeklyReportResponse,
)
from app.profile.service import ProfileService

router = APIRouter()


@router.post("/init", response_model=ProfileChatResponse)
async def init_profile(
    payload: ProfileInitRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileChatResponse:
    return await service.initialize_profile(
        student_id=payload.student_id,
        message=payload.message,
        display_name=payload.display_name,
    )


@router.post("/chat", response_model=ProfileChatResponse)
async def chat_profile(
    payload: ProfileChatRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileChatResponse:
    return await service.chat(
        student_id=payload.student_id,
        message=payload.message,
        display_name=payload.display_name,
    )


@router.post("/events/exercise-result", response_model=ProfileEventResponse)
async def update_profile_from_exercise_result(
    payload: ExerciseResultProfileUpdateRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileEventResponse:
    return await service.apply_exercise_result(payload)


@router.post("/events/exercise-round", response_model=ProfileEventResponse)
async def update_profile_from_exercise_round(
    payload: ExerciseRoundProfileUpdateRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileEventResponse:
    return await service.apply_exercise_round(payload)


@router.post("/events/learning-progress", response_model=ProfileEventResponse)
async def update_profile_from_learning_progress(
    payload: LearningProgressUpdateRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileEventResponse:
    return await service.apply_learning_progress(payload)


@router.get("/{student_id}", response_model=StudentProfile)
async def get_profile(
    student_id: str,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> StudentProfile:
    return await service.get_profile(student_id)


@router.get("/{student_id}/dashboard", response_model=ProfileDashboardResponse)
async def get_profile_dashboard(
    student_id: str,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileDashboardResponse:
    return await service.get_dashboard(student_id)


@router.get("/{student_id}/history", response_model=list[ProfileUpdateRecord])
async def get_profile_history(
    student_id: str,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> list[ProfileUpdateRecord]:
    return await service.list_history(student_id)


@router.get("/{student_id}/chat-history", response_model=list[ProfileChatMessageRecord])
async def get_profile_chat_history(
    student_id: str,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> list[ProfileChatMessageRecord]:
    return await service.list_chat_messages(student_id)


@router.get("/{student_id}/evidence/{node_id}", response_model=list[MasteryEvidenceRecord])
async def get_node_evidence(
    student_id: str,
    node_id: str,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> list[MasteryEvidenceRecord]:
    """返回某知识点的掌握度证据列表。"""
    return await service.list_node_evidence(student_id, node_id)


@router.get("/{student_id}/timeline")
async def get_learning_timeline(
    student_id: str,
    service: Annotated[ProfileService, Depends(get_profile_service)],
    days: int = 90,
):
    """获取学生成长时间轴。

    返回月度/周度/日度聚合的学习事件、学习统计、遗忘预警。
    所有数据从已有 ProfileUpdateRecord + node_mastery 实时构建，不做持久化。
    """
    from app.profile.timeline import ForgettingDetector, TimelineBuilder

    # 1. 获取原始数据
    profile = await service.get_profile(student_id)
    history = await service.list_history(student_id)
    # 限制查询范围（去掉时区信息后比较）
    import datetime as _dt
    cutoff = _dt.datetime.utcnow() - _dt.timedelta(days=days)
    history = [h for h in history if h.timestamp and (
        h.timestamp.replace(tzinfo=None) if hasattr(h.timestamp, 'replace') and h.timestamp.tzinfo is not None else h.timestamp
    ) >= cutoff]

    # 2. 从 assistant_messages 生成提问事件（可选）
    try:
        from app.assistant.memory import AssistantMemoryRepository
        from app.api.deps import get_db_session
    except Exception:
        pass

    # 3. 构建时间轴
    builder = TimelineBuilder(
        profile_updates=history,
        node_mastery=profile.node_mastery,
    )
    response = builder.build(days=days)
    response.student_id = student_id

    # 4. 遗忘检测
    detector = ForgettingDetector()
    response.forgetting_soon = detector.detect(profile.node_mastery)

    # 5. 写入遗忘检测证据（去重，7天内不重复）
    if response.forgetting_soon:
        await service.record_forgetting_evidence(student_id, response.forgetting_soon)

    # 从 profile 补充统计
    response.stats.total_exercises = sum(
        m.attempts for m in profile.node_mastery.values()
    )
    response.stats.total_feedback = profile.learning_behavior.total_feedback_count

    return response


@router.patch("/{student_id}", response_model=StudentProfile)
async def patch_profile(
    student_id: str,
    payload: ManualProfilePatchRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> StudentProfile:
    return await service.patch_profile(student_id, payload)


@router.get("/{student_id}/report", response_model=WeeklyReportResponse)
async def get_learning_report(
    student_id: str,
    service: Annotated[ProfileService, Depends(get_profile_service)],
    days: int = 7,
) -> WeeklyReportResponse:
    """生成学习周报/月报。

    支持通过 days 参数切换周报（默认 7 天）或月报（days=30）。
    返回本周/本月练习统计、掌握度变化、遗忘预警和推荐下一步学习。
    """
    return await service.generate_weekly_report(student_id, days=days)
