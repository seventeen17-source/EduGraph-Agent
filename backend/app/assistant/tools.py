from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.agents.schemas import ResourceGenerateRequest
from app.agents.service import ResourceGenerationService
from app.assistant.schemas import (
    AssistantAction,
    AssistantIntentResult,
    AssistantPathPlan,
    AssistantTraceItem,
    ClarifyIntentResult,
    ClarifyOption,
    ExerciseFeedback,
    PathPlanNode,
    SuggestedNextAction,
)
from app.assistant.state import AssistantState
from app.core.config import Settings
from app.core.errors import NotFoundError, ServiceUnavailableError
from app.diagnosis.service import DiagnosisService
from app.graphrag.service import GraphRAGService
from app.memory.embedding import EmbeddingService
from app.memory.extractor import MemoryExtractor
from app.memory.vector_store import MemoryVectorStore
from app.profile.schemas import LearningProgressUpdateRequest
from app.profile.service import ProfileService

_RESOURCE_ALIASES = {
    "diagram": "mindmap",
    "图解": "mindmap",
    "图": "mindmap",
    "代码": "code_case",
    "code": "code_case",
    "练习": "exercise",
    "题": "exercise",
    "文档": "document",
    "讲解": "document",
    "视频": "video_script",
}
_VALID_RESOURCE_TYPES = {"document", "mindmap", "exercise", "video_script", "code_case"}


