from app.graph.models import GraphNode


def rank_nodes_by_profile(
    nodes: list[GraphNode],
    weak_points: list[str],
    *,
    mastery: dict[str, float] | None = None,
    preferences: list[str] | None = None,
) -> list[GraphNode]:
    weak = set(weak_points or [])
    mastery = mastery or {}
    preferences = preferences or []

    def related_node_ids(node: GraphNode) -> set[str]:
        related = set()
        for key in ("assesses", "also_assesses", "prerequisite_node_ids", "related_node_id", "node_ids"):
            raw = node.properties.get(key, [])
            if isinstance(raw, list):
                related.update(str(item) for item in raw)
            elif raw:
                related.add(str(raw))
        return related

    def score(node: GraphNode) -> tuple[float, str]:
        value = 0.0
        related = related_node_ids(node)
        if node.uid in weak:
            value += 1.0
        if related.intersection(weak):
            value += 0.55
        for uid in related:
            mastery_score = mastery.get(uid)
            if isinstance(mastery_score, (int, float)) and mastery_score < 0.6:
                value += 0.35 * (1.0 - mastery_score)
        node_type = str(node.properties.get("type") or node.properties.get("resource_type") or "")
        if "exercise" in preferences and node.labels and "Exercise" in node.labels:
            value += 0.15
        if "code_case" in preferences and ("code" in node_type.lower() or "CodeCase" in node.labels):
            value += 0.15
        return (-value, node.uid)

    return sorted(nodes, key=score)
