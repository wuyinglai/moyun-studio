"""pytest fixtures — 供所有测试文件共享

提供：
1. 测试配置覆盖（不依赖真实 .env）
2. FastAPI TestClient（依赖注入覆盖）
3. 真实 FileService（基于 tmp_path 工作区）
4. 真实 PromptEngine + 模板
5. Mock LLMService / Mock EventBus
"""

import json
import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.config import Settings, get_settings
from backend.core.file_ops import FileService
from backend.core.event_bus import EventBus
from backend.core.prompt_engine import PromptEngine


# ─── 覆盖配置（避免依赖真实 .env）─────────────────────────

@pytest.fixture(scope="session")
def test_settings():
    """返回一份不依赖 .env 的测试配置"""
    return Settings(
        debug=True,
        workspace_path=Path("tests/fixtures/workspace").resolve(),
        llm_provider="custom",
        llm_api_key="fake-key-for-test",
        llm_model="fake-model",
    )


# ─── 临时工作区 fixture（真实文件系统）────────────────────

@pytest.fixture
def temp_workspace(tmp_path):
    """创建一个真实的临时工作区目录结构

    目录结构：
    ├── projects/
    │   └── test-project/
    │       ├── meta.json
    │       ├── context.json
    │       ├── chapters/
    │       ├── characters/
    │       ├── materials/
    │       ├── backup/
    │       ├── outline.md
    │       ├── style-guide.md
    │       ├── story-state.md
    │       └── recent-context.md
    └── prompts/
        └── generate/
            └── chapter/
                └── main.md
    """
    workspace = tmp_path / "workspace"
    projects = workspace / "projects"
    prompts = workspace / "prompts" / "generate" / "chapter"
    prompts.mkdir(parents=True, exist_ok=True)

    # 创建项目目录
    proj = projects / "test-project"
    proj.mkdir(parents=True)
    (proj / "chapters").mkdir()
    (proj / "characters").mkdir()
    (proj / "materials").mkdir()
    (proj / "backup").mkdir()

    # meta.json
    meta = {
        "project_id": "test-project",
        "name": "测试项目",
        "genre": "玄幻",
        "theme": "成长",
        "tone": "热血",
        "target_word_count": 100000,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    (proj / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # context.json
    context = {
        "project_id": "test-project",
        "stats": {
            "total_words": 5000,
            "total_sections": 10,
            "completed_sections": 6,
            "chapter_count": 3,
        },
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    (proj / "context.json").write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

    # 项目文件
    (proj / "outline.md").write_text("# 测试项目 - 大纲\n\n## 第一卷\n", encoding="utf-8")
    (proj / "style-guide.md").write_text("# 文风指南\n\n测试风格\n", encoding="utf-8")
    (proj / "story-state.md").write_text("# 故事状态\n\n测试状态\n", encoding="utf-8")
    (proj / "recent-context.md").write_text("# 近期上下文\n\n测试上下文\n", encoding="utf-8")

    # 测试章节文件（带frontmatter）
    chapter_content = """---
title: 第一章 - 开端
word_count: 1200
status: draft
---

# 第一章 开端

故事从这里开始。

这是一段测试内容。
"""
    (proj / "chapters" / "chapter-01.md").write_text(chapter_content, encoding="utf-8")

    # Prompt 模板
    template = """你是一个小说作家。

题材：{{ genre }}
主题：{{ theme }}
基调：{{ tone }}

{% if chapter_title %}章节标题：{{ chapter_title }}{% endif %}

请续写下一章内容。
"""
    (prompts / "main.md").write_text(template, encoding="utf-8")

    return workspace


@pytest.fixture
def fs(temp_workspace):
    """基于临时工作区的真实 FileService 实例"""
    return FileService(temp_workspace)


# ─── FastAPI TestClient ─────────────────────────────────────

@pytest.fixture
def app(test_settings, temp_workspace):
    """构造 FastAPI app，覆盖依赖"""
    from backend.main import create_app

    # 让 Settings 返回指向临时工作区
    test_settings.workspace_path = temp_workspace

    app = create_app()

    def _fake_get_settings():
        return test_settings

    app.dependency_overrides[get_settings] = _fake_get_settings
    return app


@pytest.fixture
def client(app):
    """返回 TestClient"""
    with TestClient(app) as c:
        yield c


# ─── 真实服务实例 ──────────────────────────────────────────

@pytest.fixture
def event_bus():
    """返回真实的 EventBus 实例"""
    return EventBus()


@pytest.fixture
def prompt_engine(temp_workspace, fs):
    """返回真实的 PromptEngine（基于临时工作区 + 真实 FileService）"""
    prompts_path = temp_workspace / "prompts"
    engine = PromptEngine(
        prompts_path=prompts_path,
        file_service=fs,
    )
    return engine


@pytest.fixture
def prompt_engine_no_fs(temp_workspace):
    """返回无 FileService 的 PromptEngine（用于测试降级行为）"""
    prompts_path = temp_workspace / "prompts"
    return PromptEngine(prompts_path=prompts_path, file_service=None)


# ─── Mock 服务 ───────────────────────────────────────────────

@pytest.fixture
def mock_llm_service():
    """Mock LLMService，不发起真实 HTTP 请求"""
    svc = MagicMock()

    async def _complete(messages, model=None, stream=True):
        if stream:
            for chunk in ["测", "试", "内", "容"]:
                yield chunk
        else:
            yield "测试内容"

    svc.complete = _complete
    svc.complete_sync = AsyncMock(return_value="测试内容")
    svc.count_tokens = AsyncMock(return_value=100)
    return svc


@pytest.fixture
def mock_event_bus():
    """Mock EventBus"""
    bus = MagicMock()
    bus.publish = AsyncMock()
    bus.subscribe = MagicMock(return_value=("mock-client-id", asyncio.Queue()))
    bus.unsubscribe = MagicMock()
    return bus


@pytest.fixture
def mock_file_service(tmp_path):
    """Mock FileService（用于纯逻辑测试，不写文件系统）"""
    svc = MagicMock()
    svc.read_file = AsyncMock(return_value=("# 测试章节\n\n内容", None))
    svc.write_file = AsyncMock()
    svc.list_directory = AsyncMock(return_value=[])
    svc.delete_file = AsyncMock()
    svc.delete_directory = AsyncMock()
    svc.exists = AsyncMock(return_value=True)
    svc.get_file_tree = AsyncMock(return_value={"name": "root", "path": "", "children": []})
    svc.workspace = tmp_path
    return svc
