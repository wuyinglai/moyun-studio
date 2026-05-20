"""墨韵 - LLM服务

封装LiteLLM调用，提供流式输出和重试机制。
"""

import asyncio
from collections.abc import AsyncGenerator
import logging
from typing import TYPE_CHECKING, Any

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import tiktoken
except ImportError:
    tiktoken = None

from backend.core.exceptions import LLMError

if TYPE_CHECKING:
    pass


def load_llm_config_from_workspace(settings) -> dict:
    """从工作区加载 LLM 配置

    按优先级读取：
    1. workspace/llm_config.json（旧格式）
    2. workspace/.config.json 下的 "llm" 键（LLM API 保存的格式）
    3. 回退到 Settings（.env 中的全局配置）

    返回 dict，包含键：apiType, apiKey, apiBase, model, thinking
    """
    import json

    # 1) 旧格式 llm_config.json
    config_file = settings.workspace_path / "llm_config.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return {
                "apiType": data.get("apiType", data.get("api_type", settings.llm_provider)),
                "apiKey": data.get("apiKey") or data.get("api_key") or settings.llm_api_key,
                "apiBase": data.get("apiBase", data.get("api_base", settings.llm_api_base or "")),
                "model": data.get("model", settings.llm_model),
                "thinking": data.get("thinking", settings.llm_thinking),
            }
        except Exception:
            pass

    # 2) .config.json（LLM API 保存到此文件）
    dot_config = settings.workspace_path / ".config.json"
    if dot_config.exists():
        try:
            full = json.loads(dot_config.read_text(encoding="utf-8"))
            data = full.get("llm") or {}
            if data.get("apiKey") or data.get("model"):
                return {
                    "apiType": data.get("apiType", data.get("api_type", settings.llm_provider)),
                    "apiKey": data.get("apiKey") or data.get("api_key") or settings.llm_api_key,
                    "apiBase": data.get("apiBase") or data.get("apiUrl") or data.get("api_base") or settings.llm_api_base or "",
                    "model": data.get("model", settings.llm_model),
                    "thinking": data.get("thinking", settings.llm_thinking),
                }
        except Exception:
            pass

    # 3) 回退到 Settings
    return {
        "apiType": settings.llm_provider,
        "apiKey": settings.llm_api_key,
        "apiBase": settings.llm_api_base or "",
        "model": settings.llm_model,
        "thinking": settings.llm_thinking,
    }


def normalize_model_for_provider(model: str, api_type: str) -> str:
    """为 LiteLLM 调用规范化模型名称

    LiteLLM 使用 ``provider/model`` 格式路由请求。
    DeepSeek API 兼容 OpenAI 格式，但 LiteLLM 1.x 不支持 ``deepseek/`` 前缀，
    所以 deepseek provider 使用 ``openai/`` 前缀。
    """
    api_type = (api_type or "").lower()

    # 处理 api_type == deepseek 但模型已有 deepseek/ 前缀的情况
    if api_type == "deepseek" and model.startswith("deepseek/"):
        return "openai/" + model[len("deepseek/"):]

    if "/" in model:
        return model

    if api_type == "ollama":
        return f"ollama/{model}"
    if api_type == "anthropic":
        return f"anthropic/{model}"
    if api_type == "deepseek":
        # DeepSeek API 兼容 OpenAI 格式，LiteLLM 1.x 不支持 deepseek/ 前缀
        return f"openai/{model}"
    if api_type == "openai":
        # openai/ 前缀可省略，但显式加上更清晰
        return f"openai/{model}"
    # custom：不追加前缀，由 api_base 决定路由
    return model


def build_litellm_kwargs(llm_cfg: dict, model: str, messages: list, **kwargs) -> dict:
    """构建 litellm.acompletion() 的参数字典

    ``llm_cfg`` 由 ``load_llm_config_from_workspace`` 返回，
    额外参数（temperature、max_tokens、stream、timeout 等）
    通过 ``**kwargs`` 传入。
    """
    result = {
        "model": model,
        "messages": messages,
    }

    api_key = llm_cfg.get("apiKey") or llm_cfg.get("api_key")
    if api_key:
        result["api_key"] = api_key

    api_base = llm_cfg.get("apiBase") or llm_cfg.get("api_base")
    if api_base:
        result["api_base"] = api_base

    result.update(kwargs)
    return result


