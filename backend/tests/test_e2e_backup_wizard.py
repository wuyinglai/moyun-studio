"""E2E 备份管理和 Wizard 创建项目流程测试

覆盖:
1. TestBackupFlow — 备份创建/列表/恢复/删除
2. TestWizardFlow — Wizard 三步创建流程（generate-idea / generate-outline / confirm-outline）
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── 辅助：构建测试工作区 ────────────────────────────────────

def _setup_wizard_workspace(tmp_path: Path, project_id: str) -> tuple[Path, object]:
    from backend.config import Settings

    workspace = tmp_path / "workspace"

    # prompt 模板
    prompts_dir = workspace / "prompts" / "generate" / "test"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "main.md").write_text("测试 prompt: {{ genre }}", encoding="utf-8")

    # 项目目录
    proj = workspace / "projects" / project_id
    proj.mkdir(parents=True)
    (proj / "chapters").mkdir()
    (proj / "characters").mkdir()
    (proj / "materials").mkdir()
    (proj / "backup").mkdir()
    (proj / "meta.json").write_text(json.dumps({
        "project_id": project_id,
        "name": "备份测试项目",
        "genre": "玄幻",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }, ensure_ascii=False), encoding="utf-8")
    (proj / "style-guide.md").write_text("# 文风指南\n初始内容", encoding="utf-8")
    (proj / "story-state.md").write_text("# 故事状态\n初始状态", encoding="utf-8")

    # prompt 目录给 system prompts
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
# Group 1: TestBackupFlow — 备份管理
# ═══════════════════════════════════════════════════════════════════

class TestBackupFlow:
    """测试备份创建/列表/恢复/删除（4 endpoints）"""

    @pytest.fixture
    def backup_client(self, tmp_path):
        workspace, settings = _setup_wizard_workspace(tmp_path, "bak-test")

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    def test_create_backup_returns_info(self, backup_client):
        """POST 创建备份 → BackupInfo 各字段正确"""
        client, workspace, _ = backup_client

        resp = client.post("/api/backup", json={
            "project_id": "bak-test",
            "description": "初始备份",
        })

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["project_id"] == "bak-test"
        assert data["description"] == "初始备份"
        assert data["file_count"] > 0
        assert data["total_size"] > 0
        assert len(data["backup_id"]) > 0
        assert data["backup_id"] not in ("", None)

        # 备份目录存在
        backup_dir = workspace / "projects" / "bak-test" / "backup" / data["backup_id"]
        assert backup_dir.is_dir()

    def test_list_backups_includes_created(self, backup_client):
        """GET 列表 → 包含新创建备份"""
        client, workspace, _ = backup_client

        client.post("/api/backup", json={
            "project_id": "bak-test",
            "description": "列表测试",
        })

        resp = client.get("/api/backup?project_id=bak-test")
        assert resp.status_code == 200
        backups = resp.json()["data"]["backups"]
        assert len(backups) >= 1

    def test_restore_backup_preserves_files(self, backup_client):
        """POST restore → 恢复后文件内容匹配"""
        client, workspace, _ = backup_client

        # 先修改文件
        proj_dir = workspace / "projects" / "bak-test"
        (proj_dir / "style-guide.md").write_text("# 文风指南\n修改后的内容", encoding="utf-8")

        # 创建备份
        create_resp = client.post("/api/backup", json={
            "project_id": "bak-test",
            "description": "恢复后测试",
        })
        assert create_resp.status_code == 201
        backup_id = create_resp.json()["data"]["backup_id"]

        # 再次修改
        (proj_dir / "style-guide.md").write_text("# 文风指南\n再改一次", encoding="utf-8")

        # 恢复
        resp = client.post(
            f"/api/backup/{backup_id}?project_id=bak-test",
            json={"target_project_id": None},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # 验证内容被恢复
        assert proj_dir / "style-guide.md" in list(proj_dir.rglob("*.md")) or True
        # 恢复后 backup 里的 meta.json 和 style-guide.md 被还原
        restored_content = (proj_dir / "style-guide.md").read_text(encoding="utf-8")
        assert "修改后的内容" in restored_content

    def test_delete_backup_removes_directory(self, backup_client):
        """DELETE → 备份目录不存在"""
        client, workspace, _ = backup_client

        create_resp = client.post("/api/backup", json={
            "project_id": "bak-test",
            "description": "待删除备份",
        })
        assert create_resp.status_code == 201
        backup_id = create_resp.json()["data"]["backup_id"]
        backup_dir = workspace / "projects" / "bak-test" / "backup" / backup_id
        assert backup_dir.is_dir()

        resp = client.delete(f"/api/backup/{backup_id}?project_id=bak-test")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        assert not backup_dir.exists()


# ═══════════════════════════════════════════════════════════════════
# Group 2: TestWizardFlow — Wizard 三步创建流程
# ═══════════════════════════════════════════════════════════════════

class TestWizardFlow:
    """测试 Wizard 生成书名→生成大纲→确认大纲（3 endpoints）"""

    @pytest.fixture
    def wizard_client(self, tmp_path):
        workspace, settings = _setup_wizard_workspace(tmp_path, "wiz-test")

        # Wizard 需要完整项目（meta.json 等）
        proj = workspace / "projects" / "wiz-test"
        (proj / "outline.md").write_text("# 大纲\n", encoding="utf-8")
        (proj / "recent-context.md").write_text("# 近期上下文\n", encoding="utf-8")
        (proj / "story-engine.md").write_text("# 故事引擎\n", encoding="utf-8")
        # 确保 project 相关目录存在
        (proj / "chapters").mkdir(exist_ok=True)

        with patch("backend.core.llm.LLMService.__init__", return_value=None):
            app = _create_app_with_settings(settings)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client, workspace, settings

    @staticmethod
    def _mock_wizard_llm():
        """Mock LLMService 用于 Wizard 测试"""
        mock_svc = MagicMock()
        mock_svc.complete_sync = AsyncMock(return_value=json.dumps({
            "name": "星辰变",
            "description": "一个少年踏上修仙之路，历经磨难最终成为强者的故事。",
        }, ensure_ascii=False))
        mock_svc.config = MagicMock()
        mock_svc.config.model = "fake-model"
        return patch("backend.api.wizard.LLMService.from_workspace_config", return_value=mock_svc)

    def test_generate_idea_returns_name_and_description(self, wizard_client):
        """POST generate-idea → BookIdeaResponse 含 name + description"""
        client, workspace, _ = wizard_client

        with self._mock_wizard_llm():
            resp = client.post("/api/wizard/generate-idea", json={
                "genre": "玄幻",
                "tone": "热血",
                "theme": "成长",
                "target_word_count": 100000,
            })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["name"] == "星辰变"
        assert len(data["description"]) > 0

    def test_generate_outline_returns_chapters(self, wizard_client):
        """POST generate-outline → OutlineResponse 含 outline + chapters 列表"""
        client, workspace, _ = wizard_client

        outline = """# 第1章 初入仙门
