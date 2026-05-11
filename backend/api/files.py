"""墨韵 - 文件操作 API

端点：
  GET  /api/file           读取文件（?project_id=&path=）
  POST /api/file           写入文件
  GET  /api/tree           获取文件树（?project_id=）
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import Settings, get_settings
from backend.core.file_ops import FileService
from backend.schemas.common import ApiResponse
from backend.schemas.file import FileReadResponse, FileTreeResponse, FileWriteRequest, TreeNode

router = APIRouter(tags=["files"])


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
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")

    return ApiResponse.ok(
        FileReadResponse(path=path, content=content, frontmatter=fm)
    )


@router.post("/file", response_model=ApiResponse[None])
async def write_file(
    req: FileWriteRequest,
    project_id: str = Query(..., description="项目ID"),
    fs: FileService = Depends(_get_file_service),
):
    """写入文件内容"""
    full_path = f"{project_id}/{req.path}"
    try:
        await fs.write_file(full_path, req.content, req.frontmatter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入失败: {e}")

    return ApiResponse.ok(message="文件已保存")


@router.get("/tree", response_model=ApiResponse[FileTreeResponse])
async def get_tree(
    project_id: str = Query(..., description="项目ID"),
    fs: FileService = Depends(_get_file_service),
    settings: Settings = Depends(get_settings),
):
    """获取项目文件树"""
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    raw_tree = await fs.get_file_tree(project_id, max_depth=5)
    nodes = _build_tree_nodes(raw_tree)

    return ApiResponse.ok(
        FileTreeResponse(project_id=project_id, tree=nodes)
    )
