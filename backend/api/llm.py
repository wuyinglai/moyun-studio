"""墨韵 - LLM 配置 API

端点：
  GET  /api/llm/config      获取当前LLM配置
  POST /api/llm/config      保存LLM配置
  GET  /api/llm/models      获取可用模型列表
  POST /api/llm/test        测试连接
  GET  /api/llm/status      获取LLM状态
"""

import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Request

from backend.config import Settings, get_settings
from backend.core.exceptions import RateLimitError
from backend.core.llm import load_llm_config_from_workspace, normalize_model_for_provider
from backend.schemas.common import ApiResponse
from backend.schemas.llm import (
    LLMConfigRequest,
    LLMConfigResponse,
    LLMModelsResponse,
    LLMStatusResponse,
    ModelInfo,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["llm"], prefix="/llm")

# 简单的内存速率限制器
_rate_limit_store: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 10  # 测试连接间隔至少10秒

# LLM 配置存储在 workspace/.config.json
_LLM_CONFIG_KEY = "llm"


def _config_file(settings: Settings) -> Path:
    return settings.workspace_path / ".config.json"


def _load_global_config(settings: Settings) -> dict:
    cf = _config_file(settings)
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_global_config(settings: Settings, data: dict) -> None:
    cf = _config_file(settings)
    cf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/config", response_model=ApiResponse[LLMConfigResponse])
async def get_llm_config(settings: Settings = Depends(get_settings)):
    """获取当前LLM配置（不返回API Key）"""
    cfg = _load_global_config(settings).get(_LLM_CONFIG_KEY, {})
    return ApiResponse.ok(
        LLMConfigResponse(
            api_type=cfg.get("apiType", settings.llm_provider),
            api_url=cfg.get("apiUrl", settings.llm_api_base),
            model=cfg.get("model", settings.llm_model),
            thinking=cfg.get("thinking", settings.llm_thinking),
        )
    )


@router.post("/config", response_model=ApiResponse[None])
async def save_llm_config(
    req: LLMConfigRequest,
    settings: Settings = Depends(get_settings),
):
    """保存LLM配置"""
    data = _load_global_config(settings)
    data[_LLM_CONFIG_KEY] = {
        "apiType": req.api_type,
        "apiUrl": req.api_url,
        "apiKey": req.api_key,
        "model": req.model,
        "thinking": req.thinking,
    }
    _save_global_config(settings, data)
    logger.info("LLM配置已保存", extra={"api_type": req.api_type, "model": req.model})
    return ApiResponse.ok(message="配置已保存")


@router.get("/status", response_model=ApiResponse[LLMStatusResponse])
async def get_llm_status(settings: Settings = Depends(get_settings)):
    """获取LLM连接状态（快速检查，不发真实请求）"""
    cfg = _load_global_config(settings).get(_LLM_CONFIG_KEY, {})
    api_key = cfg.get("apiKey", settings.llm_api_key)
    model = cfg.get("model", settings.llm_model)
    api_type = cfg.get("apiType", settings.llm_provider)

    # Ollama 不需要 key
    has_key = bool(api_key) or api_type == "ollama"
    has_model = bool(model)

    if has_key and has_model:
        return ApiResponse.ok(
            LLMStatusResponse(connected=True, model=model, message="配置就绪")
        )
    else:
        msg = "缺少API Key" if not has_key else "未配置模型"
        return ApiResponse.ok(
            LLMStatusResponse(connected=False, model=model, message=msg)
        )


@router.post("/test", response_model=ApiResponse[LLMStatusResponse])
async def test_connection(
    request: Request,
    settings: Settings = Depends(get_settings)
):
    """测试LLM连接（发送一个最小请求）"""
    # 速率限制：10秒内只能测试一次
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    last_test_time = _rate_limit_store.get(client_ip, 0)
    if now - last_test_time < _RATE_LIMIT_SECONDS:
        remaining = int(_RATE_LIMIT_SECONDS - (now - last_test_time))
        raise RateLimitError(retry_after=remaining)
    _rate_limit_store[client_ip] = now

    llm_cfg = load_llm_config_from_workspace(settings)
    model = llm_cfg.get("model", settings.llm_model)
    api_type = llm_cfg.get("apiType", settings.llm_provider)
    model = normalize_model_for_provider(model, api_type)

    try:
        logger.info("开始测试LLM连接", extra={"model": model, "api_type": api_type})

        api_key = llm_cfg.get("apiKey") or settings.llm_api_key
        api_base = (llm_cfg.get("apiBase") or llm_cfg.get("apiUrl") or settings.llm_api_base or "").rstrip("/")

        import json as _json, requests as _req
        sess = _req.Session()
        sess.trust_env = False
        resp = sess.post(
            f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": llm_cfg.get("model", settings.llm_model), "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5},
            timeout=30,
        )
        sess.close()
        resp.raise_for_status()
        data = resp.json()
        logger.info("LLM连接测试成功", extra={"model": model})
        return ApiResponse.ok(
            LLMStatusResponse(connected=True, model=model, message="连接成功")
        )
    except TimeoutError as e:
        logger.warning("LLM连接测试超时", extra={"model": model})
        return ApiResponse.ok(
            LLMStatusResponse(connected=False, model=model, message="连接超时")
        )
    except Exception as e:
        import traceback
        err_type = type(e).__name__
        err_msg = str(e)[:200]
        tb = traceback.format_exc()
        logger.error(f"LLM连接测试失败: [{err_type}] {err_msg}\n{tb[:500]}")
        return ApiResponse.ok(
            LLMStatusResponse(connected=False, model=model, message=f"[{err_type}] {err_msg}")
        )


@router.get("/models", response_model=ApiResponse[LLMModelsResponse])
async def get_models(settings: Settings = Depends(get_settings)):
    """获取可用模型列表"""
    cfg = _load_global_config(settings).get(_LLM_CONFIG_KEY, {})
    api_type = cfg.get("apiType", settings.llm_provider)

    # 预设模型列表
    presets: dict[str, list[ModelInfo]] = {
        "openai": [
            ModelInfo(id="gpt-4o", name="GPT-4o"),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini"),
            ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo"),
            ModelInfo(id="gpt-3.5-turbo", name="GPT-3.5 Turbo"),
        ],
        "anthropic": [
            ModelInfo(id="claude-3-5-sonnet-20241022", name="Claude 3.5 Sonnet"),
            ModelInfo(id="claude-3-5-haiku-20241022", name="Claude 3.5 Haiku"),
            ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus"),
        ],
        "deepseek": [
            ModelInfo(id="openai/deepseek-v4-flash", name="DeepSeek V4 Flash (推荐)"),
            ModelInfo(id="openai/deepseek-chat", name="DeepSeek Chat"),
            ModelInfo(id="openai/deepseek-coder", name="DeepSeek Coder"),
        ],
        "ollama": [
            ModelInfo(id="llama3.2", name="Llama 3.2"),
            ModelInfo(id="qwen2.5", name="Qwen 2.5"),
            ModelInfo(id="deepseek-r1", name="DeepSeek R1"),
        ],
        "custom": [],
    }

    models = presets.get(api_type, [])
    return ApiResponse.ok(LLMModelsResponse(models=models))
