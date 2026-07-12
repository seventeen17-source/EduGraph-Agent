from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Base class for relational business-data tables."""


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None):
    global _engine
    if _engine is None:
        settings = settings or get_settings()
        _ensure_sqlite_parent_dir(settings.database_url)
        _engine = create_async_engine(settings.database_url, future=True)
    return _engine


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite+aiosqlite:///"):
        return
    parsed = urlparse(database_url)
    db_path = parsed.path
    if db_path.startswith("/") and not db_path.startswith("//"):
        # sqlite+aiosqlite:///./data/app.db is parsed as /./data/app.db.
        db_path = db_path[1:]
    if db_path in {":memory:", ""}:
        return
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def get_sessionmaker(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(settings),
            expire_on_commit=False,
        )
    return _sessionmaker


async def init_relational_db(settings: Settings | None = None) -> None:
    """Create business-data tables for local/demo deployments."""
    from app.agents import models as _agent_models  # noqa: F401
    from app.assistant import models as _assistant_models  # noqa: F401
    from app.auth import models as _auth_models  # noqa: F401
    from app.exercises import models as _exercise_models  # noqa: F401
    from app.profile import models as _profile_models  # noqa: F401

    engine = get_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_relational_db() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
