"""T6.7.6c Pipeline 内部 LLM 调用 max_tokens 透传 + smoke project_id 策略 contract 测试

覆盖：
1. PipelineRunner._generate_diff_summary()：smoke 项目时 llm_extra_kwargs 中 max_tokens=300 被透传
2. PipelineRunner._generate_diff_summary()：普通项目不传 llm_extra_kwargs 时，complete 不含 max_tokens
3. /api/projects：project_id 为 uuid[:8]，不保留 name 前缀；name 保存在 meta.json

约束：不调用真实 LLM、不使用 API Key。
"""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.core.smoke_gate import is_llm_smoke_project
from backend.main import app


# ── 1. PipelineRunner._generate_diff_summary() smoke max_tokens 透传 ─


def _build_runner_and_capture(tmp_path, monkeypatch, llm_extra_kwargs_in):
    """辅助函数：构造 runner + 捕获 LLMService.complete kwargs。"""
    from backend.core.file_ops import FileService
    from backend.core.llm import LLMService
    from backend.core.pipeline import PipelineRunner

    captured = {"kwargs": None, "calls": 0}

    async def fake_complete(self, messages, model=None, timeout=None, **kwargs):
        captured["kwargs"] = dict(kwargs)
        captured["calls"] += 1
        yield "[MOCK] summary"

    # patch LLMService.complete（async 生成器）
    monkeypatch.setattr(
        "backend.core.llm.LLMService.complete",
        fake_complete,
    )

    # patch render_prompt 以避免文件系统依赖
    def fake_render_prompt(self, prompt_rel, variables=None):
        return "[MOCK] rendered prompt for test"

    monkeypatch.setattr(
        "backend.core.pipeline.PipelineRunner.render_prompt",
        fake_render_prompt,
    )

    settings = Settings(
        workspace_path=str(tmp_path / "workspace"),
        projects_subdir="projects",
        allow_real_llm_smoke=True,
        llm_smoke_max_tokens=300,
    )
    file_service = FileService(settings.projects_path)
    llm_service = object.__new__(LLMService)
    llm_service.config = type("C", (), {})()

    runner = PipelineRunner(
        prompts_path=Path("prompts"),
        llm_service=llm_service,
        file_service=file_service,
        system_prompts_path=Path("prompts"),
    )
    return runner, captured


def test_pipeline_generate_diff_summary_smoke_max_tokens_passthrough(tmp_path, monkeypatch):
    """smoke 项目：_generate_diff_summary 调用 LLM 时收到 max_tokens=300。"""
    runner, captured = _build_runner_and_capture(tmp_path, monkeypatch, llm_extra_kwargs_in=None)

    async def _run():
        return await runner._generate_diff_summary(
            project_id="__llm_smoke_t6_7_6c",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            original_content="old content line 1\n",
            modified_content="new content line 1 modified\n",
            task_id="t",
            llm_extra_kwargs={"max_tokens": 300},
        )

    asyncio.run(_run())
    assert captured["calls"] >= 1, "LLMService.complete 必须被调用"
    kwargs = captured["kwargs"] or {}
    assert "max_tokens" in kwargs, "smoke 项目 _generate_diff_summary 必须显式传 max_tokens"
    assert kwargs["max_tokens"] == 300, (
        f"smoke 项目 max_tokens 应为 300，实际 {kwargs['max_tokens']}"
    )


def test_pipeline_generate_diff_summary_plain_project_no_forced_max_tokens(tmp_path, monkeypatch):
    """普通项目：_generate_diff_summary 不传 llm_extra_kwargs 时，complete 不含 max_tokens。"""
    runner, captured = _build_runner_and_capture(tmp_path, monkeypatch, llm_extra_kwargs_in=None)

    async def _run():
        return await runner._generate_diff_summary(
            project_id="normal-t6-7-6c",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            original_content="old\n",
            modified_content="new\n",
            task_id="t",
            # 不传 llm_extra_kwargs（默认 None）
        )

    asyncio.run(_run())
    assert captured["calls"] >= 1
    kwargs = captured["kwargs"] or {}
    assert "max_tokens" not in kwargs, (
        f"普通项目 _generate_diff_summary 不应强制 max_tokens，实际收到 {kwargs.get('max_tokens')}"
    )


