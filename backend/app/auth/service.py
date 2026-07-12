"""认证服务：注册、登录、刷新令牌。"""

from __future__ import annotations

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import jwt as jwt_utils
from app.auth import models as am
from app.auth.schemas import AuthResponse, RegisterRequest, UserInfo
from app.core.config import Settings


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # ── 密码 ──

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    # ── 注册 ──

    async def register(
        self,
        session: AsyncSession,
        payload: RegisterRequest,
    ) -> AuthResponse:
        # 检查邮箱唯一性
        existing = await session.scalar(
            select(am.User).where(am.User.email == payload.email.strip().lower())
        )
        if existing is not None:
            raise ValueError("该邮箱已被注册")

        user_id = payload.email.strip().lower().replace("@", "_").replace(".", "_")[:64]
        user = am.User(
            id=user_id,
            email=payload.email.strip().lower(),
            username=payload.username.strip(),
            password_hash=self.hash_password(payload.password),
        )
        session.add(user)
        await session.flush()

        # 同时创建 Student + StudentProfileRecord（如已存在则跳过）
        from app.profile import models as pm
        existing_student = await session.scalar(
            select(pm.Student).where(pm.Student.id == user_id)
        )
        if existing_student is None:
            session.add(pm.Student(id=user_id, display_name=payload.username.strip()))
        existing_record = await session.scalar(
            select(pm.StudentProfileRecord).where(pm.StudentProfileRecord.student_id == user_id)
        )
        if existing_record is None:
            session.add(pm.StudentProfileRecord(student_id=user_id))
        await session.flush()

        return await self._build_auth_response(session, user)

    # ── 登录 ──

    async def login(
        self,
        session: AsyncSession,
        email: str,
        password: str,
    ) -> AuthResponse:
        user = await session.scalar(
            select(am.User).where(am.User.email == email.strip().lower())
        )
        if user is None:
            raise ValueError("邮箱或密码错误")
        if not user.is_active:
            raise ValueError("账号已被禁用")
        if not self.verify_password(password, user.password_hash):
            raise ValueError("邮箱或密码错误")

        return await self._build_auth_response(session, user)

    # ── 演示登录 ──

    async def demo_login(self, session: AsyncSession) -> AuthResponse:
        """演示账号一键登录。若无则自动创建。"""
        demo_email = "demo@edugraph.local"
        user = await session.scalar(
            select(am.User).where(am.User.email == demo_email)
        )
        if user is None:
            return await self.register(
                session,
                RegisterRequest(
                    email=demo_email,
                    username="张同学",
                    password="demo123",
                ),
            )
        return await self._build_auth_response(session, user)

    # ── 刷新 ──

    async def refresh(
        self,
        session: AsyncSession,
        refresh_token: str,
    ) -> AuthResponse:
        rt = await jwt_utils.verify_and_consume_refresh_token(session, refresh_token)
        if rt is None:
            raise ValueError("无效或过期的刷新令牌")

        user = await session.get(am.User, rt.user_id)
        if user is None or not user.is_active:
            raise ValueError("用户不存在或已禁用")

        return await self._build_auth_response(session, user)

    # ── 内部 ──

    async def _build_auth_response(
        self,
        session: AsyncSession,
        user: am.User,
    ) -> AuthResponse:
        access = jwt_utils.create_access_token(user.id, user.email, self.settings)
        refresh = jwt_utils.create_refresh_token()
        await jwt_utils.store_refresh_token(session, user.id, refresh)

        return AuthResponse(
            user=UserInfo(
                id=user.id,
                email=user.email,
                username=user.username,
                is_active=user.is_active,
            ),
            access_token=access,
            refresh_token=refresh,
        )
