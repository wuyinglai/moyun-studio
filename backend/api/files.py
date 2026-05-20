"""墨韵 - 文件操作 API

端点：
  GET  /api/file           读取文件（?project_id=&path=）
  POST /api/file           写入文件
  POST /api/file/create    创建新文件
  POST /api/file/rename    重命名/移动文件（?project_id=）
  POST /api/directory/create  创建新目录
  GET  /api/tree           获取文件树（?project_id=）
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.core.file_ops import FileService
from backend.schemas.common import ApiResponse
from backend.schemas.file import FileReadResponse, FileTreeResponse, FileWriteRequest, TreeNode

logger = logging.getLogger(__name__)
router = APIRouter(tags=["files"])


class CreateFileRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    path: str = Field(..., description="文件路径（相对于项目根目录）")
    content: str = Field(default="", description="文件内容")


class RenameFileRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    old_path: str = Field(..., description="原路径")
    new_path: str = Field(..., description="新路径")


class CreateDirectoryRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    path: str = Field(..., description="目录路径（相对于项目根目录）")


class DeletePathRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    path: str = Field(..., description="要移入回收站的路径")


class SearchRequest(BaseModel):
    project_id: str = Field(..., description="项目ID")
    query: str = Field(..., description="搜索关键词")
    case_sensitive: bool = Field(default=False, description="区分大小写")
    regex: bool = Field(default=False, description="使用正则表达式")


def _get_file_service(settings: Settings = Depends(get_settings)) -> FileService:
    return FileService(settings.projects_path)


def _build_tree_nodes(raw: dict) -> list[TreeNode]:
    """递归把 FileService 返回的 dict 树转为 TreeNode 列表"""
    nodes = []
    for child in raw.get("children", []):
        child_children = child.get("children")
        # 有 children 列表的是目录；文件没有 children 或 children 为空但 name 含扩展名
        has_ext = "." in child["name"]
        is_dir = child_children is not None and not has_ext
        node = TreeNode(
            name=child["name"],
            path=child["path"].replace("\\", "/"),
            type="directory" if is_dir else "file",
            children=_build_tree_nodes(child) if is_dir else [],
        )
        nodes.append(node)
    return nodes


@router.get("/file", response_model=ApiResponse[FileReadResponse])
async def read_file(
    project_id: str = Query(..., description="项目ID"),
    path: str = Query(..., description="相对于项目根目录的文件路径"),
    fs: FileService = Depends(_get_file_service),
):
    """读取文件内容"""
    full_path = f"{project_id}/{path}"
    try:
        content, fm = await fs.read_file(full_path)
    except Exception as e:
        logger.warning("读取文件失败", extra={"project_id": project_id, "path": path, "error": str(e)})
        raise ResourceNotFoundError(resource="file", identifier=f"{project_id}/{path}")

    return ApiResponse.ok(
        FileReadResponse(path=path, content=content, frontmatter=fm)
    )


@router.post("/file", response_model=ApiResponse[None])
async def write_file(
    req: FileWriteRequest,
    request: Request,
    project_id: str = Query(..., description="项目ID"),
    fs: FileService = Depends(_get_file_service),
):
    """写入文件内容"""
    full_path = f"{project_id}/{req.path}"
    try:
        await fs.write_file(full_path, req.content, req.frontmatter)
    except Exception as e:
        logger.error("写入文件失败", extra={"project_id": project_id, "path": req.path, "error": str(e)})
        raise

    logger.info("文件已保存", extra={"project_id": project_id, "path": req.path})

    # 发布文件更新事件
    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        await event_bus.publish("file-updated", {
            "path": f"{project_id}/{req.path}",
            "content": req.content,
        })

    return ApiResponse.ok(message="文件已保存")


@router.post("/file/create", response_model=ApiResponse[None])
async def create_file(
    req: CreateFileRequest,
    request: Request,
    fs: FileService = Depends(_get_file_service),
    settings: Settings = Depends(get_settings),
):
    """创建新文件"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    full_path = f"{req.project_id}/{req.path}"
    try:
        await fs.write_file(full_path, req.content)
    except Exception as e:
        logger.error("创建文件失败", extra={"path": req.path, "error": str(e)})
        raise

    logger.info("文件已创建", extra={"path": req.path})

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        await event_bus.publish("file-created", {
            "path": full_path,
            "name": req.path.split("/")[-1],
        })

    return ApiResponse.ok(message="文件已创建")


