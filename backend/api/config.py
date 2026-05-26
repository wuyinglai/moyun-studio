"""墨韵 - 全局配置 API

端点：
  GET   /api/config              获取完整配置文件
  PUT   /api/config              保存完整配置文件
  GET   /api/config/custom-params  获取自定义创作参数
  PUT   /api/config/custom-params  保存自定义创作参数

配置文件路径：workspace/.config.json

文档规范 G0104:
{
  "theme": "dark",
  "autoMode": "L1",
  "layout": { "left": 20, "right": 25, "editorChat": 75 },
  "llm": { "apiType": "openai", ... },
  "customParams": { "categories": [...] }
}
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["全局配置"], prefix="/config")

_CUSTOM_PARAMS_KEY = "customParams"


def _config_file(settings: Settings) -> Path:
    return settings.workspace_path / ".config.json"


async def _load_config(settings: Settings) -> dict:
    cf = _config_file(settings)
    if not await asyncio.to_thread(cf.exists):
        return {}
    try:
        text = await asyncio.to_thread(cf.read_text, encoding="utf-8")
        return json.loads(text)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"读取全局配置失败: {e}")
        return {}


async def _save_config(settings: Settings, data: dict) -> None:
    cf = _config_file(settings)
    cf.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    await asyncio.to_thread(cf.write_text, content, encoding="utf-8")


# ─── 完整配置 CRUD ────────────────────────────────────────────

class AppConfigResponse(BaseModel):
    """完整应用配置"""
    theme: str = "dark"
    autoMode: str = "L1"
    layout: dict[str, Any] = Field(default_factory=lambda: {"left": 20, "right": 25, "editorChat": 75})
    llm: dict[str, Any] = Field(default_factory=dict)
    customParams: dict[str, Any] = Field(default_factory=dict)


class UpdateAppConfigRequest(BaseModel):
    """更新完整配置请求"""
    theme: str | None = None
    autoMode: str | None = None
    layout: dict[str, Any] | None = None
    llm: dict[str, Any] | None = None
    customParams: dict[str, Any] | None = None


@router.get("", response_model=ApiResponse[AppConfigResponse])
async def get_app_config(settings: Settings = Depends(get_settings)):
    """获取完整应用配置"""
    config = await _load_config(settings)
    return ApiResponse.ok(AppConfigResponse(
        theme=config.get("theme", "dark"),
        autoMode=config.get("autoMode", "L1"),
        layout=config.get("layout", {"left": 20, "right": 25, "editorChat": 75}),
        llm=config.get("llm", {}),
        customParams=config.get("customParams", {}),
    ))


@router.put("", response_model=ApiResponse[AppConfigResponse])
async def save_app_config(
    req: UpdateAppConfigRequest,
    settings: Settings = Depends(get_settings),
):
    """保存完整应用配置（只更新提供的字段，不覆盖未提供的字段）"""
    config = await _load_config(settings)

    if req.theme is not None:
        config["theme"] = req.theme
    if req.autoMode is not None:
        config["autoMode"] = req.autoMode
    if req.layout is not None:
        config["layout"] = req.layout
    if req.llm is not None:
        config["llm"] = req.llm
    if req.customParams is not None:
        config["customParams"] = req.customParams

    await _save_config(settings, config)

    logger.info("应用配置已更新", extra={"fields": [k for k, v in req.model_dump(exclude_none=True).items()]})
    return ApiResponse.ok(AppConfigResponse(
        theme=config.get("theme", "dark"),
        autoMode=config.get("autoMode", "L1"),
        layout=config.get("layout", {"left": 20, "right": 25, "editorChat": 75}),
        llm=config.get("llm", {}),
        customParams=config.get("customParams", {}),
    ))


# ─── 自定义参数（兼容旧端点）─────────────────────────────────────

class CustomParamsResponse(BaseModel):
    """自定义参数响应"""
    categories: list[dict] = Field(default_factory=list, description="自定义参数类别列表")


class CustomParamCategory(BaseModel):
    """自定义参数类别"""
    key: str = Field(..., description="类别 key")
    label: str = Field(..., description="类别显示名")
    options: list[str] = Field(default_factory=list, description="选项列表")


class UpdateCustomParamsRequest(BaseModel):
    """更新自定义参数请求"""
    categories: list[CustomParamCategory] = Field(..., description="自定义参数类别列表")


@router.get("/custom-params", response_model=ApiResponse[CustomParamsResponse])
async def get_custom_params(settings: Settings = Depends(get_settings)):
    """获取自定义创作参数"""
    config = await _load_config(settings)
    params = config.get(_CUSTOM_PARAMS_KEY, {})
    categories = params.get("categories", [])
    return ApiResponse.ok(CustomParamsResponse(categories=categories))


@router.put("/custom-params", response_model=ApiResponse[CustomParamsResponse])
async def save_custom_params(
    req: UpdateCustomParamsRequest,
    settings: Settings = Depends(get_settings),
):
    """保存自定义创作参数"""
    config = await _load_config(settings)
    config[_CUSTOM_PARAMS_KEY] = {
        "categories": [c.model_dump() for c in req.categories]
    }
    await _save_config(settings, config)

    logger.info("自定义参数已保存", extra={"category_count": len(req.categories)})
    return ApiResponse.ok(
        CustomParamsResponse(categories=[c.model_dump() for c in req.categories]),
        message="自定义参数已保存",
    )
