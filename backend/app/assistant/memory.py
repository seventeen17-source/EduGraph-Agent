from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant import models
from app.assistant.schemas import (
    AssistantAction,
    AssistantConversationRecord,
    AssistantHistoryResponse,
    AssistantMessageRecord,
    AssistantTraceItem,
)


class AssistantMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_get_conversation(
        self,
        *,
        student_id: str,
        conversation_id: str | None,
        title_hint: str,
    ) -> models.AssistantConversation:
        if conversation_id:
            existing = await self.session.get(models.AssistantConversation, conversation_id)
            if existing is not None and existing.student_id == student_id:
                return existing

        title = title_hint.strip()[:60] or "学习助手会话"
        conversation = models.AssistantConversation(student_id=student_id, title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def create_run(self, *, conversation_id: str, student_id: str, input_json: dict) -> models.AssistantRun:
        run = models.AssistantRun(
            conversation_id=conversation_id,
            student_id=student_id,
            input_json=input_json,
            status="running",
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        output_json: dict,
        agent_trace_json: list,
        actions_json: list,
        error_message: str = "",
    ) -> None:
        run = await self.session.get(models.AssistantRun, run_id)
        if run is None:
            return
        run.status = status
        run.output_json = output_json
        run.agent_trace_json = agent_trace_json
        run.actions_json = actions_json
        run.error_message = error_message
        run.finished_at = datetime.utcnow()
        await self.session.flush()

    async def add_message(
        self,
        *,
        conversation_id: str,
        student_id: str,
        role: str,
        content: str,
        intent: str = "",
        target_node_id: str = "",
        agent_trace_json: list | None = None,
        actions_json: list | None = None,
        resource_record_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> models.AssistantMessage:
        message = models.AssistantMessage(
            conversation_id=conversation_id,
            student_id=student_id,
            role=role,
            content=content,
            intent=intent or "",
            target_node_id=target_node_id or "",
            agent_trace_json=agent_trace_json or [],
            actions_json=actions_json or [],
            resource_record_id=resource_record_id,
            metadata_json=metadata_json or {},
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def add_actions(
        self,
        *,
        run_id: str,
        conversation_id: str,
        student_id: str,
        actions: list[AssistantAction],
    ) -> None:
        for action in actions:
            self.session.add(
                models.AssistantActionRecord(
                    run_id=run_id,
                    conversation_id=conversation_id,
                    student_id=student_id,
                    action_type=action.type,
                    label=action.label,
                    reason=action.description,
                    payload_json=action.model_dump(mode="json"),
                )
            )
        await self.session.flush()

    async def touch_conversation(self, conversation_id: str, *, last_intent: str, summary: str = "") -> None:
        conversation = await self.session.get(models.AssistantConversation, conversation_id)
        if conversation is None:
            return
        conversation.last_intent = last_intent or conversation.last_intent
        if summary:
            conversation.summary = summary
        conversation.updated_at = datetime.utcnow()
        await self.session.flush()

    async def list_recent_messages(self, conversation_id: str, limit: int = 12) -> list[AssistantMessageRecord]:
        rows = await self.session.scalars(
            select(models.AssistantMessage)
            .where(models.AssistantMessage.conversation_id == conversation_id)
            .order_by(desc(models.AssistantMessage.created_at))
            .limit(limit)
        )
        return [self._message_record(row) for row in reversed(list(rows))]

    async def get_history(self, student_id: str, limit: int = 80) -> AssistantHistoryResponse:
        conversations_result = await self.session.scalars(
            select(models.AssistantConversation)
            .where(models.AssistantConversation.student_id == student_id)
            .order_by(desc(models.AssistantConversation.updated_at))
            .limit(20)
        )
        conversations = list(conversations_result)
        messages_result = await self.session.scalars(
            select(models.AssistantMessage)
            .where(models.AssistantMessage.student_id == student_id)
            .order_by(desc(models.AssistantMessage.created_at))
            .limit(limit)
        )
        return AssistantHistoryResponse(
            student_id=student_id,
            conversations=[
                AssistantConversationRecord(
                    id=row.id,
                    student_id=row.student_id,
                    title=row.title,
                    last_intent=row.last_intent,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in conversations
            ],
            messages=[self._message_record(row) for row in reversed(list(messages_result))],
        )

    def _message_record(self, row: models.AssistantMessage) -> AssistantMessageRecord:
        return AssistantMessageRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            role=row.role,  # type: ignore[arg-type]
            content=row.content,
            intent=row.intent,
            target_node_id=row.target_node_id,
            resource_record_id=row.resource_record_id,
            resource_has_exercises=bool((row.metadata_json or {}).get("resource_has_exercises")),
            actions=[AssistantAction.model_validate(item) for item in (row.actions_json or [])],
            agent_trace=[AssistantTraceItem.model_validate(item) for item in (row.agent_trace_json or [])],
            created_at=row.created_at,
        )
