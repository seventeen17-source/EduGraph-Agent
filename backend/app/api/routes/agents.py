from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agents.schemas import (
    ResourceCenterDetail,
    ResourceCenterListResponse,
    ResourceMindmapUpdateRequest,
    ResourceGenerateRequest,
    ResourceGenerateResponse,
    RetryRequest,
)
from app.agents.service import ResourceGenerationService
from app.api.deps import get_profile_service, get_resource_generation_service
from app.profile.service import ProfileService

router = APIRouter()


@router.post("/generate-resources", response_model=ResourceGenerateResponse)
async def generate_resources(
    payload: ResourceGenerateRequest,
    service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
) -> ResourceGenerateResponse:
    return await service.generate(payload)


@router.post("/retry")
async def retry_resource_type(
    payload: RetryRequest,
    service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
) -> dict:
    result = await service.retry_single_type(
        resource_id=payload.resource_id,
        resource_type=payload.resource_type,
        student_id=payload.student_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "重试失败"))
    return result


@router.get("/resource-center", response_model=ResourceCenterListResponse)
async def list_resource_center(
    service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    student_id: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    q: str = Query(default=""),
    filter_by_weak_points: bool = Query(default=False),
) -> ResourceCenterListResponse:
    weak_points: list[str] = []
    if filter_by_weak_points and student_id:
        try:
            profile = await profile_service.get_profile(student_id)
            weak_points = profile.to_graphrag_input().weak_points or []
        except Exception:
            weak_points = []
    return await service.list_center_items(
        student_id=student_id,
        limit=limit,
        query=q,
        filter_by_weak_points=filter_by_weak_points,
        weak_points=weak_points,
    )


@router.get("/resource-center/{resource_id}", response_model=ResourceCenterDetail)
async def get_resource_center_detail(
    resource_id: str,
    service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
) -> ResourceCenterDetail:
    detail = await service.get_center_detail(resource_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="资源记录不存在")
    return detail


@router.patch("/resource-center/{resource_id}/mindmap", response_model=ResourceCenterDetail)
async def update_resource_center_mindmap(
    resource_id: str,
    payload: ResourceMindmapUpdateRequest,
    service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
) -> ResourceCenterDetail:
    detail = await service.update_center_mindmap(resource_id, payload)
    if detail is None:
        raise HTTPException(status_code=404, detail="资源记录不存在")
    return detail
