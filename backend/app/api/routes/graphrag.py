from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_graphrag_service
from app.graphrag.schemas import (
    EvidencePackage,
    EvidenceQueryRequest,
    SemanticSearchDebugResponse,
    StudentProfileInput,
)
from app.graphrag.service import GraphRAGService

router = APIRouter()


def _split_query_values(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    return [item for item in dict.fromkeys(items) if item]


@router.get("/evidence", response_model=EvidencePackage)
async def get_evidence(
    service: Annotated[GraphRAGService, Depends(get_graphrag_service)],
    uid: str = Query(..., description="KnowledgePoint uid, for example ml_kmeans"),
) -> EvidencePackage:
    return await service.build_evidence_by_uid(uid)


@router.post("/query", response_model=EvidencePackage)
async def query_graphrag(
    payload: EvidenceQueryRequest,
    service: Annotated[GraphRAGService, Depends(get_graphrag_service)],
) -> EvidencePackage:
    return await service.query(
        payload.query,
        payload.student_profile,
        student_id=payload.student_id,
    )


@router.get("/semantic-search", response_model=SemanticSearchDebugResponse)
async def semantic_search_debug(
    service: Annotated[GraphRAGService, Depends(get_graphrag_service)],
    q: str = Query(..., description="Natural language query to search semantic course views"),
    uid: str | None = Query(None, description="Optional center KnowledgePoint uid"),
    top_k: int = Query(10, ge=1, le=30),
    weak_points: list[str] = Query(default_factory=list),
    preferences: list[str] = Query(default_factory=list),
) -> SemanticSearchDebugResponse:
    profile = StudentProfileInput(
        weak_points=_split_query_values(weak_points),
        preferences=_split_query_values(preferences),
    )
    return await service.semantic_search_debug(
        q,
        center_uid=uid,
        student_profile=profile,
        top_k=top_k,
    )
