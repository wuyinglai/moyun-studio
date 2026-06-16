"""Continuity anchor API."""

from fastapi import APIRouter, Depends

from backend.config import Settings, get_settings
from backend.core.continuity_anchor_service import ContinuityAnchorService
from backend.core.file_ops import FileService
from backend.schemas.common import ApiResponse
from backend.schemas.continuity_anchor import ContinuityAnchorsDocument

router = APIRouter(tags=["continuity-anchors"])


def _service(settings: Settings) -> ContinuityAnchorService:
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    return ContinuityAnchorService(file_service)


@router.get("/projects/{project_id}/continuity-anchors")
async def get_continuity_anchors(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    service = _service(settings)
    document = await service.read_document(project_id)
    return ApiResponse.ok(document.model_dump(mode="json"))


@router.put("/projects/{project_id}/continuity-anchors")
async def put_continuity_anchors(
    project_id: str,
    body: ContinuityAnchorsDocument,
    settings: Settings = Depends(get_settings),
):
    service = _service(settings)
    document = await service.write_document(project_id, body)
    return ApiResponse.ok(document.model_dump(mode="json"))
