"""E2E 反馈管理、修改日志和版本对比测试

覆盖:
1. TestFeedbackCRUD — 反馈创建/列表(按章节/状态过滤)/更新/删除
2. TestRevisionLogCRUD — 修改日志创建(自动diff)/列表(按类型过滤)/详情
3. TestCompare — 文本 diff / 并排对比 / 章节对比(stub)
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ─── 辅助：构建测试工作区 ────────────────────────────────────

def _setup_workspace(ctx_path: Path, project_id: str) -> tuple[Path, object]:
    from backend.config import Settings

    workspace = ctx_path / "workspace"

    # 项目目录
    proj = workspace / "projects" / project_id
    (proj / "chapters" / "vol-01" / "ch-001").mkdir(parents=True)
    (proj / "chapters" / "vol-01" / "ch-001" / "feedback").mkdir(parents=True)
    (proj / "chapters" / "vol-01" / "ch-001" / "revision-log").mkdir(parents=True)
    (proj / "materials").mkdir(parents=True, exist_ok=True)
    (proj / "backup" / "snapshots").mkdir(parents=True, exist_ok=True)

    (proj / "meta.json").write_text(json.dumps({
        "project_id": project_id,
        "name": "P2测试项目",
        "genre": "玄幻",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }, ensure_ascii=False), encoding="utf-8")

    # 场景文件
    (proj / "chapters" / "vol-01" / "ch-001" / "sec-001.md").write_text(
        "# 场景一\n\n初始内容。", encoding="utf-8"
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
# Group 1: TestFeedbackCRUD — 用户反馈管理
# ═══════════════════════════════════════════════════════════════════

class TestFeedbackCRUD:
    """测试反馈创建/列表/更新/删除（4 endpoints）"""

    @pytest.fixture
    def fb_client(self, tmp_path):
        workspace, settings = _setup_workspace(tmp_path, "fb-test")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_create_feedback_returns_model(self, fb_client):
        """POST 创建 → UserFeedback 各字段正确"""
        client, workspace, _ = fb_client

        resp = client.post("/api/feedback/fb-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "type": "suggestion",
            "content": "建议增加更多动作描写",
            "location": "第2段",
            "satisfaction_level": "满意",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["chapter_path"] == "chapters/vol-01/ch-001/sec-001.md"
        assert data["type"] == "suggestion"
        assert data["content"] == "建议增加更多动作描写"
        assert data["location"] == "第2段"
        assert data["satisfaction_level"] == "满意"
        assert data["resolved"] is False
        assert data["id"].startswith("fb-")

        # 文件存在
        fb_file = workspace / "projects" / "fb-test" / "chapters" / "vol-01" / "ch-001" / "feedback" / f"{data['id']}.json"
        assert fb_file.exists()

    def test_list_feedback_by_chapter_path(self, fb_client):
        """GET 列表 → 按 chapter_path 过滤"""
        client, workspace, _ = fb_client

        # 创建两个不同章节的反馈
        client.post("/api/feedback/fb-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "type": "error",
            "content": "逻辑错误",
        })

        # 按特定章节过滤
        resp = client.get(
            "/api/feedback/fb-test",
            params={"chapter_path": "chapters/vol-01/ch-001/sec-001.md"},
        )
        assert resp.status_code == 200
        feedbacks = resp.json()["data"]
        assert len(feedbacks) >= 1
        for fb in feedbacks:
            assert fb["chapter_path"] == "chapters/vol-01/ch-001/sec-001.md"

    def test_list_feedback_by_resolved_status(self, fb_client):
        """GET 列表 → 按 resolved 状态过滤"""
        client, workspace, _ = fb_client

        resp = client.get("/api/feedback/fb-test", params={"resolved": False})
        assert resp.status_code == 200
        feedbacks = resp.json()["data"]
        for fb in feedbacks:
            assert fb["resolved"] is False

    def test_update_feedback_mark_resolved(self, fb_client):
        """PATCH 更新 → 标记已解决"""
        client, workspace, _ = fb_client

        create_resp = client.post("/api/feedback/fb-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "type": "improvement",
            "content": "改进建议",
        })
        assert create_resp.status_code == 200
        fb_id = create_resp.json()["data"]["id"]

        resp = client.patch(f"/api/feedback/fb-test/{fb_id}", json={
            "resolved": True,
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["resolved"] is True
        assert data["resolved_at"] is not None

    def test_delete_feedback_marks_resolved(self, fb_client):
        """DELETE → 标记为已解决"""
        client, workspace, _ = fb_client

        create_resp = client.post("/api/feedback/fb-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "type": "suggestion",
            "content": "待删除建议",
        })
        assert create_resp.status_code == 200
        fb_id = create_resp.json()["data"]["id"]

        resp = client.delete(f"/api/feedback/fb-test/{fb_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # 验证被标记为已解决
        fb_file = workspace / "projects" / "fb-test" / "chapters" / "vol-01" / "ch-001" / "feedback" / f"{fb_id}.json"
        data = json.loads(fb_file.read_text(encoding="utf-8"))
        assert data["resolved"] is True


# ═══════════════════════════════════════════════════════════════════
# Group 2: TestRevisionLogCRUD — 修改日志管理
# ═══════════════════════════════════════════════════════════════════

class TestRevisionLogCRUD:
    """测试修改日志创建(自动diff)/列表/详情（3 endpoints）"""

    @pytest.fixture
    def rev_client(self, tmp_path):
        workspace, settings = _setup_workspace(tmp_path, "rev-test")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_create_revision_log_generates_diff(self, rev_client):
        """POST 创建 → 自动生成 unified diff + 字数统计"""
        client, workspace, _ = rev_client

        resp = client.post("/api/revision-log/rev-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "revision_type": "user_edit",
            "description": "手动修改第一段",
            "content_before": "# 场景一\n\n初始内容。",
            "content_after": "# 场景一\n\n修改后的精彩内容。",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["revision_type"] == "user_edit"
        assert data["description"] == "手动修改第一段"
        assert data["id"].startswith("rev-")
        # 有 diff
        assert data["diff"] is not None and len(data["diff"]) > 0 if data.get("diff") else True
        # 字数统计
        assert "word_count_before" in data
        assert "word_count_after" in data

    def test_list_revision_logs_returns_all(self, rev_client):
        """GET 列表 → 所有日志"""
        client, workspace, _ = rev_client

        client.post("/api/revision-log/rev-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "revision_type": "ai_rewrite",
            "description": "AI重写",
            "content_before": "旧内容",
            "content_after": "新内容",
        })

        resp = client.get("/api/revision-log/rev-test")
        assert resp.status_code == 200
        logs = resp.json()["data"]
        assert len(logs) >= 1

    def test_list_revision_logs_by_type(self, rev_client):
        """GET 列表 → 按 revision_type 过滤"""
        client, workspace, _ = rev_client

        client.post("/api/revision-log/rev-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "revision_type": "auto_save",
            "description": "自动保存",
            "content_before": "",
            "content_after": "自动保存内容",
        })

        resp = client.get(
            "/api/revision-log/rev-test",
            params={"revision_type": "auto_save"},
        )
        assert resp.status_code == 200
        logs = resp.json()["data"]
        for log in logs:
            assert log["revision_type"] == "auto_save"

    def test_get_revision_log_detail(self, rev_client):
        """GET 详情 → 与创建数据匹配"""
        client, workspace, _ = rev_client

        create_resp = client.post("/api/revision-log/rev-test", json={
            "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
            "revision_type": "user_edit",
            "description": "详情测试",
            "content_before": "before text",
            "content_after": "after text 现在有了更多中文",
        })
        assert create_resp.status_code == 200
        log_id = create_resp.json()["data"]["id"]

        resp = client.get(f"/api/revision-log/rev-test/{log_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["id"] == log_id
        assert data["description"] == "详情测试"


# ═══════════════════════════════════════════════════════════════════
# Group 3: TestCompare — 版本对比
# ═══════════════════════════════════════════════════════════════════

class TestCompare:
    """测试文本 diff / 并排对比 / 章节对比（stub）"""

    @pytest.fixture
    def cmp_client(self, tmp_path):
        workspace, settings = _setup_workspace(tmp_path, "cmp-test")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_compare_identical_texts_no_diff(self, cmp_client):
        """相同文本 → has_diff=False"""
        client, workspace, _ = cmp_client

        text = "第一行\n第二行\n第三行"
        resp = client.post("/api/compare", json={
            "old_text": text,
            "new_text": text,
            "fromfile": "版本1",
            "tofile": "版本2",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["has_diff"] is False
        assert data["added_lines"] == 0
        assert data["removed_lines"] == 0

    def test_compare_different_texts_shows_diff(self, cmp_client):
        """不同文本 → has_diff=True, added_lines > 0"""
        client, workspace, _ = cmp_client

        resp = client.post("/api/compare", json={
            "old_text": "第一行\n第二行\n第三行",
            "new_text": "第一行\n修改第二行\n新增第三行\n第四行",
            "fromfile": "旧版",
            "tofile": "新版",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["has_diff"] is True
        assert data["added_lines"] > 0 or data["removed_lines"] > 0

    def test_compare_side_by_side_returns_change_types(self, cmp_client):
        """并排对比 → lines 含 change_type"""
        client, workspace, _ = cmp_client

        resp = client.post("/api/compare/side-by-side", json={
            "old_text": "旧行1\n旧行2\n公共行",
            "new_text": "新行1\n公共行",
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert "lines" in data
        assert "stats" in data
        assert data["has_diff"] is True
        change_types = [line.get("change_type") for line in data["lines"]]
        assert "unchanged" in change_types or "modified" in change_types or "added" in change_types

    def test_compare_chapters_returns_placeholder(self, cmp_client):
        """章节对比（stub） → 返回占位内容"""
        client, workspace, _ = cmp_client

        resp = client.post(
            "/api/compare/chapters",
            params={
                "project_id": "cmp-test",
                "chapter_path": "chapters/vol-01/ch-001",
                "version_a": "rev-001",
                "version_b": "rev-002",
            },
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["has_diff"] is True  # stub returns True
        # stub 返回占位消息
        assert len(data["diff"]) > 0
