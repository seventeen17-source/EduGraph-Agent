from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.assistant.state import AssistantState
from app.assistant.tools import AssistantTools


def build_assistant_graph(tools: AssistantTools):
    graph = StateGraph(AssistantState)

    # === 基础节点 ===
    graph.add_node("load_context", tools.load_context)
    graph.add_node("retrieve_memory", tools.retrieve_memory)  # 新增：语义记忆检索
    graph.add_node("understand_intent", tools.understand_intent)
    graph.add_node("update_profile", tools.update_profile)
    graph.add_node("record_progress", tools.record_progress)
    graph.add_node("retrieve_evidence", tools.retrieve_evidence)
    graph.add_node("evaluate_evidence", tools.evaluate_evidence)
    graph.add_node("expand_evidence", tools.expand_evidence)
    graph.add_node("generate_resources", tools.generate_resources)
    graph.add_node("reflect_on_resources", tools.reflect_on_resources)
    graph.add_node("explain_exercise", tools.explain_exercise)
    graph.add_node("plan_learning_path", tools.plan_learning_path)
    graph.add_node("review_assessment", tools.review_assessment)
    graph.add_node("general_tutor", tools.general_tutor)
    graph.add_node("compose_response", tools.compose_response)
    graph.add_node("extract_memory", tools.extract_memory)  # 新增：记忆提取写入
    graph.add_node("error_recovery", tools.error_recovery)

    # === 主流程 ===
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "retrieve_memory")           # 加载画像 → 检索记忆
    graph.add_edge("retrieve_memory", "understand_intent")      # 检索记忆 → 意图识别

    # --- 意图路由（含澄清） ---
    graph.add_conditional_edges(
        "understand_intent",
        route_by_intent,
        {
            "profile_update": "update_profile",
            "concept_explain": "retrieve_evidence",
            "resource_generate": "retrieve_evidence",
            "exercise_help": "retrieve_evidence",
            "path_plan": "retrieve_evidence",
            "progress_update": "record_progress",
            "assessment_review": "review_assessment",
            "navigation_help": "compose_response",
            "general_learning_chat": "retrieve_evidence",
            "clarify_intent": "compose_response",  # 意图澄清 → 直接组合回复（包含澄清选项）
            "unavailable": "compose_response",
            "error": "error_recovery",
        },
    )

    # --- 画像更新后直接返回 ---
    graph.add_edge("update_profile", "compose_response")
    graph.add_edge("record_progress", "plan_learning_path")

    # --- 证据检索后 → 评估 → 扩展（如需要）→ 后置路由 ---
    graph.add_edge("retrieve_evidence", "evaluate_evidence")

    graph.add_conditional_edges(
        "evaluate_evidence",
        route_after_evidence_evaluation,
        {
            "expand": "expand_evidence",
            "generate_resources": "generate_resources",
            "explain_exercise": "explain_exercise",
            "plan_learning_path": "plan_learning_path",
            "general_tutor": "general_tutor",
        },
    )

    # 扩展证据后也根据原始意图路由
    graph.add_conditional_edges(
        "expand_evidence",
        route_after_evidence,
        {
            "generate_resources": "generate_resources",
            "explain_exercise": "explain_exercise",
            "plan_learning_path": "plan_learning_path",
            "general_tutor": "general_tutor",
        },
    )

    # --- 资源生成后 → 反思 ---
    graph.add_edge("generate_resources", "reflect_on_resources")
    graph.add_conditional_edges(
        "reflect_on_resources",
        route_after_reflection,
        {
            "improve": "generate_resources",  # 迭代改进（复用 generate_resources）
            "continue": "compose_response",
        },
    )

    # --- 其他节点直接到 compose_response ---
    graph.add_edge("explain_exercise", "compose_response")
    graph.add_edge("plan_learning_path", "compose_response")
    graph.add_edge("review_assessment", "compose_response")
    graph.add_edge("general_tutor", "compose_response")
    graph.add_edge("compose_response", "extract_memory")
    graph.add_edge("extract_memory", END)

    # --- 错误恢复后根据情况路由 ---
    graph.add_conditional_edges(
        "error_recovery",
        route_after_recovery,
        {
            "retry": "load_context",
            "compose": "compose_response",
            "abort": END,
        },
    )

    return graph.compile()


def route_by_intent(state: AssistantState) -> str:
    """根据识别出的意图路由到对应节点。"""
    # 系统状态检查
    if state.get("status") == "unavailable":
        return "unavailable"
    if state.get("errors") and not state.get("intent"):
        return "error"

    # 高优先级：意图置信度低时触发澄清
    if state.get("needs_clarification"):
        return "clarify_intent"

    intent = state.get("intent")
    return intent or "general_learning_chat"


def route_after_evidence_evaluation(state: AssistantState) -> str:
    """证据评估后决定是否需要扩展证据，然后根据意图路由。"""
    # 如果需要扩展证据，进入 expand_evidence
    if state.get("retry_evidence"):
        return "expand"
    # 否则根据原始意图直接路由到处理节点
    return route_after_evidence(state)


def route_after_evidence(state: AssistantState) -> str:
    """证据检索后根据原始意图路由到具体处理节点。"""
    intent = state.get("intent")
    if intent == "resource_generate":
        return "generate_resources"
    if intent == "exercise_help":
        return "explain_exercise"
    if intent == "path_plan":
        return "plan_learning_path"
    return "general_tutor"


def route_after_reflection(state: AssistantState) -> str:
    """反思后决定是否需要改进资源。最多 1 次自动改进。"""
    if state.get("needs_refinement") and state.get("refinement_count", 0) < 1:
        return "improve"
    return "continue"


def route_after_recovery(state: AssistantState) -> str:
    """错误恢复后决定下一步。"""
    recovery_action = state.get("recovery_action")
    if recovery_action == "retry":
        return "retry"
    if recovery_action == "compose":
        return "compose"
    if recovery_action == "abort":
        return "abort"
    return "compose"