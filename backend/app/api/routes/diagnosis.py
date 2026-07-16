from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_graph_store
from app.db.relational import get_db_session
from app.diagnosis.schemas import DiagnosisRecommendRequest, DiagnosisRecommendResponse
from app.diagnosis.service import DiagnosisService
from app.exercises.repository import ExerciseRepository
from app.graph.neo4j_store import Neo4jGraphStore
from app.profile.repository import ProfileRepository

router = APIRouter()


@router.post("/recommend", response_model=DiagnosisRecommendResponse)
async def recommend(
    payload: DiagnosisRecommendRequest,
    graph_store: Annotated[Neo4jGraphStore, Depends(get_graph_store)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DiagnosisRecommendResponse:
    service = DiagnosisService(
        graph_store,
        profile_repository=ProfileRepository(session),
        exercise_repository=ExerciseRepository(session),
    )
    return await service.recommend(
        payload.student_profile,
        top_k=payload.top_k,
        node_mastery=payload.node_mastery,
        student_id=payload.student_id,
        target_goal=payload.target_goal,
    )
