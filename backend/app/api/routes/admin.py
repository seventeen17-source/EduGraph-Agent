from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import GeneratedResourceRecord
from app.api.deps import get_db_session
from app.core.config import Settings, get_settings
from app.db.neo4j import neo4j_client
from app.exercises.models import ExerciseAttempt, ExerciseSession
from app.memory.embedding import EmbeddingService
from app.memory.vector_store import MemoryVectorStore
from app.rag.course_vector_store import CourseVectorStore


router = APIRouter()


class RuntimeComponentStatus(BaseModel):
    name: str
    status: str
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeStatusResponse(BaseModel):
    status: str
    environment: str
    components: dict[str, RuntimeComponentStatus]
    degraded_features: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _safe_url(value: str | None) -> str:
    if not value:
        return ""
    if "@" not in value:
        return value
    scheme, rest = value.split("://", 1) if "://" in value else ("", value)
    host = rest.split("@", 1)[-1]
    return f"{scheme}://***@{host}" if scheme else f"***@{host}"


async def _sqlite_status(session: AsyncSession, settings: Settings) -> RuntimeComponentStatus:
    try:
        result = await session.execute(text("SELECT 1"))
        ok = result.scalar_one_or_none() == 1
        table_names: list[str] = []
        if settings.database_url.startswith("sqlite"):
            table_result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            table_names = [str(row[0]) for row in table_result.fetchall()]
        return RuntimeComponentStatus(
            name="sqlite",
            status="ok" if ok else "error",
            detail="SQLite connection is healthy." if ok else "SQLite SELECT 1 returned an unexpected result.",
            metadata={
                "database_url": _safe_url(settings.database_url),
                "tables": table_names,
                "table_count": len(table_names),
            },
        )
    except Exception as exc:
        return RuntimeComponentStatus(
            name="sqlite",
            status="error",
            detail=f"{type(exc).__name__}: {exc}",
            metadata={"database_url": _safe_url(settings.database_url)},
        )


async def _neo4j_status(settings: Settings) -> RuntimeComponentStatus:
    try:
        result = await neo4j_client.healthcheck()
        healthy = result.get("neo4j") == "ok"
        return RuntimeComponentStatus(
            name="neo4j",
            status="ok" if healthy else "error",
            detail="Neo4j connection is healthy." if healthy else "Neo4j healthcheck returned an unexpected result.",
            metadata={
                "uri": settings.neo4j_uri,
                "database": settings.neo4j_database,
                "result": result,
            },
        )
    except Exception as exc:
        return RuntimeComponentStatus(
            name="neo4j",
            status="error",
            detail=f"{type(exc).__name__}: {exc}",
            metadata={"uri": settings.neo4j_uri, "database": settings.neo4j_database},
        )


def _llm_status(settings: Settings) -> RuntimeComponentStatus:
    configured = bool(settings.llm_api_key)
    return RuntimeComponentStatus(
        name="llm",
        status="ok" if configured else "missing",
        detail=(
            "LLM API key is configured."
            if configured
            else "LLM_API_KEY is missing; assistant/resource generation will be unavailable or degraded."
        ),
        metadata={
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "base_url": _safe_url(settings.llm_base_url),
            "resolver_enabled": settings.llm_resolver_enabled,
            "api_key_configured": configured,
        },
    )


def _embedding_status(settings: Settings) -> RuntimeComponentStatus:
    dedicated = bool(settings.embedding_api_key)
    fallback = bool(settings.llm_api_key)
    configured = dedicated or fallback
    try:
        dim = EmbeddingService(settings).embedding_dim()
    except Exception:
        dim = 1536
    status = "ok" if dedicated else "warning" if configured else "missing"
    detail = "Dedicated embedding API key is configured."
    if not dedicated and configured:
        detail = "EMBEDDING_API_KEY is missing; embedding will reuse LLM_API_KEY."
    if not configured:
        detail = "No embedding credential is configured; vector retrieval cannot build/query real embeddings."
    return RuntimeComponentStatus(
        name="embedding",
        status=status,
        detail=detail,
        metadata={
            "model": settings.embedding_model,
            "dimension": dim,
            "base_url": _safe_url(settings.embedding_base_url or settings.llm_base_url),
            "embedding_api_key_configured": dedicated,
            "using_llm_key_fallback": not dedicated and fallback,
        },
    )


