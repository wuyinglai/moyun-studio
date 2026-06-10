"""T6.7.6a 真实 LLM 冒烟测试后端 gate contract

覆盖：
1. 默认未开启 gate 时：
   - __llm_smoke_t6_7_6a + /api/generate → 403 / REAL_LLM_SMOKE_DISABLED
   - __llm_smoke_t6_7_6a + /api/generate/batch + dry_run=False → 403 / BATCH_REAL_LLM_SMOKE_FORBIDDEN
2. smoke 项目 + batch + dry_run=True → 正常通过（不触发 LLM）
3. 非 smoke 项目（普通 dry-run → 正常通过
4. gate 开启后：单文件 smoke 放行（仅 helper 层验证；不发真实网络请求
5. gate 开启后：Batch 仍然禁止（不论开关）
6. smoke 专用 max_tokens 配置（默认 300，范围校验 1-1024）

约束：
- 本测试**不调用真实 LLM**
- 本测试**不写正文**
- 本测试**不生成候选稿**
"""

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.core.smoke_gate import (
    BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE,
    check_batch_real_llm_smoke_gate,
    check_real_llm_smoke_gate,
    is_llm_smoke_project,
    LLM_SMOKE_PROJECT_PREFIX,
    REAL_LLM_SMOKE_DISABLED_CODE,
)
from backend.main import app


# ── helper 层单元测试 ──────────────────────────────────────

def test_is_llm_smoke_project_detection():
    assert is_llm_smoke_project("__llm_smoke_t6_7_6a") is True
    assert is_llm_smoke_project("__llm_smoke_") is True
    assert is_llm_smoke_project("normal-project") is False
    assert is_llm_smoke_project("__contract_test") is False
    assert is_llm_smoke_project("") is False


def test_smoke_project_prefix_constant():
    """LLM_SMOKE_PROJECT_PREFIX 应为 '__llm_smoke_'"""
    assert LLM_SMOKE_PROJECT_PREFIX == "__llm_smoke_"


def test_default_gate_allows_dry_run_for_smoke_project():
    """dry_run=True → 永远放行（不触发 LLM 路径）"""
    settings = Settings()  # allow_real_llm_smoke=False
    assert settings.allow_real_llm_smoke is False
    result = check_real_llm_smoke_gate(settings, "__llm_smoke_test", dry_run=True)
    assert result is None


def test_default_gate_allows_non_smoke_real():
    """非 smoke 项目真实生成 → 走原有业务逻辑（本 gate 不介入）"""
    settings = Settings()
    result = check_real_llm_smoke_gate(settings, "normal-project", dry_run=False)
    assert result is None


def test_default_gate_rejects_smoke_real():
    """smoke 项目 + dry_run=False + 开关未开 → 403 拒绝"""
    settings = Settings()
    result = check_real_llm_smoke_gate(settings, "__llm_smoke_test", dry_run=False)
    assert result is not None
    body = result.body
    assert b"REAL_LLM_SMOKE_DISABLED" in body
    assert result.status_code == 403


def test_enabled_gate_allows_smoke_real_single_file():
    """开启开关后：单文件 smoke 放行（仅 helper 层，不实际调用 LLM）"""
    settings = Settings(allow_real_llm_smoke=True)
    result = check_real_llm_smoke_gate(settings, "__llm_smoke_test", dry_run=False)
    assert result is None


def test_batch_gate_always_rejects_real_for_smoke():
    """Batch smoke + dry_run=False → 永远拒绝（无论开关）"""
    # 开关关闭
    settings_off = Settings()
    result = check_batch_real_llm_smoke_gate(settings_off, "__llm_smoke_test", dry_run=False)
    assert result is not None
    assert result.status_code == 403
    assert b"BATCH_REAL_LLM_SMOKE_FORBIDDEN" in result.body

    # 开关开启（Batch 仍然拒绝）
    settings_on = Settings(allow_real_llm_smoke=True)
    result = check_batch_real_llm_smoke_gate(settings_on, "__llm_smoke_test", dry_run=False)
    assert result is not None
    assert result.status_code == 403
    assert b"BATCH_REAL_LLM_SMOKE_FORBIDDEN" in result.body


def test_batch_gate_allows_smoke_dry_run():
    """Batch + dry_run=True → 正常通过（dry-run 不调 LLM）"""
    settings = Settings()
    result = check_batch_real_llm_smoke_gate(settings, "__llm_smoke_test", dry_run=True)
    assert result is None


def test_batch_gate_allows_non_smoke_real():
    """非 smoke 项目 + dry_run=False → 正常通过（不进入 smoke gate）"""
    settings = Settings()
    result = check_batch_real_llm_smoke_gate(settings, "normal-project", dry_run=False)
    assert result is None


# ── smoke max_tokens 配置测试 ────────────────────────────