class LLMConfig:
    """LLM配置"""

    # 常见模型的上下文窗口映射
    MODEL_CONTEXT_WINDOW = {
        # OpenAI
        "gpt-4": 8192,
        "gpt-4-0613": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-3.5-turbo-1106": 16384,
        # DeepSeek
        "deepseek-chat": 8192,
        "deepseek-r1-chat": 128000,
        # Qwen
        "qwen-7b-chat": 8192,
        "qwen-14b-chat": 16384,
        "qwen-72b-chat": 32768,
        "qwen-1.5-7b-chat": 32768,
        "qwen-1.5-14b-chat": 32768,
        "qwen-1.5-32b-chat": 64000,
        "qwen-2-7b-instruct": 32768,
        "qwen-2-14b-instruct": 64000,
        "qwen-2-72b-instruct": 128000,
        # Llama 3
        "llama3-8b": 8192,
        "llama3-70b": 8192,
        "llama3-1-8b": 128000,
        "llama3-1-70b": 128000,
        # Mixtral
        "mixtral-8x7b": 32768,
        "mixtral-8x22b": 64000,
        # Claude
        "claude-3-sonnet": 200000,
        "claude-3-opus": 200000,
        "claude-3-5-sonnet": 200000,
        "claude-2": 100000,
    }

    def __init__(
        self,
        provider: str = "openai",
        api_key: str | None = None,
        api_base: str | None = None,
        model: str = "gpt-4",
        max_tokens: int = 16000,
        temperature: float = 0.7,
        context_window: int | None = None,
        reserved_output_tokens: int = 3000,
    ):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.reserved_output_tokens = reserved_output_tokens
        # 根据模型名推断上下文窗口
        self.context_window = context_window or self._infer_context_window(model)

    def _infer_context_window(self, model: str) -> int:
        """根据模型名称推断上下文窗口大小"""
        # 移除 provider 前缀
        model_name = model.split("/")[-1].lower()

        # 精确匹配
        for key, window in self.MODEL_CONTEXT_WINDOW.items():
            if key.lower() in model_name or model_name in key.lower():
                return window

        # 按参数推断
        if "7b" in model_name:
            return 8192
        elif "14b" in model_name:
            return 16384
        elif "32b" in model_name:
            return 32768
        elif "72b" in model_name or "70b" in model_name:
            return 64000

        # 默认返回 GPT-4 级别
        return 8192

    @property
    def max_prompt_tokens(self) -> int:
        """计算最大提示词token数"""
        return max(0, self.context_window - self.reserved_output_tokens)


class LLMService:
    """LLM调用服务

    职责：
    - 封装LiteLLM调用
    - 提供流式输出
    - 自动重试机制
    - Token计数
    - 并发控制（Semaphore）
    """
    logger = logging.getLogger(__name__)

    # 类级别的并发限制（默认最多 3 个并发）
    _semaphore: asyncio.Semaphore | None = None
    _max_concurrent: int = 3

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
        # 确保 Semaphore 已初始化
        if LLMService._semaphore is None:
            LLMService._semaphore = asyncio.Semaphore(self._max_concurrent)

    @classmethod
    def set_max_concurrent(cls, max_concurrent: int) -> None:
        """设置最大并发数（在应用启动时调用）"""
        cls._max_concurrent = max_concurrent
        # 重新创建 Semaphore（已有请求会继续使用旧的）
        cls._semaphore = asyncio.Semaphore(max_concurrent)
        cls.logger.info(f"LLM 并发限制已设置为 {max_concurrent}")

    @classmethod
    def from_workspace_config(cls, config_dict: dict, model: str | None = None) -> "LLMService":
        """从 workspace 配置字典创建 LLMService

        Args:
            config_dict: load_llm_config_from_workspace() 返回的配置字典
            model: 可选，覆盖模型名称
        """
        provider = config_dict.get("apiType", "openai")
        model = model or config_dict.get("model", "gpt-4")
        model = normalize_model_for_provider(model, provider)

        config = LLMConfig(
            provider=provider,
            api_key=config_dict.get("apiKey"),
            api_base=config_dict.get("apiBase"),
            model=model,
        )
        return cls(config)

    @property
    def client(self):
        """懒加载LiteLLM客户端"""
        if self._client is None:
            litellm.drop_params = True
            self._client = litellm
        return self._client

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = True,
        stop_event: asyncio.Event | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """流式生成

        Args:
            messages: 消息列表
            model: 模型名称，默认使用配置中的模型
            stream: 是否流式输出
            stop_event: 可选的停止信号，设置后停止后续输出
            **kwargs: 传递给 litellm 的额外参数（如 timeout, thinking 等）

        Yields:
            生成的文本片段
        """
        model = model or self.config.model

        call_kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        if self.config.api_key:
            call_kwargs["api_key"] = self.config.api_key
        if self.config.api_base:
            call_kwargs["api_base"] = self.config.api_base
        call_kwargs.update(kwargs)

        # 使用 Semaphore 控制并发
        async with self._semaphore:
            try:
                response = await self._call_with_retry(**call_kwargs)

                if stream:
                    async for chunk in response:
                        if stop_event and stop_event.is_set():
                            break
                        if not chunk.choices:
                            continue
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                else:
                    if response.choices:
                        yield response.choices[0].message.content

            except Exception as e:
                raise LLMError(message=f"LLM调用失败: {e!s}")

    async def _call_with_retry(self, **kwargs) -> Any:
        """带重试的调用"""
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            reraise=True
        )
        async def _call():
            return await litellm.acompletion(**kwargs)

        return await _call()

    async def complete_sync(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs,
    ) -> str:
        """同步生成（非流式）"""
        chunks = []
        async for chunk in self.complete(messages, model=model, stream=False, **kwargs):
            chunks.append(chunk)
        result = "".join(chunks)
        return result

    async def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """计算token数"""
        if tiktoken is None:
            from backend.utils.token_utils import estimate_tokens_fallback
            return estimate_tokens_fallback(text)
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.config.api_key and self.config.provider == "openai":
            return False
        return True