def _collection_snapshot(
    *,
    client: chromadb.PersistentClient,
    name: str,
    expected_dim: int,
) -> dict[str, Any]:
    try:
        collection = client.get_collection(name)
    except Exception as exc:
        return {
            "name": name,
            "exists": False,
            "count": 0,
            "metadata": {},
            "dimension_matches": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    metadata = collection.metadata or {}
    raw_dim = metadata.get("dim")
    try:
        actual_dim = int(raw_dim) if raw_dim is not None else None
    except (TypeError, ValueError):
        actual_dim = None
    return {
        "name": name,
        "exists": True,
        "count": collection.count(),
        "metadata": metadata,
        "dimension": actual_dim,
        "expected_dimension": expected_dim,
        "dimension_matches": actual_dim is None or actual_dim == expected_dim,
    }


async def _chroma_status(settings: Settings) -> RuntimeComponentStatus:
    persist_dir = str(Path(settings.chroma_persist_dir).resolve())
    expected_dim = EmbeddingService(settings).embedding_dim()

    def inspect() -> dict[str, Any]:
        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        memory = _collection_snapshot(
            client=client,
            name=MemoryVectorStore.COLLECTION_NAME,
            expected_dim=expected_dim,
        )
        course = _collection_snapshot(
            client=client,
            name=CourseVectorStore.COLLECTION_NAME,
            expected_dim=expected_dim,
        )
        return {"memory": memory, "course_semantic": course}

    try:
        loop = asyncio.get_running_loop()
        collections = await loop.run_in_executor(None, inspect)
        course = collections["course_semantic"]
        memory = collections["memory"]
        status = "ok"
        details: list[str] = []
        if not course["exists"]:
            status = "missing"
            details.append("course_semantic_views collection is missing.")
        elif course["count"] <= 0:
            status = "empty"
            details.append("course_semantic_views collection is empty.")
        if course["exists"] and not course["dimension_matches"]:
            status = "error"
            details.append("course_semantic_views embedding dimension does not match current model.")
        if memory["exists"] and not memory["dimension_matches"]:
            status = "error"
            details.append("learning_memories embedding dimension does not match current model.")
        if not details:
            details.append("Chroma collections are inspectable.")
        return RuntimeComponentStatus(
            name="chroma",
            status=status,
            detail=" ".join(details),
            metadata={
                "persist_dir": persist_dir,
                "expected_embedding_model": settings.embedding_model,
                "expected_embedding_dimension": expected_dim,
                "collections": collections,
            },
        )
    except Exception as exc:
        return RuntimeComponentStatus(
            name="chroma",
            status="error",
            detail=f"{type(exc).__name__}: {exc}",
            metadata={"persist_dir": persist_dir},
        )


def _summarize(
    components: dict[str, RuntimeComponentStatus],
) -> tuple[str, list[str], list[str]]:
    degraded: list[str] = []
    warnings: list[str] = []

    if components["neo4j"].status != "ok":
        degraded.append("neo4j_unavailable")
    if components["sqlite"].status != "ok":
        degraded.append("sqlite_unavailable")
    if components["llm"].status != "ok":
        degraded.append("llm_missing")
    if components["embedding"].status == "missing":
        degraded.append("embedding_missing")
    elif components["embedding"].status == "warning":
        warnings.append("embedding_uses_llm_key_fallback")

    chroma = components["chroma"]
    chroma_meta = chroma.metadata.get("collections", {})
    course = chroma_meta.get("course_semantic", {})
    memory = chroma_meta.get("memory", {})
    if chroma.status == "error":
        degraded.append("chroma_error")
    elif not course.get("exists"):
        degraded.append("course_semantic_index_missing")
    elif course.get("count", 0) <= 0:
        degraded.append("course_semantic_index_empty")
    if memory.get("exists") and memory.get("count", 0) <= 0:
        warnings.append("memory_index_empty")

    overall = "ok"
    if degraded:
        overall = "degraded"
    if any(components[name].status == "error" for name in components):
        overall = "error"
    return overall, degraded, warnings


@router.get("/runtime-status", response_model=RuntimeStatusResponse)
async def runtime_status(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RuntimeStatusResponse:
    neo4j, sqlite, chroma = await asyncio.gather(
        _neo4j_status(settings),
        _sqlite_status(session, settings),
        _chroma_status(settings),
    )
    components = {
        "neo4j": neo4j,
        "sqlite": sqlite,
        "llm": _llm_status(settings),
        "embedding": _embedding_status(settings),
        "chroma": chroma,
    }
    status, degraded, warnings = _summarize(components)
    return RuntimeStatusResponse(
        status=status,
        environment=settings.environment,
        components=components,
        degraded_features=degraded,
        warnings=warnings,
    )


# ═══════════════════════════════════════════════════════════════
# 业务指标
# ═══════════════════════════════════════════════════════════════


class ResourceMetrics(BaseModel):
    total_generations: int = 0
    avg_quality_score: float = 0.0
    by_type: dict[str, int] = Field(default_factory=dict)


class ExerciseMetrics(BaseModel):
    total_sessions: int = 0
    total_attempts: int = 0
    avg_accuracy: float = 0.0


class BusinessMetricsResponse(BaseModel):
    resource_generation: ResourceMetrics = Field(default_factory=ResourceMetrics)
    exercises: ExerciseMetrics = Field(default_factory=ExerciseMetrics)
    active_users: int = 0
    generated_at: str = ""


@router.get("/metrics", response_model=BusinessMetricsResponse)
async def get_business_metrics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessMetricsResponse:
    """返回业务运行指标：资源生成统计、练习统计、活跃用户数。"""

    # ── 资源生成统计 ──
    total_generations = await session.scalar(
        select(func.count(GeneratedResourceRecord.id))
    ) or 0
    avg_quality = await session.scalar(
        select(func.avg(GeneratedResourceRecord.quality_score))
    ) or 0.0

    # 按类型分布：取最近 200 条记录统计
    type_rows = await session.execute(
        select(GeneratedResourceRecord.resource_types_json)
        .order_by(desc(GeneratedResourceRecord.created_at))
        .limit(200)
    )
    by_type: dict[str, int] = {}
    for row in type_rows:
        types = row[0] or []
        if isinstance(types, list):
            for t in types:
                by_type[str(t)] = by_type.get(str(t), 0) + 1

    # ── 练习统计 ──
    total_sessions = await session.scalar(
        select(func.count(ExerciseSession.id))
    ) or 0
    total_attempts = await session.scalar(
        select(func.count(ExerciseAttempt.id))
    ) or 0
    avg_accuracy = await session.scalar(
        select(func.avg(ExerciseSession.accuracy))
    ) or 0.0

    # ── 活跃用户数（两个表去重） ──
    exercise_users_result = await session.execute(
        select(func.distinct(ExerciseSession.student_id))
    )
    exercise_users = set(exercise_users_result.scalars().all())
    resource_users_result = await session.execute(
        select(func.distinct(GeneratedResourceRecord.student_id))
    )
    resource_users = set(resource_users_result.scalars().all())
    active_users = len(exercise_users | resource_users)

    return BusinessMetricsResponse(
        resource_generation=ResourceMetrics(
            total_generations=total_generations,
            avg_quality_score=round(float(avg_quality), 4),
            by_type=by_type,
        ),
        exercises=ExerciseMetrics(
            total_sessions=total_sessions,
            total_attempts=total_attempts,
            avg_accuracy=round(float(avg_accuracy), 4),
        ),
        active_users=active_users,
        generated_at=datetime.utcnow().isoformat() + "Z",
    )
