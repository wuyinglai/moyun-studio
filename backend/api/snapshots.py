"""墨韵 - 版本快照 API."""

import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError
from backend.core.file_ops import FileService
from backend.core.snapshot import SnapshotManager
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["版本快照"], prefix="/snapshots")


class CreateSnapshotRequest(BaseModel):
    """创建快照请求。"""

    file_path: str = Field(..., description="文件路径（相对于项目根目录）")
    label: str | None = Field(None, description="快照标签")


class RestoreSnapshotRequest(BaseModel):
    """恢复快照请求。"""

    project_id: str = Field(..., description="项目ID")
    snapshot_id: str = Field(..., description="快照ID")


class CompareSnapshotsRequest(BaseModel):
    """对比两个快照请求。"""

    snapshot_id1: str = Field(..., description="旧版本快照ID")
    snapshot_id2: str = Field(..., description="新版本快照ID")


@router.get("/{project_id}", response_model=ApiResponse[list])
async def list_snapshots(
    project_id: str,
    file_path: str = Query(..., description="文件路径（相对于项目根目录）"),
    settings: Settings = Depends(get_settings),
):
    """获取文件的快照列表。"""
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    manager = SnapshotManager(file_service)
    full_path = f"{project_id}/{file_path}"
    snapshots = await manager.list_snapshots(full_path)

    return ApiResponse.ok(snapshots)


@router.post("/{project_id}", response_model=ApiResponse[dict], status_code=201)
async def create_snapshot(
    project_id: str,
    req: CreateSnapshotRequest,
    settings: Settings = Depends(get_settings),
):
    """创建版本快照。"""
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    manager = SnapshotManager(file_service)
    full_path = f"{project_id}/{req.file_path}"

    snapshot = await manager.create_snapshot(full_path, req.label)

    logger.info(
        "版本快照已创建",
        extra={
            "project_id": project_id,
            "file_path": req.file_path,
            "snapshot_id": snapshot.snapshot_id,
        },
    )

    return ApiResponse.ok(snapshot.to_dict(), message="快照已创建")


@router.post("/{project_id}/restore", response_model=ApiResponse[None])
async def restore_snapshot(
    project_id: str,
    req: RestoreSnapshotRequest,
    settings: Settings = Depends(get_settings),
):
    """恢复指定快照到文件。"""
    project_dir = settings.projects_path / req.project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(req.project_id)

    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    manager = SnapshotManager(file_service)

    await manager.restore_snapshot(req.snapshot_id)

    logger.info(
        "快照已恢复",
        extra={
            "project_id": req.project_id,
            "snapshot_id": req.snapshot_id,
        },
    )

    return ApiResponse.ok(message="快照已恢复")


@router.post("/{project_id}/compare", response_model=ApiResponse[dict])
async def compare_snapshots(
    project_id: str,
    req: CompareSnapshotsRequest,
    settings: Settings = Depends(get_settings),
):
    """对比两个持久快照。"""
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    manager = SnapshotManager(file_service)
    diff = await manager.compare_versions(req.snapshot_id1, req.snapshot_id2)
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))

    return ApiResponse.ok({
        "diff": diff,
        "has_diff": bool(diff.strip()),
        "added_lines": added,
        "removed_lines": removed,
    })