class AssistantTools:
    def __init__(
        self,
        *,
        settings: Settings,
        profile_service: ProfileService,
        graphrag_service: GraphRAGService,
        resource_service: ResourceGenerationService,
        diagnosis_service: DiagnosisService,
        embedding_service: "EmbeddingService | None" = None,
        memory_store: "MemoryVectorStore | None" = None,
        memory_extractor: "MemoryExtractor | None" = None,
    ) -> None:
        self.settings = settings
        self.profile_service = profile_service
        self.graphrag_service = graphrag_service
        self.resource_service = resource_service
        self.diagnosis_service = diagnosis_service
        self.embedding_service = embedding_service
        self.memory_store = memory_store
        self.memory_extractor = memory_extractor
        self._intent_chain = None
        self._tutor_chain = None

    async def load_context(self, state: AssistantState) -> AssistantState:
        student_id = state["student_id"]
        try:
            profile = await self.profile_service.get_profile(student_id)
        except NotFoundError:
            profile = (await self.profile_service.initialize_profile(
                student_id=student_id,
                message="请先为我建立一个用于机器学习课程的学习画像。",
            )).profile
        state["profile"] = profile
        state["lightweight_profile"] = profile.to_graphrag_input()
        # 将行为画像注入 lightweight_profile（供下游节点使用）
        behavior = profile.learning_behavior
        if behavior.is_reliable():
            state["_behavior_profile"] = behavior
        # 遗忘检测：将即将遗忘的节点 ID 写入 state，供 plan_learning_path 使用
        try:
            from app.profile.timeline import ForgettingDetector
            detector = ForgettingDetector()
            forgetting = detector.detect(profile.node_mastery)
            state["_forgetting_nodes"] = [f.node_id for f in forgetting]
        except Exception:
            state["_forgetting_nodes"] = []
        self._trace(state, "load_context", "done", "已加载学生画像、薄弱点、偏好和学习进度。")
        state["relevant_memories"] = []
        return state

    async def retrieve_memory(self, state: AssistantState) -> AssistantState:
        """从向量存储中检索与当前问题相关的历史记忆。"""
        state.setdefault("relevant_memories", [])
        if not self.memory_store or not self.embedding_service:
            self._trace(state, "retrieve_memory", "skipped", "记忆存储或嵌入服务未初始化，跳过。")
            return state

        student_id = state["student_id"]
        user_message = state["user_message"]

        try:
            # 快速预推断目标知识点（基于关键词匹配，不依赖 LLM）
            hint_node = self._quick_node_match(user_message)
            if hint_node:
                state["_memory_hint_node"] = hint_node

            # 嵌入查询文本
            query_embedding = await self.embedding_service.embed(user_message)

            # 从图谱获取关联节点 ID（用于元数据扩展检索）
            related_node_ids: list[str] = []
            if hint_node:
                try:
                    prereqs = await self.diagnosis_service.graph_store.get_prerequisites(
                        hint_node, depth=1, limit=3,
                    )
                    seen_rel: set[str] = set()
                    for path in prereqs:
                        for node in path.nodes:
                            if node.uid != hint_node and node.uid not in seen_rel:
                                seen_rel.add(node.uid)
                                related_node_ids.append(node.uid)
                    related_nodes = await self.diagnosis_service.graph_store.get_related_nodes(
                        hint_node, limit=3,
                    )
                    for path in related_nodes:
                        for node in path.nodes:
                            if node.uid != hint_node and node.uid not in seen_rel:
                                seen_rel.add(node.uid)
                                related_node_ids.append(node.uid)
                except Exception:
                    pass

            # 混合检索
            all_node_ids = [hint_node] + related_node_ids if hint_node else []
            results = await self.memory_store.hybrid_search(
                query_embedding=query_embedding,
                student_id=student_id,
                node_ids=all_node_ids if all_node_ids else None,
                top_k=5,
            )

            # 序列化为可 JSON 化的字典
            relevant = []
            for r in results:
                try:
                    relevant.append(r.entry.model_dump(mode="json"))
                except Exception:
                    relevant.append({
                        "id": r.entry.id,
                        "key_insight": r.entry.key_insight,
                        "student_question_summary": r.entry.student_question_summary,
                        "confusion_nodes": r.entry.confusion_nodes,
                        "caution_topics": r.entry.caution_topics,
                        "learning_preference_hint": r.entry.learning_preference_hint,
                        "score": r.score,
                    })
            state["relevant_memories"] = relevant

            if relevant:
                self._trace(
                    state, "retrieve_memory", "done",
                    f"从记忆库中检索到 {len(relevant)} 条相关历史记忆（查询节点: {hint_node or '未识别'}）。",
                    {"top_scores": [round(r["score"], 3) for r in relevant[:3]]},
                )
            else:
                self._trace(state, "retrieve_memory", "done", "记忆库中暂无相关历史记忆。")
        except Exception as exc:
            self._trace(state, "retrieve_memory", "skipped", f"记忆检索异常：{type(exc).__name__}，降级继续。")
            state.setdefault("errors", []).append(f"记忆检索异常（已降级）：{exc}")

        return state

    async def understand_intent(self, state: AssistantState) -> AssistantState:
        if not self.settings.llm_api_key:
            state["llm_available"] = False
            state["status"] = "unavailable"
            state.setdefault("errors", []).append("LLM_API_KEY 未配置，LangGraph 学习主智能体暂不可用。")
            self._trace(state, "understand_intent", "failed", "缺少 LLM_API_KEY，无法执行结构化意图识别。")
            return state

        try:
            chain = self._get_intent_chain()
            profile_json = json.dumps(
                (state.get("lightweight_profile") or {}).model_dump(mode="json")
                if hasattr(state.get("lightweight_profile"), "model_dump")
                else {},
                ensure_ascii=False,
            )
            result: AssistantIntentResult = await chain(
                {
                    "message": state["user_message"],
                    "profile": profile_json,
                    "history": json.dumps(state.get("history_messages", [])[-8:], ensure_ascii=False),
                    "memory_context": self._format_memory_for_prompt(state),
                    "behavior_context": self._format_behavior_for_prompt(state),
                }
            )
            result.resource_types = self._normalize_resource_types(result.resource_types)
            generation_request = self._parse_generation_request(state["user_message"])
            state["intent"] = result.intent
            state["intent_confidence"] = result.confidence
            state["intent_reasoning"] = result.reasoning
            state["target_node_id"] = result.target_node_id or self._quick_node_match(state["user_message"])
            requested_types = list(result.resource_types)

            # 规则兜底：用户明确要求生成练习/出题
            has_exercise_request = bool(generation_request.get("exercise_count") or generation_request.get("exercise_type"))
            has_generation_keyword = any(token in state["user_message"] for token in ["生成", "出", "来", "设计"])
            if has_exercise_request:
                if "exercise" not in requested_types:
                    requested_types.insert(0, "exercise")
                if has_generation_keyword:
                    state["intent"] = "resource_generate"

            state["requested_resource_types"] = requested_types
            state["requested_exercise_count"] = generation_request.get("exercise_count")
            state["requested_exercise_type"] = generation_request.get("exercise_type")
            state["entities"] = result.model_dump(mode="json")

            # 高优先级 1：意图置信度低于阈值时，主动生成澄清选项
            # 【关键修复】如果规则兜底已确定为 resource_generate，不触发澄清
            if (result.confidence < 0.6 and self.settings.llm_api_key
                    and state["intent"] != "resource_generate"):
                try:
                    clarify_result = await self._generate_clarification(
                        message=state["user_message"],
                        profile=state.get("lightweight_profile"),
                        history=state.get("history_messages", [])[-4:],
                    )
                    state["needs_clarification"] = True
                    state["clarification_options"] = [
                        opt.model_dump() for opt in clarify_result.options
                    ]
                    state["clarification_question"] = clarify_result.question
                    state["intent"] = "clarify_intent"
                    self._trace(
                        state,
                        "understand_intent",
                        "done",
                        f"置信度 {result.confidence:.2f} < 0.6，已生成 {len(clarify_result.options)} 个澄清选项。",
                    )
                except Exception as exc:
                    self._trace(
                        state,
                        "understand_intent",
                        "skipped",
                        f"意图澄清生成失败，使用低置信度结果继续：{type(exc).__name__}",
                    )
                    state.setdefault("errors", []).append(f"意图澄清失败：{exc}")
            else:
                self._trace(
                    state,
                    "understand_intent",
                    "done",
                    f"识别意图为 {result.intent}，置信度 {result.confidence:.2f}。",
                    {"target_topic": result.target_topic, "target_node_id": result.target_node_id},
                )
        except Exception as exc:
            state["status"] = "error"
            state.setdefault("errors", []).append(f"结构化意图识别失败：{type(exc).__name__}: {exc}")
            self._trace(state, "understand_intent", "failed", f"结构化意图识别失败：{type(exc).__name__}")
        return state

    async def update_profile(self, state: AssistantState) -> AssistantState:
        response = await self.profile_service.chat(state["student_id"], state["user_message"])
        state["profile"] = response.profile
        state["lightweight_profile"] = response.profile.to_graphrag_input()
        state["profile_update"] = {
            "updated_dimensions": response.updated_dimensions,
            "missing_dimensions": response.missing_dimensions,
            "completeness": response.completeness,
        }
        self._trace(state, "update_profile", "done", f"画像已更新：{'、'.join(response.updated_dimensions) or '未发现明确新增字段'}。")
        # 如果 LLM 可用，生成个性化回复而不是 fallback
        if self.settings.llm_api_key:
            try:
                chain = self._get_tutor_chain()
                profile_json = json.dumps(
                    response.profile.model_dump(mode="json"),
                    ensure_ascii=False,
                )
                dims = ", ".join(response.updated_dimensions) if response.updated_dimensions else "无明确新增字段"
                completeness = int((response.completeness or 0) * 100)
                prompt_context = (
                    f"学生刚刚表达了一条画像更新信息。\n"
                    f"已确认更新的维度：{dims}。\n"
                    f"当前画像完整度：{completeness}%。\n"
                    f"学生原话：{state['user_message']}\n"
                    f"请用学习教练的口吻确认更新了什么，如果有不完整的维度可以追问。"
                )
                reply = await chain.ainvoke({
                    "message": prompt_context,
                    "profile": profile_json,
                    "evidence": "{}",
                })
                state["final_reply"] = str(reply.content if hasattr(reply, "content") else reply)
                self._trace(state, "generate_profile_reply", "done", "已生成个性化画像更新回复。")
            except Exception as exc:
                state.setdefault("errors", []).append(f"画像回复生成失败：{type(exc).__name__}: {exc}")
        return state

    async def retrieve_evidence(self, state: AssistantState) -> AssistantState:
        profile = state.get("lightweight_profile")
        target = state.get("target_node_id")
        if target:
            evidence = await self.graphrag_service.build_evidence_by_uid(
                target,
                profile,
                student_id=state.get("student_id"),
            )
        else:
            evidence = await self.graphrag_service.query(
                state["user_message"],
                profile,
                student_id=state.get("student_id"),
            )
        state["evidence"] = evidence
        state["target_node_id"] = evidence.resolved_uid or state.get("target_node_id")

        for item in evidence.student_profile_adaptation.get("hybrid_rag_trace", []):
            raw_status = item.get("status", "done")
            valid_status = raw_status if raw_status in ("started", "done", "skipped", "failed") else "done"
            self._trace(
                state,
                f"hybrid_rag:{item.get('node', 'unknown')}",
                valid_status,
                item.get("summary", ""),
                item.get("metadata", {}),
            )

        quality = evidence.student_profile_adaptation.get("hybrid_rag_quality", {})
        summary = f"已通过 HybridRAG 子图围绕 {evidence.resolved_uid or '用户问题'} 完成证据检索。"
        if quality:
            summary += f" 质量评分：{float(quality.get('overall_score', 0.0) or 0.0):.2f}"
        if evidence.ranking_reason:
            summary += f" 推荐依据：{evidence.ranking_reason[0]}"
        self._trace(state, "retrieve_evidence", "done", summary)
        return state

        profile = state.get("lightweight_profile")
        target = state.get("target_node_id")
        if target:
            evidence = await self.graphrag_service.build_evidence_by_uid(target, profile)
        else:
            evidence = await self.graphrag_service.query(state["user_message"], profile)
        state["evidence"] = evidence
        state["target_node_id"] = evidence.resolved_uid or state.get("target_node_id")
        summary = f"已围绕 {evidence.resolved_uid or '用户问题'} 检索图谱证据。"
        if evidence.ranking_reason:
            summary += f" 推荐依据：{evidence.ranking_reason[0]}"
        self._trace(state, "retrieve_evidence", "done", summary)
        return state

    async def evaluate_evidence(self, state: AssistantState) -> AssistantState:
        evidence = state.get("evidence")
        if not evidence:
            state["evidence_quality_score"] = 0.0
            state["evidence_evaluation_reason"] = "无证据可评估"
            state["retry_evidence"] = False
            return state

        report = evidence.student_profile_adaptation.get("hybrid_rag_quality") or {}
        score = float(report.get("overall_score", evidence.evidence_score or 0.0) or 0.0)
        missing = report.get("missing_categories") or []
        repair_actions = evidence.student_profile_adaptation.get("hybrid_rag_repair_actions") or []
        state["evidence_quality_score"] = score
        state["evidence_evaluation_reason"] = "; ".join([
            f"覆盖度 {float(report.get('coverage_score', 0.0) or 0.0):.2f}",
            f"相关性 {float(report.get('relevance_score', 0.0) or 0.0):.2f}",
            f"来源可信度 {float(report.get('grounding_score', 0.0) or 0.0):.2f}",
            f"个性化匹配 {float(report.get('personal_fit_score', 0.0) or 0.0):.2f}",
            f"缺失项 {', '.join(missing) if missing else '无'}",
            f"修复动作 {', '.join(repair_actions) if repair_actions else '无'}",
        ])
        state["retry_evidence"] = False
        weak_reasons = report.get("weak_reasons") or []
        self._trace(
            state,
            "evaluate_evidence",
            "done",
            f"HybridRAG 子图已完成质量评估，评分 {score:.2f}。{'；'.join(weak_reasons[:2])}",
        )
        return state
        """中优先级：评估 evidence 质量，如果不足则标记 retry_evidence。"""
        evidence = state.get("evidence")
        if not evidence:
            state["evidence_quality_score"] = 0.0
            state["evidence_evaluation_reason"] = "无证据可评估"
            state["retry_evidence"] = False
            return state

        # 计算质量分数
        score = 0.0
        reasons = []

        # 检查 completeness
        completeness = getattr(evidence.evidence_completeness, "completeness_score", 0.0) if evidence.evidence_completeness else 0.0
        if completeness >= 0.8:
            score += 0.4
            reasons.append(f"证据完整性高({completeness:.2f})")
        elif completeness >= 0.5:
            score += 0.2
            reasons.append(f"证据完整性中等({completeness:.2f})")
        else:
            reasons.append(f"证据完整性不足({completeness:.2f})")

        # 检查各类型证据数量
        doc_count = len(evidence.document_chunks) if evidence.document_chunks else 0
        code_count = len(evidence.code_cases) if evidence.code_cases else 0
        exercise_count = len(evidence.exercises) if evidence.exercises else 0
        faq_count = len(evidence.misconceptions) if evidence.misconceptions else 0

        if doc_count > 0:
            score += 0.15
        if code_count > 0:
            score += 0.15
        if exercise_count > 0:
            score += 0.15
        if faq_count > 0:
            score += 0.15

        reasons.append(f"文档:{doc_count} 代码:{code_count} 练习:{exercise_count} FAQ:{faq_count}")

        state["evidence_quality_score"] = min(score, 1.0)
        state["evidence_evaluation_reason"] = "; ".join(reasons)

        # 质量低于阈值时标记需要补充检索
        state["retry_evidence"] = score < 0.5
        if state["retry_evidence"]:
            self._trace(
                state,
                "evaluate_evidence",
                "skipped",
                f"证据质量评分 {score:.2f} < 0.5，标记需要补充扩展检索。",
            )
        else:
            self._trace(
                state,
                "evaluate_evidence",
                "done",
                f"证据质量评分 {score:.2f}，证据充足，无需补充。",
            )
        return state

    async def expand_evidence(self, state: AssistantState) -> AssistantState:
        evidence = state.get("evidence")
        actions = []
        if evidence:
            actions = evidence.student_profile_adaptation.get("hybrid_rag_repair_actions") or []
        self._trace(
            state,
            "expand_evidence",
            "done",
            f"证据修复已在 HybridRAG 子图内完成：{', '.join(actions) if actions else '无需额外修复'}。",
        )
        return state

        """证据质量不足时，尝试补充检索相关知识点和前置知识。"""
        target = state.get("target_node_id")
        evidence = state.get("evidence")

        if not target:
            self._trace(state, "expand_evidence", "skipped", "无目标节点，无法扩展证据。")
            return state

        try:
            # 尝试通过前置知识扩展
            from app.graph.neo4j_store import Neo4jGraphStore
            from app.core.config import get_settings

            settings = get_settings()
            graph_store = Neo4jGraphStore(
                uri=settings.neo4j_uri,
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                database=settings.neo4j_database,
            )
            await graph_store.initialize()

            # 获取前置知识
            prerequisites = await graph_store.get_prerequisites(target)
            if prerequisites:
                prereq_ids = [p.uid for p in prerequisites[:2]]  # 最多取 2 个前置节点
                # 构建扩展证据
                for prereq_id in prereq_ids:
                    prereq_evidence = await self.graphrag_service.build_evidence_by_uid(
                        prereq_id,
                        state.get("lightweight_profile")
                    )
                    # 合并证据（简单合并，不去重）
                    if evidence and prereq_evidence:
                        if not evidence.document_chunks:
                            evidence.document_chunks = []
                        evidence.document_chunks.extend(prereq_evidence.document_chunks or [])
                        if not evidence.code_cases:
                            evidence.code_cases = []
                        evidence.code_cases.extend(prereq_evidence.code_cases or [])
                        if not evidence.exercises:
                            evidence.exercises = []
                        evidence.exercises.extend(prereq_evidence.exercises or [])

            await graph_store.close()
            self._trace(state, "expand_evidence", "done", f"已通过前置知识扩展证据，新增 {len(prerequisites) if prerequisites else 0} 个前置节点。")
        except Exception as exc:
            state.setdefault("errors", []).append(f"扩展证据失败：{exc}")
            self._trace(state, "expand_evidence", "failed", f"扩展证据失败：{type(exc).__name__}")

        return state

    async def generate_resources(self, state: AssistantState) -> AssistantState:
        resource_types = state.get("requested_resource_types") or self._default_resource_types(state)
        response = await self.resource_service.generate(
            ResourceGenerateRequest(
                query=state["user_message"],
                node_id=state.get("target_node_id"),
                student_id=state["student_id"],
                student_profile=state.get("lightweight_profile"),
                exercise_count=state.get("requested_exercise_count"),
                exercise_type=state.get("requested_exercise_type"),
                resource_types=resource_types,  # type: ignore[arg-type]
            )
        )
        state["evidence"] = response.evidence
        state["resources"] = response.resources
        state["resource_record_id"] = response.resource_record_id
        for item in response.agent_trace:
            self._trace(state, f"resource:{item.agent}", "done" if item.status == "done" else item.status, item.summary)
        self._trace(state, "generate_resources", "done", "已生成证据约束的学习资源并写入资源中心。")

        # 中优先级：评估资源质量
        await self._evaluate_resource_quality(state)
        return state

    async def _evaluate_resource_quality(self, state: AssistantState) -> None:
        """评估生成资源的质量。"""
        resources = state.get("resources")
        if not resources:
            state["resource_quality_score"] = 0.0
            state["resource_evaluation_reason"] = "无资源可评估"
            return

        score = 0.0
        reasons = []
        items = [
            ("document", resources.document),
            ("mindmap", resources.mindmap),
            ("exercises", resources.exercises),
            ("video_script", resources.video_script),
            ("code_case", resources.code_case),
        ]
        generated = 0
        for rtype, item in items:
            if item is not None and (not isinstance(item, list) or len(item) > 0):
                score += 0.2
                generated += 1
                reasons.append(f"{rtype}:已生成")

        state["resource_quality_score"] = min(score, 1.0)
        state["resource_evaluation_reason"] = "; ".join(reasons) if reasons else "无资源生成"
        self._trace(
            state,
            "evaluate_resources",
            "done",
            f"资源质量评分 {score:.2f}，{generated}/5 类资源生成成功。",
        )

    async def reflect_on_resources(self, state: AssistantState) -> AssistantState:
        """中优先级：Agent 反思 - 资源生成后反思是否满足需求。"""
        if not self.settings.llm_api_key:
            state["reflection"] = "LLM 不可用，跳过反思。"
            state["needs_refinement"] = False
            return state

        state.setdefault("refinement_count", 0)
        max_refinements = 3

        # 检查是否需要反思（资源质量低或用户明确要求）
        resource_score = state.get("resource_quality_score", 1.0)
        evidence_score = state.get("evidence_quality_score", 1.0)

        if resource_score >= 0.8 and evidence_score >= 0.6:
            state["reflection"] = "资源和证据质量良好，无需反思。"
            state["needs_refinement"] = False
            self._trace(state, "reflect_on_resources", "skipped", "质量和证据充足，跳过反思。")
            return state

        try:
            chain = self._get_reflection_chain()
            profile_json = json.dumps(
                state.get("lightweight_profile").model_dump(mode="json")
                if state.get("lightweight_profile") and hasattr(state.get("lightweight_profile"), "model_dump")
                else {},
                ensure_ascii=False,
            )
            resources_summary = self._summarize_resources(state.get("resources"))
            evidence_summary = self._summarize_evidence(state.get("evidence"))

            reflection_prompt = f"""学生原始请求：{state['user_message']}
目标知识点：{state.get('target_node_id', '未明确')}
资源质量评分：{resource_score:.2f}（满分1.0）
证据质量评分：{evidence_score:.2f}（满分1.0）
已生成资源：{resources_summary}
证据包摘要：{evidence_summary}

请反思：这些资源是否充分满足了学生的需求？是否需要补充或改进？"""
            reflection = await chain.ainvoke({
                "message": reflection_prompt,
                "profile": profile_json,
            })
            reflection_text = str(reflection.content if hasattr(reflection, "content") else reflection)
            state["reflection"] = reflection_text

            # 判断是否需要改进
            low_quality_keywords = ["不足", "缺少", "不够", "需要补充", "建议改进", "可以更好"]
            state["needs_refinement"] = any(kw in reflection_text for kw in low_quality_keywords)

            if state["needs_refinement"] and state["refinement_count"] < max_refinements:
                state["refinement_count"] = state.get("refinement_count", 0) + 1
                self._trace(
                    state,
                    "reflect_on_resources",
                    "done",
                    f"反思发现改进空间，标记需要补充（第 {state['refinement_count']} 次迭代）。",
                    {"reflection_preview": reflection_text[:200]},
                )
            else:
                self._trace(
                    state,
                    "reflect_on_resources",
                    "done",
                    f"反思完成：{'无需改进' if not state['needs_refinement'] else '已达最大迭代次数，停止改进'}。",
                    {"reflection_preview": reflection_text[:200]},
                )
        except Exception as exc:
            state.setdefault("errors", []).append(f"反思生成失败：{exc}")
            state["reflection"] = f"反思失败：{type(exc).__name__}"
            state["needs_refinement"] = False
            self._trace(state, "reflect_on_resources", "failed", f"反思生成失败：{type(exc).__name__}")
        return state

    async def error_recovery(self, state: AssistantState) -> AssistantState:
        """中优先级错误恢复：Tool 失败时降级而非跳过整个流程。"""
        errors = state.get("errors", [])
        if not errors:
            state["recovery_action"] = "compose"
            self._trace(state, "error_recovery", "done", "无错误，无需恢复。")
            return state

        # 分析错误类型并决定恢复策略
        recoverable = []
        critical = []
        for err in errors:
            err_str = str(err).lower()
            if any(kw in err_str for kw in ["timeout", "connection", "network", "http error"]):
                recoverable.append(err)
            elif any(kw in err_str for kw in ["not found", "undefined", "invalid key"]):
                critical.append(err)
            else:
                recoverable.append(err)  # 未知错误暂时视为可恢复

        if critical and not recoverable:
            # 全部是严重错误，终止
            state["status"] = "error"
            state["recovery_action"] = "abort"
            state["recovery_message"] = "本轮对话遇到严重错误，请重新开始。"
            self._trace(state, "error_recovery", "failed",
                        f"检测到 {len(critical)} 个严重错误，建议重试：{'; '.join(str(e)[:100] for e in critical[:3])}")
        elif recoverable:
            # 有可恢复错误：清理错误列表，降级后继续
            # 保留前两个错误信息供 compose 展示
            state["errors"] = errors[:2]
            # 检查证据是否仍然可用
            if state.get("evidence") and not state.get("target_node_id"):
                # 有 evidence 但没有 target_node_id，仍然可以回复
                state["recovery_action"] = "compose"
                state["recovery_message"] = "部分功能降级，但仍有可用证据。"
                self._trace(state, "error_recovery", "skipped",
                            f"已清理 {len(recoverable)} 个可恢复错误，保留可用证据继续。")
            else:
                state["recovery_action"] = "compose"
                state["recovery_message"] = "检测到不稳定状态，将以降级模式回复。"
                self._trace(state, "error_recovery", "skipped",
                            f"已清理 {len(recoverable)} 个可恢复错误，降级到 compose 模式。")
        else:
            state["recovery_action"] = "compose"
            state["recovery_message"] = ""
            self._trace(state, "error_recovery", "done", "所有错误已清理。")
        return state

    def _summarize_resources(self, resources: Any) -> str:
        if not resources:
            return "无资源"
        parts = []
        if getattr(resources, "document", None) is not None:
            parts.append("✓讲解文档")
        if getattr(resources, "mindmap", None) is not None:
            parts.append("✓思维导图")
        exercises = getattr(resources, "exercises", None) or []
        if exercises:
            parts.append(f"✓练习题:{len(exercises)}道")
        if getattr(resources, "video_script", None) is not None:
            parts.append("✓视频脚本")
        if getattr(resources, "code_case", None) is not None:
            parts.append("✓代码案例")
        return ", ".join(parts) if parts else "无资源"

    def _summarize_evidence(self, evidence: Any) -> str:
        if not evidence:
            return "无证据"
        parts = []
        if evidence.document_chunks:
            parts.append(f"文档:{len(evidence.document_chunks)}")
        if evidence.code_cases:
            parts.append(f"代码:{len(evidence.code_cases)}")
        if evidence.exercises:
            parts.append(f"练习:{len(evidence.exercises)}")
        if evidence.misconceptions:
            parts.append(f"FAQ:{len(evidence.misconceptions)}")
        return ", ".join(parts) if parts else "证据为空"

    def _get_reflection_chain(self):
        """反思链：评估资源是否满足需求。"""
        if getattr(self, "_reflection_chain", None) is not None:
            return self._reflection_chain
        llm = self._chat_model()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的资源反思专家。请评估已生成的学习资源是否满足学生需求，"
                    "并给出具体的改进建议。如果资源质量良好，请明确说明\"无需改进\"。"
                    "回答要简洁，50-200 字以内，重点说明发现了什么问题以及建议如何改进。",
                ),
                ("human", "上下文：{message}\n学生画像：{profile}"),
            ]
        )
        self._reflection_chain = prompt | llm
        return self._reflection_chain

    async def explain_exercise(self, state: AssistantState) -> AssistantState:
        evidence = state.get("evidence")
        profile = state.get("lightweight_profile")

        # 构建练习上下文供 LLM 参考
        exercise_context_parts = []
        if evidence and evidence.exercises:
            for ex in evidence.exercises[:3]:
                exercise_context_parts.append(
                    f"- [{ex.uid}] {ex.title}: {ex.content[:300]}..."
                )
        if state.get("target_node_id"):
            exercise_context_parts.insert(
                0, f"当前主题节点：{state['target_node_id']}"
            )
        exercise_context = "\n".join(exercise_context_parts) or "未找到关联练习，请结合证据包和知识点讲解。"

        # 用 LLM 生成个性化反馈
        feedback_content = None
        if self.settings.llm_api_key:
            try:
                chain = self._get_exercise_chain()
                profile_json = json.dumps(
                    profile.model_dump(mode="json") if profile else {},
                    ensure_ascii=False,
                )
                feedback_content = await chain.ainvoke(
                    {
                        "message": state["user_message"],
                        "profile": profile_json,
                        "exercise_context": exercise_context,
                    }
                )
            except Exception as exc:
                state.setdefault("errors", []).append(
                    f"练习讲解生成失败：{type(exc).__name__}: {exc}"
                )

        # 降级：若 LLM 不可用或失败，保留上下文让 compose_response 说明
        if feedback_content:
            try:
                # 尝试解析 JSON 结构化输出
                parsed = json.loads(str(feedback_content.content if hasattr(feedback_content, "content") else feedback_content))
                state["exercise_feedback"] = ExerciseFeedback(
                    summary=parsed.get("summary", "已完成练习讲解。"),
                    likely_causes=parsed.get("likely_causes", []),
                    hints=parsed.get("hints", []),
                    related_node_ids=[state.get("target_node_id")] if state.get("target_node_id") else [],
                )
            except Exception:
                # 非 JSON 格式，直接作为 summary
                state["exercise_feedback"] = ExerciseFeedback(
                    summary=str(feedback_content.content if hasattr(feedback_content, "content") else feedback_content),
                    likely_causes=["前置概念掌握不稳", "公式或链式法则步骤不熟", "没有把题目条件映射到图谱知识点"],
                    hints=["先复述题目考查的核心概念", "把每一步推导对应到一个知识点", "完成后把结果回写到画像掌握度"],
                    related_node_ids=[state.get("target_node_id")] if state.get("target_node_id") else [],
                )
        else:
            state["exercise_feedback"] = ExerciseFeedback(
                summary=f"已定位关联练习：{evidence.exercises[0].title if evidence and evidence.exercises else state.get('target_node_id', '相关知识点')}。建议先通过知识图谱和资源中心补充基础概念，再用练习验证掌握。",
                likely_causes=["前置概念掌握不稳", "公式或链式法则步骤不熟", "没有把题目条件映射到图谱知识点"],
                hints=["先复述题目考查的核心概念", "把每一步推导对应到一个知识点", "完成后把结果回写到画像掌握度"],
                related_node_ids=[state.get("target_node_id")] if state.get("target_node_id") else [],
            )
        self._trace(state, "explain_exercise", "done", "已生成个性化练习讲解和错因提示。")
        return state

    async def plan_learning_path(self, state: AssistantState) -> AssistantState:
        profile_input = state.get("lightweight_profile")
        diagnosis = await self.diagnosis_service.recommend(profile_input, top_k=5) if profile_input else None
        nodes = diagnosis.recommended_nodes if diagnosis and diagnosis.recommended_nodes else []
        target = state.get("target_node_id")
        if target and target not in nodes:
            nodes.append(target)
        # 将遗忘预警节点加入推荐（优先级已在 diagnosis 中处理）
        forgetting = state.get("_forgetting_nodes") or []
        for fn in forgetting:
            if fn not in nodes:
                nodes.append(fn)
        if not nodes and state.get("evidence") and state["evidence"].resolved_uid:
            nodes.append(state["evidence"].resolved_uid)

        profile = state.get("profile")
        completed = set(profile.progress.completed_node_ids if profile else [])
        in_progress = set(profile.progress.in_progress_node_ids if profile else [])
        mastery = profile.node_mastery if profile else {}
        plan_nodes: list[PathPlanNode] = []
        for node_id in nodes:
            score = mastery.get(node_id).mastery_score if node_id in mastery else 0.0
            status = "mastered" if node_id in completed or score >= 0.8 else "in_progress" if node_id in in_progress else "needs_review" if score and score < 0.45 else "recommended"
            plan_nodes.append(
                PathPlanNode(
                    node_id=node_id,
                    label=node_id,
                    status=status,  # type: ignore[arg-type]
                    reason=self._path_reason(node_id, state),
                    recommended_resource_types=self._default_resource_types(state),
                )
            )
        state["path_plan"] = AssistantPathPlan(
            mode="gap_filling" if profile_input and profile_input.weak_points else "current_goal",
            title="可调整学习路径",
            goal=(profile_input.goal if profile_input else None) or "围绕当前问题补齐关键知识点",
            nodes=plan_nodes,
            reasons=(diagnosis.reasoning if diagnosis else []) + ["路径结合画像薄弱点、GraphRAG 前置关系和当前学习目标生成，可随时调整。"],
        )
        self._trace(state, "plan_learning_path", "done", f"已规划 {len(plan_nodes)} 个路径节点。")
        return state

    async def review_assessment(self, state: AssistantState) -> AssistantState:
        profile = state.get("profile")
        weak = [item.node_id or item.label for item in (await self.profile_service.get_dashboard(state["student_id"])).weak_point_rank[:5]]
        state["path_plan"] = AssistantPathPlan(
            mode="exam_review",
            title="掌握度复盘路径",
            goal="根据最近画像和练习结果复盘薄弱点",
            nodes=[PathPlanNode(node_id=item, label=item, status="needs_review", reason="来自画像掌握度或练习结果的薄弱信号。") for item in weak if item],
            reasons=["复盘优先级来自画像 dashboard 的薄弱点排序。"],
        )
        self._trace(state, "review_assessment", "done", f"已汇总 {profile.display_name if profile else state['student_id']} 的掌握度和薄弱点。")
        return state

    async def general_tutor(self, state: AssistantState) -> AssistantState:
        if not self.settings.llm_api_key:
            return state
        try:
            chain = self._get_tutor_chain()
            evidence = state.get("evidence")
            reply = await chain.ainvoke(
                {
                    "message": state["user_message"],
                    "profile": json.dumps(
                        state.get("lightweight_profile").model_dump(mode="json") if state.get("lightweight_profile") else {},
                        ensure_ascii=False,
                    ),
                    "evidence": json.dumps(evidence.model_dump(mode="json") if evidence else {}, ensure_ascii=False)[:8000],
                    "memory_context": self._format_memory_for_prompt(state),
                    "behavior_context": self._format_behavior_for_prompt(state),
                }
            )
            state["final_reply"] = str(reply.content if hasattr(reply, "content") else reply)
            self._trace(state, "general_tutor", "done", "已结合画像和证据包生成讲解。")
        except Exception as exc:
            state.setdefault("errors", []).append(f"讲解生成失败：{type(exc).__name__}: {exc}")
            self._trace(state, "general_tutor", "failed", f"讲解生成失败：{type(exc).__name__}")
        return state

    async def record_progress(self, state: AssistantState) -> AssistantState:
        target = state.get("target_node_id")
        if target:
            event = await self.profile_service.apply_learning_progress(
                LearningProgressUpdateRequest(
                    student_id=state["student_id"],
                    completed_node_ids=[],
                    in_progress_node_ids=[target],
                    current_chapter_id=None,
                )
            )
            state["profile"] = event.profile
            state["profile_update"] = {"updated_dimensions": ["progress"], "summary": event.update_event.summary}
        self._trace(state, "record_progress", "done", "已记录当前学习进度。")
        return state

    def compose_response(self, state: AssistantState) -> AssistantState:
        if state.get("status") == "unavailable":
            state["final_reply"] = (
                "当前没有配置 LLM_API_KEY，LangGraph 学习主智能体无法执行结构化意图识别和智能编排。"
                "我已保留学习助手入口，你可以先打开画像、知识图谱或资源中心；配置模型密钥后，"
                "这里会通过画像、GraphRAG、资源生成和路径规划来完成真实学习闭环。"
            )
            state["actions"] = self._base_actions(state)
            state["suggested_next_actions"] = [
                SuggestedNextAction(label="先查看我的画像", route="/profile/panel", description="确认学习目标、薄弱点和资源偏好。"),
                SuggestedNextAction(label="查看知识图谱", route="/graph", description="手动定位当前想学习的知识点。"),
            ]
            self._trace(state, "compose_response", "done", "已生成模型未配置时的明确不可用提示。")
            return state

        # 处理意图澄清
        if state.get("needs_clarification"):
            options = state.get("clarification_options", [])
            question = state.get("clarification_question", "我不太确定你的需求，能帮我明确一下吗？")
            options_text = "\n".join(f"- **{opt.get('label', opt.get('value', '?'))}**：{opt.get('description', '')}" for opt in options)
            state["final_reply"] = f"{question}\n\n{options_text}\n\n请选择一个选项或重新描述你的需求。"
            state["actions"] = self._base_actions(state)
            state["suggested_next_actions"] = [
                SuggestedNextAction(label="重新描述需求", description="用更具体的表达告诉学习助手你想了解什么。", action_type="retry", priority=1),
            ]
            self._trace(state, "compose_response", "done", "已生成意图澄清回复。")
            return state

        actions = self._base_actions(state)
        if state.get("target_node_id"):
            actions.append(
                AssistantAction(
                    type="open_graph_node",
                    label="查看图谱节点",
                    description="打开相关知识点及其前置关系。",
                    route="/graph",
                    query={"node_id": state["target_node_id"]},
                    node_id=state["target_node_id"],
                )
            )
            actions.append(
                AssistantAction(
                    type="generate_resources",
                    label="生成学习资源",
                    description="按当前偏好生成图解、代码或练习。",
                    route="/resources",
                    query={"query": state["target_node_id"], "node_id": state["target_node_id"]},
                    node_id=state["target_node_id"],
                )
            )
        if state.get("resource_record_id"):
            actions.append(
                AssistantAction(
                    type="open_resource_record",
                    label="打开资源记录",
                    description="查看本轮生成的资源详情。",
                    route="/knowledge-center",
                    query={"record_id": state["resource_record_id"]},
                    resource_record_id=state["resource_record_id"],
                )
            )
        if state.get("path_plan"):
            actions.append(
                AssistantAction(
                    type="adjust_learning_path",
                    label="查看学习路径",
                    description="打开可调整路径，查看每个节点的推荐原因。",
                    route="/learning-path",
                    query={"target_node_id": state.get("target_node_id") or "", "mode": state["path_plan"].mode},
                    node_id=state.get("target_node_id"),
                )
            )
        state["actions"] = actions
        state["suggested_next_actions"] = [
            SuggestedNextAction(label="查看证据包", description="核对本轮回答引用了哪些图谱和资料。", action_type="inspect_evidence", priority=1),
            SuggestedNextAction(label="开始练习", route="/exercise", query={"node_id": state.get("target_node_id") or ""}, description="用练习验证掌握度。", priority=2),
        ]

        # 追加资源信息到回复（如果有资源生成）
        resource_appendix = self._resource_reply(state)
        if resource_appendix:
            # 如果已有回复，先追加换行分隔
            if state.get("final_reply"):
                state["final_reply"] += "\n\n---\n\n" + resource_appendix
            else:
                state["final_reply"] = resource_appendix
        elif not state.get("final_reply"):
            state["final_reply"] = self._fallback_reply(state)

        # 如果反思发现了改进空间，添加到回复
        if state.get("reflection") and state.get("needs_refinement"):
            reflection = state["reflection"]
            refinement = state.get("refinement_count", 0)
            state["final_reply"] += f"\n\n---\n> 💡 **资源反思**（第{refinement}轮）：{reflection}"

        # 如果证据质量低，添加提示
        evidence_score = state.get("evidence_quality_score", 1.0)
        if evidence_score < 0.5:
            state["final_reply"] += f"\n\n> ⚠️ 证据质量评分 {evidence_score:.1%}，建议查看图谱确认相关内容是否完整。"

        # 如果证据是降级匹配或无匹配，添加说明和建议
        evidence = state.get("evidence")
        if evidence:
            res_quality = getattr(evidence, "resolution_quality", "exact") if hasattr(evidence, "resolution_quality") else "exact"
            alternatives = getattr(evidence, "suggested_alternatives", []) if hasattr(evidence, "suggested_alternatives") else []
            if res_quality == "none":
                state["final_reply"] += "\n\n> ℹ️ 未能找到与你问题精确匹配的知识点。"
                if alternatives:
                    names = "、".join(a.get("name", a.get("uid", "")) for a in alternatives[:5])
                    state["final_reply"] += f" 你可能想了解：{names}。你也可以换个更具体的关键词重新提问。"
            elif res_quality == "fallback":
                center_name = ""
                if evidence.center_node:
                    center_name = getattr(evidence.center_node, "properties", {}).get("name", "") or ""
                state["final_reply"] += f"\n\n> 💡 你的问题未精确匹配到具体知识点，已为你匹配最接近的「{center_name or evidence.resolved_uid or ''}」。如果这不是你想要的，请尝试更精确的表述。"
                if alternatives:
                    names = "、".join(a.get("name", a.get("uid", "")) for a in alternatives[:3])
                    state["final_reply"] += f" 其他可能相关：{names}。"

        # 错误恢复提示
        if state.get("recovery_message"):
            state["final_reply"] += f"\n\n> ℹ️ {state['recovery_message']}"

        self._trace(state, "compose_response", "done", "已汇总能力调用、推荐原因和下一步行动。")
        return state

    async def extract_memory(self, state: AssistantState) -> AssistantState:
        """从本轮对话中提取结构化记忆并写入向量存储。"""
        if not self.memory_store or not self.embedding_service or not self.memory_extractor:
            self._trace(state, "extract_memory", "skipped", "记忆服务未初始化。")
            return state

        try:
            entry = await self.memory_extractor.extract_from_state(state)
            if entry is None:
                self._trace(state, "extract_memory", "skipped", "本轮对话无值得记忆的学习内容。")
                return state

            # 填充标识信息
            entry.student_id = state["student_id"]
            entry.conversation_id = state["conversation_id"]

            # 用证据包中的知识点 ID 补充 node_ids
            evidence = state.get("evidence")
            if evidence and evidence.resolved_uid:
                if evidence.resolved_uid not in entry.node_ids:
                    entry.node_ids.append(evidence.resolved_uid)
                # 补充前置节点
                if evidence.prerequisites:
                    for prereq in evidence.prerequisites[:3]:
                        for node in prereq.nodes:
                            if node.uid not in entry.node_ids:
                                entry.node_ids.append(node.uid)

            # 生成嵌入文本并写入
            text_for_embedding = self._format_memory_for_embedding(entry)
            embedding = await self.embedding_service.embed(text_for_embedding)
            await self.memory_store.insert(entry, embedding)

            self._trace(
                state, "extract_memory", "done",
                f"已提取记忆：{entry.key_insight[:80]}... "
                f"关联节点: {entry.node_ids}, 困惑: {entry.confusion_nodes}",
            )
        except Exception as exc:
            self._trace(state, "extract_memory", "failed", f"记忆提取失败：{type(exc).__name__}")
            state.setdefault("errors", []).append(f"记忆提取失败（不影响回复）：{exc}")

        return state

    def _quick_node_match(self, message: str) -> str | None:
        """基于关键词快速预匹配知识点 ID，不依赖 LLM。

        仅当用户明确提到具体知识点时才返回 node_id。
        宽泛查询（如"机器学习的应用""AI 能做什么"）返回 None。
        """
        _keyword_map: dict[str, str] = {
            # 精确匹配 — 具体的知识点
            "反向传播": "ml_backpropagation",
            "backprop": "ml_backpropagation",
            "梯度下降": "ml_gradient_descent",
            "gradient descent": "ml_gradient_descent",
            "激活函数": "ml_activation_function",
            "activation function": "ml_activation_function",
            "链式法则": "ml_chain_rule",
            "过拟合": "ml_overfitting_underfitting",
            "overfitting": "ml_overfitting_underfitting",
            "欠拟合": "ml_overfitting_underfitting",
            "正则化": "ml_regularization",
            "regularization": "ml_regularization",
            "交叉验证": "ml_cross_validation",
            "cross validation": "ml_cross_validation",
            "卷积神经网络": "ml_cnn",
            "CNN": "ml_cnn",
            "循环神经网络": "ml_rnn",
            "RNN": "ml_rnn",
            "LSTM": "ml_lstm",
            "Transformer": "ml_transformer",
            "transformer": "ml_transformer",
            "注意力机制": "ml_attention_mechanism",
            "attention": "ml_attention_mechanism",
            "损失函数": "ml_loss_function",
            "loss function": "ml_loss_function",
            "优化器": "ml_optimizer",
            "Adam": "ml_adam_optimizer",
            "BatchNorm": "ml_batch_normalization",
            "Dropout": "ml_dropout",
            "逻辑回归": "ml_logistic_regression",
            "SVM": "ml_svm",
            "支持向量机": "ml_svm",
            "决策树": "ml_decision_tree",
            "随机森林": "ml_random_forest",
            "K-Means": "ml_kmeans",
            "Kmeans": "ml_kmeans",
            "kmeans": "ml_kmeans",
            "k-means": "ml_kmeans",
            "KNN": "ml_knn",
            "PCA": "ml_pca",
            "降维": "ml_dimensionality_reduction",
            "朴素贝叶斯": "ml_naive_bayes",
            "特征工程": "ml_feature_selection",
            "集成学习": "ml_ensemble_learning",
            "神经网络": "ml_neural_network",
            "生成对抗": "ml_gan",
            "GAN": "ml_gan",
            "强化学习": "ml_reinforcement_learning",
            "迁移学习": "ml_transfer_learning",
            "聚类": "ml_kmeans",
            "回归": "ml_linear_regression",
        }
        # 宽泛关键词 — 没有具体知识点，不应匹配
        _broad_terms = {
            "机器学习的应用", "机器学习的应用", "深度学习的应用", "AI 的应用",
            "应用场景", "应用领域", "有什么用", "能做什么", "应用案例",
            "机器学习是什么", "深度学习是什么", "入门", "概述", "综述", "介绍",
        }
        msg_lower = message.lower()
        # 先检查是否为宽泛查询
        for term in _broad_terms:
            if term in msg_lower:
                return None
        # 再检查精确匹配
        for keyword, node_id in _keyword_map.items():
            if keyword.lower() in msg_lower:
                return node_id
        return None

    def _format_behavior_for_prompt(self, state: AssistantState) -> str:
        """将行为画像格式化为 prompt 可用的文本。"""
        behavior = state.get("_behavior_profile")
        if not behavior:
            return "（暂无行为画像数据）"
        lines = []
        # 格式有效性
        if behavior.format_effectiveness:
            ranked = sorted(
                behavior.format_effectiveness.items(),
                key=lambda x: x[1].effectiveness_score, reverse=True,
            )
            top = [f"{f}={eff.effectiveness_score:.2f}" for f, eff in ranked[:3]]
            lines.append(f"有效格式：{', '.join(top)}")
        # 深度偏好
        dp = behavior.depth_preference
        if dp.preferred_level:
            lines.append(f"深度偏好：{dp.preferred_level}（太浅{getattr(dp,'too_shallow_count',0)}次/适中{getattr(dp,'just_right_count',0)}次/太深{getattr(dp,'too_deep_count',0)}次）")
        # 理解缺口
        if behavior.comprehension_gaps:
            gaps_str = "; ".join(
                f"{g.node_id}(严重度{g.severity:.1f})" for g in behavior.comprehension_gaps[:3] if not g.resolved
            )
            if gaps_str:
                lines.append(f"理解缺口：{gaps_str}")
        # 策略
        if behavior.effective_strategies:
            strategies = []
            for nid, st in list(behavior.effective_strategies.items())[:2]:
                parts = [nid]
                if st.best_approach:
                    parts.append(f"best={st.best_approach}")
                if st.avoid_approach:
                    parts.append(f"avoid={st.avoid_approach}")
                strategies.append(": ".join(parts))
            if strategies:
                lines.append(f"有效策略：{'; '.join(strategies)}")
        # 洞察
        if behavior.insights:
            for ins in behavior.insights[:2]:
                lines.append(f"洞察：{ins.description}")
        return "\n".join(lines) if lines else "（暂无行为画像数据）"

    def _format_memory_for_embedding(self, entry) -> str:
        """格式化记忆条目为嵌入文本。"""
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

    def _format_memory_for_prompt(self, state: AssistantState) -> str:
        """将相关记忆格式化为 prompt 可用的文本。"""
        memories = state.get("relevant_memories") or []
        if not memories:
            return "（暂无相关历史学习记忆）"
        lines = []
        for m in memories[:5]:
            parts = []
            if m.get("student_question_summary"):
                parts.append(f"曾提问：{m['student_question_summary']}")
            if m.get("key_insight"):
                parts.append(f"关键发现：{m['key_insight']}")
            if m.get("confusion_nodes"):
                parts.append(f"困惑点：{', '.join(m['confusion_nodes'])}")
            if m.get("caution_topics"):
                parts.append(f"需注意：{', '.join(m['caution_topics'])}")
            if m.get("learning_preference_hint"):
                parts.append(f"偏好：{m['learning_preference_hint']}")
            if parts:
                lines.append("- " + " | ".join(parts))
        return "\n".join(lines) if lines else "（暂无相关历史学习记忆）"
        """格式化记忆条目为嵌入文本。"""
        from app.memory.vector_store import MemoryVectorStore
        # 重用 vector_store 中的格式化逻辑
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

    def _get_intent_chain(self):
        if self._intent_chain is not None:
            return self._intent_chain
        llm = self._chat_model()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的 LangGraph 学习主智能体意图识别节点。"
                    "只做结构化理解，不直接回答。必须从以下有效 intent 中选择一个并输出 JSON："
                    "profile_update（修改画像）、concept_explain（知识点讲解）、resource_generate（生成学习资源）、"
                    "exercise_help（练习辅导）、path_plan（学习路径规划）、progress_update（记录学习进度）、"
                    "assessment_review（评估回顾）、navigation_help（引导跳转）、general_learning_chat（通用学习问答）。"
                    "知识点 node_id 仅当用户明确指向某个具体知识点时才填写，参考课程图谱 ID："
                    "反向传播=ml_backpropagation，梯度下降=ml_gradient_descent，K-Means=ml_kmeans，逻辑回归=ml_logistic_regression，"
                    "神经网络=ml_neural_network，卷积神经网络=ml_cnn，循环神经网络=ml_rnn，SVM=ml_svm，"
                    "决策树=ml_decision_tree，随机森林=ml_random_forest，过拟合=ml_overfitting_underfitting，"
                    "正则化=ml_regularization，PCA=ml_pca，LSTM=ml_lstm，Transformer=ml_transformer。"
                    "**重要**：如果用户问题过于宽泛/无法匹配到具体知识点，请将 target_node_id 设为 null，intent 设为 general_learning_chat。"
                    "不要强行匹配。"
                    "资源类型使用 document、mindmap、exercise、video_script、code_case。"
                    "\n请直接输出 JSON，不要输出其他文字。JSON 格式："
                    '{{"intent": "...", "confidence": 0.95, "target_node_id": "ml_xxx", "resource_types": ["exercise"], "reasoning": "..."}}',
                ),
                ("human", "学生画像摘要：{profile}\n最近历史：{history}\n历史学习记忆：{memory_context}\n行为画像：{behavior_context}\n本轮输入：{message}\n请直接输出 JSON。"),
            ]
        )
        raw_chain = prompt | llm
        # 包装为手动 JSON 解析链
        async def _intent_chain(inputs: dict) -> AssistantIntentResult:
            from app.core.manual_json import parse_model
            response = await raw_chain.ainvoke(inputs)
            text = response.content if hasattr(response, "content") else str(response)
            return parse_model(text, AssistantIntentResult)
        self._intent_chain = _intent_chain
        return self._intent_chain

    def _get_tutor_chain(self):
        if self._tutor_chain is not None:
            return self._tutor_chain
        llm = self._chat_model()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的中文学习助手。回答要解释你理解了什么、使用了哪些证据、为什么这样推荐、下一步做什么。"
                    "语气像学习教练，避免只说已完成。公式尽量克制，优先图解/代码/练习化表达。",
                ),
                ("human", "画像摘要：{profile}\n证据包：{evidence}\n历史学习记忆：{memory_context}\n行为画像：{behavior_context}\n学生问题：{message}"),
            ]
        )
        self._tutor_chain = prompt | llm
        return self._tutor_chain

    def _get_exercise_chain(self):
        """练习讲解链：结合学生画像、关联知识点和练习内容，生成个性化错因和提示。"""
        llm = self._chat_model()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的中文学习教练，擅长分析学生练习错误。"
                    "请结合学生画像和练习上下文，生成个性化反馈，必须严格按以下 JSON 格式输出（只输出 JSON，不要其他文字）：\n"
                    "{\n  \"summary\": \"总述：学生哪里卡住了，整体思路是什么\",\n  \"likely_causes\": [\"原因1\", \"原因2\", \"原因3\"],\n  \"hints\": [\"提示1\", \"提示2\", \"提示3\"]\n}\n"
                    "likely_causes 要区分：概念理解错误 / 计算步骤错误 / 条件映射错误。\n"
                    "hints 要具体且可操作，避免空泛的\"多做题\"。",
                ),
                ("human", "学生画像：{profile}\n学生问题/练习上下文：{message}\n关联练习：{exercise_context}\n请生成 JSON 格式的练习讲解反馈。"),
            ]
        )
        return prompt | llm

    def _get_clarify_chain(self):
        """意图澄清链：置信度低时生成澄清选项。"""
        if getattr(self, "_clarify_chain", None) is not None:
            return self._clarify_chain
        llm = self._chat_model()
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的意图澄清专家。当学生意图不明确时，你需要生成 2-4 个具体选项供选择。"
                    "每个选项应该明确对应一种意图类型（concept_explain/resource_generate/exercise_help/path_plan/profile_update/progress_update）。"
                    "知识点 node_id 优先使用课程图谱 ID：反向传播=ml_backpropagation，梯度下降=ml_gradient_descent，"
                    "K-Means=ml_kmeans，逻辑回归=ml_logistic_regression，神经网络=ml_neural_network，"
                    "卷积神经网络=ml_cnn，循环神经网络=ml_rnn，支持向量机=ml_svm，决策树=ml_decision_tree，"
                    "随机森林=ml_random_forest，朴素贝叶斯=ml_naive_bayes，过拟合=ml_overfitting_underfitting，"
                    "正则化=ml_regularization，交叉验证=ml_cross_validation。"
                    "\n请直接输出 JSON，格式：{{\"question\": \"...\", \"options\": [{{\"label\": \"...\", \"value\": \"...\", \"description\": \"...\"}}]}}",
                ),
                ("human", "学生画像摘要：{profile}\n最近对话：{history}\n学生原话：{message}\n请直接输出 JSON。"),
            ]
        )
        raw_chain = prompt | llm
        async def _clarify_chain(inputs: dict) -> ClarifyIntentResult:
            from app.core.manual_json import parse_model
            response = await raw_chain.ainvoke(inputs)
            text = response.content if hasattr(response, "content") else str(response)
            return parse_model(text, ClarifyIntentResult)
        self._clarify_chain = _clarify_chain
        return self._clarify_chain

    async def _generate_clarification(
        self,
        message: str,
        profile: Any,
        history: list[dict],
    ) -> ClarifyIntentResult:
        """生成意图澄清选项。"""
        chain = self._get_clarify_chain()
        profile_json = json.dumps(
            profile.model_dump(mode="json") if profile and hasattr(profile, "model_dump") else {},
            ensure_ascii=False,
        )
        return await chain({
            "message": message,
            "profile": profile_json,
            "history": json.dumps(history[-4:], ensure_ascii=False),
        })

    def _chat_model(self):
        import httpx
        kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "api_key": self.settings.llm_api_key,
            "temperature": 0,
        }
        if self.settings.llm_base_url:
            kwargs["base_url"] = self.settings.llm_base_url
        # 使用自定义 httpx client 避免被第三方代理拦截
        kwargs["http_client"] = httpx.Client()
        kwargs["http_async_client"] = httpx.AsyncClient()
        return ChatOpenAI(**kwargs)

    def _normalize_resource_types(self, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            item = _RESOURCE_ALIASES.get(value, value)
            if item in _VALID_RESOURCE_TYPES:
                normalized.append(item)
        return list(dict.fromkeys(normalized))

    def _parse_generation_request(self, message: str) -> dict[str, Any]:
        request: dict[str, Any] = {}
        text = message.strip()
        exercise_tokens = ["选择题", "单选题", "编程题", "代码题", "简答题", "问答题", "案例题", "案例分析", "练习", "题", "自测", "测验"]
        if any(token in text for token in exercise_tokens):
            match = re.search(r"(\d{1,2})\s*[道个份套]?", text)
            if match:
                request["exercise_count"] = max(1, min(int(match.group(1)), 20))
            else:
                cn_match = re.search(r"([一二两三四五六七八九十]{1,3})\s*[道个份套]", text)
                if cn_match:
                    request["exercise_count"] = self._parse_chinese_number(cn_match.group(1))
        if any(token in text for token in ["选择题", "单选题", "选择"]):
            request["exercise_type"] = "choice"
        elif "编程题" in text or "代码题" in text:
            request["exercise_type"] = "coding"
        elif "简答题" in text or "问答题" in text:
            request["exercise_type"] = "short_answer"
        elif "案例题" in text or "案例分析" in text:
            request["exercise_type"] = "case_analysis"
        return request

    @staticmethod
    def _parse_chinese_number(text: str) -> int:
        digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if text == "十":
            return 10
        if text.startswith("十"):
            return max(1, min(10 + digits.get(text[1:], 0), 20))
        if "十" in text:
            left, _, right = text.partition("十")
            return max(1, min(digits.get(left, 1) * 10 + digits.get(right, 0), 20))
        return max(1, min(digits.get(text, 3), 20))

    def _default_resource_types(self, state: AssistantState) -> list[str]:
        text = state.get("user_message", "")
        picks = []
        for key, value in _RESOURCE_ALIASES.items():
            if key and key in text:
                picks.append(value)
        if not picks and state.get("profile"):
            prefs = ["mindmap" if item == "diagram" else item for item in state["profile"].preferences.resource_ranking]
            picks.extend([item for item in prefs if item in _VALID_RESOURCE_TYPES])
        return list(dict.fromkeys(picks or ["document", "mindmap", "exercise"]))[:4]

    def _resource_reply(self, state: AssistantState) -> str:
        resources = state.get("resources")
        if not resources:
            return ""
        lines: list[str] = []
        if resources.exercises:
            count = len(resources.exercises)
            center = state.get("target_node_id") or (state.get("evidence").resolved_uid if state.get("evidence") else "")
            lines.append(f"已为你生成 {count} 道{self._exercise_type_label(state.get('requested_exercise_type'))}，主题围绕 {center or '当前知识点'}。")
            lines.append("")
            for idx, exercise in enumerate(resources.exercises, 1):
                lines.append(f"### {idx}. {exercise.title or '练习题'}")
                lines.append(exercise.question)
                if exercise.options:
                    for option in exercise.options:
                        label = option.get("label", "")
                        text = option.get("text", "")
                        lines.append(f"- {label}. {text}")
                correct = exercise.answer.get("correct") or exercise.answer.get("reference_answer")
                if correct:
                    lines.append(f"**答案**：{correct}")
                explanation = exercise.answer.get("explanation")
                if explanation:
                    lines.append(f"**解析**：{explanation}")
                lines.append("")
        if resources.document and not lines:
            lines.append(f"已生成讲解文档：{resources.document.title}")
            lines.append(resources.document.content[:1200])
        if state.get("resource_record_id"):
            lines.append(f"> 已保存到资源中心，记录 ID：{state['resource_record_id']}")
        return "\n".join(lines).strip()

    @staticmethod
    def _exercise_type_label(value: str | None) -> str:
        return {
            "choice": "选择题",
            "short_answer": "简答题",
            "coding": "编程题",
            "case_analysis": "案例分析题",
        }.get(value or "choice", "练习题")

    def _path_reason(self, node_id: str, state: AssistantState) -> str:
        profile = state.get("profile")
        if profile and any(node_id in {item.node_id, item.topic} for item in profile.weak_points.self_reported):
            return "来自画像中的自述薄弱点。"
        if profile and node_id in profile.progress.in_progress_node_ids:
            return "来自当前正在学习的进度记录。"
        evidence = state.get("evidence")
        if evidence and evidence.ranking_reason:
            return evidence.ranking_reason[0]
        return "来自 GraphRAG 前置关系和当前学习目标。"

    def _fallback_reply(self, state: AssistantState) -> str:
        parts = [f"我理解你这次的需求是：{state.get('intent') or '学习支持'}。"]
        if state.get("evidence"):
            center = state["evidence"].resolved_uid or "相关知识点"
            parts.append(f"我已通过 GraphRAG 围绕 {center} 检索了前置关系、资料、练习和常见误区。")
        if state.get("resources"):
            parts.append("我还调用资源生成能力，准备了适合当前偏好的学习材料。")
        if state.get("path_plan"):
            parts.append("我根据画像薄弱点和图谱前置关系整理了一条可调整学习路径。")
        if state.get("profile_update"):
            parts.append("我已把本轮明确表达的画像或学习进度变化写回数据库。")
        parts.append("建议下一步先查看右侧证据与行动卡片，再进入图谱、资源或练习工作区继续学习。")
        return "\n\n".join(parts)

    def _base_actions(self, state: AssistantState) -> list[AssistantAction]:
        return [
            AssistantAction(type="open_profile", label="打开画像", description="查看当前画像摘要和薄弱点。", route="/profile/panel"),
            AssistantAction(type="open_profile_chat", label="补充画像", description="补充学习目标、偏好或背景信息。", route="/profile/chat"),
        ]

    def _trace(self, state: AssistantState, node: str, status: str, summary: str, metadata: dict[str, Any] | None = None) -> None:
        state.setdefault("agent_trace", []).append(
            AssistantTraceItem(node=node, status=status, summary=summary, metadata=metadata or {})  # type: ignore[arg-type]
        )
