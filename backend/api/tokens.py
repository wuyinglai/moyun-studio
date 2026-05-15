"""墨韵 - Token 计数 API

端点：
  POST /api/tokens/count    计算文本的token数
  POST /api/tokens/estimate 估算项目/模板的token数
"""

import logging
import tiktoken
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ValidationError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Token计数"], prefix="/tokens")

# ─── 模型上下文长度映射 ───────────────────────────────────────────────
# 来源：各模型的官方文档

MODEL_CONTEXT_LENGTHS: dict[str, int] = {
    # GPT-4 系列
    "gpt-4": 8192,
    "gpt-4-0613": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4-turbo-2024-04-09": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,

    # GPT-3.5 系列
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-0613": 16385,
    "gpt-3.5-turbo-16k": 16385,

    # Claude 系列
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-2.1": 200000,
    "claude-2": 100000,

    # DeepSeek 系列
    "deepseek-chat": 64000,
    "deepseek-coder": 16000,

    # 通义千问
    "qwen-turbo": 128000,
    "qwen-plus": 128000,
    "qwen-max": 128000,

    # Gemini
    "gemini-pro": 32768,
    "gemini-ultra": 32768,
}

DEFAULT_CONTEXT_LENGTH = 4096  # 未知模型默认上下文长度


# ─── Schema ──────────────────────────────────────────────────────────

class TokenCountRequest(BaseModel):
    """Token计数请求"""
    text: str = Field(..., description="待计算的文本")
    model: str = Field(default="gpt-4", description="模型名称")


class TokenCountResponse(BaseModel):
    """Token计数响应"""
    tokens: int = Field(..., description="Token数")
    model: str = Field(..., description="使用的模型")
    max_context: int = Field(..., description="模型最大上下文长度")
    remaining: int = Field(..., description="剩余可用Token数")


class TokenEstimateRequest(BaseModel):
    """Token估算请求"""
    project_id: str = Field(..., description="项目ID")
    target: str = Field(
        ...,
        description="目标类型: prompt/chapter/outline",
        pattern="^(prompt|chapter|outline)$"
    )
    template: str | None = Field(None, description="模板路径（target=prompt时必填）")
    variables: dict[str, Any] | None = Field(None, description="模板变量")


class TokenEstimateResponse(BaseModel):
    """Token估算响应"""
    estimated_tokens: int = Field(..., description="估算Token数")
    target: str = Field(..., description="目标类型")
    template: str | None = Field(None, description="模板路径")


# ─── 工具函数 ────────────────────────────────────────────────────────

def _get_context_length(model: str) -> int:
    """获取模型的上下文长度"""
    # 尝试精确匹配
    if model in MODEL_CONTEXT_LENGTHS:
        return MODEL_CONTEXT_LENGTHS[model]

    # 尝试前缀匹配
    for known_model, length in MODEL_CONTEXT_LENGTHS.items():
        if model.startswith(known_model):
            return length

    # 默认值
    return DEFAULT_CONTEXT_LENGTH


async def _count_tokens_async(text: str, model: str = "gpt-4") -> int:
    """异步计算Token数"""
    try:
        try:
            enc = tiktoken.encoding_for_model(model)
        except (KeyError, tiktoken.TiktokenError):
            enc = tiktoken.get_encoding("cl100k_base")

        tokens = len(enc.encode(text))
        return tokens

    except Exception as e:
        logger.warning(f"tiktoken 计算失败，使用估算方法: {e}")
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        from backend.utils.token_utils import estimate_tokens_fallback
        return estimate_tokens_fallback(text)

# ─── 路由 ────────────────────────────────────────────────────────────

@router.post("/count", response_model=ApiResponse[TokenCountResponse])
async def count_tokens(
    req: TokenCountRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[TokenCountResponse]:
    """计算文本的token数

    Args:
        req: 计数请求

    Returns:
        Token数统计
    """
    tokens = await _count_tokens_async(req.text, req.model)
    max_context = _get_context_length(req.model)
    remaining = max(0, max_context - tokens)

    logger.debug(
        "Token计数: 模型=%s, Token数=%d, 最大上下文=%d, 剩余=%d",
        req.model, tokens, max_context, remaining
    )

    return ApiResponse.ok(TokenCountResponse(
        tokens=tokens,
        model=req.model,
        max_context=max_context,
        remaining=remaining
    ))


@router.post("/estimate", response_model=ApiResponse[TokenEstimateResponse])
async def estimate_tokens(
    req: TokenEstimateRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[TokenEstimateResponse]:
    """估算项目/模板的token数

    Args:
        req: 估算请求

    Returns:
        估算Token数
    """
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    text = ""

    if req.target == "prompt":
        # 估算Prompt模板渲染后的Token数
        if not req.template:
            raise ValidationError(message="template参数必填", field="template")

        # 读取模板文件
        template_path = settings.prompts_path / req.template / "main.md"
        if template_path.exists():
            template_content = template_path.read_text(encoding="utf-8")
            # 简单估算：模板变量替换后的长度
            text = template_content
            if req.variables:
                for key, value in req.variables.items():
                    if isinstance(value, str):
                        text = text.replace(f"{{{{{key}}}}}", value)
        else:
            text = ""

    elif req.target == "chapter":
        # 估算最新章节的Token数
        chapters_dir = project_dir / "chapters"
        if chapters_dir.exists():
            # 查找最新章节
            chapter_files = list(chapters_dir.rglob("sec-*.md"))
            if chapter_files:
                latest = max(chapter_files, key=lambda f: f.stat().st_mtime)
                text = latest.read_text(encoding="utf-8")

    elif req.target == "outline":
        # 估算大纲文件的Token数
        outline_file = project_dir / "outline.md"
        if outline_file.exists():
            text = outline_file.read_text(encoding="utf-8")

    # 计算Token数
    tokens = await _count_tokens_async(text)

    logger.debug(
        "Token估算: 项目=%s, 目标=%s, 模板=%s, 估算Token=%d",
        req.project_id, req.target, req.template, tokens
    )

    return ApiResponse.ok(TokenEstimateResponse(
        estimated_tokens=tokens,
        target=req.target,
        template=req.template
    ))
