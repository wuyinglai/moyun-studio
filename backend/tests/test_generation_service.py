"""生成服务安全策略测试

测试要点：
1. fallback rewrite 不直接覆盖正式文件，生成 candidate
2. batch_generate 对已有 sec 文件不直接覆盖
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.config import Settings
from backend.core.generation_service import GenerationService


def _make_project(workspace: Path, project_id: str = "test-project") -> Path:
    """创建测试项目目录结构"""
    project_dir = workspace / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "chapters").mkdir(exist_ok=True)
    (project_dir / "characters").mkdir(exist_ok=True)
    (project_dir / "materials").mkdir(exist_ok=True)
    (project_dir / "outline.md").write_text("# 大纲", encoding="utf-8")
    (project_dir / "style-guide.md").write_text("# 文风", encoding="utf-8")
    (project_dir / "story-state.md").write_text("# 状态", encoding="utf-8")
    (project_dir / "recent-context.md").write_text("# 上下文", encoding="utf-8")
    return project_dir


class TestFallbackRewriteSafety:
    """fallback rewrite 安全策略测试"""

    @pytest.mark.asyncio
    async def test_fallback_rewrite_generates_candidate(self, temp_workspace):
        """fallback rewrite 必须生成候选稿，不直接覆盖正式文件"""
        settings = Settings(
            workspace_path=temp_workspace,
            llm_provider="custom",
            llm_api_key="fake-key",
            llm_model="fake-model",
        )
        service = GenerationService(settings)

        project_dir = _make_project(temp_workspace)
        target_file = "chapters/test.md"
        (project_dir / target_file).write_text("原始内容", encoding="utf-8")

        # Mock LLM service
        mock_llm = MagicMock()
        mock_llm.config.max_prompt_tokens = 120000
        mock_llm.config.context_window = 128000
        mock_llm.config.reserved_output_tokens = 8000

        async def mock_complete(*args, **kwargs):
            yield "生成的新内容"

        mock_llm.complete = mock_complete

        # 收集事件
        events = []
        with patch("backend.core.generation_service.LLMService") as MockLLM, \
             patch("backend.core.generation_service.load_llm_config_from_workspace") as mock_load:
            MockLLM.from_workspace_config.return_value = mock_llm
            mock_load.return_value = {"model": "fake", "thinking": False}

            async for event in service.generate_stream(
                project_id="test-project",
                file_path=target_file,
                prompt_type="custom/rewrite",
                extra_vars={},
                mode="rewrite",
                task_id="test-rewrite-001",
            ):
                events.append(event)

        # 验证原始文件未被覆盖
        original_content = (project_dir / target_file).read_text(encoding="utf-8")
        assert original_content == "原始内容", "fallback rewrite 不应直接覆盖正式文件"

        # 验证生成了 candidate_created 事件
        event_types = [e.get("event") for e in events]
        assert "candidate_created" in event_types, "fallback rewrite 应生成候选稿"


class TestBatchGenerateSafety:
    """batch_generate 安全策略测试"""

    @pytest.mark.asyncio
    async def test_batch_generate_skips_existing_sec(self, temp_workspace):
        """batch_generate 对已有内容的 sec 文件应生成候选稿，不直接覆盖"""
        settings = Settings(
            workspace_path=temp_workspace,
            llm_provider="custom",
            llm_api_key="fake-key",
            llm_model="fake-model",
        )
        service = GenerationService(settings)

        project_dir = _make_project(temp_workspace)
        vol_dir = project_dir / "chapters" / "vol-01"
        ch_dir = vol_dir / "ch-001"
        ch_dir.mkdir(parents=True)

        # 创建已有内容的 sec 文件
        (ch_dir / "sec-001.md").write_text("已有场景内容", encoding="utf-8")
        (ch_dir / "ch-meta.json").write_text(
            json.dumps({"title": "第一章", "status": "draft"}),
            encoding="utf-8",
        )

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.config.max_prompt_tokens = 120000
        mock_llm.config.context_window = 128000
        mock_llm.config.reserved_output_tokens = 8000
        mock_llm.complete_sync = AsyncMock(return_value="新生成的场景内容")

        with patch("backend.core.generation_service.LLMService") as MockLLM, \
             patch("backend.core.generation_service.load_llm_config_from_workspace") as mock_load:
            MockLLM.from_workspace_config.return_value = mock_llm
            mock_load.return_value = {"model": "fake", "thinking": False}

            result = await service.batch_generate(
                project_id="test-project",
                prompt_type="generate/continuation",
                volume_number=1,
                chapter_number=1,
                section_numbers=[1],
            )

        # 验证原始文件未被覆盖
        original_content = (ch_dir / "sec-001.md").read_text(encoding="utf-8")
        assert original_content == "已有场景内容", "batch_generate 不应直接覆盖已有 sec 文件"

        # 验证任务状态为 candidate 或 skipped
        if result.tasks:
            assert result.tasks[0].status in ("candidate", "skipped"), \
                f"已有内容的 sec 文件应生成候选稿或跳过，实际状态: {result.tasks[0].status}"

    @pytest.mark.asyncio
    async def test_batch_generate_writes_empty_sec(self, temp_workspace):
        """batch_generate 对空的 sec 文件可以直接写入"""
        settings = Settings(
            workspace_path=temp_workspace,
            llm_provider="custom",
            llm_api_key="fake-key",
            llm_model="fake-model",
        )
        service = GenerationService(settings)

        project_dir = _make_project(temp_workspace)
        vol_dir = project_dir / "chapters" / "vol-01"
        ch_dir = vol_dir / "ch-001"
        ch_dir.mkdir(parents=True)

        # 创建空的 sec 文件
        (ch_dir / "sec-001.md").write_text("", encoding="utf-8")
        (ch_dir / "ch-meta.json").write_text(
            json.dumps({"title": "第一章", "status": "draft"}),
            encoding="utf-8",
        )

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.config.max_prompt_tokens = 120000
        mock_llm.config.context_window = 128000
        mock_llm.config.reserved_output_tokens = 8000
        mock_llm.complete_sync = AsyncMock(return_value="新生成的场景内容")

        with patch("backend.core.generation_service.LLMService") as MockLLM, \
             patch("backend.core.generation_service.load_llm_config_from_workspace") as mock_load:
            MockLLM.from_workspace_config.return_value = mock_llm
            mock_load.return_value = {"model": "fake", "thinking": False}

            result = await service.batch_generate(
                project_id="test-project",
                prompt_type="generate/continuation",
                volume_number=1,
                chapter_number=1,
                section_numbers=[1],
            )

        # 验证空文件已被写入
        new_content = (ch_dir / "sec-001.md").read_text(encoding="utf-8")
        assert "新生成的场景内容" in new_content, f"空 sec 文件应被直接写入，实际内容: {new_content!r}"