@router.post("/file/rename", response_model=ApiResponse[None])
async def rename_file(
    req: RenameFileRequest,
    request: Request,
    fs: FileService = Depends(_get_file_service),
    settings: Settings = Depends(get_settings),
):
    """重命名/移动文件（路径安全校验通过 FileService.rename_path）"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    # 使用 FileService 的安全重命名方法
    await fs.rename_path(req.project_id, req.old_path, req.new_path)

    logger.info("文件已重命名", extra={"from": req.old_path, "to": req.new_path})

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        await event_bus.publish("file-renamed", {
            "oldPath": f"{req.project_id}/{req.old_path}",
            "newPath": f"{req.project_id}/{req.new_path}",
        })

    return ApiResponse.ok(message="文件已重命名")


@router.post("/directory/create", response_model=ApiResponse[None])
async def create_directory(
    req: CreateDirectoryRequest,
    request: Request,
    fs: FileService = Depends(_get_file_service),
    settings: Settings = Depends(get_settings),
):
    """创建新目录（路径安全校验通过 FileService.create_directory）"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    # 使用 FileService 的安全创建目录方法
    await fs.create_directory(req.project_id, req.path)

    logger.info("目录已创建", extra={"path": req.path})

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        await event_bus.publish("directory-created", {
            "path": f"{req.project_id}/{req.path}",
            "name": req.path.split("/")[-1],
        })

    return ApiResponse.ok(message="目录已创建")


@router.post("/file/delete", response_model=ApiResponse[dict | None])
async def delete_file(
    req: DeletePathRequest,
    request: Request,
    fs: FileService = Depends(_get_file_service),
    settings: Settings = Depends(get_settings),
):
    """将文件移入回收站"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    full_path = f"{req.project_id}/{req.path}"
    result = await fs.delete_file(full_path)

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        await event_bus.publish("file-deleted", {
            "path": full_path,
            "trash": result,
        })

    return ApiResponse.ok(result, message="文件已移入回收站")


@router.post("/directory/delete", response_model=ApiResponse[dict | None])
async def delete_directory(
    req: DeletePathRequest,
    request: Request,
    fs: FileService = Depends(_get_file_service),
    settings: Settings = Depends(get_settings),
):
    """将目录移入回收站"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    full_path = f"{req.project_id}/{req.path}"
    result = await fs.delete_directory(full_path)

    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        await event_bus.publish("directory-deleted", {
            "path": full_path,
            "trash": result,
        })

    return ApiResponse.ok(result, message="目录已移入回收站")


@router.get("/tree", response_model=ApiResponse[FileTreeResponse])
async def get_tree(
    project_id: str = Query(..., description="项目ID"),
    fs: FileService = Depends(_get_file_service),
    settings: Settings = Depends(get_settings),
):
    """获取项目文件树"""
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    raw_tree = await fs.get_file_tree(project_id, max_depth=5)
    nodes = _build_tree_nodes(raw_tree)

    return ApiResponse.ok(
        FileTreeResponse(project_id=project_id, tree=nodes)
    )


class SearchResultItem(BaseModel):
    file: str = Field(..., description="文件路径")
    line: int = Field(..., description="行号")
    content: str = Field(..., description="匹配内容")


@router.post("/files/search", response_model=ApiResponse[list[SearchResultItem]])
async def search_files(
    req: SearchRequest,
    fs: FileService = Depends(_get_file_service),
):
    """在项目中搜索文件内容"""
    results = await fs.search_files(
        req.project_id,
        req.query,
        case_sensitive=req.case_sensitive,
        regex=req.regex,
    )
    return ApiResponse.ok([SearchResultItem(**r) for r in results])
