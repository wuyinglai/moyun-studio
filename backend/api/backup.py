"""墨韵 - 项目备份 API."""

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["backup"])


class BackupInfo(BaseModel):
    backup_id: str
    project_id: str
    description: str
    created_at: str
    file_count: int
    total_size: int


class BackupListResponse(BaseModel):
    backups: list[BackupInfo]
    total: int


class BackupCreateRequest(BaseModel):
    project_id: str
    description: str = ""


class BackupRestoreRequest(BaseModel):
    target_project_id: str | None = None


def _backup_dir(project_dir: Path) -> Path:
    return project_dir / "backup"


def _ensure_backup_dir(project_dir: Path) -> Path:
    backup_dir = _backup_dir(project_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


async def _load_backup_meta(backup_path: Path) -> dict | None:
    meta_file = backup_path / "meta.json"
    if not await asyncio.to_thread(meta_file.exists):
        return None
    try:
        text = await asyncio.to_thread(meta_file.read_text, encoding="utf-8")
        return json.loads(text)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("备份元数据解析失败: %s - %s", meta_file, e)
        return None


async def _save_backup_meta(backup_path: Path, meta: dict) -> None:
    meta_file = backup_path / "meta.json"
    content = json.dumps(meta, ensure_ascii=False, indent=2)
    await asyncio.to_thread(meta_file.write_text, content, encoding="utf-8")


async def _compute_backup_size(backup_path: Path) -> int:
    def _compute() -> int:
        total = 0
        for item in backup_path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total
    return await asyncio.to_thread(_compute)


async def _count_files(backup_path: Path) -> int:
    def _count() -> int:
        return sum(1 for item in backup_path.rglob("*") if item.is_file())
    return await asyncio.to_thread(_count)


async def _get_backup_info(backup_path: Path) -> BackupInfo | None:
    meta = await _load_backup_meta(backup_path)
    if meta is None:
        return None
    size = await _compute_backup_size(backup_path)
    return BackupInfo(
        backup_id=meta["backup_id"],
        project_id=meta["project_id"],
        description=meta.get("description", ""),
        created_at=meta.get("created_at", ""),
        file_count=meta.get("file_count", 0),
        total_size=size,
    )


async def _copytree_async(src: Path, dst: Path) -> None:
    await asyncio.to_thread(shutil.copytree, src, dst, dirs_exist_ok=True)


async def _rmtree_async(path: Path) -> None:
    await asyncio.to_thread(shutil.rmtree, path)


async def _copy2_async(src: Path, dst: Path) -> None:
    await asyncio.to_thread(shutil.copy2, src, dst)


def _create_backup_snapshot(source_dir: Path, backup_path: Path) -> None:
    for item in source_dir.iterdir():
        if item.name == "backup":
            continue
        dest = backup_path / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


@router.get("/backup", response_model=ApiResponse[BackupListResponse])
async def list_backups(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    logger.info("获取备份列表", extra={"project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    backup_root = _backup_dir(project_dir)
    if not await asyncio.to_thread(backup_root.exists):
        return ApiResponse.ok(BackupListResponse(backups=[], total=0))

    paths = await asyncio.to_thread(lambda: sorted(backup_root.iterdir(), key=lambda x: x.name, reverse=True))
    backups: list[BackupInfo] = []
    for path in paths:
        if await asyncio.to_thread(path.is_dir):
            info = await _get_backup_info(path)
            if info:
                backups.append(info)

    return ApiResponse.ok(BackupListResponse(backups=backups, total=len(backups)))


@router.post("/backup", response_model=ApiResponse[BackupInfo], status_code=201)
async def create_backup(
    req: BackupCreateRequest,
    settings: Settings = Depends(get_settings),
):
    logger.info("创建备份", extra={"project_id": req.project_id, "description": req.description})
    project_dir = settings.projects_path / req.project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(req.project_id)

    backup_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    backup_path = _ensure_backup_dir(project_dir) / backup_id
    await asyncio.to_thread(backup_path.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(_create_backup_snapshot, project_dir, backup_path)

    file_count = await _count_files(backup_path)
    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "backup_id": backup_id,
        "project_id": req.project_id,
        "description": req.description,
        "created_at": now,
        "file_count": file_count,
    }
    await _save_backup_meta(backup_path, meta)

    total_size = await _compute_backup_size(backup_path)
    info = BackupInfo(
        backup_id=backup_id,
        project_id=req.project_id,
        description=req.description,
        created_at=now,
        file_count=file_count,
        total_size=total_size,
    )
    return ApiResponse.ok(info, message="备份创建成功")


@router.post("/backup/{backup_id}", response_model=ApiResponse[None])
async def restore_backup(
    backup_id: str,
    project_id: str,
    req: BackupRestoreRequest,
    settings: Settings = Depends(get_settings),
):
    logger.info("恢复备份", extra={"backup_id": backup_id, "project_id": project_id, "target": req.target_project_id})
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    backup_path = _backup_dir(project_dir) / backup_id
    if not await asyncio.to_thread(backup_path.exists):
        raise ResourceNotFoundError(resource="backup", identifier=backup_id)

    target_dir = settings.projects_path / req.target_project_id if req.target_project_id else project_dir
    await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)

    items = await asyncio.to_thread(lambda: list(target_dir.iterdir()))
    for item in items:
        if item.name == "backup":
            continue
        if await asyncio.to_thread(item.is_dir):
            await _rmtree_async(item)
        else:
            await asyncio.to_thread(item.unlink)

    backup_items = await asyncio.to_thread(lambda: list(backup_path.iterdir()))
    for item in backup_items:
        dest = target_dir / item.name
        if await asyncio.to_thread(item.is_dir):
            await _copytree_async(item, dest)
        else:
            await _copy2_async(item, dest)

    logger.info("备份恢复成功", extra={"backup_id": backup_id, "project_id": project_id, "target": str(target_dir)})
    return ApiResponse.ok(message="备份恢复成功")


@router.delete("/backup/{backup_id}", response_model=ApiResponse[None])
async def delete_backup(
    backup_id: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    logger.info("删除备份", extra={"backup_id": backup_id, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    backup_path = _backup_dir(project_dir) / backup_id
    if not await asyncio.to_thread(backup_path.exists):
        raise ResourceNotFoundError(resource="backup", identifier=backup_id)

    await _rmtree_async(backup_path)
    logger.info("备份已删除", extra={"backup_id": backup_id})
    return ApiResponse.ok(message=f"备份 {backup_id} 已删除")
