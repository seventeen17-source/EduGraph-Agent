from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_assistant_service, get_db_session
from app.assistant.feedback import FeedbackRepository
from app.assistant.schemas import AssistantChatRequest, AssistantHistoryResponse, AssistantResponse
from app.assistant.service import AssistantService
from app.core.config import Settings, get_settings
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/chat", response_model=AssistantResponse)
async def chat_assistant(
    payload: AssistantChatRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantResponse:
    return await service.chat(payload)


@router.post("/stream")
async def stream_assistant(
    payload: AssistantChatRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> StreamingResponse:
    return StreamingResponse(
        service.stream(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{student_id}/history", response_model=AssistantHistoryResponse)
async def get_assistant_history(
    student_id: str,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantHistoryResponse:
    return await service.history(student_id)


# ── 反馈端点 ──


class FeedbackSubmitRequest(BaseModel):
    message_id: str
    student_id: str
    tags: list[str] = Field(default_factory=list)
    # 可选值: helpful, clear, dont_get, too_hard, too_easy,
    #         too_vague, want_examples, want_summary, incorrect
    free_text: str | None = None
    conversation_id: str = ""
    intent: str = ""
    target_node_id: str = ""


class FeedbackSubmitResponse(BaseModel):
    ok: bool = True
    feedback_id: str = ""
    created: bool = True            # True=新增, False=更新已有
    profile_updated: bool = False   # 行为画像是否已更新
    profile_update_error: str = ""  # 画像更新失败时的错误信息
    adaptation_summary: str = ""    # 展示给学生的下次个性化调整说明
    action_taken: str = ""          # 系统触发的动作类型（re_explain/simplify/advance 等）
    action_result: str = ""         # 系统响应给学生的说明消息


def _extract_reply_features(content: str) -> dict:
    """从回复内容中提取特征，用于反馈分析。"""
    if not content:
        return {}
    features: dict = {}
    features["has_code"] = bool(
        any(kw in content for kw in ["```python", "```", "def ", "import ", "class ", "print("])
    )
    features["has_formula"] = bool(
        any(kw in content for kw in ["$$", "$", "\\frac", "\\sum", "\\partial", "\\theta", "\\nabla"])
    )
    features["has_diagram"] = bool(
        any(kw in content for kw in ["mermaid", "graph ", "flowchart", "图示", "如图所示", "下图"])
    )
    features["has_analogy"] = bool(
        any(kw in content for kw in ["想象", "就像", "好比", "比喻", "类比", "相当于", "可以把"])
    )
    styles = []
    if features.get("has_formula"):
        styles.append("公式推导")
    if features.get("has_code"):
        styles.append("代码示例")
    if features.get("has_diagram"):
        styles.append("图解")
    if features.get("has_analogy"):
        styles.append("类比")
    if not styles:
        length = len(content)
        if length < 300:
            styles.append("简短概述")
        elif length < 800:
            styles.append("中等详细")
        else:
            styles.append("详细讲解")
    features["style"] = " + ".join(styles)
    features["length"] = len(content)
    return features


def _feedback_adaptation_summary(tags: list[str], free_text: str | None) -> str:
    actions: list[str] = []
    tag_set = set(tags or [])
    if "dont_get" in tag_set:
        actions.append("下次会先补前置概念，并减少跳步推理")
    if "too_hard" in tag_set:
        actions.append("下次会降低讲解难度，用更基础的例子开始")
    if "too_easy" in tag_set:
        actions.append("下次会提高挑战度，增加推导、对比或综合题")
    if "want_examples" in tag_set:
        actions.append("下次会优先加入例题、代码或具体场景")
    if "want_summary" in tag_set:
        actions.append("下次会在结尾给出更清晰的要点总结")
    if "too_vague" in tag_set:
        actions.append("下次会给出更具体的步骤、依据和可执行建议")
    if not actions and tag_set.intersection({"helpful", "clear"}):
        actions.append("系统会保留这类回答风格作为后续偏好")
    if free_text:
        actions.append("你的补充说明也会作为行为画像信号参与后续调整")
    return "；".join(dict.fromkeys(actions)) or "反馈已记录，会用于后续个性化调整"


@router.post("/feedback", response_model=FeedbackSubmitResponse)
async def submit_feedback(
    payload: FeedbackSubmitRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FeedbackSubmitResponse:
    # 1. 校验消息归属
    from sqlalchemy import select as sa_select
    from app.assistant import models as am

    row = await session.scalar(
        sa_select(am.AssistantMessage).where(am.AssistantMessage.id == payload.message_id)
    )
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"消息不存在: {payload.message_id}")
    if row.student_id != payload.student_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="消息不属于该学生")
    if row.role != "assistant":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="只能给助手回复提供反馈")

    # 2. 优先使用消息中的 intent / target_node_id
    intent = row.intent or payload.intent
    target_node_id = row.target_node_id or payload.target_node_id
    conversation_id = row.conversation_id or payload.conversation_id

    # 3. 提取回复特征
    reply_features = _extract_reply_features(row.content or "")

    # 4. 写入或更新反馈（同 student_id + message_id 去重）
    from app.assistant.feedback import FeedbackRepository
    repo = FeedbackRepository(session)
    fb, created = await repo.create_or_update(
        message_id=payload.message_id,
        student_id=payload.student_id,
        conversation_id=conversation_id,
        tags=payload.tags,
        free_text=payload.free_text,
        intent=intent,
        target_node_id=target_node_id,
        reply_features=reply_features,
    )

    # 5. 增量更新行为画像（仅新增反馈时累计，更新已有反馈不重复累计）
    profile_updated = False
    profile_update_error = ""
    if created:
        try:
            from app.profile.behavior_updater import BehaviorProfileUpdater
            from app.profile.repository import ProfileRepository

            profile_repo = ProfileRepository(session)
            profile = await profile_repo.get_profile(payload.student_id)
            if profile is not None:
                updater = BehaviorProfileUpdater()
                updater.update(
                    profile.learning_behavior,
                    tags=payload.tags,
                    reply_features=reply_features,
                    target_node_id=target_node_id,
                    intent=intent,
                )
                await profile_repo.save_learning_behavior(
                    payload.student_id,
                    profile.learning_behavior,
                )
                profile_updated = True
        except Exception as exc:
            profile_update_error = f"{type(exc).__name__}: {exc}"

    # 6. 触发反馈闭环动作（按优先级匹配负反馈标签 → 生成系统响应）
    action_taken = ""
    action_result = ""
    try:
        from app.assistant.feedback_analyzer import FeedbackAnalyzer
        analyzer = FeedbackAnalyzer(settings)
        action_info = analyzer.trigger_feedback_action(
            feedback_tags=payload.tags,
            message_content=row.content or "",
            student_id=payload.student_id,
        )
        action_taken = action_info.get("action", "")
        action_result = action_info.get("user_message", "")
        # 持久化到反馈记录
        fb.action_taken = action_taken or None
        fb.action_result = action_result or None
    except Exception:
        # 触发动作失败不影响反馈提交
        pass

    await session.commit()
    return FeedbackSubmitResponse(
        feedback_id=fb.id,
        created=created,
        profile_updated=profile_updated,
        profile_update_error=profile_update_error,
        adaptation_summary=_feedback_adaptation_summary(payload.tags, payload.free_text),
        action_taken=action_taken,
        action_result=action_result,
    )


@router.post("/feedback/analyze/{student_id}")
async def analyze_feedback(
    student_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """显式触发 LLM 反馈分析（演示/调试用）。

    独立 session，不依赖 LangGraph 节点。
    """
    from app.assistant.feedback import FeedbackRepository
    from app.assistant.feedback_analyzer import FeedbackAnalyzer
    from app.profile.repository import ProfileRepository
    from app.profile.service import ProfileService
    from app.profile.extractor import ProfileExtractor

    repo = FeedbackRepository(session)
    profile_service = ProfileService(
        ProfileRepository(session),
        extractor=ProfileExtractor(settings),
    )
    analyzer = FeedbackAnalyzer(settings)
    try:
        result = await analyzer.analyze_and_update_profile(
            student_id,
            feedback_repo=repo,
            profile_service=profile_service,
        )
        await session.commit()
        return result
    except Exception as exc:
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "analyzed_count": 0,
        }


@router.get("/feedback/stats/{student_id}")
async def get_feedback_stats(
    student_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = 30,
):
    repo = FeedbackRepository(session)
    total = await repo.total_count(student_id)
    by_intent = await repo.tag_counts_by_intent(student_id, days=days)
    by_node = await repo.tag_counts_by_node(student_id, days=days)
    recent = await repo.recent_feedback(student_id, limit=10)
    return {
        "student_id": student_id,
        "total": total,
        "by_intent": by_intent,
        "by_node": by_node,
        "recent": [
            {
                "id": fb.id,
                "tags": fb.tags,
                "free_text": fb.free_text,
                "intent": fb.intent,
                "target_node_id": fb.target_node_id,
                "action_taken": fb.action_taken or "",
                "action_result": fb.action_result or "",
                "created_at": fb.created_at.isoformat(),
            }
            for fb in recent
        ],
    }
