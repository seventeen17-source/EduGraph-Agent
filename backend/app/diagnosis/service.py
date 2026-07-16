from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.labels import choose_node_label, localize_text
from app.core.logging import log_business_metric
from app.diagnosis.schemas import (
    DiagnosisRecommendResponse,
    RecommendationEvidence,
    RecommendationItem,
)
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.schemas import StudentProfileInput
from app.profile.repository import ProfileRepository
from app.profile.schemas import ForgettingNode, KnowledgePointMastery
from app.profile.timeline import ForgettingDetector

if TYPE_CHECKING:
    from app.exercises.repository import ExerciseRepository

logger = logging.getLogger(__name__)


class DiagnosisService:
    """Recommends knowledge nodes for a student based on weak points, mastery, prerequisites, and profile."""

    def __init__(
        self,
        graph_store: Neo4jGraphStore,
        profile_repository: ProfileRepository | None = None,
        exercise_repository: ExerciseRepository | None = None,
    ) -> None:
        self.graph_store = graph_store
        self.profile_repository = profile_repository
        self.exercise_repository = exercise_repository

    async def recommend(
        self,
        student_profile: StudentProfileInput,
        top_k: int = 5,
        node_mastery: dict[str, dict] | None = None,
        student_id: str | None = None,
        target_goal: str | None = None,
    ) -> DiagnosisRecommendResponse:
        mastery = node_mastery or {}
        profile_mastery = student_profile.mastery or {}
        reason_lines: list[str] = []
        priority: dict[str, float] = {}
        # 多目标支持：target_goal 优先于 student_profile.goal
        effective_goal = target_goal or student_profile.goal

        # 0. Gather supplementary data (mastery, mistakes, forgetting) for evidence
        mastery_info: dict[str, dict] = {}  # uid -> {mastery_score, confidence, last_practiced_at, node_name}
        for uid, m in mastery.items():
            if isinstance(m, dict):
                mastery_info[uid] = {
                    "mastery_score": m.get("mastery_score", 1.0),
                    "confidence": m.get("confidence", 0.0),
                    "last_practiced_at": m.get("last_practiced_at"),
                    "node_name": m.get("node_name", ""),
                }

        recent_mistakes: list[dict] = []  # [{related_node, created_at, exercise_title}]

        if student_id and self.profile_repository is not None:
            try:
                profile = await self.profile_repository.get_profile(student_id)
                if profile is not None:
                    for uid, km in profile.node_mastery.items():
                        mastery_info.setdefault(uid, {
                            "mastery_score": km.mastery_score,
                            "confidence": km.confidence,
                            "last_practiced_at": km.last_practiced_at.isoformat() if km.last_practiced_at else None,
                            "node_name": choose_node_label(km.node_name, uid),
                        })
            except Exception as exc:
                logger.debug("Failed to load profile for diagnosis evidence: %s", exc)

        if student_id and self.exercise_repository is not None:
            try:
                _, mistake_records = await self.exercise_repository.list_mistakes(student_id, limit=50)
                recent_mistakes = [
                    {
                        "related_node": r.related_node_id,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "exercise_title": r.exercise_title,
                    }
                    for r in mistake_records
                    if r.related_node_id
                ]
            except Exception as exc:
                logger.debug("Failed to load recent mistakes for diagnosis evidence: %s", exc)

        forgetting_nodes = self._detect_forgetting(mastery_info)
        forgetting_node_ids = [fn.node_id for fn in forgetting_nodes]

        # 1. Collect candidate nodes from multiple sources
        candidates: set[str] = set()

        # Source A: explicit weak points from profile
        weak_uids: list[str] = list(dict.fromkeys(student_profile.weak_points))
        candidates.update(weak_uids)

        # Source B: low-mastery nodes (mastery_score < 0.5, confidence > 0.3)
        low_mastery_uids = [
            uid for uid, m in mastery.items()
            if isinstance(m, dict) and m.get("mastery_score", 1.0) < 0.5
            and m.get("confidence", 0) > 0.3
        ]
        if not low_mastery_uids and profile_mastery:
            low_mastery_uids = [
                uid for uid, score in profile_mastery.items()
                if isinstance(score, (int, float)) and score < 0.5
            ]
        candidates.update(low_mastery_uids)

        # Source C: in-progress nodes from profile
        in_progress_nodes: list[str] = []
        if hasattr(student_profile, "in_progress_nodes"):
            in_progress_nodes = list(getattr(student_profile, "in_progress_nodes", []) or [])
            candidates.update(in_progress_nodes)

        # Source D: learning goal semantic-ish graph search.
        goal_candidate_uids: list[str] = []
        if effective_goal:
            try:
                goal_nodes = await self.graph_store.search_knowledge_points(effective_goal, limit=5)
                goal_candidate_uids = [node.uid for node in goal_nodes]
                candidates.update(goal_candidate_uids)
            except Exception:
                pass

        if not candidates:
            reason_lines.append("未发现明确薄弱点或低掌握度节点。建议先完成画像对话或做一次诊断练习，系统将根据练习结果自动识别薄弱点。")
            return DiagnosisRecommendResponse(
                recommended_nodes=[],
                recommended_exercises=[],
                reasoning=reason_lines,
                node_priorities={},
                sorted_by_prerequisites=False,
                recommendations=[],
                current_node_id=None,
            )

        # 2. Expand: fetch prerequisites for each candidate (depth=1)
        #    Collect node properties (name/chapter/difficulty) and prerequisite edges.
        all_nodes: set[str] = set()
        node_props_map: dict[str, dict] = {}  # uid -> properties dict from Neo4j
        prerequisites_map: dict[str, list[str]] = {}  # uid -> [prerequisite_uids]
        for uid in candidates:
            all_nodes.add(uid)
            try:
                prereqs = await self.graph_store.get_prerequisites(uid, depth=1, limit=3)
                for path in prereqs:
                    for node in path.nodes:
                        if node.uid and node.uid not in node_props_map:
                            node_props_map[node.uid] = node.properties
                        if node.uid != uid:
                            all_nodes.add(node.uid)
                    for rel in path.relationships:
                        if rel.type == "PREREQUISITE":
                            src, tgt = rel.source_uid, rel.target_uid
                            if tgt == uid:
                                prerequisites_map.setdefault(uid, [])
                                if src not in prerequisites_map[uid]:
                                    prerequisites_map[uid].append(src)
            except Exception:
                pass  # single node fetch failure should not block the whole diagnosis

        # Populate node names from mastery_info where graph properties are missing
        for uid, info in mastery_info.items():
            if info.get("node_name") and uid not in node_props_map:
                node_props_map.setdefault(uid, {"name": info["node_name"]})

        # 3. Calculate priority score for each node (higher = more urgent)
        for uid in all_nodes:
            score = 0.0
            # explicit weak point = highest priority
            if uid in weak_uids:
                score += 0.5
            # low mastery = proportional priority
            if uid in mastery:
                m = mastery[uid]
                if isinstance(m, dict):
                    mastery_score = m.get("mastery_score", 1.0)
                    score += max(0, 0.3 * (1.0 - mastery_score))  # lower mastery → higher score
            elif uid in profile_mastery:
                mastery_score = profile_mastery.get(uid, 1.0)
                if isinstance(mastery_score, (int, float)):
                    score += max(0, 0.3 * (1.0 - mastery_score))
            if uid in goal_candidate_uids:
                score += 0.25
            # prerequisite of weak point = medium priority
            if uid not in weak_uids:
                score += 0.1
            priority[uid] = round(score, 3)

        # 4. Topological sort by prerequisite edges
        sorted_nodes = await self._topo_sort(list(all_nodes))
        sorted_by_prerequisites = len(sorted_nodes) > 1

        # 5. Reorder by priority within topological constraints:
        # Keep topo order, but promote high-priority nodes within each topo level
        recommended = self._priority_aware_sort(sorted_nodes, priority, top_k)

        # 6. Fetch exercises
        exercise_ids: list[str] = []
        for uid in recommended:
            try:
                exercises = await self.graph_store.get_exercises_for_node(uid, limit=2)
                exercise_ids.extend(ex.uid for ex in exercises)
            except Exception:
                pass
        exercise_ids = list(dict.fromkeys(exercise_ids))[:top_k]

        # 7. Build reasoning
        if weak_uids:
            reason_lines.append(
                f"检测到 {len(weak_uids)} 个画像薄弱点：{'、'.join(weak_uids[:3])}{'等' if len(weak_uids) > 3 else ''}，优先处理。"
            )
        if low_mastery_uids:
            new_low = [u for u in low_mastery_uids if u not in weak_uids]
            if new_low:
                reason_lines.append(
                    f"发现 {len(new_low)} 个掌握度偏低的节点（mastery < 0.5）：{'、'.join(new_low[:3])}{'等' if len(new_low) > 3 else ''}，建议回顾。"
                )
        if goal_candidate_uids:
            reason_lines.append(
                f"已根据学习目标补充 {len(goal_candidate_uids)} 个候选知识点，避免在暂无错题时生成空路径。"
            )
        if sorted_by_prerequisites:
            reason_lines.append("已按知识图谱前置依赖关系进行拓扑排序，确保先学前置、再学核心。")
        if len(all_nodes) > len(candidates):
            reason_lines.append(f"已自动补齐 {len(all_nodes) - len(candidates)} 个前置知识节点，确保学习路径可执行。")
        if recommended:
            reason_lines.append(f"共推荐 {len(recommended)} 个学习节点，顶部为重点推荐。")
        if exercise_ids:
            reason_lines.append(f"已匹配 {len(exercise_ids)} 道练习题，可用于掌握度诊断。")

        # 8. Build per-node recommendation items with type/reason/score/evidence
        goal_candidate_set = set(goal_candidate_uids)
        recommendations: list[RecommendationItem] = []
        for uid in recommended:
            node_name = self._get_node_name(uid, node_props_map, mastery_info)
            node_props = node_props_map.get(uid, {})

            rec_type = self._classify_recommendation_type(
                uid, weak_uids, mastery_info, forgetting_node_ids,
                recent_mistakes, effective_goal or "",
                prerequisites_map, goal_candidate_set,
            )
            mastery_score_val = mastery_info.get(uid, {}).get("mastery_score")
            if mastery_score_val is None and uid in profile_mastery:
                mastery_score_val = profile_mastery.get(uid)
            evidence = self._gather_evidence(uid, mastery_info, recent_mistakes, student_id or "")
            score = self._compute_score(rec_type, mastery_score_val, weak_uids, forgetting_node_ids)
            reason = self._build_reason(rec_type, node_name, evidence, effective_goal or "")

            recommendations.append(RecommendationItem(
                node_id=uid,
                node_name=node_name,
                recommendation_type=rec_type,
                reason=reason,
                score=round(score, 3),
                evidence=evidence,
                prerequisites=prerequisites_map.get(uid, []),
                difficulty=str(node_props.get("difficulty")) if node_props.get("difficulty") is not None else None,
                chapter=node_props.get("chapter"),
            ))

        # 9. Determine current_node_id (SubTask 3.6)
        current_node_id = self._determine_current_node(
            recommended, in_progress_nodes, student_id or "",
        )

        # 业务指标：推荐数量
        log_business_metric(
            "diagnosis_recommendation_count",
            len(recommended),
            student_id=student_id or "",
            target_goal=target_goal or "",
        )

        return DiagnosisRecommendResponse(
            recommended_nodes=recommended,
            recommended_exercises=exercise_ids,
            reasoning=reason_lines,
            node_priorities={uid: priority.get(uid, 0) for uid in recommended},
            sorted_by_prerequisites=sorted_by_prerequisites,
            recommendations=recommendations,
            current_node_id=current_node_id,
        )

    # ── 拓扑排序（保留原有逻辑） ──

    async def _topo_sort(self, nodes: list[str]) -> list[str]:
        """Kahn topological sort based on PREREQUISITE edges from Neo4j."""
        if len(nodes) <= 1:
            return nodes

        node_set = set(nodes)
        in_degree: dict[str, int] = {uid: 0 for uid in nodes}
        adj: dict[str, list[str]] = {uid: [] for uid in nodes}

        # Fetch prerequisite edges by querying subgraph for each node
        for uid in nodes:
            try:
                prereqs = await self.graph_store.get_prerequisites(uid, depth=1, limit=10)
                for path in prereqs:
                    for rel in path.relationships:
                        if rel.type == "PREREQUISITE":
                            src, tgt = rel.source_uid, rel.target_uid
                            if src in node_set and tgt in node_set:
                                adj.setdefault(src, []).append(tgt)
                                in_degree[tgt] = in_degree.get(tgt, 0) + 1
            except Exception:
                pass

        # Kahn's algorithm
        queue = deque([uid for uid in nodes if in_degree.get(uid, 0) == 0])
        result: list[str] = []
        while queue:
            n = queue.popleft()
            result.append(n)
            for tgt in adj.get(n, []):
                in_degree[tgt] -= 1
                if in_degree[tgt] == 0:
                    queue.append(tgt)

        # Append any remaining nodes
        for n in nodes:
            if n not in result:
                result.append(n)

        return result

    def _priority_aware_sort(
        self, topo_sorted: list[str], priority: dict[str, float], top_k: int
    ) -> list[str]:
        """Within each topological level, promote high-priority nodes."""
        # Simple approach: sort by descending priority, but keep topo order as tiebreaker
        indexed = [(i, uid) for i, uid in enumerate(topo_sorted)]
        # Sort by -priority (descending), then by topo index (ascending)
        indexed.sort(key=lambda x: (-priority.get(x[1], 0), x[0]))
        return [uid for _, uid in indexed[:top_k]]

    # ── 逐节点解释辅助方法 ──

    def _detect_forgetting(self, mastery_info: dict[str, dict]) -> list[ForgettingNode]:
        """基于掌握度和上次复习时间检测即将遗忘的知识点。"""
        detector = ForgettingDetector()
        mastery_objs: dict[str, KnowledgePointMastery] = {}
        for uid, info in mastery_info.items():
            last_practiced = info.get("last_practiced_at")
            if isinstance(last_practiced, str):
                try:
                    last_practiced = datetime.fromisoformat(last_practiced)
                except Exception:
                    last_practiced = None
            mastery_objs[uid] = KnowledgePointMastery(
                node_id=uid,
                node_name=choose_node_label(info.get("node_name"), uid),
                mastery_score=info.get("mastery_score", 0.0),
                confidence=info.get("confidence", 0.0),
                last_practiced_at=last_practiced,  # type: ignore[arg-type]
            )
        return detector.detect(mastery_objs)

    def _get_node_name(
        self, uid: str, node_props_map: dict[str, dict], mastery_info: dict[str, dict],
    ) -> str:
        """从图谱属性或掌握度数据中获取节点名称。"""
        props = node_props_map.get(uid, {})
        name = props.get("name") or props.get("title")
        if name:
            return choose_node_label(name, uid)
        info = mastery_info.get(uid, {})
        if info.get("node_name"):
            return choose_node_label(info["node_name"], uid)
        return choose_node_label(None, uid)

    def _classify_recommendation_type(
        self,
        node_id: str,
        weak_points: list,
        mastery: dict,
        forgetting_nodes: list,
        recent_mistakes: list,
        goal: str,
        prerequisites_map: dict,
        goal_candidate_uids: set[str] | None = None,
    ) -> str:
        """判断推荐类型。"""
        if node_id in weak_points:
            return "weak_point"
        if node_id in forgetting_nodes:
            return "forgetting_review"
        if any(node_id in prereqs for prereqs in prerequisites_map.values()):
            return "prerequisite"
        if goal and self._is_goal_related(node_id, goal, goal_candidate_uids):
            return "goal_related"
        if any(mistake.get("related_node") == node_id for mistake in recent_mistakes):
            return "mistake_related"
        return "goal_related"  # 默认

    def _is_goal_related(
        self, node_id: str, goal: str, goal_candidate_uids: set[str] | None = None,
    ) -> bool:
        """判断节点是否与学习目标相关。"""
        if goal_candidate_uids and node_id in goal_candidate_uids:
            return True
        if goal and node_id:
            node_lower = node_id.lower()
            goal_lower = goal.lower()
            if node_lower in goal_lower or goal_lower in node_lower:
                return True
        return False

    def _build_reason(
        self,
        rec_type: str,
        node_name: str,
        evidence: RecommendationEvidence | None,
        goal: str = "",
    ) -> str:
        """根据推荐类型和证据生成自然语言理由。"""
        mastery_val = evidence.mastery if evidence else None
        if rec_type == "weak_point":
            rate = int((mastery_val or 0) * 100)
            return localize_text(f"你在最近的练习中{node_name}正确率仅{rate}%，建议优先巩固")
        elif rec_type == "prerequisite":
            return localize_text(f"学习后续内容前需要先掌握{node_name}")
        elif rec_type == "goal_related":
            return localize_text(f"这与你的学习目标'{goal}'直接相关")
        elif rec_type == "forgetting_review":
            return localize_text(f"你上次学习{node_name}已有一段时间，建议复习以防遗忘")
        elif rec_type == "mistake_related":
            return localize_text(f"你最近做错的题目涉及{node_name}知识点")
        return localize_text(f"建议学习{node_name}")

    def _compute_score(
        self,
        rec_type: str,
        mastery: float | None,
        weak_points: list,
        forgetting_nodes: list,
    ) -> float:
        """计算推荐优先级分数 0-1。"""
        if rec_type == "weak_point":
            return 0.9 - (mastery or 0.5) * 0.3  # mastery越低分越高
        elif rec_type == "forgetting_review":
            return 0.7
        elif rec_type == "prerequisite":
            return 0.6
        elif rec_type == "mistake_related":
            return 0.75
        return 0.5

    def _gather_evidence(
        self,
        node_id: str,
        mastery: dict,
        recent_attempts: list,
        student_id: str,
    ) -> RecommendationEvidence | None:
        """收集推荐节点的证据。"""
        node_mastery = mastery.get(node_id)
        mastery_score: float | None = None
        last_attempt: str | None = None

        if node_mastery is not None:
            if isinstance(node_mastery, dict):
                mastery_score = node_mastery.get("mastery_score")
            elif isinstance(node_mastery, (int, float)):
                mastery_score = float(node_mastery)

        # 从最近练习中查找该节点的最后一次作答时间
        for attempt in recent_attempts:
            if attempt.get("related_node") == node_id:
                last_attempt = attempt.get("created_at")
                break

        if mastery_score is not None:
            source = "exercise_result"
            detail = f"当前掌握度: {mastery_score:.0%}"
            return RecommendationEvidence(
                source=source,
                detail=detail,
                mastery=mastery_score,
                last_attempt=last_attempt,
            )
        if last_attempt is not None:
            return RecommendationEvidence(
                source="mistake_history",
                detail="最近做错过该知识点的题目",
                mastery=None,
                last_attempt=last_attempt,
            )
        return None

    def _determine_current_node(
        self,
        recommended: list[str],
        in_progress_nodes: list[str],
        student_id: str,
    ) -> str | None:
        """SubTask 3.6: 当当前建议为空时（没有进行中的节点），从推荐队列取第一项补入。"""
        if in_progress_nodes:
            # 已有进行中的节点，优先返回在推荐队列中的进行中节点
            for node_id in in_progress_nodes:
                if node_id in recommended:
                    return node_id
            return in_progress_nodes[0]
        # 无进行中节点，从推荐队列取首项作为当前建议
        if recommended:
            return recommended[0]
        return None
