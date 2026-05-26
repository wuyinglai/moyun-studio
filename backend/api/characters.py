"""墨韵 - 角色管理 API

端点：
  GET    /api/characters              获取角色列表
  GET    /api/characters/{id}         获取角色详情
  POST   /api/characters               创建/更新角色
  DELETE /api/characters/{id}        标记角色为 inactive
"""

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.config import Settings, get_settings
from backend.core.character_service import CharacterService
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
    svc = CharacterService(settings)
    characters = [_dict_to_profile(c) for c in await asyncio.to_thread(svc.list_characters, project_id)]
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
    svc = CharacterService(settings)
    data = await asyncio.to_thread(svc.get_character, project_id, character_id)
    return ApiResponse.ok(_dict_to_profile(data))


@router.post("/characters", response_model=ApiResponse[CharacterProfile], status_code=201)
async def create_character(
    req: CharacterCreateRequest,
    settings: Settings = Depends(get_settings),
):
    """创建新角色"""
    logger.info("创建角色", extra={"name": req.name, "project_id": req.project_id})
    svc = CharacterService(settings)
    character = await asyncio.to_thread(svc.create_character, req.project_id, req)
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
    svc = CharacterService(settings)
    data = await asyncio.to_thread(svc.update_character, project_id, character_id, req)
    return ApiResponse.ok(_dict_to_profile(data), message="角色更新成功")


@router.delete("/characters/{character_id}", response_model=ApiResponse[None])
async def deactivate_character(
    character_id: str,
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """将角色标记为 inactive（不提供物理删除）"""
    logger.info("标记角色为inactive", extra={"character_id": character_id, "project_id": project_id})
    svc = CharacterService(settings)
    await asyncio.to_thread(svc.deactivate_character, project_id, character_id)
    return ApiResponse.ok(message="角色已标记为 inactive")
