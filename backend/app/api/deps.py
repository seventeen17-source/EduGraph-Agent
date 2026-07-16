import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.service_cache import get_service_cache

logger = logging.getLogger(__name__)
from app.db.relational import get_db_session
from app.agents.repository import ResourceRepository
from app.agents.service import ResourceGenerationService
from app.assistant.memory import AssistantMemoryRepository
from app.assistant.service import AssistantService
from app.assistant.tools import AssistantTools
from app.diagnosis.service import DiagnosisService
from app.graphrag.service import GraphRAGService
from app.profile.extractor import ProfileExtractor
from app.profile.repository import ProfileRepository
from app.profile.service import ProfileService

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
    except Exception as exc:
        logger.debug("Authentication failed: %s", exc)
        return None


def get_graph_store():
    cache = get_service_cache()
    return cache.graph_store


def get_graphrag_service():
    cache = get_service_cache()
    return cache.graphrag_service


def get_diagnosis_service():
    cache = get_service_cache()
    return cache.diagnosis_service


def get_profile_extractor():
    cache = get_service_cache()
    return cache.profile_extractor


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
    extractor: Annotated[ProfileExtractor, Depends(get_profile_extractor)],
) -> ProfileService:
    return ProfileService(ProfileRepository(session), extractor=extractor)


async def get_assistant_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    graphrag_service: Annotated[GraphRAGService, Depends(get_graphrag_service)],
    resource_service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
    diagnosis_service: Annotated[DiagnosisService, Depends(get_diagnosis_service)],
) -> AssistantService:
    tools = AssistantTools(
        settings=settings,
        profile_service=profile_service,
        graphrag_service=graphrag_service,
        resource_service=resource_service,
        diagnosis_service=diagnosis_service,
    )
    return AssistantService(
        settings=settings,
        memory=AssistantMemoryRepository(session),
        tools=tools,
    )
