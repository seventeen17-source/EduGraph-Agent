from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graphrag.langgraph.nodes import HybridRAGNodes
from app.graphrag.langgraph.state import HybridRAGState


def build_hybrid_rag_graph(nodes: HybridRAGNodes):
    graph = StateGraph(HybridRAGState)

    graph.add_node("prepare_query", nodes.prepare_query)
    graph.add_node("resolve_learning_target", nodes.resolve_learning_target)
    graph.add_node("retrieve_graph_context", nodes.retrieve_graph_context)
    graph.add_node("retrieve_semantic_context", nodes.retrieve_semantic_context)
    graph.add_node("retrieve_memory_context", nodes.retrieve_memory_context)
    graph.add_node("fuse_canonical_evidence", nodes.fuse_canonical_evidence)
    graph.add_node("grade_evidence", nodes.grade_evidence)
    graph.add_node("repair_evidence", nodes.repair_evidence)
    graph.add_node("finalize_evidence", nodes.finalize_evidence)

    graph.set_entry_point("prepare_query")
    graph.add_edge("prepare_query", "resolve_learning_target")
    graph.add_edge("resolve_learning_target", "retrieve_graph_context")
    graph.add_edge("retrieve_graph_context", "retrieve_semantic_context")
    graph.add_edge("retrieve_semantic_context", "retrieve_memory_context")
    graph.add_edge("retrieve_memory_context", "fuse_canonical_evidence")
    graph.add_edge("fuse_canonical_evidence", "grade_evidence")
    graph.add_conditional_edges(
        "grade_evidence",
        route_after_grade,
        {
            "repair": "repair_evidence",
            "finalize": "finalize_evidence",
        },
    )
    graph.add_conditional_edges(
        "repair_evidence",
        route_after_repair,
        {
            "grade": "grade_evidence",
            "finalize": "finalize_evidence",
        },
    )
    graph.add_edge("finalize_evidence", END)

    return graph.compile()


def route_after_grade(state: HybridRAGState) -> str:
    report = state.get("quality_report", {})
    if report.get("enough"):
        return "finalize"
    if state.get("repair_attempts", 0) >= state.get("max_repair_attempts", 2):
        return "finalize"
    if state.get("pending_repair_action") in {"ask_clarification", "finalize_with_warning"}:
        return "finalize"
    return "repair"


def route_after_repair(state: HybridRAGState) -> str:
    if state.get("repair_attempts", 0) >= state.get("max_repair_attempts", 2):
        return "finalize"
    if state.get("pending_repair_action") in {"ask_clarification", "finalize_with_warning"}:
        return "finalize"
    return "grade"
