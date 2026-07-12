"""认证路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_settings
from app.auth.schemas import (
    AuthResponse,
    DemoLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.auth.service import AuthService
from app.core.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    service = AuthService(settings)
    try:
        result = await service.register(session, payload)
        await session.commit()
        return result
    except ValueError as e:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    service = AuthService(settings)
    try:
        result = await service.login(session, payload.email, payload.password)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/demo", response_model=AuthResponse)
async def demo_login(
    _payload: DemoLoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    """演示账号一键登录。"""
    service = AuthService(settings)
    result = await service.demo_login(session)
    await session.commit()
    return result


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    service = AuthService(settings)
    try:
        result = await service.refresh(session, payload.refresh_token)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
