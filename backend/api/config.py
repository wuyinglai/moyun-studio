"""墨韵 - 全局配置 API

端点：
  GET  /api/config/custom-params  获取自定义创作参数
  PUT  /api/config/custom-params  保存自定义创作参数
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["全局配置"], prefix="/config")

# 配置存储在 workspace/.config.json
_CUSTOM_PARAMS_KEY = "customParams"


def _config_file(settings: Settings) -> Path:
    return settings.workspace_path / ".config.json"


def _load_config(settings: Settings) -> dict:
    cf = _config_file(settings)
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(settings: Settings, data: dict) -> None:
    cf = _config_file(settings)
    cf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    config = _load_config(settings)
    params = config.get(_CUSTOM_PARAMS_KEY, {})
    categories = params.get("categories", [])
    return ApiResponse.ok(CustomParamsResponse(categories=categories))


@router.put("/custom-params", response_model=ApiResponse[CustomParamsResponse])
async def save_custom_params(
    req: UpdateCustomParamsRequest,
    settings: Settings = Depends(get_settings),
):
    """保存自定义创作参数"""
    config = _load_config(settings)
    config[_CUSTOM_PARAMS_KEY] = {
        "categories": [c.model_dump() for c in req.categories]
    }
    _save_config(settings, config)

    logger.info("自定义参数已保存", extra={"category_count": len(req.categories)})
    return ApiResponse.ok(
        CustomParamsResponse(categories=[c.model_dump() for c in req.categories]),
        message="自定义参数已保存",
    )
