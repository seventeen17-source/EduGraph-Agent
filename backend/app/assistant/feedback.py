"""反馈收集与聚合查询。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import models


class FeedbackRepository:
    """学生反馈的 CRUD 与聚合查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── 写入 ──

    async def create_or_update(
        self,
        *,
        message_id: str,
        student_id: str,
        run_id: str = "",
        conversation_id: str = "",
        tags: list[str] | None = None,
        free_text: str | None = None,
        intent: str = "",
        target_node_id: str = "",
        reply_features: dict | None = None,
    ) -> tuple[models.AssistantFeedback, bool]:
        """创建或更新反馈。同一 student_id + message_id 只保留一条记录。

        Returns:
            (feedback, created): created=True 表示新增，False 表示更新了已有记录。
        """
        existing = await self.get_for_message(message_id, student_id)
        if existing is not None:
            # 更新已有记录
            existing.tags = tags or []
            if free_text is not None:
                existing.free_text = free_text
            existing.intent = intent or existing.intent
            existing.target_node_id = target_node_id or existing.target_node_id
            existing.reply_features = reply_features or existing.reply_features
            await self.session.flush()
            return existing, False

        return await self.create(
            message_id=message_id,
            run_id=run_id,
            student_id=student_id,
            conversation_id=conversation_id,
            tags=tags,
            free_text=free_text,
            intent=intent,
            target_node_id=target_node_id,
            reply_features=reply_features,
        ), True

    async def create(
        self,
        *,
        message_id: str,
        run_id: str = "",
        student_id: str,
        conversation_id: str = "",
        tags: list[str] | None = None,
        free_text: str | None = None,
        intent: str = "",
        target_node_id: str = "",
        reply_features: dict | None = None,
    ) -> models.AssistantFeedback:
        feedback = models.AssistantFeedback(
            message_id=message_id,
            run_id=run_id,
            student_id=student_id,
            conversation_id=conversation_id,
            tags=tags or [],
            free_text=free_text,
            intent=intent,
            target_node_id=target_node_id,
            reply_features=reply_features or {},
        )
        self.session.add(feedback)
        await self.session.flush()
        return feedback

    # ── 查询 ──

    async def count_unanalyzed(self, student_id: str) -> int:
        """统计未分析的反馈数量。"""
        result = await self.session.scalar(
            select(func.count(models.AssistantFeedback.id)).where(
                models.AssistantFeedback.student_id == student_id,
                models.AssistantFeedback.analyzed == False,  # noqa: E712
            )
        )
        return result or 0

    async def list_unanalyzed(self, student_id: str, limit: int = 50) -> list[models.AssistantFeedback]:
        """列出未分析的反馈。"""
        rows = await self.session.scalars(
            select(models.AssistantFeedback)
            .where(
                models.AssistantFeedback.student_id == student_id,
                models.AssistantFeedback.analyzed == False,  # noqa: E712
            )
            .order_by(models.AssistantFeedback.created_at)
            .limit(limit)
        )
        return list(rows)

    async def mark_analyzed(self, feedback_ids: list[str]) -> None:
        """将反馈标记为已分析。"""
        if not feedback_ids:
            return
        await self.session.execute(
            select(models.AssistantFeedback).where(
                models.AssistantFeedback.id.in_(feedback_ids)
            )
        )
        for fid in feedback_ids:
            fb = await self.session.get(models.AssistantFeedback, fid)
            if fb:
                fb.analyzed = True
        await self.session.flush()

    # ── 聚合 ──

    async def tag_counts_by_intent(
        self,
        student_id: str,
        days: int = 30,
    ) -> dict[str, dict[str, int]]:
        """按 intent 统计标签分布。
        返回: {"concept_explain": {"helpful": 5, "dont_get": 2}, ...}
        """
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)

        rows = await self.session.scalars(
            select(models.AssistantFeedback).where(
                models.AssistantFeedback.student_id == student_id,
                models.AssistantFeedback.created_at >= cutoff,
            )
        )
        result: dict[str, dict[str, int]] = {}
        for fb in rows:
            if fb.intent not in result:
                result[fb.intent] = {}
            for tag in fb.tags or []:
                result[fb.intent][tag] = result[fb.intent].get(tag, 0) + 1
        return result

    async def tag_counts_by_node(
        self,
        student_id: str,
        days: int = 30,
    ) -> dict[str, dict[str, int]]:
        """按知识点统计标签分布。"""
        cutoff = datetime.utcnow()
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)

        rows = await self.session.scalars(
            select(models.AssistantFeedback).where(
                models.AssistantFeedback.student_id == student_id,
                models.AssistantFeedback.created_at >= cutoff,
                models.AssistantFeedback.target_node_id != "",
            )
        )
        result: dict[str, dict[str, int]] = {}
        for fb in rows:
            node = fb.target_node_id or "unknown"
            if node not in result:
                result[node] = {}
            for tag in fb.tags or []:
                result[node][tag] = result[node].get(tag, 0) + 1
        return result

    async def recent_feedback(
        self,
        student_id: str,
        limit: int = 20,
    ) -> list[models.AssistantFeedback]:
        """获取最近的反馈记录。"""
        rows = await self.session.scalars(
            select(models.AssistantFeedback)
            .where(models.AssistantFeedback.student_id == student_id)
            .order_by(desc(models.AssistantFeedback.created_at))
            .limit(limit)
        )
        return list(rows)

    async def total_count(self, student_id: str) -> int:
        """统计总反馈数。"""
        result = await self.session.scalar(
            select(func.count(models.AssistantFeedback.id)).where(
                models.AssistantFeedback.student_id == student_id,
            )
        )
        return result or 0

    async def get_for_message(
        self, message_id: str, student_id: str | None = None,
    ) -> models.AssistantFeedback | None:
        """获取某条消息的反馈，可选限制 student_id。"""
        conditions = [models.AssistantFeedback.message_id == message_id]
        if student_id:
            conditions.append(models.AssistantFeedback.student_id == student_id)
        return await self.session.scalar(
            select(models.AssistantFeedback).where(*conditions)
        )
