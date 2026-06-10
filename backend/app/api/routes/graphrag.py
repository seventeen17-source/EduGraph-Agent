from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_graphrag_service
from app.graphrag.schemas import EvidencePackage, EvidenceQueryRequest
from app.graphrag.service import GraphRAGService

router = APIRouter()


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
    return await service.query(payload.query, payload.student_profile)