def test_smoke_max_tokens_default_300():
    settings = Settings()
    assert settings.llm_smoke_max_tokens == 300


def test_smoke_max_tokens_range_validation():
    """smoke max_tokens 范围 1-1024"""
    # 合法值
    Settings(llm_smoke_max_tokens=1)
    Settings(llm_smoke_max_tokens=1024)
    Settings(llm_smoke_max_tokens=300)


def test_smoke_max_tokens_zero_rejected():
    """0 应被 pydantic 拒绝"""
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        Settings(llm_smoke_max_tokens=0)


def test_smoke_max_tokens_too_large_rejected():
    """> 1025 应被 pydantic 拒绝"""
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        Settings(llm_smoke_max_tokens=1025)


# ── API 层 contract 测试 ─────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_generate_rejects_smoke_project_without_gate(client):
    """未开启 gate：smoke 项目 + /api/generate → 403 + 明确错误码"""
    r = client.post(
        "/api/generate",
        json={
            "project_id": "__llm_smoke_t6_7_6a",
            "file_path": "chapters/vol-01/ch-001/sec-001.md",
            "prompt_type": "generate/chapter",
            "extra_vars": {},
            "mode": "rewrite",
            "stream": True,
        },
    )
    assert r.status_code == 403
    body = r.json()
    assert body.get("success") is False
    assert body.get("code") == REAL_LLM_SMOKE_DISABLED_CODE


def test_api_batch_rejects_smoke_project_without_gate(client):
    """未开启 gate：smoke 项目 + batch + dry_run=False → 403 + BATCH_REAL_LLM_SMOKE_FORBIDDEN"""
    r = client.post(
        "/api/generate/batch",
        json={
            "project_id": "__llm_smoke_t6_7_6a_batch",
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
    assert body.get("success") is False
    assert body.get("code") == BATCH_REAL_LLM_SMOKE_FORBIDDEN_CODE


def test_api_batch_smoke_dry_run_not_blocked_by_gate(client):
    """smoke 项目 + batch + dry_run=True → gate 不拦截（返回 200 或其它非 403；不进入真实 LLM 分支）"""
    r = client.post(
        "/api/generate/batch",
        json={
            "project_id": "__llm_smoke_t6_7_6a_dry",
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1],
            "prompt_type": "generate/chapter",
            "temperature": 0.7,
            "dry_run": True,
        },
    )
    # gate 只拦截 dry_run=False；dry_run=True 必须不返回 403
    assert r.status_code != 403
    # 真实结果可能是 200 或其它状态（由项目是否存在决定），但重点是 gate 不拒绝


def test_api_non_smoke_project_not_blocked_by_gate(client):
    """非 smoke 项目 → gate 不拦截（非 smoke 项目不在 gate 管理范围内）"""
    # dry_run=True 确保不调用 LLM
    r = client.post(
        "/api/generate/batch",
        json={
            "project_id": "__contract_t6_7_6a_normal_proj",
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1],
            "prompt_type": "generate/chapter",
            "temperature": 0.7,
            "dry_run": True,
        },
    )
    # gate 不拦截 → 不应返回 403（真实结果取决于项目是否存在）
    assert r.status_code != 403


# ── 确认：对非 smoke 真实项目（dry_run=False），gate 不主动介入 ──
def test_api_non_smoke_real_generate_not_blocked_by_gate(client):
    """普通项目 + /api/generate + dry_run（隐含 False）→ gate 不返回 403

    注意：此测试不执行真实 LLM 调用；仅验证 gate 不拦截非 smoke 项目。
    实际行为取决于项目是否存在，但 gate 层不会主动拒绝。
    """
    r = client.post(
        "/api/generate",
        json={
            "project_id": "contract-t6-7-6a-real-proj",
            "file_path": "chapters/vol-01/ch-001/sec-001.md",
            "prompt_type": "generate/chapter",
            "extra_vars": {},
            "mode": "rewrite",
            "stream": False,
        },
    )
    assert r.status_code != 403  # gate 不拦截
    # 由于项目不存在，generation service 可能返回 404 或其它错误，这与 gate 无关


# ── monkeypatch 开关开启场景：helper 层验证（不实际调用网络
def test_enabled_gate_allows_single_file_via_helper():
    """开启开关后：smoke 项目在 helper 层被放行（返回 None"""
    settings = Settings(allow_real_llm_smoke=True)
    result = check_real_llm_smoke_gate(settings, "__llm_smoke_test", dry_run=False)
    assert result is None


def test_enabled_gate_still_blocks_batch_via_helper():
    """开启开关后：Batch 仍然拒绝（helper 层）"""
    settings = Settings(allow_real_llm_smoke=True)
    result = check_batch_real_llm_smoke_gate(settings, "__llm_smoke_test", dry_run=False)
    assert result is not None
    assert result.status_code == 403
