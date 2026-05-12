"""墨韵 - LLM服务

封装LiteLLM调用，提供流式输出和重试机制。
"""

import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, TYPE_CHECKING

from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.exceptions import LLMError

if TYPE_CHECKING:
    from backend.config import Settings
    from backend.core.exceptions import LLMConfigError


def _get_tiktoken():
    """安全获取tiktoken模块"""
    try:
        import tiktoken
        return tiktoken
    except ImportError:
        logging.getLogger(__name__).warning("tiktoken 未安装，token计数将使用估算")
        return None


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


def load_llm_config_from_workspace(settings: 'Settings') -> dict:
    """从工作区配置文件读取LLM配置
    
    优先读取嵌套的 llm 配置，为空时回退到顶层配置（兼容旧格式）
    
    Args:
        settings: 应用设置对象
        
    Returns:
        LLM配置字典，包含 apiType, apiUrl, apiKey, model 等字段
    """
    cfg_file = settings.workspace_path / ".config.json"
    llm_cfg = {}
    
    if cfg_file.exists():
        try:
            raw_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            # 优先使用嵌套的 llm 配置
            llm_cfg = raw_cfg.get("llm", {})
            # 如果 llm 配置为空或 apiType 为空，回退到顶层配置（兼容旧格式）
            if not llm_cfg or not llm_cfg.get("apiType"):
                llm_cfg = {
                    "apiType": raw_cfg.get("apiType", "openai"),
                    "apiUrl": raw_cfg.get("apiUrl", ""),
                    "apiKey": raw_cfg.get("apiKey", ""),
                    "model": raw_cfg.get("model", ""),
                }
        except Exception as e:
            logging.getLogger(__name__).warning(f"读取LLM配置文件失败: {e}")
    
    return llm_cfg


def normalize_model_for_provider(model: str, api_type: str) -> str:
    """根据提供商规范化模型名称
    
    Args:
        model: 模型名称
        api_type: 提供商类型 (deepseek, openai, etc.)
        
    Returns:
        规范化后的模型名称
    """
    if api_type == "deepseek":
        if model and not model.startswith("deepseek/"):
            model = "deepseek/" + model
        elif not model:
            model = "deepseek/deepseek-chat"
    return model


def build_litellm_kwargs(llm_cfg: dict, model: str, messages: list, timeout: int = 120, **extra_kwargs) -> dict:
    """构建LiteLLM调用参数
    
    Args:
        llm_cfg: LLM配置字典
        model: 模型名称
        messages: 消息列表
        timeout: 请求超时时间（秒），默认120秒
        **extra_kwargs: 额外参数（如temperature, max_tokens等）
        
    Returns:
        LiteLLM调用参数字典
    """
    kwargs = {
        "model": model,
        "messages": messages,
        "timeout": timeout,
        **extra_kwargs
    }
    
    if llm_cfg.get("apiKey"):
        kwargs["api_key"] = llm_cfg["apiKey"]
    if llm_cfg.get("apiUrl"):
        kwargs["api_base"] = llm_cfg["apiUrl"]
    
    return kwargs


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
        try:
            response = await self._call_with_retry(**kwargs)

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
        tiktoken = _get_tiktoken()
        if tiktoken is None:
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return int(chinese_chars * 0.5 + other_chars * 0.25)
        
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
