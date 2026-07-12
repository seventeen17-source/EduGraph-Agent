from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agents.schemas import (
    ResourceCenterDetail,
    ResourceCenterListResponse,
    ResourceMindmapUpdateRequest,
    ResourceGenerateRequest,
    ResourceGenerateResponse,
)
from app.agents.service import ResourceGenerationService
from app.api.deps import get_resource_generation_service

router = APIRouter()


@router.post("/generate-resources", response_model=ResourceGenerateResponse)
async def generate_resources(
    payload: ResourceGenerateRequest,
    service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
) -> ResourceGenerateResponse:
    return await service.generate(payload)


@router.get("/resource-center", response_model=ResourceCenterListResponse)
async def list_resource_center(
    service: Annotated[ResourceGenerationService, Depends(get_resource_generation_service)],
    student_id: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
) -> ResourceCenterListResponse:
    return await service.list_center_items(student_id=student_id, limit=limit)


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
