from typing import Annotated

from fastapi import Depends
from neo4j import AsyncDriver

from app.core.config import Settings, get_settings
from app.db.neo4j import get_neo4j_driver
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.service import GraphRAGService


async def get_graph_store(
    driver: Annotated[AsyncDriver, Depends(get_neo4j_driver)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Neo4jGraphStore:
    return Neo4jGraphStore(driver=driver, settings=settings)


async def get_graphrag_service(
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
) -> GraphRAGService:
    return GraphRAGService(graph_store)
