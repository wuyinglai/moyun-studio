"""E2E 项目管理和角色管理测试

覆盖:
1. TestProjectCRUD — 项目创建/列表/详情/更新/统计/删除
2. TestCharacterCRUD — 角色创建/列表/详情/更新/停用
"""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest


# ─── 辅助：构建测试工作区 ────────────────────────────────────

def _setup_project_workspace(tmp_path: Path, project_id: str = "mgmt-test") -> tuple[Path, object]:
    """创建包含 prompt 模板的测试工作区"""
    from backend.config import Settings

    workspace = tmp_path / "workspace"

    # prompt 模板目录（项目创建时需读取）
    prompts_dir = workspace / "prompts" / "generate" / "test"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "main.md").write_text("测试 prompt: {{ genre }}", encoding="utf-8")

    settings = Settings(
        debug=True,
        workspace_path=workspace,
        llm_provider="custom",
        llm_api_key="fake-key-for-test",
        llm_model="fake-model",
    )
    return workspace, settings


# ─── 通用：创建 App + 清除 get_settings 缓存 ────────────────────

def _create_app_with_settings(settings):
    import backend.config as bc
    bc.get_settings.cache_clear()

    with patch("backend.config.Settings", return_value=settings):
        from backend.main import create_app
        return create_app()


# ═══════════════════════════════════════════════════════════════════
# Group 1: TestProjectCRUD — 项目 CRUD + 统计 + 删除
# ═══════════════════════════════════════════════════════════════════

