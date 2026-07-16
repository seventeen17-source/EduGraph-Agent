from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from app.assistant.graph import build_assistant_graph

logger = logging.getLogger(__name__)
from app.assistant.memory import AssistantMemoryRepository
from app.assistant.schemas import AssistantChatRequest, AssistantHistoryResponse, AssistantResponse, ClarifyOption
from app.assistant.state import AssistantState
from app.assistant.tools import AssistantTools
from app.core.config import Settings
from app.memory.embedding import EmbeddingService
from app.memory.extractor import MemoryExtractor
from app.memory.vector_store import MemoryVectorStore


class AssistantService:
    def __init__(
        self,
        *,
        settings: Settings,
        memory: AssistantMemoryRepository,
        tools: AssistantTools,
    ) -> None:
        self.settings = settings
        self.memory = memory
        self.tools = tools
        self.graph = build_assistant_graph(tools)
        # 初始化语义记忆服务
        self._init_memory_services(settings, tools)

    def _init_memory_services(self, settings: Settings, tools: AssistantTools) -> None:
        """初始化 embedding、向量存储、记忆提取器，注入到 tools 中。"""
        try:
            if not (settings.embedding_api_key or settings.llm_api_key):
                raise RuntimeError("Embedding credential is not configured.")
            embedding_service = EmbeddingService(settings)
            memory_store = MemoryVectorStore(
                settings,
                embedding_dim=embedding_service.embedding_dim(),
            )
            memory_extractor = MemoryExtractor(settings)
            tools.embedding_service = embedding_service
            tools.memory_store = memory_store
            tools.memory_extractor = memory_extractor
            tools.graphrag_service.set_memory_services(
                embedding_service=embedding_service,
                memory_store=memory_store,
            )
            # 异步种子记忆（不阻塞服务启动）
            import asyncio
            asyncio.create_task(self._seed_demo_memories(embedding_service, memory_store))
        except Exception as exc:
            logger.warning("Memory services initialization failed, continuing without memory features: %s", exc)
            tools.embedding_service = None
            tools.memory_store = None
            tools.memory_extractor = None
            tools.graphrag_service.set_memory_services(
                embedding_service=None,
                memory_store=None,
            )

    async def _seed_demo_memories(
        self,
        embedding_service: EmbeddingService,
        memory_store: MemoryVectorStore,
    ) -> None:
        """为演示学生预填充种子记忆（如果记忆库为空）。"""
        try:
            from app.memory.seed import seed_memories

            demo_id = "demo_student_001"
            existing = await memory_store.count(student_id=demo_id)
            if existing > 0:
                return  # 已有记忆，跳过

            entries = seed_memories(demo_id)
            texts = [self._seed_format_text(e) for e in entries]
            embeddings = await embedding_service.embed_batch(texts)
            await memory_store.insert_batch(entries, embeddings)
        except Exception as exc:
            logger.warning("Seed memories population failed: %s", exc)

    @staticmethod
    def _seed_format_text(entry) -> str:
        parts = [
            f"[{entry.intent}] 学生问题：{entry.student_question_summary}",
            f"助教回复：{entry.agent_response_summary}",
        ]
        if entry.key_insight:
            parts.append(f"关键发现：{entry.key_insight}")
        if entry.confusion_nodes:
            parts.append(f"困惑点：{', '.join(entry.confusion_nodes)}")
        if entry.learning_preference_hint:
            parts.append(f"偏好：{entry.learning_preference_hint}")
        return " | ".join(parts)

    async def chat(self, payload: AssistantChatRequest) -> AssistantResponse:
        state = await self._prepare_state(payload)
        final_state = await self.graph.ainvoke(state)
        response = self._response(final_state)
        await self._persist(payload, final_state, response)
        return response

    async def stream(self, payload: AssistantChatRequest) -> AsyncIterator[str]:
        state = await self._prepare_state(payload)
        yield self._sse("run_started", {"conversation_id": state["conversation_id"]})
        final_state = state
        seen_trace_count = 0
        try:
            async for event in self.graph.astream_events(state, version="v2"):
                event_name = event.get("event")
                node = event.get("name")
                if event_name == "on_chain_start" and node and self._is_business_node(node):
                    yield self._sse("node_started", {
                        "node": node,
                        "label": self._node_label(node),
                    })
                elif event_name == "on_chain_end" and node:
                    if node == "LangGraph":
                        graph_output = event.get("data", {}).get("output")
                        if isinstance(graph_output, dict):
                            final_state = graph_output
                    # 提取该节点新增的 agent_trace 项
                    raw_node_output = event.get("data", {}).get("output") or event.get("data", {}).get("input") or {}
                    node_output = raw_node_output if isinstance(raw_node_output, dict) else {}
                    traces = node_output.get("agent_trace") or []
                    while len(traces) > seen_trace_count:
                        item = self._trace_item_dict(traces[seen_trace_count])
                        yield self._sse("trace_item", {
                            "node": item.get("node", node),
                            "status": item.get("status", "done"),
                            "summary": item.get("summary", ""),
                        })
                        seen_trace_count += 1
                    # 发送节点完成的元数据
                    if self._is_business_node(node):
                        yield self._sse("node_completed", {
                            "node": node,
                            "label": self._node_label(node),
                        })
                    # 发送 evidence_quality_score（如果刚计算出来）
                    score = node_output.get("evidence_quality_score")
                    if score is not None and score > 0:
                        yield self._sse("quality_update", {
                            "type": "evidence",
                            "score": score,
                            "reason": node_output.get("evidence_evaluation_reason", ""),
                        })
                    res_score = node_output.get("resource_quality_score")
                    if res_score is not None and res_score > 0:
                        yield self._sse("quality_update", {
                            "type": "resource",
                            "score": res_score,
                            "reason": node_output.get("resource_evaluation_reason", ""),
                        })
        except Exception as exc:
            message = f"流式执行异常：{type(exc).__name__}: {exc}"
            final_state.setdefault("errors", []).append(message)
            final_state["status"] = "error"
            final_state["recovery_message"] = "流式执行遇到异常，已返回降级结果。"
            yield self._sse("error", {"message": message})
        response = self._response(final_state)
        await self._persist(payload, final_state, response)
        yield self._sse("final_response", response.model_dump(mode="json"))
        yield self._sse("persisted", {"conversation_id": response.conversation_id})

    @staticmethod
    def _business_node_labels() -> dict[str, str]:
        return {
            "load_context": "加载画像上下文",
            "retrieve_memory": "检索历史记忆",
            "understand_intent": "识别学习意图",
            "update_profile": "更新学生画像",
            "record_progress": "记录学习进度",
            "retrieve_evidence": "检索 GraphRAG 证据",
            "evaluate_evidence": "评估证据质量",
            "expand_evidence": "扩展证据检索",
            "generate_resources": "生成学习资源",
            "reflect_on_resources": "反思资源质量",
            "explain_exercise": "生成练习讲解",
            "plan_learning_path": "规划学习路径",
            "review_assessment": "评估复盘",
            "general_tutor": "智能答疑",
            "compose_response": "整理学习回复",
            "extract_memory": "提取记忆条目",
            "error_recovery": "错误恢复",
        }

    @classmethod
    def _is_business_node(cls, node: str) -> bool:
        return node in cls._business_node_labels()

    @staticmethod
    def _trace_item_dict(item) -> dict:
        if isinstance(item, dict):
            return item
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")
        return {}

    @staticmethod
    def _node_label(node: str) -> str:
        return AssistantService._business_node_labels().get(node, node)

    async def history(self, student_id: str) -> AssistantHistoryResponse:
        return await self.memory.get_history(student_id)

    async def _prepare_state(self, payload: AssistantChatRequest) -> AssistantState:
        conversation = await self.memory.create_or_get_conversation(
            student_id=payload.student_id,
            conversation_id=payload.conversation_id,
            title_hint=payload.message,
        )
        recent = await self.memory.list_recent_messages(conversation.id)
        run = await self.memory.create_run(
            conversation_id=conversation.id,
            student_id=payload.student_id,
            input_json=payload.model_dump(mode="json"),
        )
        return AssistantState(
            student_id=payload.student_id,
            user_message=payload.message,
            conversation_id=conversation.id,
            run_id=run.id,
            history_messages=[item.model_dump(mode="json") for item in recent],
            intent=None,
            intent_confidence=0.0,
            entities={},
            target_node_id=None,
            requested_resource_types=[],
            relevant_memories=[],
            actions=[],
            agent_trace=[],
            suggested_next_actions=[],
            errors=[],
            llm_available=bool(self.settings.llm_api_key),
            status="ok",
            final_reply="",
        )

    async def _persist(
        self,
        payload: AssistantChatRequest,
        state: AssistantState,
        response: AssistantResponse,
    ) -> None:
        trace_json = [item.model_dump(mode="json") for item in response.agent_trace]
        actions_json = [item.model_dump(mode="json") for item in response.actions]
        await self.memory.add_message(
            conversation_id=response.conversation_id,
            student_id=payload.student_id,
            role="user",
            content=payload.message,
            intent=response.intent or "",
            target_node_id=state.get("target_node_id") or "",
        )
        assistant_msg = await self.memory.add_message(
            conversation_id=response.conversation_id,
            student_id=payload.student_id,
            role="assistant",
            content=response.reply,
            intent=response.intent or "",
            target_node_id=state.get("target_node_id") or "",
            agent_trace_json=trace_json,
            actions_json=actions_json,
            resource_record_id=response.resource_record_id,
            metadata_json={"resource_has_exercises": response.resource_has_exercises},
        )
        # 回填真实 message id 到 response，供前端反馈绑定
        response.assistant_message_id = assistant_msg.id
        await self.memory.add_actions(
            run_id=state["run_id"],
            conversation_id=response.conversation_id,
            student_id=payload.student_id,
            actions=response.actions,
        )
        await self.memory.finish_run(
            state["run_id"],
            status=response.status,
            output_json=response.model_dump(mode="json"),
            agent_trace_json=trace_json,
            actions_json=actions_json,
            error_message="; ".join(response.errors),
        )
        await self.memory.touch_conversation(
            response.conversation_id,
            last_intent=response.intent or "",
            summary=response.reply[:300],
        )
        await self.memory.session.commit()

    def _response(self, state: AssistantState) -> AssistantResponse:
        status = state.get("status") or ("degraded" if state.get("recovery_message") else ("error" if state.get("errors") else "ok"))
        return AssistantResponse(
            reply=state.get("final_reply") or "本轮学习助手运行结束，但没有生成可展示回复。",
            intent=state.get("intent"),
            intent_confidence=state.get("intent_confidence") or 0.0,
            conversation_id=state["conversation_id"],
            status=status,  # type: ignore[arg-type]
            # 语义记忆
            relevant_memories=state.get("relevant_memories") or [],
            # 意图澄清
            needs_clarification=state.get("needs_clarification") or False,
            clarification_options=[
                ClarifyOption(**opt) if isinstance(opt, dict) else opt
                for opt in state.get("clarification_options") or []
            ],
            clarification_question=state.get("clarification_question") or "",
            # 质量评分
            evidence_quality_score=state.get("evidence_quality_score"),
            resource_quality_score=state.get("resource_quality_score"),
            # 反思
            reflection=state.get("reflection") or "",
            needs_refinement=state.get("needs_refinement") or False,
            # 原有字段
            actions=state.get("actions", []),
            suggested_next_actions=state.get("suggested_next_actions", []),
            profile_delta=state.get("profile_update", {}),
            evidence=state.get("evidence"),
            resource_record_id=state.get("resource_record_id"),
            resource_has_exercises=state.get("resource_has_exercises") or False,
            resources=state.get("resources"),
            path_plan=state.get("path_plan"),
            exercise_feedback=state.get("exercise_feedback"),
            agent_trace=state.get("agent_trace", []),
            errors=state.get("errors", []),
        )

    def _sse(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
