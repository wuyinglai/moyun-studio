"""墨韵 - 素材提取 API

端点：
  GET    /api/materials/{type}             获取提取结果列表
  GET    /api/materials/{type}/{id}        获取提取结果详情
  POST   /api/materials/{type}              创建提取结果（手动录入）
  POST   /api/extract                       提交提取任务（LLM自动提取）
  DELETE /api/materials/{type}/{id}        删除提取结果
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.exceptions import (
    ProjectNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.prompt_engine import PromptEngine
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["materials"])


# ─── Schema ─────────────────────────────────────────────────────────

class PlotItem(BaseModel):
    plot_id: str
    title: str
    description: str = ""
    chapter_range: list[int] | None = None  # [start_ch, end_ch]
    characters: list[str] = []
    importance: str = "normal"  # normal, important, key
    status: str = "active"
    created_at: str = ""


class SceneItem(BaseModel):
    scene_id: str
    location: str = ""
    time: str = ""
    participants: list[str] = []
    atmosphere: str = ""
    key_events: list[str] = []
    status: str = "active"
    created_at: str = ""


class SummaryItem(BaseModel):
    summary_id: str
    chapter_id: str
    summary: str = ""
    word_count: int = 0
    key_events: list[str] = []
    characters_appeared: list[str] = []
    foreshadowing: list[str] = []
    created_at: str = ""


class WorldbuildingItem(BaseModel):
    world_id: str = "main"
    content: str = ""
    updated_at: str = ""


class MaterialListResponse(BaseModel):
    items: list[dict]
    total: int


class MaterialCreateRequest(BaseModel):
    project_id: str
    title: str = ""
    description: str = ""
    content: dict | None = None


class ExtractTaskRequest(BaseModel):
    project_id: str
    type: str  # plot, scene, summary, character
    source_file: str  # 源文件路径
    extract_options: dict | None = None


# ─── 辅助函数 ──────────────────────────────────────────────────────

def _materials_dir(project_dir: Path) -> Path:
    return project_dir / "materials" / "extracted"


def _type_dir(project_dir: Path, material_type: str) -> Path:
    """获取指定类型素材的目录"""
    td = _materials_dir(project_dir) / material_type
    td.mkdir(parents=True, exist_ok=True)
    return td


def _material_file(project_dir: Path, material_type: str, item_id: str) -> Path:
    if material_type == "summaries":
        return _materials_dir(project_dir) / material_type / f"{item_id}.md"
    elif material_type == "worldbuilding":
        return _materials_dir(project_dir) / "worldbuilding.md"
    else:
        return _type_dir(project_dir, material_type) / f"{item_id}.json"


def _load_material(project_dir: Path, material_type: str, item_id: str) -> dict | None:
    mf = _material_file(project_dir, material_type, item_id)
    if not mf.exists():
        return None
    if material_type == "worldbuilding":
        return {"content": mf.read_text(encoding="utf-8")}
    elif material_type == "summaries":
        # summaries 是 markdown 文件
        return {"summary_id": item_id, "summary": mf.read_text(encoding="utf-8")}
    return json.loads(mf.read_text(encoding="utf-8"))


def _save_material(project_dir: Path, material_type: str, item_id: str, data: dict) -> None:
    mf = _material_file(project_dir, material_type, item_id)
    mf.parent.mkdir(parents=True, exist_ok=True)
    if material_type == "worldbuilding":
        mf.write_text(data.get("content", ""), encoding="utf-8")
    elif material_type == "summaries":
        mf.write_text(data.get("summary", ""), encoding="utf-8")
    else:
        mf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_materials(project_dir: Path, material_type: str) -> list[dict]:
    """列出指定类型的所有素材"""
    if material_type == "worldbuilding":
        mf = _materials_dir(project_dir) / "worldbuilding.md"
        if mf.exists():
            return [{"world_id": "main", "content": mf.read_text(encoding="utf-8")[:200]}]
        return []

    type_dir = _type_dir(project_dir, material_type)
    if not type_dir.exists():
        return []

    items = []
    for f in type_dir.iterdir():
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append(data)
        elif f.suffix == ".md" and material_type == "summaries":
            data = {"summary_id": f.stem, "summary": f.read_text(encoding="utf-8")[:200]}
            items.append(data)
    return items


def _validate_type(material_type: str) -> bool:
    """验证素材类型是否合法"""
    valid_types = ["plots", "scenes", "summaries", "worldbuilding", "character"]
    return material_type in valid_types or material_type in ["plot", "scene", "summary", "character"]


# ─── 路由 ─────────────────────────────────────────────────────────

@router.get("/materials/{material_type}", response_model=ApiResponse[MaterialListResponse])
async def list_materials(
    material_type: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """获取指定类型素材列表"""
    logger.info("获取素材列表", extra={"material_type": material_type, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    if not _validate_type(material_type):
        raise ValidationError(message=f"无效的素材类型: {material_type}", field="material_type")

    # 统一为复数形式
    if material_type in ["plot", "scene", "summary", "character"]:
        material_type = f"{material_type}s"

    items = _list_materials(project_dir, material_type)
    return ApiResponse.ok(MaterialListResponse(items=items, total=len(items)))


@router.get("/materials/{material_type}/{item_id}", response_model=ApiResponse[dict])
async def get_material(
    material_type: str,
    item_id: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """获取素材详情"""
    logger.info("获取素材详情", extra={"material_type": material_type, "item_id": item_id, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    if not _validate_type(material_type):
        raise ValidationError(message=f"无效的素材类型: {material_type}", field="material_type")

    # 统一为复数形式
    if material_type in ["plot", "scene", "summary", "character"]:
        material_type = f"{material_type}s"

    data = _load_material(project_dir, material_type, item_id)
    if data is None:
        raise ResourceNotFoundError(resource="material", identifier=item_id)

    return ApiResponse.ok(data)


@router.post("/materials/{material_type}", response_model=ApiResponse[dict], status_code=201)
async def create_material(
    material_type: str,
    project_id: str,
    req: MaterialCreateRequest,
    settings: Settings = Depends(get_settings),
):
    """手动创建素材"""
    logger.info("创建素材", extra={"material_type": material_type, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    if not _validate_type(material_type):
        raise ValidationError(message=f"无效的素材类型: {material_type}", field="material_type")

    # 统一为复数形式
    if material_type in ["plot", "scene", "summary", "character"]:
        material_type = f"{material_type}s"

    item_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    if material_type == "plots":
        data = {
            "plot_id": item_id,
            "title": req.title,
            "description": req.description,
            "chapter_range": None,
            "characters": [],
            "importance": "normal",
            "status": "active",
            "created_at": now,
        }
    elif material_type == "scenes":
        data = {
            "scene_id": item_id,
            "location": req.title,
            "description": req.description,
            "time": "",
            "participants": [],
            "atmosphere": "",
            "key_events": [],
            "status": "active",
            "created_at": now,
        }
    elif material_type == "worldbuilding":
        data = {
            "world_id": "main",
            "content": req.description,
            "updated_at": now,
        }
    else:
        data = req.content or {"id": item_id}

    _save_material(project_dir, material_type, item_id, data)
    return ApiResponse.ok(data, message="素材创建成功")


@router.post("/extract", response_model=ApiResponse[dict], status_code=200)
async def submit_extract_task(
    req: ExtractTaskRequest,
    settings: Settings = Depends(get_settings),
):
    """提交提取任务 - 使用LLM从源文件中提取角色/情节/场景/摘要"""
    logger.info("提取任务开始", extra={
        "type": req.type,
        "source_file": req.source_file,
        "project_id": req.project_id,
    })
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    # 验证提取类型
    valid_types = {"character", "plot", "scene", "summary"}
    if req.type not in valid_types:
        raise ValidationError(message=f"不支持的提取类型: {req.type}，支持: {', '.join(valid_types)}")

    # 验证源文件存在
    source_path = project_dir / req.source_file
    if not source_path.exists():
        raise ResourceNotFoundError(resource="file", identifier=req.source_file)

    try:
        # 读取源文件
        file_service = FileService(settings.projects_path)
        source_content, _ = await file_service.read_file(f"{req.project_id}/{req.source_file}")

        # 读取 style-guide
        style_guide = ""
        try:
            content, _ = await file_service.read_file(f"{req.project_id}/style-guide.md")
            style_guide = content
        except Exception:
            pass

        # 渲染提取 prompt
        prompt_engine = PromptEngine(settings.prompts_path, file_service)
        variables = {
            "text": source_content,
            "style_guide": style_guide,
        }
        prompt_text = await prompt_engine.render(f"extract/{req.type}", variables)

        # 调用 LLM（提取任务使用较低温度）
        llm_cfg = load_llm_config_from_workspace(settings)
        svc = LLMService.from_workspace_config(llm_cfg)

        logger.info("LLM提取中", extra={
            "type": req.type,
            "source": req.source_file,
            "text_length": len(source_content),
        })

        result = await svc.complete_sync(
            [{"role": "user", "content": prompt_text}],
            temperature=0.3,
            max_tokens=16000,
            timeout=180,
        )
        result = result.strip()

        # 保存提取结果
        now = datetime.now(timezone.utc).isoformat()
        item_id = str(uuid.uuid4())[:8]

        # 摘要用源文件标识，其他类型用随机 ID
        if req.type == "summary":
            save_id = Path(req.source_file).stem  # sec-001 → sec-001
        else:
            save_id = item_id

        save_type = f"{req.type}s"  # character → characters
        if req.type == "summary":
            # 摘要保存为 markdown
            _save_material(project_dir, "summaries", save_id, {
                "summary": result,
                "source_file": req.source_file,
                "created_at": now,
            })
        else:
            # 角色/情节/场景保存为带 content 字段的 JSON
            _save_material(project_dir, save_type, save_id, {
                f"{req.type}_id": save_id,
                "content": result,
                "source_file": req.source_file,
                "created_at": now,
            })

        # 尝试从结果中提取名称/标题用于列表显示
        title = result.split("\n")[0].strip("# \t")[:60] if result else ""

        logger.info("提取完成", extra={
            "type": req.type,
            "source": req.source_file,
            "result_length": len(result),
        })

        return ApiResponse.ok({
            "id": save_id,
            "type": req.type,
            "title": title,
            "content": result,
            "source_file": req.source_file,
            "created_at": now,
        }, message="提取完成")

    except Exception as e:
        logger.error("提取失败", extra={
            "type": req.type,
            "source": req.source_file,
            "error": str(e)[:200],
        })
        raise


@router.delete("/materials/{material_type}/{item_id}", response_model=ApiResponse[None])
async def delete_material(
    material_type: str,
    item_id: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """删除素材"""
    logger.info("删除素材", extra={"material_type": material_type, "item_id": item_id, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    if not _validate_type(material_type):
        raise ValidationError(message=f"无效的素材类型: {material_type}", field="material_type")

    # 统一为复数形式
    if material_type in ["plot", "scene", "summary", "character"]:
        material_type = f"{material_type}s"

    mf = _material_file(project_dir, material_type, item_id)
    if not mf.exists():
        raise ResourceNotFoundError(resource="material", identifier=item_id)

    await asyncio.to_thread(mf.unlink)
    return ApiResponse.ok(message="素材已删除")
