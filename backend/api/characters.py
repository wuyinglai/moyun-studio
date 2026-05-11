"""墨韵 - 角色管理 API

端点：
  GET    /api/characters              获取角色列表
  GET    /api/characters/{id}         获取角色详情
  POST   /api/characters               创建/更新角色
  DELETE /api/characters/{id}        标记角色为 inactive
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["characters"])


# ─── Schema ─────────────────────────────────────────────────────────

class CharacterProfile(BaseModel):
    character_id: str
    name: str
    role: str = "supporting"  # protagonist, antagonist, supporting
    age: str | None = None
    appearance: str = ""
    personality: str = ""
    background: str = ""
    abilities: list[str] = []
    relationships: dict[str, str] = {}  # other_character_id -> relationship
    status: str = "active"  # active, inactive
    created_at: str = ""
    updated_at: str = ""


class CharacterListResponse(BaseModel):
    characters: list[CharacterProfile]
    total: int


class CharacterCreateRequest(BaseModel):
    project_id: str
    name: str
    role: str = "supporting"
    age: str | None = None
    appearance: str = ""
    personality: str = ""
    background: str = ""
    abilities: list[str] = []
    relationships: dict[str, str] = {}


class CharacterUpdateRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    age: str | None = None
    appearance: str | None = None
    personality: str | None = None
    background: str | None = None
    abilities: list[str] | None = None
    relationships: dict[str, str] | None = None


# ─── 辅助函数 ──────────────────────────────────────────────────────

def _characters_dir(project_dir: Path) -> Path:
    return project_dir / "characters"


def _ensure_characters_dir(project_dir: Path) -> Path:
    cd = _characters_dir(project_dir)
    cd.mkdir(parents=True, exist_ok=True)
    return cd


def _character_file(project_dir: Path, character_id: str) -> Path:
    return _characters_dir(project_dir) / f"{character_id}.json"


def _load_character(project_dir: Path, character_id: str) -> dict | None:
    cf = _character_file(project_dir, character_id)
    if not cf.exists():
        return None
    return json.loads(cf.read_text(encoding="utf-8"))


def _save_character(project_dir: Path, character: dict) -> None:
    cf = _character_file(project_dir, character["character_id"])
    cf.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")


def _dict_to_profile(data: dict) -> CharacterProfile:
    return CharacterProfile(**{k: v for k, v in data.items() if k in CharacterProfile.model_fields})


# ─── 路由 ─────────────────────────────────────────────────────────

@router.get("/characters", response_model=ApiResponse[CharacterListResponse])
async def list_characters(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """获取项目角色列表"""
    logger.info("获取角色列表", extra={"project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    char_dir = _characters_dir(project_dir)
    if not char_dir.exists():
        return ApiResponse.ok(CharacterListResponse(characters=[], total=0))

    characters: list[CharacterProfile] = []
    for cf in char_dir.glob("*.json"):
        data = json.loads(cf.read_text(encoding="utf-8"))
        characters.append(_dict_to_profile(data))

    # 按名称排序
    characters.sort(key=lambda c: c.name)
    return ApiResponse.ok(CharacterListResponse(characters=characters, total=len(characters)))


@router.get("/characters/{character_id}", response_model=ApiResponse[CharacterProfile])
async def get_character(
    character_id: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """获取角色详情"""
    logger.info("获取角色详情", extra={"character_id": character_id, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    data = _load_character(project_dir, character_id)
    if data is None:
        raise ResourceNotFoundError(resource="character", identifier=character_id)

    return ApiResponse.ok(_dict_to_profile(data))


@router.post("/characters", response_model=ApiResponse[CharacterProfile], status_code=201)
async def create_character(
    req: CharacterCreateRequest,
    settings: Settings = Depends(get_settings),
):
    """创建新角色"""
    logger.info("创建角色", extra={"name": req.name, "project_id": req.project_id})
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    _ensure_characters_dir(project_dir)

    # 检查是否已存在同名角色（允许同名但用不同ID）
    character_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    character = {
        "character_id": character_id,
        "name": req.name,
        "role": req.role,
        "age": req.age,
        "appearance": req.appearance,
        "personality": req.personality,
        "background": req.background,
        "abilities": req.abilities,
        "relationships": req.relationships,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }

    _save_character(project_dir, character)
    return ApiResponse.ok(_dict_to_profile(character), message="角色创建成功")


@router.put("/characters/{character_id}", response_model=ApiResponse[CharacterProfile])
async def update_character(
    character_id: str,
    project_id: str,
    req: CharacterUpdateRequest,
    settings: Settings = Depends(get_settings),
):
    """更新角色信息"""
    logger.info("更新角色", extra={"character_id": character_id, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    data = _load_character(project_dir, character_id)
    if data is None:
        raise ResourceNotFoundError(resource="character", identifier=character_id)

    # 更新字段
    for field in ["name", "role", "age", "appearance", "personality", "background", "abilities", "relationships"]:
        value = getattr(req, field, None)
        if value is not None:
            data[field] = value

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_character(project_dir, data)

    return ApiResponse.ok(_dict_to_profile(data), message="角色更新成功")


@router.delete("/characters/{character_id}", response_model=ApiResponse[None])
async def deactivate_character(
    character_id: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """将角色标记为 inactive（不提供物理删除）"""
    logger.info("标记角色为inactive", extra={"character_id": character_id, "project_id": project_id})
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    data = _load_character(project_dir, character_id)
    if data is None:
        raise ResourceNotFoundError(resource="character", identifier=character_id)

    data["status"] = "inactive"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_character(project_dir, data)

    return ApiResponse.ok(message="角色已标记为 inactive")
