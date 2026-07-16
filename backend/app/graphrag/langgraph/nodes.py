from __future__ import annotations

from typing import Any

from app.core.labels import choose_node_label
from app.graph.models import GraphNode, GraphPath
from app.graph.node_resolver import NodeResolver
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.evidence_retriever import EvidenceRetriever
from app.graphrag.langgraph.quality import choose_repair_action, grade_evidence_package
from app.graphrag.langgraph.state import HybridRAGState, RepairAction
from app.graphrag.schemas import EvidencePackage, StudentProfileInput
from app.memory.embedding import EmbeddingService
from app.memory.vector_store import MemoryVectorStore


class HybridRAGNodes:
    def __init__(
        self,
        *,
        graph_store: Neo4jGraphStore,
        node_resolver: NodeResolver,
        evidence_retriever: EvidenceRetriever,
        embedding_service: EmbeddingService | None = None,
        memory_store: MemoryVectorStore | None = None,
    ) -> None:
        self.graph_store = graph_store
        self.node_resolver = node_resolver
        self.evidence_retriever = evidence_retriever
        self.embedding_service = embedding_service
        self.memory_store = memory_store

    async def prepare_query(self, state: HybridRAGState) -> HybridRAGState:
        query = (state.get("query") or "").strip()
        state["query"] = query
        state["normalized_query"] = " ".join(query.split())
        state.setdefault("warnings", [])
        state.setdefault("trace", [])
        state.setdefault("repair_attempts", 0)
        state.setdefault("max_repair_attempts", 2)
        state.setdefault("repair_actions", [])
        state.setdefault("student_profile", StudentProfileInput())
        state["query_type"] = self._classify_query(query)
        state["intent"] = state.get("intent") or state["query_type"]
        self._trace(
            state,
            "prepare_query",
            "done",
            f"已标准化查询，识别为 {state['query_type']} 类型。",
            {"query": state["normalized_query"]},
        )
        return state

    async def resolve_learning_target(self, state: HybridRAGState) -> HybridRAGState:
        requested = state.get("requested_center_uid")
        profile = state.get("student_profile") or StudentProfileInput()
        if requested:
            state["target_uid"] = requested
            state["resolution_quality"] = "exact"
            state["candidate_nodes"] = [{"uid": requested, "reason": "调用方指定中心知识点"}]
            self._trace(state, "resolve_learning_target", "done", f"使用指定中心知识点 {requested}。")
            return state

        try:
            resolution = await self.node_resolver.resolve(state.get("normalized_query") or state["query"], profile.weak_points)
            state["target_uid"] = resolution.resolved_uid
            state["resolution_quality"] = "exact" if resolution.resolved_uid else "none"
            state["candidate_nodes"] = [
                {
                    "uid": node.uid,
                    "name": choose_node_label(node.properties.get("name"), node.uid),
                    "labels": node.labels,
                }
                for node in resolution.candidates
            ]
            if resolution.uncertainty:
                state.setdefault("warnings", []).extend(resolution.uncertainty)
            state["_node_resolution"] = {
                "normalized_query": resolution.normalized_query,
                "intent": resolution.intent,
                "candidate_uids": [node.uid for node in resolution.candidates],
                "llm_understanding": (
                    resolution.llm_understanding.model_dump()
                    if resolution.llm_understanding is not None
                    else None
                ),
            }
            if resolution.resolved_uid:
                self._trace(
                    state,
                    "resolve_learning_target",
                    "done",
                    f"定位到中心知识点 {resolution.resolved_uid}。",
                    {"candidate_count": len(resolution.candidates)},
                )
            else:
                fallback_uid = self._fallback_target_from_profile(profile)
                if fallback_uid:
                    state["target_uid"] = fallback_uid
                    state["resolution_quality"] = "fallback"
                    state.setdefault("warnings", []).append(
                        f"未精确匹配问题，暂按学生画像薄弱点 {choose_node_label(None, fallback_uid)} 组织证据。"
                    )
                    state.setdefault("candidate_nodes", []).append({
                        "uid": fallback_uid,
                        "reason": "student_profile_weak_point_fallback",
                    })
                self._trace(
                    state,
                    "resolve_learning_target",
                    "warning" if fallback_uid else "warning",
                    f"未精确定位中心知识点，{'已使用画像薄弱点降级。' if fallback_uid else '后续将尝试画像或候选降级。'}",
                    {"candidate_count": len(resolution.candidates)},
                )
        except Exception as exc:
            fallback_uid = self._fallback_target_from_profile(profile)
            state["target_uid"] = fallback_uid
            state["resolution_quality"] = "fallback" if fallback_uid else "none"
            state.setdefault("warnings", []).append(f"知识点解析失败：{type(exc).__name__}: {exc}")
            if fallback_uid:
                state.setdefault("warnings", []).append(f"已按学生画像薄弱点 {fallback_uid} 降级检索。")
            self._trace(state, "resolve_learning_target", "failed", "知识点解析失败，将进入修复逻辑。")
        return state

    async def retrieve_graph_context(self, state: HybridRAGState) -> HybridRAGState:
        target_uid = state.get("target_uid")
        profile = state.get("student_profile") or StudentProfileInput()
        if not target_uid:
            state["evidence_package"] = EvidencePackage(
                query=state["query"],
                resolution_quality=state.get("resolution_quality", "none"),
                uncertainty=state.get("warnings", []),
                missing_evidence=["resolved_center_node"],
            )
            self._trace(state, "retrieve_graph_context", "skipped", "缺少中心知识点，跳过 Neo4j 结构检索。")
            return state

        try:
            evidence = await self.evidence_retriever.retrieve(
                query=state["query"],
                center_uid=target_uid,
                student_profile=profile,
            )
            evidence.resolution_quality = state.get("resolution_quality", evidence.resolution_quality)
            evidence.uncertainty.extend(state.get("warnings", []))
            state["evidence_package"] = evidence
            state["target_uid"] = evidence.resolved_uid or target_uid
            state["graph_context"] = {
                "center_node": evidence.center_node,
                "prerequisites": evidence.prerequisites,
                "related_nodes": evidence.related_nodes,
                "dependency_paths": evidence.dependency_paths,
                "document_chunks": evidence.document_chunks,
                "exercises": evidence.exercises,
                "code_cases": evidence.code_cases,
                "misconceptions": evidence.misconceptions,
                "sources": evidence.sources,
                "candidate_node_ids": self._candidate_node_ids(evidence),
            }
            self._trace(
                state,
                "retrieve_graph_context",
                "done",
                f"已检索 Neo4j 结构证据：文档 {len(evidence.document_chunks)}、练习 {len(evidence.exercises)}、代码 {len(evidence.code_cases)}、FAQ {len(evidence.misconceptions)}。",
                {"resolved_uid": evidence.resolved_uid},
            )
        except Exception as exc:
            state["evidence_package"] = EvidencePackage(
                query=state["query"],
                resolved_uid=target_uid,
                resolution_quality="fallback",
                uncertainty=[*state.get("warnings", []), f"Neo4j 证据检索失败：{type(exc).__name__}: {exc}"],
                missing_evidence=["graph_context"],
            )
            state.setdefault("warnings", []).append(f"Neo4j 证据检索失败：{type(exc).__name__}: {exc}")
            self._trace(state, "retrieve_graph_context", "failed", "Neo4j 结构检索失败。")
        return state

    async def retrieve_semantic_context(self, state: HybridRAGState) -> HybridRAGState:
        evidence = state.get("evidence_package")
        hits = list(evidence.semantic_hits if evidence else [])
        state["semantic_hits"] = hits
        if hits:
            top = hits[0]
            self._trace(
                state,
                "retrieve_semantic_context",
                "done",
                f"语义索引命中 {len(hits)} 条，最高命中 {top.view.target_uid}。",
                {
                    "top_target_uid": top.view.target_uid,
                    "top_target_type": top.view.target_type,
                    "top_score": top.score,
                },
            )
        else:
            self._trace(state, "retrieve_semantic_context", "warning", "未获得课程语义命中，可能是 embedding API 不可用或查询相关性较低。")
        return state

    async def retrieve_memory_context(self, state: HybridRAGState) -> HybridRAGState:
        state["memory_hits"] = []
        if not self.embedding_service or not self.memory_store or not state.get("student_id"):
            self._trace(state, "retrieve_memory_context", "skipped", "未注入学生记忆检索组件，跳过 Memory RAG。")
            return state

        try:
            embedding = await self.embedding_service.embed(state["query"])
            graph_context = state.get("graph_context", {})
            node_ids = graph_context.get("candidate_node_ids") or ([state["target_uid"]] if state.get("target_uid") else None)
            results = await self.memory_store.hybrid_search(
                query_embedding=embedding,
                student_id=state["student_id"] or "",
                node_ids=node_ids,
                top_k=5,
            )
            hits: list[dict[str, Any]] = []
            for item in results:
                hits.append({
                    "score": item.score,
                    "entry": item.entry.model_dump(mode="json"),
                })
            state["memory_hits"] = hits
            self._trace(state, "retrieve_memory_context", "done", f"检索到 {len(hits)} 条学生长期记忆。")
        except Exception as exc:
            state.setdefault("warnings", []).append(f"学生记忆检索失败：{type(exc).__name__}: {exc}")
            self._trace(state, "retrieve_memory_context", "warning", "学生记忆检索失败，已降级继续。")
        return state

    async def fuse_canonical_evidence(self, state: HybridRAGState) -> HybridRAGState:
        evidence = state.get("evidence_package")
        if not evidence:
            state["merge_report"] = {}
            self._trace(state, "fuse_canonical_evidence", "skipped", "没有 EvidencePackage 可融合。")
            return state

        report = evidence.student_profile_adaptation.get("semantic_canonical_merge", {})
        state["merge_report"] = report
        evidence.student_profile_adaptation["hybrid_rag_trace"] = state.get("trace", [])
        evidence.student_profile_adaptation["memory_hits_count"] = len(state.get("memory_hits", []))
        evidence.student_profile_adaptation["memory_hits"] = [
            self._memory_hit_brief(hit)
            for hit in state.get("memory_hits", [])[:5]
        ]
        if state.get("_node_resolution"):
            evidence.student_profile_adaptation["node_resolution"] = state["_node_resolution"]
        if report:
            added = report.get("added", {})
            total = sum(int(value or 0) for value in added.values())
            self._trace(state, "fuse_canonical_evidence", "done", f"已将语义命中回灌 Neo4j canonical evidence，新增 {total} 条证据。", report)
        else:
            self._trace(state, "fuse_canonical_evidence", "done", "无新增语义回灌证据。")
        return state

    async def grade_evidence(self, state: HybridRAGState) -> HybridRAGState:
        profile = state.get("student_profile") or StudentProfileInput()
        report = grade_evidence_package(
            evidence=state.get("evidence_package"),
            semantic_hits=state.get("semantic_hits", []),
            profile=profile,
            resolution_quality=state.get("resolution_quality", "none"),
        )
        state["quality_report"] = report
        action = choose_repair_action(
            report,
            attempts=state.get("repair_attempts", 0),
            max_attempts=state.get("max_repair_attempts", 2),
        )
        state["pending_repair_action"] = action
        self._trace(
            state,
            "grade_evidence",
            "done" if report.get("enough") else "warning",
            f"证据质量评分 {report.get('overall_score', 0):.2f}，覆盖 {report.get('coverage_score', 0):.2f}，相关 {report.get('relevance_score', 0):.2f}。",
            {
                "quality_report": report,
                "pending_repair_action": action,
            },
        )
        return state

    async def repair_evidence(self, state: HybridRAGState) -> HybridRAGState:
        action = state.get("pending_repair_action") or "finalize_with_warning"
        attempts = state.get("repair_attempts", 0) + 1
        state["repair_attempts"] = attempts
        state.setdefault("repair_actions", []).append(action)
        evidence = state.get("evidence_package")
        profile = state.get("student_profile") or StudentProfileInput()

        if action == "profile_guided_search":
            if evidence and profile.weak_points:
                for node_uid in profile.weak_points[:3]:
                    await self._supplement_node_evidence(evidence, node_uid)
                await self._supplement_semantic_hits(
                    state,
                    candidate_node_ids=profile.weak_points,
                    top_k=12,
                    reason="profile_guided_search",
                )
                state["resolution_quality"] = "fallback"
                state.setdefault("warnings", []).append(f"证据不足，已按学生薄弱点 {', '.join(profile.weak_points[:3])} 补充检索。")
        elif action == "expand_related_nodes":
            if evidence and state.get("target_uid"):
                await self._supplement_related_nodes(evidence, state["target_uid"])
                await self._supplement_semantic_hits(
                    state,
                    candidate_node_ids=self._candidate_node_ids(evidence),
                    top_k=12,
                    reason="expand_related_nodes",
                )
            state.setdefault("warnings", []).append("证据覆盖不足，已扩展相关知识点和相关资源。")
        elif action == "expand_prerequisites":
            if evidence and state.get("target_uid"):
                await self._supplement_prerequisites(evidence, state["target_uid"])
                await self._supplement_semantic_hits(
                    state,
                    candidate_node_ids=self._candidate_node_ids(evidence),
                    top_k=12,
                    reason="expand_prerequisites",
                )
            state.setdefault("warnings", []).append("证据覆盖不足，已扩展前置知识和前置节点资源。")
        elif action == "global_semantic_search":
            await self._supplement_semantic_hits(
                state,
                candidate_node_ids=[],
                top_k=16,
                reason="global_semantic_search",
            )
            state.setdefault("warnings", []).append("语义相关性不足，已执行全局课程语义检索并回查 Neo4j 证据。")
        elif action == "ask_clarification":
            state["resolution_quality"] = "none"
            state.setdefault("warnings", []).append("当前问题无法可靠定位知识点，需要向学生澄清。")
        else:
            state.setdefault("warnings", []).append("证据仍不足，最终回答需要保留不确定性提示。")

        if evidence:
            await self._refresh_evidence_metrics(evidence)
            state["semantic_hits"] = list(evidence.semantic_hits)
            state["graph_context"] = {
                "center_node": evidence.center_node,
                "prerequisites": evidence.prerequisites,
                "related_nodes": evidence.related_nodes,
                "dependency_paths": evidence.dependency_paths,
                "document_chunks": evidence.document_chunks,
                "exercises": evidence.exercises,
                "code_cases": evidence.code_cases,
                "misconceptions": evidence.misconceptions,
                "sources": evidence.sources,
                "candidate_node_ids": self._candidate_node_ids(evidence),
            }
            evidence.student_profile_adaptation["hybrid_rag_trace"] = state.get("trace", [])

        self._trace(state, "repair_evidence", "done", f"执行修复动作：{action}，第 {attempts} 次。")
        return state

    async def finalize_evidence(self, state: HybridRAGState) -> HybridRAGState:
        evidence = state.get("evidence_package")
        if evidence is None:
            evidence = EvidencePackage(
                query=state["query"],
                resolved_uid=state.get("target_uid"),
                resolution_quality=state.get("resolution_quality", "none"),
                uncertainty=state.get("warnings", []),
                missing_evidence=["evidence_package"],
            )
            state["evidence_package"] = evidence

        evidence.resolution_quality = state.get("resolution_quality", evidence.resolution_quality)
        evidence.uncertainty = list(dict.fromkeys([*evidence.uncertainty, *state.get("warnings", [])]))
        evidence.student_profile_adaptation["hybrid_rag_quality"] = state.get("quality_report", {})
        evidence.student_profile_adaptation["hybrid_rag_repair_actions"] = state.get("repair_actions", [])
        evidence.student_profile_adaptation["hybrid_rag_trace"] = state.get("trace", [])

        quality = state.get("quality_report", {})
        if quality.get("missing_categories"):
            evidence.missing_evidence = list(dict.fromkeys([
                *evidence.missing_evidence,
                *quality.get("missing_categories", []),
            ]))
        self._trace(state, "finalize_evidence", "done", "已输出 HybridRAG EvidencePackage。")
        return state

    @staticmethod
    def _candidate_node_ids(evidence: EvidencePackage) -> list[str]:
        node_ids: list[str] = []
        if evidence.resolved_uid:
            node_ids.append(evidence.resolved_uid)
        for path in [*evidence.prerequisites, *evidence.related_nodes]:
            node_ids.extend(node.uid for node in path.nodes)
        for dep_path in evidence.dependency_paths:
            node_ids.extend(dep_path.path_nodes)
        return list(dict.fromkeys([node_id for node_id in node_ids if node_id]))

    @staticmethod
    def _fallback_target_from_profile(profile: StudentProfileInput) -> str | None:
        if profile.weak_points:
            return profile.weak_points[0]
        if profile.mastery:
            return min(profile.mastery.items(), key=lambda item: item[1])[0]
        return None

    async def _supplement_related_nodes(self, evidence: EvidencePackage, center_uid: str) -> None:
        try:
            related_paths = await self.graph_store.get_related_nodes(
                center_uid,
                limit=max(self.evidence_retriever.policy.max_related_nodes * 2, 12),
            )
        except Exception:
            return
        self._append_unique_paths(evidence.related_nodes, related_paths)
        for node_uid in self._node_ids_from_paths(related_paths, exclude_uid=center_uid)[:8]:
            await self._supplement_node_evidence(evidence, node_uid)

    async def _supplement_prerequisites(self, evidence: EvidencePackage, center_uid: str) -> None:
        try:
            prereq_paths = await self.graph_store.get_prerequisite_tree(
                center_uid,
                max_depth=self.evidence_retriever.policy.max_hop_depth,
                limit_per_level=max(self.evidence_retriever.policy.max_prerequisites, 12),
            )
        except Exception:
            return
        self._append_unique_paths(evidence.prerequisites, [path for path in prereq_paths if len(path.nodes) <= 2])
        for node_uid in self._node_ids_from_paths(prereq_paths, exclude_uid=center_uid)[:10]:
            await self._supplement_node_evidence(evidence, node_uid)

    async def _supplement_node_evidence(self, evidence: EvidencePackage, node_uid: str) -> None:
        try:
            docs = await self.graph_store.get_document_chunks_for_node(node_uid, limit=4)
            code_cases = await self.graph_store.get_code_cases_for_node(node_uid, limit=3)
            exercises = await self.graph_store.get_exercises_for_node(node_uid, limit=4)
            misconceptions = await self.graph_store.get_misconceptions_for_node(node_uid, limit=6)
        except Exception:
            return
        self._append_unique_nodes(evidence.document_chunks, docs)
        self._append_unique_nodes(evidence.code_cases, code_cases)
        self._append_unique_nodes(evidence.exercises, exercises)
        self._append_unique_nodes(evidence.misconceptions, misconceptions)

    async def _supplement_semantic_hits(
        self,
        state: HybridRAGState,
        *,
        candidate_node_ids: list[str],
        top_k: int,
        reason: str,
    ) -> None:
        evidence = state.get("evidence_package")
        profile = state.get("student_profile") or StudentProfileInput()
        if evidence is None or self.evidence_retriever.semantic_retriever is None:
            return
        try:
            hits = await self.evidence_retriever.semantic_retriever.search(
                state.get("query", ""),
                candidate_node_ids=list(dict.fromkeys(candidate_node_ids)),
                weak_points=profile.weak_points,
                preferences=profile.preferences,
                top_k=top_k,
            )
        except Exception as exc:
            state.setdefault("warnings", []).append(f"补充语义检索失败：{type(exc).__name__}: {exc}")
            return

        existing_view_ids = {hit.view.id for hit in evidence.semantic_hits}
        new_hits = [hit for hit in hits if hit.view.id not in existing_view_ids]
        for hit in new_hits:
            hit.rank_reason = list(dict.fromkeys([*hit.rank_reason, f"HybridRAG 修复动作：{reason}"]))
        evidence.semantic_hits.extend(new_hits)
        state["semantic_hits"] = list(evidence.semantic_hits)
        if not new_hits:
            return

        merge_report = await self.evidence_retriever._merge_semantic_canonical_evidence(
            semantic_hits=new_hits,
            exercises=evidence.exercises,
            document_chunks=evidence.document_chunks,
            code_cases=evidence.code_cases,
            misconceptions=evidence.misconceptions,
        )
        existing_report = evidence.student_profile_adaptation.get("semantic_canonical_merge", {})
        evidence.student_profile_adaptation["semantic_canonical_merge"] = self._merge_semantic_reports(
            existing_report,
            merge_report,
        )
        self._trace(
            state,
            "repair_semantic_context",
            "done",
            f"补充语义检索命中 {len(new_hits)} 条，并回查 Neo4j canonical evidence。",
            {"reason": reason, "merge_report": merge_report},
        )

    async def _refresh_evidence_metrics(self, evidence: EvidencePackage) -> None:
        if evidence.center_node is None and evidence.resolved_uid:
            evidence.center_node = await self.graph_store.get_node(evidence.resolved_uid)
        if evidence.center_node is None:
            return
        evidence.sources = await self.evidence_retriever._collect_sources(
            evidence.center_node,
            evidence.exercises,
            evidence.document_chunks,
            evidence.code_cases,
            evidence.misconceptions,
        )
        score, coverage, completeness, diversity = self.evidence_retriever._compute_score(
            evidence.center_node,
            evidence.prerequisites,
            evidence.related_nodes,
            evidence.exercises,
            evidence.document_chunks,
            evidence.code_cases,
            evidence.misconceptions,
        )
        coverage.sources_count = len(evidence.sources)
        evidence.evidence_score = score
        evidence.coverage_stats = coverage
        evidence.evidence_completeness = completeness
        evidence.resource_diversity = diversity
        evidence.relevance_score = self.evidence_retriever._compute_relevance(
            evidence.query,
            evidence.center_node,
            evidence.document_chunks,
            evidence.code_cases,
            evidence.exercises,
        )
        evidence.missing_evidence = list(dict.fromkeys(completeness.missing_categories))

    @staticmethod
    def _append_unique_nodes(target: list[GraphNode], additions: list[GraphNode]) -> int:
        seen = {item.uid for item in target}
        added = 0
        for node in additions:
            if node.uid in seen:
                continue
            target.append(node)
            seen.add(node.uid)
            added += 1
        return added

    @staticmethod
    def _append_unique_paths(target: list[GraphPath], additions: list[GraphPath]) -> int:
        seen = {
            tuple([*(node.uid for node in path.nodes), *(rel.type for rel in path.relationships)])
            for path in target
        }
        added = 0
        for path in additions:
            key = tuple([*(node.uid for node in path.nodes), *(rel.type for rel in path.relationships)])
            if key in seen:
                continue
            target.append(path)
            seen.add(key)
            added += 1
        return added

    @staticmethod
    def _node_ids_from_paths(paths: list[GraphPath], *, exclude_uid: str) -> list[str]:
        node_ids: list[str] = []
        for path in paths:
            for node in path.nodes:
                if node.uid and node.uid != exclude_uid:
                    node_ids.append(node.uid)
        return list(dict.fromkeys(node_ids))

    @staticmethod
    def _merge_semantic_reports(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = {
            "added": dict(existing.get("added", {})),
            "skipped": dict(existing.get("skipped", {})),
            "missing_uids": list(existing.get("missing_uids", [])),
            "type_mismatches": list(existing.get("type_mismatches", [])),
        }
        for group in ["added", "skipped"]:
            for key, value in incoming.get(group, {}).items():
                merged[group][key] = int(merged[group].get(key, 0) or 0) + int(value or 0)
        merged["missing_uids"] = list(dict.fromkeys([*merged["missing_uids"], *incoming.get("missing_uids", [])]))
        merged["type_mismatches"].extend(incoming.get("type_mismatches", []))
        return merged

    @staticmethod
    def _memory_hit_brief(hit: dict[str, Any]) -> dict[str, Any]:
        entry = hit.get("entry") or {}
        return {
            "score": hit.get("score", 0.0),
            "memory_id": entry.get("id", ""),
            "intent": entry.get("intent", ""),
            "node_ids": entry.get("node_ids", []),
            "confusion_nodes": entry.get("confusion_nodes", []),
            "student_question_summary": entry.get("student_question_summary", ""),
            "key_insight": entry.get("key_insight", ""),
            "learning_preference_hint": entry.get("learning_preference_hint", ""),
        }

    @staticmethod
    def _classify_query(query: str) -> str:
        q = query.lower()
        if any(token in q for token in ["代码", "python", "实现", "demo", "code"]):
            return "code_help"
        if any(token in q for token in ["错", "题", "练习", "答案", "为什么不对"]):
            return "exercise_help"
        if any(token in q for token in ["路线", "计划", "怎么学", "顺序"]):
            return "path_plan"
        if any(token in q for token in ["复习", "测试", "评估", "掌握"]):
            return "assessment_review"
        if any(token in q for token in ["为什么", "是什么", "原理", "解释", "定义", "loss", "震荡"]):
            return "concept_explanation"
        return "general"

    @staticmethod
    def _trace(
        state: HybridRAGState,
        node: str,
        status: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        state.setdefault("trace", []).append({
            "node": node,
            "status": status,
            "summary": summary,
            "metadata": metadata or {},
        })
