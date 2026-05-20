"""墨韵 - 回收站 API

端点：
  GET  /api/trash/list      列出回收站内容
  POST /api/trash/restore   从回收站恢复
  POST /api/trash/empty     清空回收站
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.exceptions import ResourceNotFoundError
from backend.core.trash import TrashService
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["trash"])


class RestoreRequest(BaseModel):
    trash_name: str


@router.get("/trash/list")
async def list_trash(
    settings: Settings = Depends(get_settings),
):
    """列出回收站所有内容"""
    trash = TrashService(settings.workspace_path)
    items = trash.list_trash()
    return ApiResponse.ok({"items": items, "total": len(items)})


@router.post("/trash/restore")
async def restore_from_trash(
    req: RestoreRequest,
    settings: Settings = Depends(get_settings),
):
    """从回收站恢复到原位置"""
    trash = TrashService(settings.workspace_path)
    dest = trash.restore(req.trash_name)
    if dest is None:
        raise ResourceNotFoundError(resource="trash", identifier=req.trash_name)
    return ApiResponse.ok({"restored_path": str(dest)})


@router.post("/trash/empty")
async def empty_trash(
    settings: Settings = Depends(get_settings),
):
    """清空回收站"""
    trash = TrashService(settings.workspace_path)
    count = trash.empty_trash()
    return ApiResponse.ok({"message": f"回收站已清空，共删除 {count} 项", "count": count})
