"""墨韵 - LLM服务

封装LiteLLM调用，提供流式输出和重试机制。
"""

import logging
from typing import Any, AsyncGenerator, TYPE_CHECKING

import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.exceptions import LLMError

if TYPE_CHECKING:
    from backend.core.exceptions import LLMConfigError


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
            import litellm
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
        import litellm

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
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            else:
                yield response.choices[0].message.content

        except Exception as e:
            raise LLMError(message=f"LLM调用失败: {str(e)}")

    async def _call_with_retry(self, **kwargs) -> Any:
        """带重试的调用"""
        import litellm

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
