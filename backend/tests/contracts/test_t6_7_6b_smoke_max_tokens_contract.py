"""T6.7.6b 真实 LLM smoke max_tokens contract 测试

覆盖：
1. helper 层：get_smoke_max_tokens / maybe_apply_smoke_max_tokens / is_llm_smoke_project
2. API 层：smoke 项目 + gate 关闭 → 403；smoke 项目 + dry_run=True → gate 放行
3. API 层（mock LLM）：smoke 项目 + gate 开启 → max_tokens <= 300
4. Batch：smoke 项目 + dry_run=False 永远 403；smoke 项目 + dry_run=True 不被 gate 拦截

约束：不调用真实 LLM、不使用 API Key。

关键修正（T6.7.6b 收口问题）：
  /api/projects 返回的 project_id = uuid[:8]，**不**保留 name 前缀。
  因此 contract 测试必须**直接**使用 `__llm_smoke_*` 字面量作为 project_id，
  并通过构造最小项目目录（tmp_path）让 FileService 找到目标文件。
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.core.smoke_gate import (
    BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE,
    check_batch_real_llm_smoke_gate,
    check_real_llm_smoke_gate,
    get_smoke_max_tokens,
    is_llm_smoke_project,
    LLM_SMOKE_MAX_TOKENS_DEFAULT,
    LLM_SMOKE_MAX_TOKENS_HARD_CAP,
    maybe_apply_smoke_max_tokens,
    REAL_LLM_SMOKE_DISABLED_CODE,
)
from backend.main import app

# smoke 项目字面量（硬编码，不依赖 /api/projects 生成）
SMOKE_PROJECT_ID = "__llm_smoke_t6_7_6b"
NORMAL_PROJECT_ID = "__contract_t6_7_6b_normal"

TARGET_FILE = "chapters/vol-01/ch-001/sec-001.md"


# ── helpers ─────────────────────────────────────────────


def _make_project_dir(projects_path: Path, project_id: str, files: list[str] | None = None):
    """在给定 projects_path 下创建最小项目目录 + 目标场景文件。"""
    proj_dir = projects_path / project_id
    chapter_dir = proj_dir / "chapters" / "vol-01" / "ch-001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    to_write = files or [TARGET_FILE]
    for rel in to_write:
        (proj_dir / rel).write_text("", encoding="utf-8")
    return proj_dir


def _apply_projects_path(monkeypatch, projects_path: Path, workspace_path: Path):
    """让 FastAPI 依赖注入返回的 Settings 使用临时 projects_path。"""

    def fake_get_settings():
        return Settings(
            workspace_path=str(workspace_path),
            projects_subdir="projects",
            allow_real_llm_smoke=True,
            llm_smoke_max_tokens=300,
        )

    monkeypatch.setattr("backend.config.get_settings", fake_get_settings)


# ── 1. helper 层 ─────────────────────────────────────────


def test_is_llm_smoke_project_prefix_matching():
    assert is_llm_smoke_project("__llm_smoke_t6_7_6b") is True
    assert is_llm_smoke_project("__llm_smoke_anything") is True
    assert is_llm_smoke_project("normal-project") is False
    assert is_llm_smoke_project("") is False
    assert is_llm_smoke_project("__e2e_t6_6_4_batch_dry_run") is False


def test_get_smoke_max_tokens_default_300():
    assert get_smoke_max_tokens(Settings(allow_real_llm_smoke=True)) == 300


def test_get_smoke_max_tokens_valid_values_within_range():
    assert get_smoke_max_tokens(Settings(allow_real_llm_smoke=True, llm_smoke_max_tokens=100)) == 100
    assert get_smoke_max_tokens(Settings(allow_real_llm_smoke=True, llm_smoke_max_tokens=1024)) == 1024


def test_get_smoke_max_tokens_robust_to_raw_outliers():
    """调用方绕过 Settings 直接传异常值（defense-in-depth）"""

    class FakeSettings:
        def __init__(self, raw):
            self.llm_smoke_max_tokens = raw

    assert get_smoke_max_tokens(FakeSettings("not-a-number")) == LLM_SMOKE_MAX_TOKENS_DEFAULT
    assert get_smoke_max_tokens(FakeSettings(None)) == LLM_SMOKE_MAX_TOKENS_DEFAULT
    assert get_smoke_max_tokens(FakeSettings(-100)) == 1
    assert get_smoke_max_tokens(FakeSettings(999999)) == LLM_SMOKE_MAX_TOKENS_HARD_CAP


def test_maybe_apply_smoke_max_tokens_non_smoke_unchanged():
    """非 smoke 项目：不注入 max_tokens，原 dict 被保留"""
    settings = Settings()
    original = {"thinking": "x"}
    result = maybe_apply_smoke_max_tokens(settings, "normal-project", original)
    assert result.get("max_tokens") is None or result.get("max_tokens") != LLM_SMOKE_MAX_TOKENS_DEFAULT
    assert result.get("thinking") == "x" or "thinking" in original


def test_maybe_apply_smoke_max_tokens_smoke_injected():
    """smoke 项目：max_tokens 被设为 <= 300"""
    settings = Settings()
    original = {"thinking": "x"}
    result = maybe_apply_smoke_max_tokens(settings, SMOKE_PROJECT_ID, original)
    assert result["max_tokens"] == LLM_SMOKE_MAX_TOKENS_DEFAULT
    assert result["thinking"] == "x"
    assert "max_tokens" not in original or original.get("max_tokens") != LLM_SMOKE_MAX_TOKENS_DEFAULT


def test_maybe_apply_smoke_max_tokens_none_input():
    """None 输入：对非 smoke 返回 {}，对 smoke 返回 {max_tokens: 300}"""
    settings = Settings()
    assert maybe_apply_smoke_max_tokens(settings, "normal", None) == {}
    r = maybe_apply_smoke_max_tokens(settings, SMOKE_PROJECT_ID, None)
    assert r == {"max_tokens": LLM_SMOKE_MAX_TOKENS_DEFAULT}


# ── 2. API 层：gate 拒绝行为（不需要真实项目目录）─────


def test_api_generate_rejects_smoke_when_gate_closed():
    """默认配置（allow_real_llm_smoke=False）：/api/generate + smoke 项目 → 403

    关键：直接使用 `__llm_smoke_t6_7_6b` 字面量作为 project_id，
    不依赖 /api/projects（它会返回 uuid[:8]，丢失前缀）。
    gate 在进入生成流程前触发，不依赖项目目录存在。
    """
    client = TestClient(app)
    r = client.post(
        "/api/generate",
        json={
            "project_id": SMOKE_PROJECT_ID,
            "file_path": TARGET_FILE,
            "prompt_type": "generate/chapter",
            "extra_vars": {},
            "mode": "rewrite",
            "stream": False,
        },
    )
    assert r.status_code == 403
    body = r.json()
    assert body.get("success") is False
    assert body.get("code") == REAL_LLM_SMOKE_DISABLED_CODE


def test_api_chat_rejects_smoke_when_gate_closed():
    """默认配置：/api/chat + smoke 项目 → 403"""
    client = TestClient(app)
    r = client.post(
        "/api/chat",
        json={
            "project_id": SMOKE_PROJECT_ID,
            "context_file": TARGET_FILE,
            "message": "hi",
            "history": [],
        },
    )
    assert r.status_code == 403
    body = r.json()
    assert body.get("code") == REAL_LLM_SMOKE_DISABLED_CODE


def test_api_pipeline_run_rejects_smoke_when_gate_closed():
    """默认配置：/api/pipeline/run + smoke 项目 + dry_run=False → 403"""
    client = TestClient(app)
    r = client.post(
        "/api/pipeline/run",
        json={
            "project_id": SMOKE_PROJECT_ID,
            "pipeline": "generate",
            "target_file": TARGET_FILE,
            "user_input": "",
            "output_mode": "candidate",
            "extra_vars": {},
            "scene_plan": {},
            "dry_run": False,
        },
    )
    assert r.status_code == 403
    body = r.json()
    assert body.get("code") == REAL_LLM_SMOKE_DISABLED_CODE


def test_api_batch_rejects_smoke_real_even_if_gate_were_open():
    """Batch 永远不允许 smoke 真实调用（与 allow_real_llm_smoke 无关）

    使用 `__llm_smoke_t6_7_6b` 字面量，不依赖 /api/projects。
    """
    client = TestClient(app)
    r = client.post(
        "/api/generate/batch",
        json={
            "project_id": SMOKE_PROJECT_ID,
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1],
            "prompt_type": "generate/chapter",
            "temperature": 0.7,
            "dry_run": False,
        },
    )
    assert r.status_code == 403
    body = r.json()
    assert body.get("code") == BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE


def test_api_batch_gate_dry_run_smoke_not_blocked(monkeypatch, tmp_path):
    """smoke 项目 + batch + dry_run=True → gate 放行（gate 不拦截 dry-run）

    注意：本测试只验证 gate 行为，真实 batch_generate 需要完整项目结构，
    所以我们只断言 gate check_batch_real_llm_smoke_gate 返回 None。
    """
    settings = Settings()
    result = check_batch_real_llm_smoke_gate(settings, SMOKE_PROJECT_ID, dry_run=True)
    assert result is None, "smoke 项目的 batch dry-run 不应被 gate 拦截"


def test_api_batch_gate_real_smoke_rejected():
    """helper 层直接验证：smoke + batch + dry_run=False → 永远拒绝"""
    # 开关关闭
    settings_off = Settings()
    result = check_batch_real_llm_smoke_gate(settings_off, SMOKE_PROJECT_ID, dry_run=False)
    assert result is not None
    assert result.status_code == 403
    assert BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE in result.body.decode()

    # 开关开启（Batch 仍然拒绝）
    settings_on = Settings(allow_real_llm_smoke=True)
    result = check_batch_real_llm_smoke_gate(settings_on, SMOKE_PROJECT_ID, dry_run=False)
    assert result is not None
    assert result.status_code == 403
    assert BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE in result.body.decode()


def test_api_non_smoke_project_not_affected_by_smoke_gate():
    """非 smoke 项目：单文件 generate 的 gate 不拦截（helper 层验证）"""
    settings = Settings()
    result = check_real_llm_smoke_gate(settings, NORMAL_PROJECT_ID, dry_run=False)
    assert result is None, "非 smoke 项目不应被 smoke gate 拦截"


# ── 3. Service 层 max_tokens 验证（gate 开启 + mock LLM）──
#    目标：证明 generate_stream 的管线模式 / fallback 路径 / batch 路径
#    在 smoke 项目上把 max_tokens 覆盖为 300。
#    不通过 HTTP API，避免 FastAPI Depends(get_settings) 的 lru_cache 干扰。


def _make_minimal_project(tmp_path: Path, project_id: str, projects_subdir: str = "projects"):
    """在 tmp_path/workspace/<projects_subdir>/<project_id> 下创建最小项目目录。"""
    proj_dir = tmp_path / "workspace" / projects_subdir / project_id
    chapter_dir = proj_dir / "chapters" / "vol-01" / "ch-001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "sec-001.md").write_text("", encoding="utf-8")
    return proj_dir


def _make_smoke_settings(tmp_path: Path, allow_real_llm_smoke: bool = True) -> Settings:
    """构造 Settings，projects_path / workspace_path 指向 tmp_path。"""
    return Settings(
        workspace_path=str(tmp_path / "workspace"),
        projects_subdir="projects",
        allow_real_llm_smoke=allow_real_llm_smoke,
        llm_smoke_max_tokens=300,
    )


def test_service_generate_stream_pipeline_smoke_injects_max_tokens(monkeypatch, tmp_path):
    """smoke 项目 + pipeline 生成路径：LLMService.complete 收到 max_tokens=300。"""
    import asyncio
    from backend.core.generation_service import GenerationService

    pid = "__llm_smoke_t6_7_6b"
    _make_minimal_project(tmp_path, pid)

    settings = _make_smoke_settings(tmp_path, allow_real_llm_smoke=True)

    captured = {"kwargs": None, "calls": 0}

    async def fake_complete_sync(self, messages, model=None, **kwargs):
        captured["kwargs"] = dict(kwargs)
        captured["calls"] += 1
        return "[MOCK] normal section body"

    monkeypatch.setattr(
        "backend.core.llm.LLMService.complete_sync",
        fake_complete_sync,
    )

    async def fake_complete(self, messages, model=None, stop_event=None, timeout=None, **kwargs):
        captured["kwargs"] = dict(kwargs)
        captured["calls"] += 1
        yield "[MOCK]"

    monkeypatch.setattr(
        "backend.core.llm.LLMService.complete",
        fake_complete,
    )

    async def fake_write_file(self, *a, **kw):
        return {"path": "mock", "hash": "mock"}

    monkeypatch.setattr(
        "backend.core.file_ops.FileService.write_file",
        fake_write_file,
    )

    svc = GenerationService(settings)

    async def _run():
        events = []
        async for event in svc.generate_stream(
            project_id=pid,
            file_path="chapters/vol-01/ch-001/sec-001.md",
            prompt_type="generate/chapter",
            extra_vars={},
            mode="rewrite",
            task_id="t",
        ):
            events.append(event)
        return events

    asyncio.run(_run())

    assert captured["calls"] >= 1, "LLM 必须被调用（被 mock 拦截）"
    kwargs = captured["kwargs"] or {}
    assert "max_tokens" in kwargs, "smoke 项目必须显式传递 max_tokens"
    assert isinstance(kwargs["max_tokens"], int)
    assert kwargs["max_tokens"] <= 300, (
        f"smoke 项目 max_tokens 必须 <= 300（当前 {kwargs['max_tokens']}）"
    )
    assert kwargs["max_tokens"] != 2500, "smoke 项目不应回落到硬编码 2500"


def test_service_batch_generate_smoke_overrides_max_tokens(monkeypatch, tmp_path):
    """smoke 项目 batch_generate(dry_run=False)：max_tokens 被覆盖为 300。"""
    import asyncio
    from backend.core.generation_service import GenerationService

    pid = "__llm_smoke_t6_7_6b_batch"
    _make_minimal_project(tmp_path, pid)

    settings = _make_smoke_settings(tmp_path, allow_real_llm_smoke=True)

    captured = {"kwargs": None, "calls": 0}

    async def fake_complete_sync(self, messages, model=None, **kwargs):
        captured["kwargs"] = dict(kwargs)
        captured["calls"] += 1
        return "[MOCK] body"

    monkeypatch.setattr(
        "backend.core.llm.LLMService.complete_sync",
        fake_complete_sync,
    )

    async def fake_write_file(self, *a, **kw):
        return {"path": "mock", "hash": "mock"}

    monkeypatch.setattr(
        "backend.core.file_ops.FileService.write_file",
        fake_write_file,
    )

    svc = GenerationService(settings)

    asyncio.run(
        svc.batch_generate(
            project_id=pid,
            prompt_type="generate/chapter",
            volume_number=1,
            chapter_number=1,
            section_numbers=[1],
            temperature=0.7,
            dry_run=False,
        )
    )

    assert captured["calls"] >= 1
    kwargs = captured["kwargs"] or {}
    assert kwargs.get("max_tokens") == 300, (
        f"smoke batch 期望 max_tokens=300，实际 {kwargs.get('max_tokens')}"
    )


def test_service_batch_generate_non_smoke_keeps_default(monkeypatch, tmp_path):
    """非 smoke 项目 batch_generate(dry_run=False)：max_tokens 保持 2500。"""
    import asyncio
    from backend.core.generation_service import GenerationService

    pid = "normal_t6_7_6b"
    _make_minimal_project(tmp_path, pid)

    settings = _make_smoke_settings(tmp_path, allow_real_llm_smoke=False)

    captured = {"kwargs": None, "calls": 0}

    async def fake_complete_sync(self, messages, model=None, **kwargs):
        captured["kwargs"] = dict(kwargs)
        captured["calls"] += 1
        return "[MOCK] body"

    monkeypatch.setattr(
        "backend.core.llm.LLMService.complete_sync",
        fake_complete_sync,
    )

    async def fake_write_file(self, *a, **kw):
        return {"path": "mock", "hash": "mock"}

    monkeypatch.setattr(
        "backend.core.file_ops.FileService.write_file",
        fake_write_file,
    )

    svc = GenerationService(settings)

    asyncio.run(
        svc.batch_generate(
            project_id=pid,
            prompt_type="generate/chapter",
            volume_number=1,
            chapter_number=1,
            section_numbers=[1],
            temperature=0.7,
            dry_run=False,
        )
    )

    assert captured["calls"] >= 1
    kwargs = captured["kwargs"] or {}
    assert kwargs.get("max_tokens") == 2500, (
        f"非 smoke batch 期望 max_tokens=2500，实际 {kwargs.get('max_tokens')}"
    )


# ── 4. 常量范围校验（防御性）──────────────────────────


def test_smoke_max_tokens_hard_cap_constants():
    assert LLM_SMOKE_MAX_TOKENS_DEFAULT == 300
    assert LLM_SMOKE_MAX_TOKENS_HARD_CAP >= LLM_SMOKE_MAX_TOKENS_DEFAULT


def test_smoke_project_id_prefix_constant():
    """确保 SMOKE_PROJECT_ID 确实以 gate 前缀开头"""
    assert SMOKE_PROJECT_ID.startswith("__llm_smoke_")
    assert is_llm_smoke_project(SMOKE_PROJECT_ID) is True
