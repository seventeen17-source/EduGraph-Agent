from app.core.labels import choose_node_label
from app.graph.expansion_policy import GraphExpansionPolicy
from app.graph.models import DependencyPath, GraphNode, GraphPath, MultiHopSummary
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.ranking import rank_nodes_by_profile
from app.graphrag.schemas import CoverageStats, EvidenceCompleteness, EvidencePackage, StudentProfileInput
from app.rag.course_retriever import CourseSemanticRetriever
from app.rag.schemas import CourseSemanticHit


class EvidenceRetriever:
    """Collects explainable graph evidence around one resolved KnowledgePoint."""

    def __init__(
        self,
        graph_store: Neo4jGraphStore,
        policy: GraphExpansionPolicy,
        semantic_retriever: CourseSemanticRetriever | None = None,
    ) -> None:
        self.graph_store = graph_store
        self.policy = policy
        self.semantic_retriever = semantic_retriever

    async def retrieve(
        self,
        query: str,
        center_uid: str,
        student_profile: StudentProfileInput | None = None,
    ) -> EvidencePackage:
        profile = student_profile or StudentProfileInput()
        center = await self.graph_store.get_node(center_uid)
        if center is None:
            return EvidencePackage(
                query=query,
                resolved_uid=center_uid,
                uncertainty=["未找到中心知识点"],
                missing_evidence=["中心知识点"],
            )

        # ── 多跳前置依赖树 ──
        dependency_paths: list[DependencyPath] = []
        intermediate_evidence: dict[str, dict] = {}
        if self.policy.multi_hop_enabled:
            prereq_tree = await self.graph_store.get_prerequisite_tree(
                center_uid,
                max_depth=self.policy.max_hop_depth,
                limit_per_level=self.policy.max_prerequisites,
            )
            # 同时收集 1-hop 前置（用于兼容现有逻辑）
            prerequisites = [p for p in prereq_tree if len(p.nodes) <= 2]
            if not prerequisites:
                prerequisites = await self.graph_store.get_prerequisites(
                    center_uid, depth=1, limit=self.policy.max_prerequisites,
                )
            # 构建多跳依赖路径 + 收集中间节点证据
            dependency_paths, intermediate_evidence = await self._build_dependency_paths(
                center_uid, prereq_tree, profile,
            )
        else:
            prerequisites = await self.graph_store.get_prerequisites(
                center_uid,
                depth=self.policy.clamp_depth(),
                limit=self.policy.max_prerequisites,
            )

        related_nodes = await self.graph_store.get_related_nodes(
            center_uid,
            limit=self.policy.max_related_nodes,
        )
        exercises = await self.graph_store.get_exercises_for_node(
            center_uid,
            limit=self.policy.max_exercises,
        )
        document_chunks = await self.graph_store.get_document_chunks_for_node(
            center_uid,
            limit=self.policy.max_document_chunks,
        )
        code_cases = await self.graph_store.get_code_cases_for_node(
            center_uid,
            limit=self.policy.max_code_cases,
        )
        misconceptions = await self.graph_store.get_misconceptions_for_node(center_uid)

        # ── 多跳证据合并：收集中间节点的证据追加到 evidence ──
        if self.policy.collect_intermediate_evidence and intermediate_evidence:
            for node_id, evidence_dict in intermediate_evidence.items():
                # 合并 document_chunks
                for doc in evidence_dict.get("document_chunks", []):
                    if doc.uid not in {d.uid for d in document_chunks}:
                        document_chunks.append(doc)
                # 合并 code_cases
                for cc in evidence_dict.get("code_cases", []):
                    if cc.uid not in {c.uid for c in code_cases}:
                        code_cases.append(cc)
                # 合并 exercises
                for ex in evidence_dict.get("exercises", []):
                    if ex.uid not in {e.uid for e in exercises}:
                        exercises.append(ex)
                # 合并 misconceptions
                for mc in evidence_dict.get("misconceptions", []):
                    if mc.uid not in {m.uid for m in misconceptions}:
                        misconceptions.append(mc)

        subgraph = await self.graph_store.get_subgraph(
            center_uid,
            relation_types=self.policy.graphrag_relations,
            depth=self.policy.clamp_depth(),
            limit=self.policy.max_subgraph_items,
        )

        semantic_hits = await self._retrieve_semantic_hits(
            query=query,
            center_uid=center_uid,
            prerequisites=prerequisites,
            related_nodes=related_nodes,
            dependency_paths=dependency_paths,
            profile=profile,
        )

        semantic_merge_report = await self._merge_semantic_canonical_evidence(
            semantic_hits=semantic_hits,
            exercises=exercises,
            document_chunks=document_chunks,
            code_cases=code_cases,
            misconceptions=misconceptions,
        )

        exercises = rank_nodes_by_profile(
            exercises,
            profile.weak_points,
            mastery=profile.mastery,
            preferences=profile.preferences,
        )
        sources = await self._collect_sources(center, exercises, document_chunks, code_cases, misconceptions)
        missing = []
        if not document_chunks:
            missing.append("文档证据")
        if not code_cases:
            missing.append("代码案例")
        if not exercises:
            missing.append("练习题")
        if not misconceptions:
            missing.append("常见误区")

        # 计算质量评分
        evidence_score, coverage_stats, evidence_completeness, resource_diversity = self._compute_score(
            center, prerequisites, related_nodes, exercises,
            document_chunks, code_cases, misconceptions,
        )

        # 计算相关性评分
        relevance_score = self._compute_relevance(query, center, document_chunks, code_cases, exercises)

        # ── 构建多跳摘要 ──
        multi_hop_summary = self._build_multi_hop_summary(
            center_uid, dependency_paths, prerequisites, profile,
        ) if self.policy.multi_hop_enabled else None

        # 增强关系摘要（加入多跳信息）
        relation_summary = self._summarize_relations(center, prerequisites, related_nodes)
        if multi_hop_summary and multi_hop_summary.reasoning_chain:
            relation_summary = multi_hop_summary.reasoning_chain + relation_summary

        return EvidencePackage(
            query=query,
            resolved_uid=center_uid,
            center_node=center,
            query_type=self._classify_query(query),
            evidence_score=evidence_score,
            relation_summary=relation_summary,
            recommended_next_actions=self._recommend_actions(
                center, exercises, document_chunks, code_cases,
                evidence_completeness.missing_categories, profile,
            ),
            prerequisites=prerequisites,
            related_nodes=related_nodes,
            exercises=exercises,
            document_chunks=document_chunks,
            code_cases=code_cases,
            misconceptions=misconceptions,
            semantic_hits=semantic_hits,
            graph_paths=subgraph.paths,
            sources=sources,
            ranking_reason=self._ranking_reason(profile, exercises, document_chunks),
            student_profile_adaptation={
                "weak_points": profile.weak_points,
                "preferences": profile.preferences,
                "goal": profile.goal,
                "semantic_canonical_merge": semantic_merge_report,
            },
            missing_evidence=evidence_completeness.missing_categories,
            coverage_stats=coverage_stats,
            evidence_completeness=evidence_completeness,
            resource_diversity=resource_diversity,
            relevance_score=relevance_score,
            # 多跳依赖
            multi_hop_summary=multi_hop_summary,
            dependency_paths=dependency_paths,
        )

    async def _retrieve_semantic_hits(
        self,
        *,
        query: str,
        center_uid: str,
        prerequisites: list[GraphPath],
        related_nodes: list[GraphPath],
        dependency_paths: list[DependencyPath],
        profile: StudentProfileInput,
    ) -> list[CourseSemanticHit]:
        if self.semantic_retriever is None:
            return []

        candidate_node_ids: list[str] = [center_uid]
        for path in [*prerequisites, *related_nodes]:
            candidate_node_ids.extend(node.uid for node in path.nodes)
        for dep_path in dependency_paths:
            candidate_node_ids.extend(dep_path.path_nodes)
        candidate_node_ids = list(dict.fromkeys([node_id for node_id in candidate_node_ids if node_id]))

        try:
            return await self.semantic_retriever.search(
                query,
                candidate_node_ids=candidate_node_ids,
                weak_points=profile.weak_points,
                preferences=profile.preferences,
                top_k=10,
            )
        except Exception:
            return []

    async def _merge_semantic_canonical_evidence(
        self,
        *,
        semantic_hits: list[CourseSemanticHit],
        exercises: list[GraphNode],
        document_chunks: list[GraphNode],
        code_cases: list[GraphNode],
        misconceptions: list[GraphNode],
    ) -> dict:
        """Fetch semantic-hit targets from Neo4j and merge canonical evidence.

        Chroma is only a semantic entry layer. This method deliberately uses
        target_uid to re-read the real evidence node from Neo4j before the item
        can affect coverage, resource generation, or source collection.
        """

        report = {
            "added": {
                "DocumentChunk": 0,
                "Exercise": 0,
                "CodeCase": 0,
                "Misconception": 0,
            },
            "skipped": {
                "KnowledgePoint": 0,
                "duplicate": 0,
                "missing_in_neo4j": 0,
                "type_mismatch": 0,
            },
            "missing_uids": [],
            "type_mismatches": [],
        }
        seen_targets: set[str] = set()

        for hit in semantic_hits:
            target_uid = hit.view.target_uid
            target_type = hit.view.target_type
            if not target_uid or target_uid in seen_targets:
                if target_uid:
                    report["skipped"]["duplicate"] += 1
                continue
            seen_targets.add(target_uid)

            if target_type == "KnowledgePoint":
                report["skipped"]["KnowledgePoint"] += 1
                continue

            try:
                node = await self.graph_store.get_node(target_uid)
            except Exception as exc:
                report["skipped"]["missing_in_neo4j"] += 1
                report["missing_uids"].append(f"{target_uid} ({type(exc).__name__})")
                continue

            if node is None:
                report["skipped"]["missing_in_neo4j"] += 1
                report["missing_uids"].append(target_uid)
                continue

            if target_type not in node.labels:
                report["skipped"]["type_mismatch"] += 1
                report["type_mismatches"].append({
                    "uid": target_uid,
                    "expected": target_type,
                    "labels": node.labels,
                })
                continue

            canonical_node = self._annotate_semantic_match(node, hit)
            added = False
            if target_type == "DocumentChunk":
                added = self._append_unique_node(document_chunks, canonical_node)
            elif target_type == "Exercise":
                added = self._append_unique_node(exercises, canonical_node)
            elif target_type == "CodeCase":
                added = self._append_unique_node(code_cases, canonical_node)
            elif target_type == "Misconception":
                added = self._append_unique_node(misconceptions, canonical_node)

            if added:
                report["added"][target_type] += 1
            else:
                report["skipped"]["duplicate"] += 1

        return report

    @staticmethod
    def _append_unique_node(items: list[GraphNode], node: GraphNode) -> bool:
        if node.uid in {item.uid for item in items}:
            return False
        items.append(node)
        return True

    @staticmethod
    def _annotate_semantic_match(node: GraphNode, hit: CourseSemanticHit) -> GraphNode:
        enriched = node.model_copy(deep=True)
        enriched.properties["_semantic_match"] = {
            "view_id": hit.view.id,
            "view_type": hit.view.view_type,
            "score": hit.score,
            "semantic_score": hit.semantic_score,
            "graph_bonus": hit.graph_bonus,
            "profile_bonus": hit.profile_bonus,
            "rank_reason": hit.rank_reason,
        }
        return enriched

    async def _build_dependency_paths(
        self,
        center_uid: str,
        prereq_tree: list[GraphPath],
        profile: StudentProfileInput,
    ) -> tuple[list[DependencyPath], dict[str, dict]]:
        """从多跳前置树构建 DependencyPath 列表 + 收集中间节点证据。"""
        dep_paths: list[DependencyPath] = []
        intermediate_evidence: dict[str, dict] = {}
        collected_nodes: set[str] = set()

        for path in prereq_tree:
            if len(path.nodes) < 2:
                continue

            node_ids = [n.uid for n in path.nodes]
            node_labels = [
                n.properties.get("name") or n.properties.get("title") or n.uid
                for n in path.nodes
            ]
            depth = len(path.relationships)

            reasoning = self._generate_path_reasoning(node_ids, node_labels, profile)

            # 收集中间节点的证据（depth >= 2 的路径中，中间节点也收集）
            evidence_for_path: dict[str, dict] = {}
            if self.policy.collect_intermediate_evidence and depth >= 2:
                # 跳过 center node (最后一个) 只收集前置节点
                for i, nid in enumerate(node_ids[:-1]):
                    if nid in collected_nodes:
                        continue
                    collected_nodes.add(nid)
                    try:
                        docs = await self.graph_store.get_document_chunks_for_node(
                            nid, limit=3,
                        )
                        code = await self.graph_store.get_code_cases_for_node(
                            nid, limit=2,
                        )
                        exs = await self.graph_store.get_exercises_for_node(
                            nid, limit=2,
                        )
                        mcs = await self.graph_store.get_misconceptions_for_node(nid)
                        evidence_for_path[nid] = {
                            "document_chunks": docs,
                            "code_cases": code,
                            "exercises": exs,
                            "misconceptions": mcs,
                        }
                    except Exception:
                        pass

            dep_path = DependencyPath(
                path_nodes=node_ids,
                path_labels=node_labels,
                depth=depth,
                reasoning=reasoning,
                intermediate_evidence=evidence_for_path,
            )
            dep_paths.append(dep_path)
            # 合并到总 intermediate_evidence
            for nid, ev in evidence_for_path.items():
                if nid not in intermediate_evidence:
                    intermediate_evidence[nid] = ev
                else:
                    # 简单合并（避免重复）
                    for key in ["document_chunks", "code_cases", "exercises", "misconceptions"]:
                        existing = intermediate_evidence[nid].get(key, [])
                        for item in ev.get(key, []):
                            if item.uid not in {e.uid for e in existing}:
                                existing.append(item)
                        intermediate_evidence[nid][key] = existing

        return dep_paths, intermediate_evidence

    @staticmethod
    def _generate_path_reasoning(
        node_ids: list[str],
        node_labels: list[str],
        profile: StudentProfileInput,
    ) -> str:
        """为一条依赖路径生成自然语言推理说明。"""
        if len(node_ids) < 2:
            return ""

        # 构建链式描述
        chain = " → ".join(node_labels)
        parts = [f"学习路径：{chain}"]

        # 标记薄弱点
        weak_in_path = [nid for nid in node_ids if nid in profile.weak_points]
        if weak_in_path:
            weak_labels = [node_labels[node_ids.index(nid)] for nid in weak_in_path if nid in node_ids]
            if weak_labels:
                parts.append(f"⚠️ 你的薄弱点在「{'、'.join(weak_labels)}」，建议优先掌握")

        # 标记低掌握度
        if profile.mastery:
            low_mastery = [
                node_labels[node_ids.index(nid)]
                for nid in node_ids
                if nid in profile.mastery and profile.mastery[nid] < 0.5
            ]
            if low_mastery:
                parts.append(f"📊 掌握度偏低的节点：{'、'.join(low_mastery)}")

        # 学习建议
        if len(node_ids) >= 3:
            parts.append(f"💡 建议学习顺序：先「{node_labels[0]}」→ 再「{node_labels[-2]}」→ 最后「{node_labels[-1]}」")

        return "；".join(parts)

    def _build_multi_hop_summary(
        self,
        center_uid: str,
        dependency_paths: list[DependencyPath],
        prerequisites: list[GraphPath],
        profile: StudentProfileInput,
    ) -> MultiHopSummary:
        """构建多跳依赖分析摘要。"""
        direct_prereqs: list[str] = []
        transitive_prereqs: list[str] = []
        max_depth = 0

        for dp in dependency_paths:
            if dp.depth == 1:
                direct_prereqs.extend(dp.path_nodes[:-1])  # 去掉 center node
            else:
                transitive_prereqs.extend(dp.path_nodes[:-1])
            max_depth = max(max_depth, dp.depth)

        # 从 prerequisites 补充直接前置
        for p in prerequisites:
            for node in p.nodes:
                if node.uid != center_uid and node.uid not in direct_prereqs:
                    direct_prereqs.append(node.uid)

        direct_prereqs = list(dict.fromkeys(direct_prereqs))
        transitive_prereqs = list(dict.fromkeys(
            [n for n in transitive_prereqs if n not in direct_prereqs]
        ))

        # 构建推理链
        reasoning_chain: list[str] = []
        if direct_prereqs:
            reasoning_chain.append(
                f"「{center_uid}」的直接前置知识包括：{'、'.join(direct_prereqs[:5])}"
                f"{'等' if len(direct_prereqs) > 5 else ''}。掌握这些前置内容是理解当前知识点的前提。"
            )
        if transitive_prereqs:
            reasoning_chain.append(
                f"进一步追溯发现 {len(transitive_prereqs)} 个间接依赖：{'、'.join(transitive_prereqs[:5])}"
                f"{'等' if len(transitive_prereqs) > 5 else ''}。这些知识点是前置的前置，形成了 {max_depth} 层依赖链路。"
            )

        # 结合学生画像给出个性化建议
        weak_in_deps = [n for n in direct_prereqs + transitive_prereqs if n in profile.weak_points]
        if weak_in_deps:
            reasoning_chain.append(
                f"⚠️ 你的画像显示「{'、'.join(weak_in_deps[:3])}」是薄弱点——"
                f"这直接影响了 {center_uid} 的学习。建议优先攻克这些薄弱前置。"
            )

        if max_depth >= 2:
            reasoning_chain.append(
                f"💡 多跳依赖链表明：要掌握 {center_uid}，需要先通过 {max_depth} 层前置知识。"
                f"建议按拓扑顺序逐步学习，不要跳过中间节点。"
            )

        node_label_by_id = {center_uid: choose_node_label(None, center_uid)}
        for dp in dependency_paths:
            for node_id, label in zip(dp.path_nodes, dp.path_labels):
                node_label_by_id[node_id] = choose_node_label(label, node_id)
        for path in prerequisites:
            for node in path.nodes:
                node_label_by_id[node.uid] = (
                    node.properties.get("name")
                    or node.properties.get("title")
                    or choose_node_label(None, node.uid)
                )

        for node_id, label in sorted(node_label_by_id.items(), key=lambda item: len(item[0]), reverse=True):
            if node_id != label:
                reasoning_chain = [text.replace(node_id, label) for text in reasoning_chain]

        return MultiHopSummary(
            center_node_id=center_uid,
            total_dependencies=len(direct_prereqs) + len(transitive_prereqs),
            max_depth_found=max_depth,
            dependency_paths=dependency_paths,
            direct_prerequisites=direct_prereqs,
            transitive_prerequisites=transitive_prereqs,
            reasoning_chain=reasoning_chain,
        )

    async def _collect_sources(
        self,
        center: GraphNode,
        exercises: list[GraphNode],
        document_chunks: list[GraphNode],
        code_cases: list[GraphNode],
        misconceptions: list[GraphNode] | None = None,
    ) -> list[GraphNode]:
        seen: dict[str, GraphNode] = {}
        for node in [center, *exercises, *document_chunks, *code_cases, *(misconceptions or [])]:
            try:
                for source in await self.graph_store.get_sources_for_entity(node.uid, limit=self.policy.max_sources):
                    seen[source.uid] = source
            except Exception:
                continue
        return list(seen.values())

    def _ranking_reason(
        self,
        profile: StudentProfileInput,
        exercises: list[GraphNode],
        document_chunks: list[GraphNode],
    ) -> list[str]:
        reasons = ["使用 Neo4j 图谱中的知识关系、资源关系和来源关系构建证据包。"]
        if profile.weak_points:
            reasons.append("根据学生画像中的薄弱点，对练习题和相关证据进行优先排序。")
        if not document_chunks:
            reasons.append("当前文档证据数量较少，演示阶段会更多依赖题目、前置链和来源链。")
        elif document_chunks:
            reasons.append("已纳入资料支撑文档，作为知识解释证据。")
        if exercises:
            reasons.append("已纳入测评题目，用于诊断和练习推荐。")
        return reasons

    def _classify_query(self, query: str) -> str:
        """根据查询文本推断查询类型。"""
        q = query.lower()
        if any(k in q for k in ["为什么", "是什么", "概念", "原理", "解释", "定义", "什么是", "讲讲"]):
            return "concept_explanation"
        if any(k in q for k in ["题", "练习", "作业", "怎么做", "怎么解", "答题", "做一", "做题"]):
            return "exercise_help"
        if any(k in q for k in ["路径", "计划", "学习路线", "怎么学", "步骤", "顺序", "学什么"]):
            return "path_plan"
        if any(k in q for k in ["评估", "复习", "测试", "检验", "考核", "诊断"]):
            return "assessment_review"
        return "general"

    def _compute_score(
        self,
        center: GraphNode,
        prerequisites: list,
        related_nodes: list,
        exercises: list[GraphNode],
        document_chunks: list[GraphNode],
        code_cases: list[GraphNode],
        misconceptions: list[GraphNode],
    ) -> tuple[float, CoverageStats, EvidenceCompleteness, float]:
        """计算证据包质量评分，返回 (质量分, 覆盖统计, 完整性, 资源多样性)。"""
        coverage = CoverageStats(
            exercises_count=len(exercises),
            document_chunks_count=len(document_chunks),
            code_cases_count=len(code_cases),
            misconceptions_count=len(misconceptions),
            prerequisites_count=len(prerequisites),
            related_nodes_count=len(related_nodes),
        )

        # 计算完整性
        completeness = EvidenceCompleteness(
            has_document=bool(document_chunks),
            has_code_case=bool(code_cases),
            has_exercises=bool(exercises),
            has_misconceptions=bool(misconceptions),
            has_prerequisites=bool(prerequisites),
        )
        completeness_score = sum([
            completeness.has_document,
            completeness.has_code_case,
            completeness.has_exercises,
            completeness.has_misconceptions,
            completeness.has_prerequisites,
        ]) / 5.0
        completeness.completeness_score = round(completeness_score, 3)
        missing = []
        if not document_chunks:
            missing.append("文档证据")
        if not code_cases:
            missing.append("代码案例")
        if not exercises:
            missing.append("练习题")
        if not misconceptions:
            missing.append("常见误区")
        if not prerequisites:
            missing.append("前置知识")
        completeness.missing_categories = missing

        # 计算资源多样性 (0-1)
        resource_diversity = 0.0
        if document_chunks:
            resource_diversity += 0.25
        if code_cases:
            resource_diversity += 0.25
        if exercises:
            resource_diversity += 0.25
        if misconceptions:
            resource_diversity += 0.25
        resource_diversity = round(resource_diversity, 3)

        # 计算总体质量评分 (0-1)
        score = 0.0
        if center:
            score += 0.2
        score += min(0.25, len(document_chunks) * 0.08)
        score += min(0.20, len(exercises) * 0.05)
        score += min(0.15, len(code_cases) * 0.08)
        score += min(0.10, len(misconceptions) * 0.05)
        score += min(0.10, len(prerequisites) * 0.03)
        score = round(score, 3)

        return score, coverage, completeness, resource_diversity

    def _summarize_relations(
        self,
        center: GraphNode,
        prerequisites: list[GraphPath],
        related_nodes: list[GraphPath],
    ) -> list[str]:
        """生成关键关系摘要。"""
        summaries = []
        center_name = center.properties.get("name") or center.uid
        if center:
            summaries.append(f"【{center_name}】是当前查询的核心知识点。")
        if prerequisites:
            names = [p.nodes[-1].properties.get("name") or p.nodes[-1].uid for p in prerequisites[:3]]
            summaries.append(f"其前置知识包括：{', '.join(names)}，掌握前置有助于理解当前内容。")
        if related_nodes:
            names = [r.nodes[-1].properties.get("name") or r.nodes[-1].uid for r in related_nodes[:3]]
            summaries.append(f"与当前内容紧密相关的知识点有：{', '.join(names)}。")
        if not summaries:
            summaries.append("当前证据包关系较少，建议补充文档或前置知识边。")
        return summaries

    def _recommend_actions(
        self,
        center: GraphNode,
        exercises: list[GraphNode],
        document_chunks: list[GraphNode],
        code_cases: list[GraphNode],
        missing: list[str],
        profile: StudentProfileInput,
    ) -> list[str]:
        """生成推荐的下一步学习动作。"""
        actions = []
        center_name = (center.properties.get("name") or center.uid) if center else "当前知识点"
        if document_chunks:
            actions.append(f"阅读「{center_name}」的讲解文档，建立概念基础")
        if code_cases:
            actions.append(f"通过代码案例实践「{center_name}」，加深理解")
        if exercises:
            actions.append(f"完成「{center_name}」相关练习题，检验掌握程度")
        if "常见误区" not in missing:
            actions.append(f"了解「{center_name}」的常见误区，避免思维陷阱")
        if profile.weak_points and any(center_name in wp for wp in profile.weak_points):
            actions.append("针对你的薄弱点，建议先看前置知识再进入当前内容")
        if not actions:
            actions.append(f"建议先补充「{center_name}」相关学习资源，再进行练习")
        return actions

    def _compute_relevance(
        self,
        query: str,
        center: GraphNode,
        document_chunks: list[GraphNode],
        code_cases: list[GraphNode],
        exercises: list[GraphNode],
    ) -> float:
        """计算查询与证据包的相关性评分 (0-1)。"""
        q = query.lower()
        query_type = self._classify_query(query)
        score = 0.5  # 基础分

        # 根据查询类型加权
        if query_type == "concept_explanation":
            if document_chunks:
                score += 0.3
            if center:
                score += 0.2
        elif query_type == "exercise_help":
            if exercises:
                score += 0.3
            if document_chunks:
                score += 0.1
        elif query_type == "path_plan":
            if center:
                score += 0.2
            score += 0.1  # 路径规划主要依赖图谱结构
        else:
            # general 或其他
            if document_chunks or code_cases:
                score += 0.2
            if exercises:
                score += 0.1

        return min(1.0, round(score, 3))
