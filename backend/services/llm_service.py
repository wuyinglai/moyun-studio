"""墨韵 - LLM服务实现

封装LLM调用，提供统一的LLM接口。
"""

import json
from typing import Any, AsyncGenerator

import litellm

from backend.config import get_settings
from backend.services.base import LLMServiceInterface


class LLMService(LLMServiceInterface):
    """LLM服务实现"""

    def __init__(self):
        self.settings = get_settings()
        self._config = None

    def _load_config(self) -> dict[str, Any]:
        """加载LLM配置"""
        if self._config is None:
            config_path = self.settings.workspace_path / ".config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    full_config = json.load(f)
                    self._config = full_config.get("llm", {})
            else:
                self._config = {}
        return self._config

    @property
    def provider(self) -> str:
        return self._load_config().get("apiType", "openai")

    @property
    def api_key(self) -> str | None:
        return self._load_config().get("apiKey")

    @property
    def api_base(self) -> str | None:
        return self._load_config().get("apiUrl")

    @property
    def model(self) -> str:
        return self._load_config().get("model", "gpt-4")

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """流式生成"""
        model = model or self.model

        kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        # 设置provider
        if self.provider == "ollama":
            kwargs["api_base"] = self.api_base or "http://localhost:11434"

        try:
            response = await litellm.acompletion(**kwargs)

            if stream:
                async for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            else:
                yield response.choices[0].message.content

        except Exception as e:
            raise Exception(f"LLM调用失败: {str(e)}")

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

    async def count_tokens(self, text: str) -> int:
        """计算token数"""
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(self.model)
            return len(enc.encode(text))
        except Exception:
            # 回退到简单估算
            return len(text) // 4

    async def test_connection(self) -> dict[str, Any]:
        """测试LLM连接"""
        test_messages = [{"role": "user", "content": "你好"}]

        try:
            result = await self.complete_sync(test_messages)
            return {
                "success": True,
                "message": "连接成功",
                "model": self.model,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
            }

    async def list_models(self) -> list[dict[str, str]]:
        """获取可用模型列表"""
        # 这里可以扩展为动态获取模型列表
        # 当前返回常用模型
        return [
            {"id": "gpt-4", "name": "GPT-4"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
            {"id": "claude-3-opus", "name": "Claude 3 Opus"},
            {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet"},
            {"id": "ollama/llama2", "name": "Llama 2 (Ollama)"},
        ]
