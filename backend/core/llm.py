"""墨韵 - LLM服务

封装LiteLLM调用，提供流式输出和重试机制。
"""

import logging
from typing import Any, AsyncGenerator, TYPE_CHECKING

import litellm
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.exceptions import LLMError

if TYPE_CHECKING:
    from backend.core.exceptions import LLMConfigError


def load_llm_config_from_workspace(settings) -> dict:
    """从工作区加载 LLM 配置

    优先读取工作区根目录下的 llm_config.json，
    若不存在则回退到 Settings 中的全局配置。

    返回 dict，包含键：apiType, apiKey, apiBase, model, thinking
    """
    import json

    config_file = settings.workspace_path / "llm_config.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            # 统一字段名（支持驼峰和蛇形）
            return {
                "apiType": data.get("apiType", data.get("api_type", settings.llm_provider)),
                "apiKey": data.get("apiKey", data.get("api_key", settings.llm_api_key)),
                "apiBase": data.get("apiBase", data.get("api_base", settings.llm_api_base or "")),
                "model": data.get("model", settings.llm_model),
                "thinking": data.get("thinking", settings.llm_thinking),
            }
        except Exception:
            pass

    # 回退到 Settings
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
    若模型名已包含 ``/``，视为已规范化，直接返回。
    """
    if "/" in model:
        return model

    api_type = (api_type or "").lower()

    if api_type == "ollama":
        return f"ollama/{model}"
    if api_type == "anthropic":
        return f"anthropic/{model}"
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

    def __init__(
        self,
        provider: str = "openai",
        api_key: str | None = None,
        api_base: str | None = None,
        model: str = "gpt-4",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature


class LLMService:
    """LLM调用服务

    职责：
    - 封装LiteLLM调用
    - 提供流式输出
    - 自动重试机制
    - Token计数
    """
    logger = logging.getLogger(__name__)

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

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
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """流式生成

        Args:
            messages: 消息列表
            model: 模型名称，默认使用配置中的模型
            stream: 是否流式输出

        Yields:
            生成的文本片段
        """
        model = model or self.config.model

        kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base

        try:
            response = await self._call_with_retry(**kwargs)

            if stream:
                async for chunk in response:
                    if not chunk.choices:
                        continue
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            else:
                if response.choices:
                    yield response.choices[0].message.content

        except Exception as e:
            raise LLMError(message=f"LLM调用失败: {str(e)}")

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
        model: str | None = None
    ) -> str:
        """同步生成"""
        chunks = []
        async for chunk in self.complete(messages, model=model, stream=True):
            chunks.append(chunk)
        return "".join(chunks)

    async def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """计算token数"""
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
