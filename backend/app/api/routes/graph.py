from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.errors import NotFoundError
from app.graph.expansion_policy import GraphExpansionPolicy
from app.graph.models import GraphNode, SubgraphResult
from app.graph.neo4j_store import Neo4jGraphStore
from app.api.deps import get_graph_store

router = APIRouter()


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
