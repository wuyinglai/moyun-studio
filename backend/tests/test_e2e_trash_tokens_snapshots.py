"""E2E 回收站、Token 计数和版本快照测试

覆盖:
1. TestTrashFlow — 回收站列表/恢复/清空
2. TestTokens — Token 计数/估算
3. TestSnapshots — 快照创建/列表/恢复/对比
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ─── 辅助 ────────────────────────────────────────────────────

def _setup_workspace(ctx_path: Path, project_id: str) -> tuple[Path, object]:
    from backend.config import Settings

    workspace = ctx_path / "workspace"

    # 项目目录
    proj = workspace / "projects" / project_id
    (proj / "chapters" / "vol-01" / "ch-001").mkdir(parents=True)
    (proj / "chapters" / "vol-01" / "ch-001" / "revision-log").mkdir(exist_ok=True)
    (proj / "materials").mkdir(exist_ok=True)

    (proj / "meta.json").write_text(json.dumps({
        "project_id": project_id,
        "name": "P3测试项目",
        "genre": "玄幻",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }, ensure_ascii=False), encoding="utf-8")

    (proj / "outline.md").write_text("# 大纲\nP3测试大纲内容\n", encoding="utf-8")
    (proj / "style-guide.md").write_text("# 文风指南\nP3测试风格", encoding="utf-8")

    # 场景文件（供 snapshot 使用）
    (proj / "chapters" / "vol-01" / "ch-001" / "sec-001.md").write_text(
        "# 场景一\n\n初始内容。\n\n第二段。", encoding="utf-8"
    )

    # prompt 目录
    (workspace / "prompts").mkdir(parents=True, exist_ok=True)

    settings = Settings(
        debug=True,
        workspace_path=workspace,
        llm_provider="custom",
        llm_api_key="fake-key-for-test",
        llm_model="fake-model",
    )
    return workspace, settings


def _create_app_with_settings(settings):
    import backend.config as bc
    bc.get_settings.cache_clear()
    with patch("backend.config.Settings", return_value=settings):
        from backend.main import create_app
        return create_app()


# ═══════════════════════════════════════════════════════════════════
# Group 1: TestTrashFlow — 回收站
# ═══════════════════════════════════════════════════════════════════

class TestTrashFlow:
    """测试回收站列表/恢复/清空（3 endpoints）"""

    @pytest.fixture
    def trash_client(self, tmp_path):
        workspace, settings = _setup_workspace(tmp_path, "trash-test")

        # 预置一些到回收站
        from backend.core.trash import TrashService
        ts = TrashService(workspace)
        # 移动一个文件到回收站
        test_file = workspace / "projects" / "trash-test" / "style-guide.md"
        ts.move_to_trash(test_file)

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings, ts

    def test_list_trash_has_items(self, trash_client):
        """GET /api/trash/list → items 含预置条目"""
        client, workspace, _, _ = trash_client

        resp = client.get("/api/trash/list")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        # 检查 item 字段
        item = data["items"][0]
        assert "trash_name" in item
        assert "original_path" in item

    def test_restore_from_trash(self, trash_client):
        """POST /api/trash/restore → 文件恢复到原位置"""
        client, workspace, _, ts = trash_client

        # 获取当前垃圾列表
        list_resp = client.get("/api/trash/list")
        items = list_resp.json()["data"]["items"]
        if len(items) == 0:
            pytest.skip("No trash items to restore")
        trash_name = items[0]["trash_name"]

        resp = client.post("/api/trash/restore", json={"trash_name": trash_name})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "restored_path" in resp.json()["data"]

        # 恢复后回收站少一项
        list_after = client.get("/api/trash/list")
        assert list_after.json()["data"]["total"] == list_resp.json()["data"]["total"] - 1

    def test_empty_trash(self, trash_client):
        """POST /api/trash/empty → 清空后 total=0"""
        client, workspace, _, _ = trash_client

        resp = client.post("/api/trash/empty")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["count"] >= 0

        # 清空后无条目
        list_resp = client.get("/api/trash/list")
        assert list_resp.json()["data"]["total"] == 0


# ═══════════════════════════════════════════════════════════════════
# Group 2: TestTokens — Token 计数
# ═══════════════════════════════════════════════════════════════════

class TestTokens:
    """测试 Token 计数/估算（2 endpoints）"""

    @pytest.fixture
    def tok_client(self, tmp_path):
        workspace, settings = _setup_workspace(tmp_path, "tok-test")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_count_tokens_chinese_text(self, tok_client):
        """POST /api/tokens/count → 中文文本 token > 0"""
        client, workspace, _ = tok_client

        resp = client.post("/api/tokens/count", json={
            "text": "# 第一章\n\n主角踏入大殿，环顾四周。众人屏息凝神。\n\n这是一段测试文本。",
            "model": "gpt-4",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["tokens"] > 0
        assert data["model"] == "gpt-4"
        assert data["max_context"] == 8192
        assert data["remaining"] == data["max_context"] - data["tokens"]

    def test_count_tokens_returns_remaining(self, tok_client):
        """token 计数 → remaining + max_context 正确"""
        client, workspace, _ = tok_client

        resp = client.post("/api/tokens/count", json={
            "text": "Hello world! 你好世界！",
            "model": "claude-3-5-sonnet",
        })

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["max_context"] == 200000
        assert data["remaining"] > 0

    def test_estimate_tokens_prompt(self, tok_client):
        """POST /api/tokens/estimate target=prompt → 估算 token"""
        client, workspace, _ = tok_client

        resp = client.post("/api/tokens/estimate", json={
            "project_id": "tok-test",
            "target": "prompt",
            "template": "generate/test",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["target"] == "prompt"
        assert data["estimated_tokens"] >= 0
        assert data["template"] == "generate/test"

    def test_estimate_tokens_outline(self, tok_client):
        """POST /api/tokens/estimate target=outline → 估算 token"""
        client, workspace, _ = tok_client

        resp = client.post("/api/tokens/estimate", json={
            "project_id": "tok-test",
            "target": "outline",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["target"] == "outline"
        assert data["estimated_tokens"] >= 0


# ═══════════════════════════════════════════════════════════════════
# Group 3: TestSnapshots — 版本快照
# ═══════════════════════════════════════════════════════════════════

class TestSnapshots:
    """测试快照创建/列表/恢复/对比（4 endpoints）"""

    @pytest.fixture
    def snap_client(self, tmp_path):
        workspace, settings = _setup_workspace(tmp_path, "snap-test")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_create_snapshot_returns_snapshot_id(self, snap_client):
        """POST 创建快照 → snapshot_id + file_path + word_count"""
        client, workspace, _ = snap_client

        resp = client.post("/api/snapshots/snap-test", json={
            "file_path": "chapters/vol-01/ch-001/sec-001.md",
            "label": "初始版本",
        })

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "snapshot_id" in data
        assert data["file_path"].endswith("sec-001.md") or "sec-001" in data["file_path"]
        assert data["label"] == "初始版本"
        assert data["word_count"] > 0

    def test_list_snapshots_returns_created(self, snap_client):
        """GET 列表 → 包含已创建快照"""
        client, workspace, _ = snap_client

        # 创建快照
        create_resp = client.post("/api/snapshots/snap-test", json={
            "file_path": "chapters/vol-01/ch-001/sec-001.md",
            "label": "列表测试",
        })
        assert create_resp.status_code == 201
        snapshot_id = create_resp.json()["data"]["snapshot_id"]

        resp = client.get(
            "/api/snapshots/snap-test",
            params={"file_path": "chapters/vol-01/ch-001/sec-001.md"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        snapshots = resp.json()["data"]
        ids = [s["snapshot_id"] for s in snapshots]
        assert snapshot_id in ids

    def test_restore_snapshot_writes_file_content(self, snap_client):
        """POST restore → 文件内容被恢复为快照内容"""
        client, workspace, _ = snap_client

        # 记录当前内容
        sec_path = workspace / "projects" / "snap-test" / "chapters" / "vol-01" / "ch-001" / "sec-001.md"
        original = sec_path.read_text(encoding="utf-8")

        # 创建快照
        create_resp = client.post("/api/snapshots/snap-test", json={
            "file_path": "chapters/vol-01/ch-001/sec-001.md",
            "label": "恢复测试",
        })
        assert create_resp.status_code == 201
        snapshot_id = create_resp.json()["data"]["snapshot_id"]

        # 修改文件
        sec_path.write_text("# 场景一\n\n修改后的内容。", encoding="utf-8")

        # 恢复
        resp = client.post("/api/snapshots/snap-test/restore", json={
            "project_id": "snap-test",
            "snapshot_id": snapshot_id,
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # 验证内容恢复
        restored = sec_path.read_text(encoding="utf-8")
        assert restored == original

    def test_compare_snapshots_returns_diff(self, snap_client):
        """POST compare → diff 包含差异信息"""
        client, workspace, _ = snap_client

        # 创建第一个快照
        sec_path = workspace / "projects" / "snap-test" / "chapters" / "vol-01" / "ch-001" / "sec-001.md"
        create1 = client.post("/api/snapshots/snap-test", json={
            "file_path": "chapters/vol-01/ch-001/sec-001.md",
            "label": "v1",
        })
        assert create1.status_code == 201
        snap1 = create1.json()["data"]["snapshot_id"]

        # 修改文件后创建第二个快照
        sec_path.write_text("# 场景一\n\n修改后的新内容。\n\n新增第三段。", encoding="utf-8")
        create2 = client.post("/api/snapshots/snap-test", json={
            "file_path": "chapters/vol-01/ch-001/sec-001.md",
            "label": "v2",
        })
        assert create2.status_code == 201
        snap2 = create2.json()["data"]["snapshot_id"]

        resp = client.post("/api/snapshots/snap-test/compare", json={
            "snapshot_id1": snap1,
            "snapshot_id2": snap2,
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "diff" in data
        assert data["has_diff"] is True

    def test_snapshot_nonexistent_project_404(self, snap_client):
        """不存在项目 → 404"""
        client, workspace, _ = snap_client

        resp = client.get(
            "/api/snapshots/nonexist",
            params={"file_path": "chapters/vol-01/ch-001/sec-001.md"},
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
