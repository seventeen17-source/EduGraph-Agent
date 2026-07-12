from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from neo4j import AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.relational import get_db_session
from app.db.neo4j import get_neo4j_driver
from app.agents.repository import ResourceRepository
from app.agents.service import ResourceGenerationService
from app.assistant.memory import AssistantMemoryRepository
from app.assistant.service import AssistantService
from app.assistant.tools import AssistantTools
from app.diagnosis.service import DiagnosisService
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.service import GraphRAGService
from app.profile.repository import ProfileRepository
from app.profile.service import ProfileService
from app.profile.extractor import ProfileExtractor

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """从 Bearer token 中提取当前用户。未登录返回 None（而非 401）。

    各端点自行决定是否需要强制登录。
    """
    if credentials is None:
        return None
    try:
        from app.auth.jwt import decode_access_token
        payload = decode_access_token(credentials.credentials, settings)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        from sqlalchemy import select
        from app.auth import models as am
        user = await session.scalar(select(am.User).where(am.User.id == user_id))
        if user is None or not user.is_active:
            return None
        return user
    except Exception:
        return None


async def get_graph_store(
    driver: Annotated[AsyncDriver, Depends(get_neo4j_driver)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Neo4jGraphStore:
    return Neo4jGraphStore(driver=driver, settings=settings)


async def get_graphrag_service(
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
) -> GraphRAGService:
    return GraphRAGService(graph_store)


async def get_resource_generation_service(
    graphrag_service: Annotated[GraphRAGService, Depends(get_graphrag_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceGenerationService:
    return ResourceGenerationService(
        graphrag_service=graphrag_service,
        settings=settings,
        repository=ResourceRepository(session),
    )


async def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProfileService:
    return ProfileService(ProfileRepository(session), extractor=ProfileExtractor(settings))


async def get_assistant_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    graphrag_service: Annotated[GraphRAGService, Depends(get_graphrag_service)],
    resource_service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
) -> AssistantService:
    tools = AssistantTools(
        settings=settings,
        profile_service=profile_service,
        graphrag_service=graphrag_service,
        resource_service=resource_service,
        diagnosis_service=DiagnosisService(graph_store),
    )
    return AssistantService(
        settings=settings,
        memory=AssistantMemoryRepository(session),
        tools=tools,
    )
