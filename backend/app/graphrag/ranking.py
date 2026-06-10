from app.graph.models import GraphNode


def rank_nodes_by_profile(nodes: list[GraphNode], weak_points: list[str]) -> list[GraphNode]:
    def score(node: GraphNode) -> tuple[int, str]:
        value = 0
        if node.uid in weak_points:
            value += 100
        related = set()
        for key in ("assesses", "also_assesses", "prerequisite_node_ids"):
            raw = node.properties.get(key, [])
            if isinstance(raw, list):
                related.update(str(item) for item in raw)
        if related.intersection(weak_points):
            value += 40
        return (-value, node.uid)

    return sorted(nodes, key=score)
