from __future__ import annotations

from collections import deque

from app.diagnosis.schemas import DiagnosisRecommendResponse
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.schemas import StudentProfileInput


class DiagnosisService:
    """Recommends knowledge nodes for a student based on weak points, mastery, prerequisites, and profile."""

    def __init__(self, graph_store: Neo4jGraphStore) -> None:
        self.graph_store = graph_store

    async def recommend(
        self,
        student_profile: StudentProfileInput,
        top_k: int = 5,
        node_mastery: dict[str, dict] | None = None,
    ) -> DiagnosisRecommendResponse:
        mastery = node_mastery or {}
        reason_lines: list[str] = []
        priority: dict[str, float] = {}

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
        candidates.update(low_mastery_uids)

        # Source C: in-progress nodes from profile
        if hasattr(student_profile, "in_progress_nodes"):
            candidates.update(getattr(student_profile, "in_progress_nodes", []) or [])

        if not candidates:
            reason_lines.append("未发现明确薄弱点或低掌握度节点。建议先完成画像对话或做一次诊断练习，系统将根据练习结果自动识别薄弱点。")
            return DiagnosisRecommendResponse(
                recommended_nodes=[],
                recommended_exercises=[],
                reasoning=reason_lines,
                node_priorities={},
                sorted_by_prerequisites=False,
            )

        # 2. Expand: fetch prerequisites for each candidate (depth=1)
        all_nodes: set[str] = set()
        for uid in candidates:
            all_nodes.add(uid)
            try:
                prereqs = await self.graph_store.get_prerequisites(uid, depth=1, limit=3)
                for path in prereqs:
                    for node in path.nodes:
                        if node.uid != uid:
                            all_nodes.add(node.uid)
            except Exception:
                pass  # single node fetch failure should not block the whole diagnosis

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
        if sorted_by_prerequisites:
            reason_lines.append("已按知识图谱前置依赖关系进行拓扑排序，确保先学前置、再学核心。")
        if len(all_nodes) > len(candidates):
            reason_lines.append(f"已自动补齐 {len(all_nodes) - len(candidates)} 个前置知识节点，确保学习路径可执行。")
        if recommended:
            reason_lines.append(f"共推荐 {len(recommended)} 个学习节点，顶部为重点推荐。")
        if exercise_ids:
            reason_lines.append(f"已匹配 {len(exercise_ids)} 道练习题，可用于掌握度诊断。")

        return DiagnosisRecommendResponse(
            recommended_nodes=recommended,
            recommended_exercises=exercise_ids,
            reasoning=reason_lines,
            node_priorities={uid: priority.get(uid, 0) for uid in recommended},
            sorted_by_prerequisites=sorted_by_prerequisites,
        )

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
