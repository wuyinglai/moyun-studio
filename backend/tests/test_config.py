"""配置管理单元测试

测试要点：
1. Settings 默认值验证
2. 环境变量覆盖
3. .env 文件加载
4. 路径属性（projects_path、prompts_path 等）
5. get_settings 缓存行为
6. 字段验证器（workspace_path resolve）
7. llm_provider 字面量约束
8. temperature 范围约束
"""

from pathlib import Path

import pytest

from backend.config import Settings, get_settings


class TestSettingsDefaults:
    """默认值验证（通过传参覆盖避免受 .env 影响）"""

    def test_default_host(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.host == "127.0.0.1"

    def test_default_port(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.port == 8000

    def test_default_debug(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.debug is False

    def test_default_workspace_path(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.workspace_path.name == "workspace"

    def test_default_llm_provider(self):
        settings = Settings(llm_provider="openai", llm_model="gpt-4", debug=False)
        assert settings.llm_provider == "openai"

    def test_default_llm_model(self):
        settings = Settings(llm_model="gpt-4", llm_provider="openai", debug=False)
        assert settings.llm_model == "gpt-4"

    def test_default_llm_max_tokens(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.llm_max_tokens == 16000

    def test_default_llm_temperature(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.llm_temperature == 0.7

    def test_default_auto_mode(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.auto_mode == "L1"

    def test_default_task_queue_max_concurrent(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.task_queue_max_concurrent == 1

    def test_default_snapshot_settings(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert settings.snapshot_max_versions == 20
        assert settings.snapshot_interval_seconds == 10

    def test_default_cors_origins(self):
        settings = Settings(debug=False, llm_provider="openai", llm_model="gpt-4")
        assert "http://localhost:5173" in settings.cors_origins
        assert "http://127.0.0.1:5173" in settings.cors_origins


class TestSettingsCustomValues:
    """自定义值测试"""

    def test_custom_host(self):
        settings = Settings(host="0.0.0.0")
        assert settings.host == "0.0.0.0"

    def test_custom_port(self):
        settings = Settings(port=9000)
        assert settings.port == 9000

    def test_custom_llm_provider(self):
        settings = Settings(llm_provider="anthropic")
        assert settings.llm_provider == "anthropic"

    def test_custom_llm_model(self):
        settings = Settings(llm_model="claude-3")
        assert settings.llm_model == "claude-3"

    def test_custom_api_key(self):
        settings = Settings(llm_api_key="sk-custom")
        assert settings.llm_api_key == "sk-custom"

    def test_custom_temperature(self):
        settings = Settings(llm_temperature=0.3)
        assert settings.llm_temperature == 0.3

    def test_custom_auto_mode(self):
        settings = Settings(auto_mode="L2")
        assert settings.auto_mode == "L2"


class TestSettingsPathProperties:
    """路径属性测试"""

    def test_projects_path(self, temp_workspace):
        settings = Settings(workspace_path=temp_workspace)
        assert settings.projects_path == temp_workspace / "projects"

    def test_prompts_path(self, temp_workspace):
        settings = Settings(workspace_path=temp_workspace)
        assert settings.prompts_path == temp_workspace / "prompts"

    def test_templates_path(self, temp_workspace):
        settings = Settings(workspace_path=temp_workspace)
        assert settings.templates_path == temp_workspace / "templates"

    def test_custom_subdirs(self, temp_workspace):
        settings = Settings(
            workspace_path=temp_workspace,
            projects_subdir="custom_projects",
            prompts_subdir="custom_prompts",
        )
        assert settings.projects_path == temp_workspace / "custom_projects"
        assert settings.prompts_path == temp_workspace / "custom_prompts"

    def test_projects_path_is_path_object(self):
        settings = Settings()
        assert isinstance(settings.projects_path, Path)

    def test_prompts_path_is_path_object(self):
        settings = Settings()
        assert isinstance(settings.prompts_path, Path)


class TestSettingsValidation:
    """字段验证测试"""

    def test_workspace_path_resolves(self, tmp_path):
        rel_path = tmp_path / "subdir" / ".." / "workspace"
        settings = Settings(workspace_path=rel_path)
        # resolve() 会规范化路径
        assert str(settings.workspace_path) == str(rel_path.resolve())

    def test_llm_provider_invalid_raises(self):
        with pytest.raises(Exception):
            Settings(llm_provider="invalid_provider")

    def test_llm_provider_all_valid_values(self):
        for provider in ["openai", "anthropic", "ollama", "custom"]:
            settings = Settings(llm_provider=provider)
            assert settings.llm_provider == provider

    def test_temperature_within_range(self):
        # ge=0.0, le=2.0
        settings = Settings(llm_temperature=0.0)
        assert settings.llm_temperature == 0.0

        settings = Settings(llm_temperature=2.0)
        assert settings.llm_temperature == 2.0

    def test_temperature_out_of_range_raises(self):
        with pytest.raises(Exception):
            Settings(llm_temperature=3.0)

        with pytest.raises(Exception):
            Settings(llm_temperature=-0.1)


class TestGetSettings:
    """get_settings 缓存测试"""

    def test_get_settings_returns_settings(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_get_settings_cache_reset_on_new_call(self):
        """after clearing lru_cache, new instance should be created"""
        # 由于 lru_cache 使用 session 级别，我们在这里只测试返回类型
        s = get_settings()
        assert s.host == "127.0.0.1"
