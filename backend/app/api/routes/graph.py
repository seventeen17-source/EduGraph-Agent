from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.errors import NotFoundError
from app.graph.expansion_policy import GraphExpansionPolicy
from app.graph.models import GraphNode, SubgraphResult
from app.graph.neo4j_store import Neo4jGraphStore
from app.api.deps import get_graph_store, get_profile_service
from app.profile.service import ProfileService
from app.profile.timeline import ForgettingDetector

router = APIRouter()


# ── 节点决策面板响应模型 ──


class NodeDetailNode(BaseModel):
    uid: str
    name: str
    type: str
    chapter: str
    difficulty: str


class NodeDetailMastery(BaseModel):
    value: float
    trend: str
    last_attempt: str | None


class NodeDetailWeakStatus(BaseModel):
    is_weak: bool
    reason: str


class NodeDetailForgettingRisk(BaseModel):
    level: str
    days_since_last: int | None
    suggested_review_date: str | None


class NodeDetailRecommendation(BaseModel):
    action: str
    reason: str


class NodeDetailPrerequisite(BaseModel):
    uid: str
    name: str
    weight: float
    explanation: str
    mastered: bool


class NodeDetailNextNode(BaseModel):
    uid: str
    name: str
    weight: float
    explanation: str


class NodeDetailResponse(BaseModel):
    node: NodeDetailNode
    mastery: NodeDetailMastery
    weak_status: NodeDetailWeakStatus
    forgetting_risk: NodeDetailForgettingRisk
    recommendation: NodeDetailRecommendation
    prerequisites: list[NodeDetailPrerequisite]
    next_nodes: list[NodeDetailNextNode]


class NodeWithMastery(BaseModel):
    uid: str
    name: str
    chapter: str
    difficulty: str
    summary: str
    mastery_score: float
    status: str  # mastered | weak | forgetting | learning | unlearned
    last_practiced: str | None


class LearningOverviewResponse(BaseModel):
    total_nodes: int
    mastered: int
    weak: int
    forgetting: int
    learning: int
    unlearned: int
    mastery_rate: float
    nodes: list[NodeWithMastery]


class RecommendedStartResponse(BaseModel):
    uid: str
    name: str
    reason: str
    status: str


@router.get("/node/{uid}", response_model=GraphNode)
async def get_node(
    uid: str,
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
) -> GraphNode:
    node = await graph_store.get_node(uid)
    if node is None:
        raise NotFoundError(f"Graph node not found: {uid}")
    return node


@router.get("/all", response_model=list[GraphNode])
async def get_all_nodes(
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    limit: int = Query(default=200, ge=1, le=500),
) -> list[GraphNode]:
    return await graph_store.get_all_nodes(limit=limit)


@router.get("/search", response_model=list[GraphNode])
async def search_nodes(
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[GraphNode]:
    return await graph_store.search_knowledge_points(q, limit=limit)


@router.get("/subgraph/{uid}", response_model=SubgraphResult)
async def get_subgraph(
    uid: str,
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    depth: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=80, ge=1, le=200),
    relations: list[str] | None = Query(default=None),
) -> SubgraphResult:
    policy = GraphExpansionPolicy(depth=depth, max_subgraph_items=limit)
    relation_types = relations or policy.graphrag_relations
    return await graph_store.get_subgraph(
        uid=uid,
        relation_types=relation_types,
        depth=depth,
        limit=limit,
    )


@router.get("/node-labels", response_model=dict[str, str])
async def get_node_labels() -> dict[str, str]:
    from app.assistant.tools import AssistantTools
    return AssistantTools._get_node_label_map()  # type: ignore