class TestProjectCRUD:
    """测试项目创建/列表/详情/更新/统计/删除（6 endpoints）"""

    @pytest.fixture
    def proj_client(self, tmp_path):
        workspace, settings = _setup_project_workspace(tmp_path, "mgmt-proj")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_create_project_returns_info_and_creates_dirs(self, proj_client):
        """POST 创建项目 → ProjectInfo 各字段正确 + 目录结构完整"""
        client, workspace, _ = proj_client

        resp = client.post("/api/projects", json={
            "name": "测试项目",
            "genre": "玄幻",
            "theme": "成长",
            "tone": "热血",
            "target_word_count": 200000,
            "author": "测试作者",
        })

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["data"]["name"] == "测试项目"
        assert data["data"]["genre"] == "玄幻"
        assert data["data"]["target_word_count"] == 200000
        assert data["data"]["author"] == "测试作者"
        project_id = data["data"]["project_id"]
        assert len(project_id) == 8

        # 目录结构
        proj_dir = workspace / "projects" / project_id
        assert (proj_dir / "meta.json").exists()
        assert (proj_dir / "context.json").exists()
        assert (proj_dir / "chapters").is_dir()
        assert (proj_dir / "characters").is_dir()
        assert (proj_dir / "materials").is_dir()
        assert (proj_dir / "backup").is_dir()
        assert (proj_dir / "feedback").is_dir()
        assert (proj_dir / "style-guide.md").exists()
        assert (proj_dir / "story-state.md").exists()
        assert (proj_dir / "outline.md").exists()

    def test_list_projects_includes_created(self, proj_client):
        """GET 列表 → 包含新创建的项目"""
        client, workspace, _ = proj_client

        resp = client.post("/api/projects", json={
            "name": "列表测试项目",
            "genre": "奇幻",
        })
        assert resp.status_code == 201
        created_id = resp.json()["data"]["project_id"]

        list_resp = client.get("/api/projects")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        projects = list_data["data"]["projects"]
        assert len(projects) >= 1
        ids = [p["project_id"] for p in projects]
        assert created_id in ids

    def test_get_project_detail_completion_rate_present(self, proj_client):
        """GET 详情 → ProjectInfo 各字段存在"""
        client, workspace, _ = proj_client

        create_resp = client.post("/api/projects", json={
            "name": "详情测试",
            "genre": "仙侠",
        })
        assert create_resp.status_code == 201
        project_id = create_resp.json()["data"]["project_id"]

        resp = client.get(f"/api/projects/{project_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "详情测试"
        assert data["genre"] == "仙侠"
        assert "completion_rate" in data
        assert "total_words" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_nonexistent_project_returns_404(self, proj_client):
        """GET 不存在的项目 → 404"""
        client, workspace, _ = proj_client

        resp = client.get("/api/projects/nonexist")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"

    def test_update_project_meta(self, proj_client):
        """PUT 更新 → 返回更新后数据"""
        client, workspace, _ = proj_client

        create_resp = client.post("/api/projects", json={
            "name": "原始名称",
            "genre": "科幻",
        })
        assert create_resp.status_code == 201
        project_id = create_resp.json()["data"]["project_id"]

        resp = client.put(f"/api/projects/{project_id}", json={
            "name": "新名称",
            "theme": "新主题",
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["name"] == "新名称"
        assert data["theme"] == "新主题"
        assert data["genre"] == "科幻"  # 未修改的保持原值

    def test_recalculate_stats_with_scene_files(self, proj_client):
        """POST recalculate-stats → 有场景文件时统计正确"""
        client, workspace, _ = proj_client

        create_resp = client.post("/api/projects", json={
            "name": "统计测试",
            "genre": "都市",
        })
        assert create_resp.status_code == 201
        project_id = create_resp.json()["data"]["project_id"]

        # 创建场景文件
        proj_dir = workspace / "projects" / project_id
        (proj_dir / "chapters" / "vol-01" / "ch-001").mkdir(parents=True)
        (proj_dir / "chapters" / "vol-01" / "ch-001" / "sec-001.md").write_text(
            "# 场景一\n\n这是测试场景内容，包含一些中文文字。\n\n第二段内容。", encoding="utf-8"
        )
        (proj_dir / "chapters" / "vol-01" / "ch-001" / "sec-002.md").write_text("", encoding="utf-8")

        resp = client.post(f"/api/projects/{project_id}/recalculate-stats")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        stats = resp.json()["data"]
        assert stats["total_sections"] == 2
        assert stats["completed_sections"] >= 1
        assert stats["total_words"] > 0
        assert stats["chapter_count"] >= 1
        assert stats["volume_count"] >= 1
        assert "completion_rate" in stats

    def test_delete_project_removes_directory(self, proj_client):
        """DELETE → 项目目录不存在 + 返回 success"""
        client, workspace, _ = proj_client

        create_resp = client.post("/api/projects", json={
            "name": "删除测试",
            "genre": "历史",
        })
        assert create_resp.status_code == 201
        project_id = create_resp.json()["data"]["project_id"]
        proj_dir = workspace / "projects" / project_id
        assert proj_dir.exists()

        resp = client.delete(f"/api/projects/{project_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert not proj_dir.exists()


# ═══════════════════════════════════════════════════════════════════
# Group 2: TestCharacterCRUD — 角色管理
# ═══════════════════════════════════════════════════════════════════

class TestCharacterCRUD:
    """测试角色创建/列表/详情/更新/停用（5 endpoints）"""

    @pytest.fixture
    def char_client(self, tmp_path):
        workspace, settings = _setup_project_workspace(tmp_path, "mgmt-char")
        proj = workspace / "projects" / "mgmt-char"
        proj.mkdir(parents=True)
        (proj / "characters").mkdir()
        (proj / "meta.json").write_text(json.dumps({
            "project_id": "mgmt-char",
            "name": "角色测试项目",
            "genre": "玄幻",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }, ensure_ascii=False), encoding="utf-8")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_create_character_returns_profile(self, char_client):
        """POST 创建 → CharacterProfile 各字段正确"""
        client, workspace, _ = char_client

        resp = client.post("/api/characters", json={
            "project_id": "mgmt-char",
            "name": "主角·叶凡",
            "role": "protagonist",
            "age": "18",
            "appearance": "黑衣少年",
            "personality": "坚韧不拔",
            "background": "普通少年",
            "abilities": ["剑术", "医术"],
            "relationships": {},
        })

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["name"] == "主角·叶凡"
        assert data["role"] == "protagonist"
        assert data["age"] == "18"
        assert data["appearance"] == "黑衣少年"
        assert data["personality"] == "坚韧不拔"
        assert data["status"] == "active"
        assert data["character_id"].startswith("char_") or re.match(r"^[a-f0-9]{8}$", data["character_id"])
        assert data["abilities"] == ["剑术", "医术"]

    def test_list_characters_includes_created(self, char_client):
        """GET 列表 → 包含新创建角色"""
        client, workspace, _ = char_client

        create_resp = client.post("/api/characters", json={
            "project_id": "mgmt-char",
            "name": "列表角色",
        })
        assert create_resp.status_code == 201
        created_id = create_resp.json()["data"]["character_id"]

        resp = client.get(f"/api/characters?project_id=mgmt-char")
        assert resp.status_code == 200
        characters = resp.json()["data"]["characters"]
        assert len(characters) >= 1
        ids = [c["character_id"] for c in characters]
        assert created_id in ids

    def test_get_character_detail(self, char_client):
        """GET 详情 → 与创建数据一致"""
        client, workspace, _ = char_client

        create_resp = client.post("/api/characters", json={
            "project_id": "mgmt-char",
            "name": "详情角色",
            "role": "antagonist",
            "age": "99",
        })
        assert create_resp.status_code == 201
        char_id = create_resp.json()["data"]["character_id"]

        resp = client.get(f"/api/characters/{char_id}?project_id=mgmt-char")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "详情角色"
        assert data["role"] == "antagonist"
        assert data["age"] == "99"

    def test_update_character_fields(self, char_client):
        """PUT 更新 → 字段正确更新"""
        client, workspace, _ = char_client

        create_resp = client.post("/api/characters", json={
            "project_id": "mgmt-char",
            "name": "原始角色",
            "personality": "内向",
        })
        assert create_resp.status_code == 201
        char_id = create_resp.json()["data"]["character_id"]

        resp = client.put(f"/api/characters/{char_id}?project_id=mgmt-char", json={
            "name": "更名角色",
            "personality": "外向开朗",
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["name"] == "更名角色"
        assert data["personality"] == "外向开朗"

    def test_deactivate_character_marks_inactive(self, char_client):
        """DELETE → 角色标记为 inactive"""
        client, workspace, _ = char_client

        create_resp = client.post("/api/characters", json={
            "project_id": "mgmt-char",
            "name": "待停用角色",
        })
        assert create_resp.status_code == 201
        char_id = create_resp.json()["data"]["character_id"]

        resp = client.delete(f"/api/characters/{char_id}?project_id=mgmt-char")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # 验证角色文件被标记为 inactive
        char_file = workspace / "projects" / "mgmt-char" / "characters" / f"{char_id}.json"
        assert char_file.exists()
        data = json.loads(char_file.read_text(encoding="utf-8"))
        assert data.get("status") == "inactive"
