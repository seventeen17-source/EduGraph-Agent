"""JWT 令牌签发、验证、刷新。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import models as am
from app.core.config import Settings


ACCESS_EXPIRE_MINUTES = 30
REFRESH_EXPIRE_DAYS = 7
ALGORITHM = "HS256"


def _secret(settings: Settings) -> str:
    """JWT 签名密钥。优先使用 JWT_SECRET，本地环境回退到 LLM_API_KEY。"""
    if settings.jwt_secret:
        return hashlib.sha256(settings.jwt_secret.encode()).hexdigest()
    if settings.environment == "local":
        return hashlib.sha256((settings.llm_api_key or settings.neo4j_password or "local-dev-secret").encode()).hexdigest()
    raise ValueError("JWT_SECRET must be configured in non-local environments")


def create_access_token(user_id: str, email: str, settings: Settings) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, _secret(settings), algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> dict:
    """解码并验证 access token。抛出 JWTError 如果无效/过期。"""
    return jwt.decode(token, _secret(settings), algorithms=[ALGORITHM])


def create_refresh_token() -> str:
    """生成随机 refresh token（存储时哈希）。"""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def store_refresh_token(
    session: AsyncSession,
    user_id: str,
    token: str,
) -> am.RefreshToken:
    """存储 refresh token 到数据库。"""
    rt = am.RefreshToken(
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS),
    )
    session.add(rt)
    await session.flush()
    return rt


async def verify_and_consume_refresh_token(
    session: AsyncSession,
    token: str,
) -> am.RefreshToken | None:
    """验证 refresh token 并标记为已使用（轮换）。"""
    from sqlalchemy import select

    token_h = hash_token(token)
    row = await session.scalar(
        select(am.RefreshToken).where(
            am.RefreshToken.token_hash == token_h,
            am.RefreshToken.revoked == False,  # noqa: E712
        )
    )
    if row is None:
        return None
    if row.expires_at < datetime.utcnow():
        return None
    # 轮换：撤销旧 token
    row.revoked = True
    await session.flush()
    return row


async def revoke_user_tokens(session: AsyncSession, user_id: str) -> None:
    """撤销用户所有 refresh token（用于修改密码等场景）。"""
    from sqlalchemy import select, update

    await session.execute(
        update(am.RefreshToken)
        .where(
            am.RefreshToken.user_id == user_id,
            am.RefreshToken.revoked == False,  # noqa: E712
        )
        .values(revoked=True)
    )
    await session.flush()
