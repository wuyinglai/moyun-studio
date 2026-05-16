"""墨韵 - Prompt 模板 API

端点：
  GET  /api/prompts           获取所有Prompt模板列表
  GET  /api/prompts/{name}    获取指定Prompt内容（渲染后）
  POST /api/prompts/{name}    保存/更新Prompt内容
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.exceptions import ResourceNotFoundError, TemplateNotFoundError
from backend.core.file_ops import FileService
from backend.core.prompt_engine import PromptEngine
from backend.core.prompt_versioning import list_archives, restore_archive
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["prompts"], prefix="/prompts")


def _get_engine(settings: Settings = Depends(get_settings)) -> PromptEngine:
    fs = FileService(settings.prompts_path)
    return PromptEngine(settings.prompts_path, fs)


class PromptUpdateRequest(BaseModel):
    content: str


@router.get("/raw", response_model=ApiResponse[dict])
async def get_raw_prompt(
    path: str = Query(..., description="相对于 prompts 目录的文件路径"),
    settings: Settings = Depends(get_settings),
):
    """读取 prompts 目录下的原始文件内容"""
    file_path = settings.prompts_path / path
    if not file_path.exists() or not file_path.is_relative_to(settings.prompts_path):
        raise HTTPException(status_code=404, detail=f"Prompt 文件不存在: {path}")
    content = file_path.read_text(encoding="utf-8")
    return ApiResponse.ok({"path": path, "content": content})

@router.get("", response_model=ApiResponse[dict])
async def list_prompts(settings: Settings = Depends(get_settings)):
    """获取所有Prompt模板列表"""
    prompts_path = settings.prompts_path
    if not prompts_path.exists():
        return ApiResponse.ok({"prompts": [], "total": 0})

    prompts = []
    for category in ["generate", "extract", "transform"]:
        cat_path = prompts_path / category
        if cat_path.exists():
            for d in sorted(cat_path.iterdir()):
                if d.is_dir():
                    prompt_file = d / "main.md"
                    prompts.append({
                        "name": f"{category}/{d.name}",
                        "category": category,
                        "exists": prompt_file.exists(),
                    })

    return ApiResponse.ok({"prompts": prompts, "total": len(prompts)})


@router.get("/version-all", response_model=ApiResponse[dict])
async def list_all_prompt_versions(
    pipeline_name: str | None = Query(default=None, description="可选：按管线名筛选"),
    settings: Settings = Depends(get_settings),
):
    """列出 prompt 归档版本。"""
    versions = list_archives(settings.prompts_path, pipeline_name=pipeline_name)
    return ApiResponse.ok({"versions": versions, "total": len(versions)})


@router.get("/version-content/{version}", response_model=ApiResponse[dict])
async def get_prompt_version_content(
    version: str,
    settings: Settings = Depends(get_settings),
):
    """读取指定 prompt 归档版本的内容。"""
    archive_dir = settings.prompts_path / ".archive" / version
    if not archive_dir.exists() or not archive_dir.is_dir():
        raise ResourceNotFoundError(resource="prompt archive", identifier=version)

    metadata = _read_archive_metadata(archive_dir)
    md_files = sorted(p for p in archive_dir.rglob("*.md") if p.is_file())
    content = md_files[0].read_text(encoding="utf-8") if md_files else ""

    return ApiResponse.ok({
        "version": version,
        "metadata": metadata,
        "source": metadata.get("source", ""),
        "content": content,
        "files": [str(p.relative_to(archive_dir)).replace("\\", "/") for p in md_files],
    })


@router.post("/version-restore/{version}", response_model=ApiResponse[None])
async def restore_prompt_version(
    version: str,
    settings: Settings = Depends(get_settings),
):
    """将 prompt 恢复到归档记录中的来源路径。"""
    archive_dir = settings.prompts_path / ".archive" / version
    if not archive_dir.exists() or not archive_dir.is_dir():
        raise ResourceNotFoundError(resource="prompt archive", identifier=version)

    metadata = _read_archive_metadata(archive_dir)
    source = metadata.get("source")
    if not source:
        raise HTTPException(status_code=400, detail="归档缺少 source，无法恢复")

    target_path = _resolve_prompt_source(settings.prompts_path, source)
    ok = restore_archive(archive_dir, target_path)
    if not ok:
        raise HTTPException(status_code=500, detail="恢复归档失败")

    logger.info("Prompt 已从归档 %s 恢复到 %s", version, target_path)
    return ApiResponse.ok(message=f"Prompt 已恢复到版本 {version}")


@router.get("/{category}/{name}", response_model=ApiResponse[dict])
async def get_prompt(
    category: str,
    name: str,
    project_id: str = Query(default="", description="项目ID（用于变量替换）"),
    settings: Settings = Depends(get_settings),
    engine: PromptEngine = Depends(_get_engine),
):
    """获取指定Prompt内容"""
    prompt_key = f"{category}/{name}"
    prompt_file = settings.prompts_path / category / name / "main.md"
    if not prompt_file.exists():
        raise TemplateNotFoundError(template=f"{category}/{name}")

    raw_content = prompt_file.read_text(encoding="utf-8")

    return ApiResponse.ok({
        "name": prompt_key,
        "category": category,
        "content": raw_content,
    })


@router.post("/{category}/{name}", response_model=ApiResponse[None])
async def save_prompt(
    category: str,
    name: str,
    req: PromptUpdateRequest,
    settings: Settings = Depends(get_settings),
):
    """保存Prompt内容"""
    prompt_dir = settings.prompts_path / category / name
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = prompt_dir / "main.md"
    prompt_file.write_text(req.content, encoding="utf-8")

    return ApiResponse.ok(message=f"Prompt {category}/{name} 已保存")


def _read_archive_metadata(archive_dir: Path) -> dict:
    meta_file = archive_dir / ".metadata.json"
    if not meta_file.exists():
        return {}
    import json
    return json.loads(meta_file.read_text(encoding="utf-8"))


def _resolve_prompt_source(prompts_path: Path, source: str) -> Path:
    source_path = Path(source)
    target_path = source_path if source_path.is_absolute() else prompts_path / source_path
    try:
        target_path.resolve().relative_to(prompts_path.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="归档 source 不在 prompts 目录内")
    return target_path
