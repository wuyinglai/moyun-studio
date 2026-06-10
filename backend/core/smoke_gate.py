"""真实 LLM 冒烟测试 gate 辅助函数

仅对 __llm_smoke_* 隔离项目生效；默认拒绝（allow_real_llm_smoke=False）。
抽离到独立模块，便于 contract 测试直接 import。

设计原则：
1. dry_run=True 的请求永远不受 gate 影响（它们本来就不调 LLM）
2. 普通项目（__llm_smoke_ 前缀外）的真实生成不受 gate 影响
3. __llm_smoke_* 项目的真实生成：
     a. 单文件 generate / chat：需开启 allow_real_llm_smoke 开关
     b. Batch：永远禁止真实 LLM smoke（批量风险高）
4. 拒绝时返回 403，code = REAL_LLM_SMOKE_DISABLED / BATCH_REAL_LLM_SMOKE_FORBIDDEN

smoke 专用 max_tokens 当前仅在配置中声明（Settings.llm_smoke_max_tokens）；
后续可在 LLMService 层接入。
"""

from typing import Optional

from fastapi import status
from fastapi.responses import JSONResponse

from backend.config import Settings


LLM_SMOKE_PROJECT_PREFIX = "__llm_smoke_"
REAL_LLM_SMOKE_DISABLED_CODE = "REAL_LLM_SMOKE_DISABLED"
BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE = "BATCH_REAL_LLM_SMOKE_FORBIDDEN"
# smoke 最大 tokens 硬上限（最终 cap，防止配置溢出）
LLM_SMOKE_MAX_TOKENS_HARD_CAP = 1024
# smoke 最大 tokens 默认值（与 Settings.llm_smoke_max_tokens 默认一致）
LLM_SMOKE_MAX_TOKENS_DEFAULT = 300


def is_llm_smoke_project(project_id: str) -> bool:
    """判断是否为真实 LLM 冒烟测试隔离项目"""
    return bool(project_id and project_id.startswith(LLM_SMOKE_PROJECT_PREFIX))


def build_smoke_disabled_response(message: str, code: str) -> JSONResponse:
    """构建 smoke gate 拒绝响应（403）"""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "success": False,
            "code": code,
            "message": message,
            "data": None,
        },
    )


def check_real_llm_smoke_gate(
    settings: Settings,
    project_id: str,
    dry_run: bool,
) -> Optional[JSONResponse]:
    """
    对真实 LLM smoke 项目进行 gate 检查。

    返回 None 表示放行；返回 JSONResponse 表示拒绝。
    """
    if dry_run:
        # dry-run 不触发 LLM，永远放行
        return None
    if not is_llm_smoke_project(project_id):
        # 非 smoke 测试项目，不进入 smoke gate
        return None
    # smoke 项目且 dry_run=False：必须显式开启开关
    if not settings.allow_real_llm_smoke:
        return build_smoke_disabled_response(
            message=(
                "真实 LLM 冒烟测试未开启；请设置 MOYUN_ALLOW_REAL_LLM_SMOKE=1 "
                "或使用 dry_run=True 模拟。注意：__llm_smoke_* 项目仅用于冒烟测试。"
            ),
            code=REAL_LLM_SMOKE_DISABLED_CODE,
        )
    return None


def check_batch_real_llm_smoke_gate(
    settings: Settings,
    project_id: str,
    dry_run: bool,
) -> Optional[JSONResponse]:
    """
    Batch 专用 gate：Batch 永远不允许真实 LLM smoke（批量风险高）。
    """
    if dry_run:
        return None
    if not is_llm_smoke_project(project_id):
        # 非 smoke 项目 → 走通用 gate
        return check_real_llm_smoke_gate(settings, project_id, dry_run)
    # smoke 项目 + Batch + dry_run=False → 永远拒绝
    return build_smoke_disabled_response(
        message=(
            "Batch 真实 LLM 冒烟测试被禁止；请使用 dry_run=True 进行模拟测试。"
            "真实 LLM 冒烟请使用单文件 generate 入口。"
        ),
        code=BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE,
    )


def get_smoke_max_tokens(settings: Settings) -> int:
    """
    返回 smoke 专用 max_tokens，强制落在 [1, LLM_SMOKE_MAX_TOKENS_HARD_CAP] 区间内。
    非 smoke 项目不应调用此函数。
    """
    raw = getattr(settings, "llm_smoke_max_tokens", LLM_SMOKE_MAX_TOKENS_DEFAULT)
    try:
        raw_int = int(raw)
    except (TypeError, ValueError):
        raw_int = LLM_SMOKE_MAX_TOKENS_DEFAULT
    return min(max(raw_int, 1), LLM_SMOKE_MAX_TOKENS_HARD_CAP)


def maybe_apply_smoke_max_tokens(
    settings: Settings,
    project_id: str,
    llm_extra_kwargs: dict | None,
) -> dict:
    """
    在不破坏现有接口的前提下，对 smoke 项目强制覆盖 max_tokens。

    - 非 smoke 项目 → 直接返回输入 dict
    - smoke 项目 → 返回一个新 dict（不会修改输入对象），新增 max_tokens=llm_smoke_max_tokens
    """
    if not is_llm_smoke_project(project_id):
        return llm_extra_kwargs or {}

    smoke_tokens = get_smoke_max_tokens(settings)
    merged = dict(llm_extra_kwargs or {})
    merged["max_tokens"] = smoke_tokens
    return merged
