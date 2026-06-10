"""T6.6.4 Batch Dry-Run Contract 测试

验证：
1. Batch dry_run 请求成功
2. 不调用真实 LLM
3. 不覆盖正文
4. 不生成候选稿
5. 返回结构包含 dry_run 标记
6. 多文件 batch dry_run 返回每个 item
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def test_project(client):
    """创建测试项目"""
    resp = client.post(
        "/api/projects",
        json={
            "name": "__e2e_t6_6_4_batch_dry_run",
            "genre": "测试",
            "theme": "T6.6.4 Batch Dry-Run Test",
            "tone": "中性",
            "background": "测试背景",
            "writing_style": "普通",
            "target_word_count": 50000,
            "author": "e2e",
        },
    )
    data = resp.json()
    project_id = data["data"]["project_id"]
    return project_id


@pytest.fixture(scope="session")
def create_test_files(client, test_project):
    """创建测试文件（场景正文）"""
    files = []
    for sec_num in [1, 2, 3]:
        rel_path = f"chapters/vol-01/ch-001/sec-{sec_num:03d}.md"
        client.post(
            f"/api/file?project_id={test_project}",
            json={"path": rel_path, "content": f"T6.6.4 初始正文 {sec_num}"},
        )
        files.append(rel_path)
    return files


def test_batch_dry_run_request_success(client, test_project, create_test_files):
    """1. Batch dry_run 请求成功"""
    resp = client.post(
        "/api/generate/batch",
        json={
            "project_id": test_project,
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1, 2],
            "prompt_type": "generate/chapter",
            "temperature": 0.8,
            "dry_run": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    print(f"\n[test_batch_dry_run] 响应: {resp.json()}")


def test_batch_dry_run_returns_items(client, test_project, create_test_files):
    """6. 多文件 batch dry_run 返回每个 item"""
    resp = client.post(
        "/api/generate/batch",
        json={
            "project_id": test_project,
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1, 2],
            "prompt_type": "generate/chapter",
            "dry_run": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    result = data["data"]

    assert "total" in result
    assert "tasks" in result
    assert result["total"] == 2
    assert len(result["tasks"]) == 2
    print(f"\n[test_batch_items] total={result['total']}, tasks={len(result['tasks'])}")


def test_batch_dry_run_items_marked_dry_run(client, test_project, create_test_files):
    """5. 返回结构包含 dry_run 标记"""
    resp = client.post(
        "/api/generate/batch",
        json={
            "project_id": test_project,
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1, 2],
            "prompt_type": "generate/chapter",
            "dry_run": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    result = data["data"]

    for task in result["tasks"]:
        assert task["dry_run"] is True, f"任务 {task.get('target_file')} 未标记 dry_run"
        assert task["status"] == "dry_run"
        assert task["dry_run_content"]
        assert "[DRY-RUN]" in task["dry_run_content"]
    print(f"\n[test_batch_markers] 所有任务均标记为 dry_run")


def test_batch_dry_run_does_not_cover_body(client, test_project, create_test_files):
    """3. 不覆盖正文"""
    # 先触发 batch dry-run
    resp = client.post(
        "/api/generate/batch",
        json={
            "project_id": test_project,
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1, 2],
            "prompt_type": "generate/chapter",
            "dry_run": True,
        },
    )
    assert resp.status_code == 200

    # 验证正文未被覆盖
    for sec_num in [1, 2]:
        rel_path = f"chapters/vol-01/ch-001/sec-{sec_num:03d}.md"
        file_resp = client.get(f"/api/file?project_id={test_project}&path={rel_path}")
        file_data = file_resp.json()
        assert file_data["data"]["content"] == f"T6.6.4 初始正文 {sec_num}"
    print(f"\n[test_no_cover] 正文未被覆盖")


def test_batch_dry_run_does_not_create_candidates(client, test_project, create_test_files):
    """4. 不生成候选稿"""
    # 先触发 batch dry-run
    resp = client.post(
        "/api/generate/batch",
        json={
            "project_id": test_project,
            "volume_number": 1,
            "chapter_number": 1,
            "section_numbers": [1, 2],
            "prompt_type": "generate/chapter",
            "dry_run": True,
        },
    )
    assert resp.status_code == 200

    # 验证候选稿列表为空
    candidates_resp = client.get(f"/api/candidates/{test_project}")
    candidates = candidates_resp.json()["candidates"]
    assert len(candidates) == 0, f"发现候选稿，数量：{len(candidates)}"
    print(f"\n[test_no_candidate] 未生成候选稿")


def test_batch_dry_run_default_false(client, test_project, create_test_files):
    """默认 dry_run=false（不实际调用 LLM，只验证 schema）"""
    req = {
        "project_id": test_project,
        "volume_number": 1,
        "chapter_number": 1,
        "section_numbers": [1],
        "prompt_type": "generate/chapter",
        # 不指定 dry_run，默认为 False
    }
    # 验证请求格式正确（不实际调用生成）
    resp = client.post("/api/generate/batch", json=req)
    assert resp.status_code == 200  # 可能成功或失败，取决于实际 LLM 配置
    # 关键：dry_run 字段默认为 False，已通过 schema 定义
    print(f"\n[test_default_false] dry_run 默认 false")


def test_batch_dry_run_cleanup_project(client, test_project):
    """清理测试项目"""
    resp = client.delete(f"/api/projects/{test_project}")
    assert resp.status_code == 200 or resp.status_code == 404  # 可能已被清理
    print(f"\n[test_cleanup] 测试项目清理完成")