@router.get("/node-detail/{uid}", response_model=NodeDetailResponse)
async def get_node_detail(
    uid: str,
    student_id: Annotated[str, Query(description="学生 ID")],
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> NodeDetailResponse:
    """返回节点详情 + 掌握度 + 遗忘风险 + 前置关系 + 推荐决策。"""
    # 1. 获取节点基本信息（Neo4j）
    node_info = await graph_store.get_node_with_mastery(uid, student_id)
    if node_info is None:
        raise NotFoundError(f"Graph node not found: {uid}")

    # 2. 获取掌握度数据（SQLite）
    mastery_value = 0.0
    mastery_trend = "unknown"
    last_attempt_str: str | None = None
    last_attempt_dt = None
    attempts = 0
    correct_count = 0
    node_mastery_map: dict = {}

    try:
        profile = await profile_service.get_profile(student_id)
        node_mastery_map = profile.node_mastery
        node_mastery = node_mastery_map.get(uid)
        if node_mastery is not None:
            mastery_value = node_mastery.mastery_score
            last_attempt_dt = node_mastery.last_practiced_at
            attempts = node_mastery.attempts
            correct_count = node_mastery.correct_count
            if attempts > 0:
                if mastery_value >= 0.6:
                    mastery_trend = "improving"
                elif mastery_value < 0.4:
                    mastery_trend = "declining"
                else:
                    mastery_trend = "stable"
            if last_attempt_dt is not None:
                last_attempt_str = last_attempt_dt.strftime("%Y-%m-%d")
    except NotFoundError:
        pass  # 画像不存在，使用默认值

    # 3. 获取边信息（前置/后续/相关）
    edges = await graph_store.get_edges_with_weight(uid, direction="both")

    # 4. 拆分为前置和后续，并补充前置的 mastered 状态
    prerequisites: list[NodeDetailPrerequisite] = []
    next_nodes: list[NodeDetailNextNode] = []
    has_unmastered_prereq = False

    for edge in edges:
        if edge["direction"] == "prerequisite":
            pre_mastery = node_mastery_map.get(edge["uid"])
            pre_mastered = pre_mastery is not None and pre_mastery.mastery_score >= 0.6
            if not pre_mastered:
                has_unmastered_prereq = True
            prerequisites.append(NodeDetailPrerequisite(
                uid=edge["uid"],
                name=edge["name"],
                weight=edge["weight"],
                explanation=edge["explanation"],
                mastered=pre_mastered,
            ))
        elif edge["direction"] == "next":
            next_nodes.append(NodeDetailNextNode(
                uid=edge["uid"],
                name=edge["name"],
                weight=edge["weight"],
                explanation=edge["explanation"],
            ))

    # 5. 评估遗忘风险
    detector = ForgettingDetector()
    risk = detector.assess_node_risk(uid, mastery_value, last_attempt_dt)

    # 6. 计算薄弱状态
    is_weak = mastery_value < 0.4
    if is_weak:
        if attempts > 0:
            correct_rate = correct_count / attempts
            weak_reason = f"最近练习正确率仅{int(correct_rate * 100)}%"
        else:
            weak_reason = "掌握度较低，建议加强学习"
    else:
        weak_reason = "掌握度良好"

    # 7. 计算推荐决策
    if risk["level"] == "high":
        action = "review"
        reason = "遗忘风险较高，建议及时复习"
    elif mastery_value >= 0.8:
        action = "skip"
        reason = "已掌握，可跳过"
    elif mastery_value < 0.4:
        if has_unmastered_prereq:
            action = "learn_prerequisites_first"
            reason = "掌握度较低且存在未掌握的前置知识"
        else:
            action = "recommend_now"
            reason = "掌握度较低，前置知识已就绪"
    else:
        action = "recommend_now"
        reason = "推荐现在学习"

    return NodeDetailResponse(
        node=NodeDetailNode(**node_info),
        mastery=NodeDetailMastery(
            value=mastery_value,
            trend=mastery_trend,
            last_attempt=last_attempt_str,
        ),
        weak_status=NodeDetailWeakStatus(is_weak=is_weak, reason=weak_reason),
        forgetting_risk=NodeDetailForgettingRisk(**risk),
        recommendation=NodeDetailRecommendation(action=action, reason=reason),
        prerequisites=prerequisites,
        next_nodes=next_nodes,
    )


@router.get("/learning-overview", response_model=LearningOverviewResponse)
async def get_learning_overview(
    student_id: Annotated[str, Query(description="学生 ID")],
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> LearningOverviewResponse:
    """返回学生的全局学习进度概览。"""
    nodes = await graph_store.get_all_nodes_with_mastery(student_id, profile_service)
    
    counts = {"mastered": 0, "weak": 0, "forgetting": 0, "learning": 0, "unlearned": 0}
    for n in nodes:
        counts[n["status"]] = counts.get(n["status"], 0) + 1
    
    total = len(nodes)
    mastery_rate = round(counts["mastered"] / total, 2) if total > 0 else 0.0
    
    return LearningOverviewResponse(
        total_nodes=total,
        mastered=counts["mastered"],
        weak=counts["weak"],
        forgetting=counts["forgetting"],
        learning=counts["learning"],
        unlearned=counts["unlearned"],
        mastery_rate=mastery_rate,
        nodes=[NodeWithMastery(**n) for n in nodes],
    )


@router.get("/recommended-start", response_model=RecommendedStartResponse)
async def get_recommended_start(
    student_id: Annotated[str, Query(description="学生 ID")],
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> RecommendedStartResponse:
    """根据画像返回推荐起始节点。优先级：遗忘风险 > 薄弱 > 学习路径 > 第一个节点。"""
    nodes = await graph_store.get_all_nodes_with_mastery(student_id, profile_service)
    
    if not nodes:
        raise NotFoundError("No knowledge points found")
    
    # 优先遗忘风险
    forgetting = [n for n in nodes if n["status"] == "forgetting"]
    if forgetting:
        n = forgetting[0]
        return RecommendedStartResponse(
            uid=n["uid"], name=n["name"],
            reason=f"{n['name']} 已 {n['last_practiced']} 未复习，遗忘风险较高",
            status="forgetting",
        )
    
    # 其次薄弱
    weak = [n for n in nodes if n["status"] == "weak"]
    if weak:
        n = weak[0]
        return RecommendedStartResponse(
            uid=n["uid"], name=n["name"],
            reason=f"{n['name']} 掌握度仅 {int(n['mastery_score']*100)}%，建议优先加强",
            status="weak",
        )
    
    # 其次学习中
    learning = [n for n in nodes if n["status"] == "learning"]
    if learning:
        n = learning[0]
        return RecommendedStartResponse(
            uid=n["uid"], name=n["name"],
            reason=f"{n['name']} 正在学习中，继续巩固",
            status="learning",
        )
    
    # 默认第一个节点
    n = nodes[0]
    return RecommendedStartResponse(
        uid=n["uid"], name=n["name"],
        reason=f"开始学习 {n['name']}",
        status=n["status"],
    )


@router.get("/all-with-mastery", response_model=list[NodeWithMastery])
async def get_all_nodes_with_mastery(
    student_id: Annotated[str, Query(description="学生 ID")],
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> list[NodeWithMastery]:
    """返回所有节点及其掌握度状态，消除前端 N+1 查询。"""
    nodes = await graph_store.get_all_nodes_with_mastery(student_id, profile_service)
    return [NodeWithMastery(**n) for n in nodes]