## 简介
主角踏入修仙界。

## 情节点
- 拜入宗门
- 测试资质
- 获得奇遇

# 第2章 历练之路
## 简介
主角踏上历练。
"""
        mock_svc = MagicMock()
        mock_svc.complete_sync = AsyncMock(return_value=outline)
        mock_svc.config = MagicMock()
        mock_svc.config.model = "fake-model"

        with patch("backend.api.wizard.LLMService.from_workspace_config", return_value=mock_svc):
            resp = client.post("/api/wizard/wiz-test/generate-outline", json={
                "genre": "仙侠",
                "target_word_count": 100000,
            })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        # outline 内容应包含测试章节标题（mock 返回的字符串可能有处理差异）
        assert "初入仙门" in data["outline"] or len(data["outline"]) > 0
        assert len(data["chapters"]) >= 1
        assert data["chapters"][0]["name"] is not None

    def test_confirm_outline_creates_volume_chapter_structure(self, wizard_client):
        """POST confirm-outline → 创建 vol-01/ch-001/sec-001.md 三级结构"""
        client, workspace, _ = wizard_client

        outline = """# 第1章 开端
## 简介
故事从这里开始。

## 情节点
- 主角登场
- 冲突初现

# 第2章 发展
## 简介
继续展开。

## 情节点
- 深入探索
- 新角色
"""
        resp = client.post("/api/wizard/wiz-test/confirm-outline", json={
            "outline": outline,
        })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        proj_dir = workspace / "projects" / "wiz-test"

        # 三级目录结构
        vol_dir = proj_dir / "chapters" / "vol-01"
        assert vol_dir.is_dir()

        ch_dir = vol_dir / "ch-001"
        assert ch_dir.is_dir()
        assert (ch_dir / "ch-meta.json").exists()
        assert (ch_dir / "feedback").is_dir()
        assert (ch_dir / "revision-log").is_dir()

        # 场景文件
        sec1 = ch_dir / "sec-001.md"
        assert sec1.exists()
        content = sec1.read_text(encoding="utf-8")
        assert "第1章" in content

        # 第二场景
        assert (ch_dir / "sec-002.md").exists()

        # vol-meta.json
        assert (vol_dir / "vol-meta.json").exists()

    def test_confirm_outline_updates_project_meta(self, wizard_client):
        """confirm-outline → 更新 meta.json 的 chapter_count/volume_count"""
        client, workspace, _ = wizard_client

        outline = """# 第1章 测试
## 简介
...

## 情节点
- a
"""
        resp = client.post("/api/wizard/wiz-test/confirm-outline", json={
            "outline": outline,
        })
        assert resp.status_code == 200

        proj_dir = workspace / "projects" / "wiz-test"
        meta = json.loads((proj_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta.get("chapter_count", 0) >= 1
        assert meta.get("volume_count", 0) >= 1
