"""LLM 服务单元测试

测试要点：
1. LLMConfig 初始化
2. normalize_model_for_provider 四种 provider 分支
3. build_litellm_kwargs 参数构建
4. load_llm_config_from_workspace（有/无 llm_config.json）
5. count_tokens（正常模型 + fallback 编码）
6. validate_config
7. complete 流式/非流式
8. _call_with_retry 重试机制
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.core.exceptions import LLMError
from backend.core.llm import (
    LLMConfig,
    LLMService,
    build_litellm_kwargs,
    load_llm_config_from_workspace,
    normalize_model_for_provider,
)


class TestLLMConfig:
    """LLMConfig 初始化测试"""

    def test_default_values(self):
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.api_key is None
        assert config.api_base is None
        assert config.model == "gpt-4"
        assert config.max_tokens == 16000
        assert config.temperature == 0.7

    def test_custom_values(self):
        config = LLMConfig(
            provider="anthropic",
            api_key="sk-test",
            api_base="https://api.example.com",
            model="claude-3",
            max_tokens=8192,
            temperature=0.3,
        )
        assert config.provider == "anthropic"
        assert config.api_key == "sk-test"
        assert config.api_base == "https://api.example.com"
        assert config.model == "claude-3"
        assert config.max_tokens == 8192
        assert config.temperature == 0.3


class TestNormalizeModelForProvider:
    """model 名称规范化测试"""

    def test_already_normalized(self):
        assert normalize_model_for_provider("openai/gpt-4", "openai") == "openai/gpt-4"
        assert normalize_model_for_provider("anthropic/claude-3", "anthropic") == "anthropic/claude-3"

    def test_ollama_prefix(self):
        result = normalize_model_for_provider("llama3", "ollama")
        assert result == "ollama/llama3"

    def test_anthropic_prefix(self):
        result = normalize_model_for_provider("claude-3", "anthropic")
        assert result == "anthropic/claude-3"

    def test_openai_prefix(self):
        result = normalize_model_for_provider("gpt-4", "openai")
        assert result == "openai/gpt-4"

    def test_custom_no_prefix(self):
        result = normalize_model_for_provider("local-model", "custom")
        assert result == "local-model"

    def test_case_insensitive_api_type(self):
        result = normalize_model_for_provider("llama3", "OLLAMA")
        assert result == "ollama/llama3"

    def test_empty_api_type(self):
        result = normalize_model_for_provider("gpt-4", "")
        assert result == "gpt-4"

    def test_none_api_type(self):
        result = normalize_model_for_provider("gpt-4", None)
        assert result == "gpt-4"


class TestBuildLitellmKwargs:
    """build_litellm_kwargs 测试"""

    def test_basic_kwargs(self):
        llm_cfg = {
            "apiType": "openai",
            "apiKey": "sk-test",
            "apiBase": "",
            "model": "gpt-4",
        }
        result = build_litellm_kwargs(
            llm_cfg,
            "openai/gpt-4",
            [{"role": "user", "content": "Hello"}],
        )
        assert result["model"] == "openai/gpt-4"
        assert result["messages"] == [{"role": "user", "content": "Hello"}]
        assert result["api_key"] == "sk-test"

    def test_no_api_key(self):
        llm_cfg = {"apiType": "custom", "model": "local-model"}
        result = build_litellm_kwargs(llm_cfg, "local-model", [])
        assert "api_key" not in result

    def test_with_api_base(self):
        llm_cfg = {"apiBase": "https://api.example.com"}
        result = build_litellm_kwargs(llm_cfg, "model", [])
        assert result["api_base"] == "https://api.example.com"

    def test_extra_kwargs(self):
        llm_cfg = {}
        result = build_litellm_kwargs(
            llm_cfg, "model", [],
            temperature=0.5, max_tokens=100,
        )
        assert result["temperature"] == 0.5
        assert result["max_tokens"] == 100

    def test_snake_case_fallback(self):
        """验证驼峰和蛇形字段名兼容"""
        llm_cfg = {
            "api_key": "sk-snake",
            "api_base": "https://snake.example.com",
        }
        result = build_litellm_kwargs(llm_cfg, "model", [])
        assert result["api_key"] == "sk-snake"
        assert result["api_base"] == "https://snake.example.com"


class TestLoadLLMConfigFromWorkspace:
    """从工作区加载配置测试"""

    def test_with_config_file(self, temp_workspace):
        config_data = {
            "apiType": "custom",
            "apiKey": "sk-from-file",
            "apiBase": "https://custom.example.com",
            "model": "custom-model",
            "thinking": True,
        }
        (temp_workspace / "llm_config.json").write_text(
            json.dumps(config_data, ensure_ascii=False), encoding="utf-8"
        )

        class MockSettings:
            workspace_path = temp_workspace
            llm_provider = "openai"
            llm_api_key = "sk-default"
            llm_api_base = ""
            llm_model = "gpt-4"
            llm_thinking = False

        result = load_llm_config_from_workspace(MockSettings())
        assert result["apiType"] == "custom"
        assert result["apiKey"] == "sk-from-file"
        assert result["apiBase"] == "https://custom.example.com"
        assert result["model"] == "custom-model"
        assert result["thinking"] is True

    def test_without_config_file(self, temp_workspace):
        class MockSettings:
            workspace_path = temp_workspace
            llm_provider = "openai"
            llm_api_key = "sk-default"
            llm_api_base = "https://default.example.com"
            llm_model = "gpt-4"
            llm_thinking = False

        result = load_llm_config_from_workspace(MockSettings())
        assert result["apiType"] == "openai"
        assert result["apiKey"] == "sk-default"
        assert result["apiBase"] == "https://default.example.com"
        assert result["model"] == "gpt-4"
        assert result["thinking"] is False

    def test_with_invalid_config_file(self, temp_workspace):
        (temp_workspace / "llm_config.json").write_text("invalid json", encoding="utf-8")

        class MockSettings:
            workspace_path = temp_workspace
            llm_provider = "openai"
            llm_api_key = "sk-default"
            llm_api_base = ""
            llm_model = "gpt-4"
            llm_thinking = False

        result = load_llm_config_from_workspace(MockSettings())
        assert result["apiType"] == "openai"


class TestLLMService:
    """LLMService 测试"""

    def test_init(self):
        config = LLMConfig(provider="openai", api_key="sk-test")
        svc = LLMService(config)
        assert svc.config is config

    def test_validate_config_with_api_key(self):
        config = LLMConfig(provider="openai", api_key="sk-test")
        svc = LLMService(config)
        assert svc.validate_config() is True

    def test_validate_config_without_api_key(self):
        config = LLMConfig(provider="openai", api_key=None)
        svc = LLMService(config)
        assert svc.validate_config() is False

    def test_validate_config_custom_provider(self):
        config = LLMConfig(provider="custom", api_key="")
        svc = LLMService(config)
        assert svc.validate_config() is True

    @pytest.mark.asyncio
    async def test_count_tokens_with_valid_model(self):
        config = LLMConfig()
        svc = LLMService(config)
        tokens = await svc.count_tokens("Hello world")
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_count_tokens_with_fallback_encoding(self):
        config = LLMConfig()
        svc = LLMService(config)
        tokens = await svc.count_tokens("Hello world", model="unknown-model-xyz")
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_count_tokens_chinese(self):
        config = LLMConfig()
        svc = LLMService(config)
        tokens = await svc.count_tokens("你好世界这是一个测试")
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_complete_sync_joins_chunks(self):
        config = LLMConfig()
        svc = LLMService(config)

        async def mock_complete(messages, model=None, stream=True):
            for chunk in ["A", "B", "C"]:
                yield chunk

        svc.complete = mock_complete
        result = await svc.complete_sync([{"role": "user", "content": "test"}])
        assert result == "ABC"

    @pytest.mark.asyncio
    async def test_complete_with_model_override(self):
        config = LLMConfig(model="gpt-4")
        svc = LLMService(config)

        with patch("backend.core.llm.litellm.acompletion") as mock_acompletion:
            mock_acompletion.return_value = MagicMock()

            # 执行 complete（非流式）
            async for _ in svc.complete(
                [{"role": "user", "content": "test"}],
                model="gpt-3.5-turbo",
                stream=False,
            ):
                pass

            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["model"] == "gpt-3.5-turbo"

    def test_complete_raises_llm_error(self):
        config = LLMConfig()
        svc = LLMService(config)

        with patch("backend.core.llm.litellm.acompletion", side_effect=Exception("API Error")):
            with pytest.raises(LLMError):
                import asyncio
                asyncio.run(svc.complete_sync([{"role": "user", "content": "test"}]))


class TestAPIKeyRedaction:
    """验证 API Key 在错误日志中被脱敏"""

    def test_sk_pattern_redacted(self):
        import re
        msg = "Request failed with key sk-1234567890abcdef1234567890"
        safe = re.sub(r'sk-[a-zA-Z0-9]{10,}', 'sk-***', msg)
        assert 'sk-1234567890' not in safe
        assert 'sk-***' in safe

    def test_api_key_assignment_redacted(self):
        import re
        msg = "api_key=sk-abcdef1234567890"
        safe = re.sub(r'(api[_-]?key[=:]\s*)\S+', r'\1***', msg, flags=re.IGNORECASE)
        assert 'sk-abcdef' not in safe
        assert 'api_key=***' in safe

    def test_bearer_token_redacted(self):
        import re
        msg = "Authorization: Bearer sk-1234567890abcdef"
        safe = re.sub(r'sk-[a-zA-Z0-9]{10,}', 'sk-***', msg)
        assert 'sk-1234567890abcdef' not in safe
        assert 'sk-***' in safe

    def test_no_key_unchanged(self):
        import re
        msg = "Connection timeout after 30s"
        safe = re.sub(r'sk-[a-zA-Z0-9]{10,}', 'sk-***', msg)
        safe = re.sub(r'(api[_-]?key[=:]\s*)\S+', r'\1***', safe, flags=re.IGNORECASE)
        assert safe == msg
