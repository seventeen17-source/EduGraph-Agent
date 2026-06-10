from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_graph_store
from app.diagnosis.schemas import DiagnosisRecommendRequest, DiagnosisRecommendResponse
from app.diagnosis.service import DiagnosisService
from app.graph.neo4j_store import Neo4jGraphStore

router = APIRouter()


@router.post("/recommend", response_model=DiagnosisRecommendResponse)
async def recommend(
    payload: DiagnosisRecommendRequest,
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
) -> DiagnosisRecommendResponse:
    service = DiagnosisService(graph_store)
    return await service.recommend(payload.student_profile, top_k=payload.top_k)