# ── 2. /api/projects project_id 行为 contract ─


def test_api_projects_returns_uuid_short_id_not_name():
    """POST /api/projects 返回的 project_id = uuid[:8]，不等于输入的 name。"""
    client = TestClient(app)
    r = client.post(
        "/api/projects",
        json={
            "name": "__llm_smoke_t6_7_6c_project",
            "genre": "测试",
            "theme": "smoke project id contract",
            "tone": "中性",
            "background": "测试",
            "writing_style": "普通",
            "target_word_count": 10000,
            "author": "contract",
        },
    )
    assert r.status_code in (200, 201), f"创建项目返回 {r.status_code}: {r.text}"
    body = r.json()
    pid = body["data"]["project_id"]

    # 1) project_id 不等于 name（这是关键约束）
    assert pid != "__llm_smoke_t6_7_6c_project", (
        "project_id 不应直接使用 name；当前实现应为 uuid[:8]"
    )

    # 2) project_id 不以 __llm_smoke_ 开头
    assert not is_llm_smoke_project(pid), (
        f"通过 /api/projects 创建的项目 id 不应保留 __llm_smoke_ 前缀；实际 id={pid}"
    )

    # 3) project_id 长度为 8（uuid[:8]）
    assert len(pid) == 8, f"uuid[:8] 预期长度 8，实际 {len(pid)}（id={pid}）"


def test_api_projects_name_saved_in_meta(tmp_path):
    """name 保存在 projects/<pid>/meta.json（service 层验证）。

    避免 FastAPI Depends 缓存问题，直接通过 ProjectService 测试：
    1) 构造临时 settings.projects_path
    2) 用 ProjectService.write_meta / create_project_meta
    3) 验证 meta.json 中 name 字段被完整保留
    """
    from backend.core.project_service import ProjectService
    import uuid

    temp_root = tmp_path / "workspace"
    temp_root.mkdir(parents=True, exist_ok=True)
    settings_override = Settings(
        workspace_path=str(temp_root),
        projects_subdir="projects",
    )
    expected_projects_path = settings_override.projects_path
    expected_projects_path.mkdir(parents=True, exist_ok=True)

    svc = ProjectService(settings_override)

    # 模拟 projects 目录下的项目，project_id = uuid[:8]
    project_id = str(uuid.uuid4())[:8]
    project_dir = expected_projects_path / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # 模拟 req 对象（提供 create_project_meta 所需字段）
    class _Req:
        genre = "测试"
        theme = "name preservation"
        tone = "中性"
        background = "测试"
        writing_style = "普通"
        target_word_count = 10000
        author = "contract"

    meta = svc.create_project_meta(project_id, "__llm_smoke_t6_7_6c_meta", _Req())
    svc.write_meta(project_dir, meta)

    meta_path = project_dir / "meta.json"
    assert meta_path.exists(), f"meta.json 应存在于 {meta_path}"
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta_data.get("name") == "__llm_smoke_t6_7_6c_meta", (
        f"meta.json 中的 name 应保留原始输入值；实际 {meta_data.get('name')}"
    )
    assert meta_data.get("project_id") == project_id, (
        f"meta.json project_id 应等于 {project_id}；实际 {meta_data.get('project_id')}"
    )
    # 关键断言：name 不以 __llm_smoke_ 前缀丢失问题不会发生在 meta 中
    # （仅 project_id 会变成 uuid[:8]，name 始终保留原始值）


# ── 3. smoke gate helper：确认 is_llm_smoke_project 对 uuid[:8] 返回 False ─


def test_is_llm_smoke_project_for_uuid8_returns_false():
    """uuid[:8]（hex）不会误命中 smoke 前缀。"""
    samples = ["a1b2c3d4", "deadbeef", "cafebabe", "12345678", "abcdef01"]
    for s in samples:
        assert is_llm_smoke_project(s) is False, (
            f"{s} 不应被误判为 smoke 项目"
        )


def test_is_llm_smoke_project_for_manual_dir_returns_true():
    """手工在 projects 下创建 __llm_smoke_* 目录会被识别为 smoke 项目。"""
    assert is_llm_smoke_project("__llm_smoke_t6_7_6c_manual") is True
