"""墨韵 - Prompt 模板 API

端点：
  GET  /api/prompts           获取所有Prompt模板列表
  GET  /api/prompts/{name}    获取指定Prompt内容（渲染后）
  POST /api/prompts/{name}    保存/更新Prompt内容
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.exceptions import TemplateNotFoundError
from backend.core.file_ops import FileService
from backend.core.prompt_engine import PromptEngine
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["prompts"], prefix="/prompts")


def _get_engine(settings: Settings = Depends(get_settings)) -> PromptEngine:
    fs = FileService(settings.prompts_path)
    return PromptEngine(settings.prompts_path, fs)


class PromptUpdateRequest(BaseModel):
    content: str


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
