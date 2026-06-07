"""墨韵 - Scene Plan API 路由

端点：
  POST /api/scene-plan/validate  校验 Scene Plan 结构
"""

from typing import Any
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.core.scene_plan_validator import validate_scene_plan
from backend.schemas.common import ApiResponse
from backend.schemas.scene_plan import ScenePlan

logger = logging.getLogger(__name__)
router = APIRouter(tags=["scene-plan"], prefix="/scene-plan")


# ─── Schema ──────────────────────────────────────────────────────────

class ScenePlanValidationErrorDetail(BaseModel):
    """校验错误详情"""
    field: str
    message: str


class ScenePlanValidationWarningDetail(BaseModel):
    """校验警告详情"""
    field: str
    message: str


class ScenePlanValidateResponse(BaseModel):
    """Scene Plan 校验响应"""
    valid: bool
    errors: list[ScenePlanValidationErrorDetail] = Field(default_factory=list)
    warnings: list[ScenePlanValidationWarningDetail] = Field(default_factory=list)


# ─── 路由 ────────────────────────────────────────────────────────────

@router.post("/validate", response_model=ApiResponse[ScenePlanValidateResponse])
async def validate_scene_plan_api(
    scene_plan_data: ScenePlan | dict[str, Any],
) -> ApiResponse[ScenePlanValidateResponse]:
    """校验 Scene Plan

    不调用 LLM，不写文件，不创建 candidate，只做纯数据校验。

    Args:
        scene_plan_data: ScenePlan 对象或字典

    Returns:
        校验结果，包含 valid、errors、warnings
    """
    logger.debug("Scene Plan 校验请求")

    # 调用校验器
    result = validate_scene_plan(scene_plan_data)

    # 转换结果格式
    errors = [
        ScenePlanValidationErrorDetail(field=e.field, message=e.message)
        for e in result.errors
    ]
    warnings = [
        ScenePlanValidationWarningDetail(field=w.field, message=w.message)
        for w in result.warnings
    ]

    response = ScenePlanValidateResponse(
        valid=result.valid,
        errors=errors,
        warnings=warnings,
    )

    logger.debug("Scene Plan 校验完成: valid=%s, errors=%d, warnings=%d",
                 result.valid, len(errors), len(warnings))

    return ApiResponse.ok(response)
