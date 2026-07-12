from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_profile_service
from app.exercises.repository import ExerciseRepository
from app.exercises.schemas import (
    ExerciseActionResponse,
    ExerciseBookmarkRequest,
    ExerciseMistakeListResponse,
    ExerciseReviewRequest,
    ExerciseSessionListResponse,
    ExerciseSessionRecord,
    ExerciseSessionSubmitRequest,
    ExerciseSessionSubmitResponse,
    ExerciseStatsResponse,
)
from app.exercises.service import ExerciseRecordService
from app.profile.service import ProfileService

router = APIRouter()


async def get_exercise_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ExerciseRecordService:
    return ExerciseRecordService(ExerciseRepository(session), profile_service)


@router.post("/sessions", response_model=ExerciseSessionSubmitResponse)
async def submit_exercise_session(
    payload: ExerciseSessionSubmitRequest,
    service: Annotated[ExerciseRecordService, Depends(get_exercise_service)],
) -> ExerciseSessionSubmitResponse:
    return await service.submit_session(payload)


@router.get("/sessions/{student_id}", response_model=ExerciseSessionListResponse)
async def list_exercise_sessions(
    student_id: str,
    service: Annotated[ExerciseRecordService, Depends(get_exercise_service)],
    limit: int = 50,
    offset: int = 0,
) -> ExerciseSessionListResponse:
    return await service.list_sessions(student_id, limit=limit, offset=offset)


@router.get("/sessions/{student_id}/{session_id}", response_model=ExerciseSessionRecord)
async def get_exercise_session(
    student_id: str,
    session_id: str,
    service: Annotated[ExerciseRecordService, Depends(get_exercise_service)],
) -> ExerciseSessionRecord:
    record = await service.get_session(student_id, session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="练习记录不存在")
    return record


@router.get("/mistakes/{student_id}", response_model=ExerciseMistakeListResponse)
async def list_mistakes(
    student_id: str,
    service: Annotated[ExerciseRecordService, Depends(get_exercise_service)],
    limit: int = 100,
    offset: int = 0,
    node_id: str | None = None,
) -> ExerciseMistakeListResponse:
    return await service.list_mistakes(student_id, limit=limit, offset=offset, node_id=node_id)


@router.get("/stats/{student_id}", response_model=ExerciseStatsResponse)
async def exercise_stats(
    student_id: str,
    service: Annotated[ExerciseRecordService, Depends(get_exercise_service)],
) -> ExerciseStatsResponse:
    return await service.stats(student_id)


@router.post("/attempts/{attempt_id}/bookmark", response_model=ExerciseActionResponse)
async def bookmark_attempt(
    attempt_id: str,
    payload: ExerciseBookmarkRequest,
    service: Annotated[ExerciseRecordService, Depends(get_exercise_service)],
) -> ExerciseActionResponse:
    return await service.bookmark_attempt(payload.student_id, attempt_id, payload.tag, payload.note)


@router.post("/attempts/{attempt_id}/review", response_model=ExerciseActionResponse)
async def review_attempt(
    attempt_id: str,
    payload: ExerciseReviewRequest,
    service: Annotated[ExerciseRecordService, Depends(get_exercise_service)],
) -> ExerciseActionResponse:
    return await service.review_attempt(
        student_id=payload.student_id,
        attempt_id=attempt_id,
        session_id="",
        review_session_id=payload.review_session_id,
        review_result=payload.review_result,
        mastery_delta=payload.mastery_delta,
        notes=payload.notes,
    )
