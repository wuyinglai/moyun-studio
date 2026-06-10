"""T6.7.5a Batch result schema contract 加固

目标：
1. 锁定 BatchGenerateResponse schema 字段（tasks / total / succeeded / failed）
2. 锁定 BatchGenerateItem schema 字段（target_file / status / dry_run / dry_run_content / candidate_id / prompt / word_count / error）
3. dry-run 单文件 batch：结果结构稳定，不调 LLM，不写正文，不生成 candidate
4. dry-run 多文件 batch：total/succeeded/dry_run 稳定
5. 空目标 batch：未找到目标时返回 empty tasks
6. 确保 dry-run 路径不触发真实 LLM / 文件写入 / candidate 创建

约束：
- 本测试**不调用真实 LLM**
- 本测试**不覆盖正文**
- 本测试**不生成候选稿**
- 本测试不改 Batch 执行逻辑，只锁响应结构
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def test_project(client):
    """创建隔离测试项目"""
    resp = client.post(
        "/api/projects",
        json={
            "name": "__contract_t6_7_5a_batch_schema",
            "genre": "测试",
            "theme": "T6.7.5a Batch schema contract",
            "tone": "中性",
            "background": "测试背景",
            "writing_style": "普通",
            "target_word_count": 50000,
            "author": "contract",
        },
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["success"] is True
    return data["data"]["project_id"]


@pytest.fixture(scope="module")
def ensure_scene_files(client, test_project):
    """在测试项目内创建若干场景文件（空内容，供 dry-run batch 探测）"""
    files = []
    for sec_num in (1, 2, 3):
        rel_path = f"chapters/vol-01/ch-001/sec-{sec_num:03d}.md"
        r = client.post(
            f"/api/file?project_id={test_project}",
            json={"path": rel_path, "content": ""},
        )
        assert r.status_code == 200
        files.append(rel_path)
    return files


def _post_batch(client, project_id, section_numbers, dry_run=True):
    body = {
        "project_id": project_id,
        "volume_number": 1,
        "chapter_number": 1,
        "section_numbers": section_numbers,
        "prompt_type": "generate/chapter",
        "temperature": 0.7,
        "dry_run": dry_run,
    }
    resp = client.post("/api/generate/batch", json=body)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    return body["data"]


# ── schema 锁：BatchGenerateResponse ─────────────────────────


def test_response_schema_top_level_fields(client, test_project, ensure_scene_files):
    """BatchGenerateResponse 顶层字段必须包含 tasks / total / succeeded / failed"""
    result = _post_batch(client, test_project, [1], dry_run=True)
    assert "tasks" in result
    assert "total" in result
    assert "succeeded" in result
    assert "failed" in result
    assert isinstance(result["tasks"], list)
    assert isinstance(result["total"], int)
    assert isinstance(result["succeeded"], int)
    assert isinstance(result["failed"], int)


def test_response_schema_total_matches_tasks_length(client, test_project, ensure_scene_files):
    """total 必须等于 tasks 长度"""
    result = _post_batch(client, test_project, [1, 2], dry_run=True)
    assert result["total"] == len(result["tasks"])
    assert result["total"] == 2


# ── schema 锁：BatchGenerateItem ──────────────────────────


def test_item_schema_required_fields(client, test_project, ensure_scene_files):
    """每个 item 必须包含 BatchGenerateItem 定义的全部字段"""
    result = _post_batch(client, test_project, [1], dry_run=True)
    assert result["total"] >= 1
    item = result["tasks"][0]
    required = {
        "target_file",
        "status",
        "word_count",
        "error",
        "prompt",
        "candidate_id",
        "dry_run",
        "dry_run_content",
    }
    missing = required - set(item.keys())
    assert not missing, f"item 缺少字段: {missing}"
    assert isinstance(item["target_file"], str) and item["target_file"]
    assert isinstance(item["status"], str)
    assert isinstance(item["word_count"], int)
    assert isinstance(item["prompt"], str)
    assert "dry_run_content" in item


def test_item_schema_target_file_contains_scene_path(client, test_project, ensure_scene_files):
    """target_file 必须指向项目内 sec-*.md 场景文件"""
    result = _post_batch(client, test_project, [1], dry_run=True)
    item = result["tasks"][0]
    assert "chapters" in item["target_file"]
    assert "sec-" in item["target_file"]
    assert item["target_file"].endswith(".md")


def test_item_schema_status_is_known_value(client, test_project, ensure_scene_files):
    """status 必须落在已知值域内"""
    known = {"pending", "success", "error", "candidate", "skipped", "dry_run"}
    result = _post_batch(client, test_project, [1, 2], dry_run=True)
    for item in result["tasks"]:
        assert item["status"] in known, f"未知 status: {item['status']}"


# ── dry-run 语义锁 ────────────────────────────────────────


def test_dry_run_single_file_marks_item_dry_run(client, test_project, ensure_scene_files):
    """dry-run 单文件：item.dry_run = True, status = 'dry_run'"""
    result = _post_batch(client, test_project, [1], dry_run=True)
    assert result["total"] == 1
    item = result["tasks"][0]
    assert item["dry_run"] is True
    assert item["status"] == "dry_run"
    assert item["dry_run_content"]  # 非空字符串
    assert "[DRY-RUN]" in item["dry_run_content"]


def test_dry_run_single_file_candidate_id_none(client, test_project, ensure_scene_files):
    """dry-run 单文件：candidate_id 必须为 None（不生成候选稿）"""
    result = _post_batch(client, test_project, [1], dry_run=True)
    item = result["tasks"][0]
    assert item["candidate_id"] is None


def test_dry_run_single_file_succeeded_equal_total(client, test_project, ensure_scene_files):
    """dry-run 单文件：succeeded == total, failed == 0"""
    result = _post_batch(client, test_project, [1], dry_run=True)
    assert result["succeeded"] == result["total"]
    assert result["failed"] == 0


def test_dry_run_multi_file_total_and_succeeded(client, test_project, ensure_scene_files):
    """dry-run 多文件：total == 2, succeeded == 2"""
    result = _post_batch(client, test_project, [1, 2], dry_run=True)
    assert result["total"] == 2
    assert result["succeeded"] == 2
    assert result["failed"] == 0
    assert len(result["tasks"]) == 2


def test_dry_run_multi_file_every_item_has_dry_run_true(client, test_project, ensure_scene_files):
    """dry-run 多文件：每个 item 都标记 dry_run = True"""
    result = _post_batch(client, test_project, [1, 2], dry_run=True)
    for item in result["tasks"]:
        assert item["dry_run"] is True
        assert item["status"] == "dry_run"
        assert item["dry_run_content"]


def test_dry_run_multi_file_every_item_has_path_and_target_file(client, test_project, ensure_scene_files):
    """dry-run 多文件：每个 item 都有稳定的 target_file"""
    result = _post_batch(client, test_project, [1, 2], dry_run=True)
    paths = [item["target_file"] for item in result["tasks"]]
    assert all(p for p in paths)
    assert len(set(paths)) == len(paths)  # 每个 target_file 唯一


def test_dry_run_does_not_write_body(client, test_project, ensure_scene_files):
    """dry-run 不覆盖正文：执行前后文件内容保持为空"""
    rel_path = "chapters/vol-01/ch-001/sec-003.md"
    before = client.get(f"/api/file?project_id={test_project}&path={rel_path}").json()["data"]["content"]
    _post_batch(client, test_project, [3], dry_run=True)
    after = client.get(f"/api/file?project_id={test_project}&path={rel_path}").json()["data"]["content"]
    assert before == after


def test_dry_run_does_not_create_candidates(client, test_project, ensure_scene_files):
    """dry-run 不生成候选稿"""
    _post_batch(client, test_project, [1, 2], dry_run=True)
    resp = client.get(f"/api/candidates/{test_project}")
    candidates = resp.json()["candidates"]
    assert len(candidates) == 0, f"dry-run 生成了候选稿: {candidates}"


# ── 空目标 batch ─────────────────────────────────────────


def test_empty_targets_returns_zero_total(client, test_project):
    """未匹配目标：tasks 为空，total/succeeded/failed 都为 0"""
    result = _post_batch(client, test_project, [999], dry_run=True)  # 不存在的 sec
    assert result["tasks"] == [] or result["total"] == 0
    assert result["total"] == 0
    assert result["succeeded"] == 0
    assert result["failed"] == 0


# ── 消息外壳：ApiResponse 的 message 字段 ───────────────


def test_api_response_contains_success_and_message(client, test_project, ensure_scene_files):
    """ApiResponse 外壳必须带 success / data / message"""
    body = client.post(
        "/api/generate/batch",
        json={
            "project_id": test_project,
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1],
            "prompt_type": "generate/chapter",
            "temperature": 0.7,
            "dry_run": True,
        },
    ).json()
    assert "success" in body
    assert "data" in body
    assert "message" in body
    assert isinstance(body["message"], str)
    assert body["message"]  # 非空消息
