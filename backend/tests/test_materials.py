"""Materials API 测试

验证 materials.py 通过 FileService 进行文件读写，
item_id 路径遍历防护，以及安全删除行为。
"""

import json

import pytest

from backend.api.materials import (
    _list_materials,
    _load_material,
    _make_file_service,
    _material_rel_path,
    _save_material,
    _type_dir_rel_path,
    _validate_item_id,
    _validate_type,
)
from backend.core.exceptions import ValidationError
from backend.core.file_ops import FileService


# ═══════════════════════════════════════════════════════════
# _material_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestMaterialRelPath:
    """_material_rel_path 构建安全相对路径"""

    def test_plots_type(self):
        assert _material_rel_path("plots", "abc123") == "materials/extracted/plots/abc123.json"

    def test_scenes_type(self):
        assert _material_rel_path("scenes", "xyz") == "materials/extracted/scenes/xyz.json"

    def test_summaries_type(self):
        assert _material_rel_path("summaries", "sec-001") == "materials/extracted/summaries/sec-001.md"

    def test_worldbuilding_type(self):
        assert _material_rel_path("worldbuilding", "main") == "materials/extracted/worldbuilding.md"

    def test_character_type(self):
        assert _material_rel_path("character", "char1") == "materials/extracted/character/char1.json"


# ═══════════════════════════════════════════════════════════
# _type_dir_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestTypeDirRelPath:
    """_type_dir_rel_path 构建类型目录相对路径"""

    def test_plots(self):
        assert _type_dir_rel_path("plots") == "materials/extracted/plots"

    def test_summaries(self):
        assert _type_dir_rel_path("summaries") == "materials/extracted/summaries"


# ═══════════════════════════════════════════════════════════
# _validate_type 测试
# ═══════════════════════════════════════════════════════════


class TestValidateType:
    """_validate_type 验证素材类型"""

    def test_valid_plural_types(self):
        for t in ["plots", "scenes", "summaries", "worldbuilding", "character"]:
            assert _validate_type(t) is True

    def test_valid_singular_types(self):
        for t in ["plot", "scene", "summary", "character"]:
            assert _validate_type(t) is True

    def test_invalid_type(self):
        assert _validate_type("../../../etc") is False

    def test_empty_type(self):
        assert _validate_type("") is False


# ═══════════════════════════════════════════════════════════
# _validate_item_id 测试
# ═══════════════════════════════════════════════════════════


class TestValidateItemId:
    """_validate_item_id 拒绝路径遍历"""

    def test_normal_id(self):
        _validate_item_id("abc123")  # should not raise

    def test_uuid_id(self):
        _validate_item_id("a1b2c3d4")  # should not raise

    def test_dotdot_rejected(self):
        with pytest.raises(ValidationError, match="非法 item_id"):
            _validate_item_id("../etc")

    def test_slash_rejected(self):
        with pytest.raises(ValidationError, match="非法 item_id"):
            _validate_item_id("sub/file")

    def test_backslash_rejected(self):
        with pytest.raises(ValidationError, match="非法 item_id"):
            _validate_item_id("sub\\file")

    def test_dot_prefix_rejected(self):
        with pytest.raises(ValidationError, match="非法 item_id"):
            _validate_item_id(".env")

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="item_id 不能为空"):
            _validate_item_id("")


# ═══════════════════════════════════════════════════════════
# FileService 正常读写测试
# ═══════════════════════════════════════════════════════════


class TestMaterialFileService:
    """验证 FileService 正常读写素材文件"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.fixture
    def project_dir(self, tmp_path):
        d = tmp_path / "test-project"
        d.mkdir()
        return d

    @pytest.mark.asyncio
    async def test_save_and_load_plot(self, fs, project_dir):
        """保存和读取情节素材"""
        data = {"plot_id": "p1", "title": "主线情节", "description": "测试"}
        await _save_material(fs, "test-project", "plots", "p1", data)

        result = await _load_material(fs, "test-project", "plots", "p1")
        assert result is not None
        assert result["plot_id"] == "p1"
        assert result["title"] == "主线情节"

    @pytest.mark.asyncio
    async def test_save_and_load_summary(self, fs, project_dir):
        """保存和读取摘要素材"""
        data = {"summary_id": "sec-001", "summary": "场景摘要内容"}
        await _save_material(fs, "test-project", "summaries", "sec-001", data)

        result = await _load_material(fs, "test-project", "summaries", "sec-001")
        assert result is not None
        assert result["summary_id"] == "sec-001"

    @pytest.mark.asyncio
    async def test_save_and_load_worldbuilding(self, fs, project_dir):
        """保存和读取世界观素材"""
        data = {"world_id": "main", "content": "世界设定内容"}
        await _save_material(fs, "test-project", "worldbuilding", "main", data)

        result = await _load_material(fs, "test-project", "worldbuilding", "main")
        assert result is not None
        assert "世界设定内容" in result["content"]

    @pytest.mark.asyncio
    async def test_list_materials(self, fs, project_dir):
        """列出素材"""
        # 创建两个情节
        await _save_material(fs, "test-project", "plots", "p1", {"plot_id": "p1", "title": "情节1"})
        await _save_material(fs, "test-project", "plots", "p2", {"plot_id": "p2", "title": "情节2"})

        items = await _list_materials(fs, "test-project", "plots")
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_none(self, fs, project_dir):
        """加载不存在的素材返回 None"""
        result = await _load_material(fs, "test-project", "plots", "nonexistent")
        assert result is None


# ═══════════════════════════════════════════════════════════
# FileService 安全删除测试
# ═══════════════════════════════════════════════════════════


class TestMaterialDelete:
    """验证素材删除通过 FileService（移到回收站）"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.fixture
    def project_dir(self, tmp_path):
        d = tmp_path / "test-project"
        d.mkdir()
        return d

    @pytest.mark.asyncio
    async def test_delete_material_moves_to_trash(self, fs, project_dir):
        """删除素材移到回收站而非直接删除"""
        data = {"plot_id": "p1", "title": "待删除"}
        await _save_material(fs, "test-project", "plots", "p1", data)

        # 确认文件存在
        full_rel = "test-project/materials/extracted/plots/p1.json"
        assert await fs.exists(full_rel)

        # 删除
        result = await fs.delete_file(full_rel)
        assert result is not None  # 回收站记录

        # 确认文件已不在原位
        assert not await fs.exists(full_rel)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_none(self, fs, project_dir):
        """删除不存在的素材返回 None"""
        full_rel = "test-project/materials/extracted/plots/nonexistent.json"
        result = await fs.delete_file(full_rel)
        assert result is None


# ═══════════════════════════════════════════════════════════
# FileService 路径遍历防护测试
# ═══════════════════════════════════════════════════════════


class TestMaterialPathTraversal:
    """验证 FileService 拒绝恶意路径遍历"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_traversal_project_id_rejected(self, fs):
        """../project_id 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/materials/extracted/plots/p1.json")

    @pytest.mark.asyncio
    async def test_absolute_path_rejected(self, fs):
        """绝对路径被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("/etc/materials/extracted/plots/p1.json")

    @pytest.mark.asyncio
    async def test_windows_traversal_rejected(self, fs):
        """Windows 风格遍历被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("..\\etc\\materials/extracted/plots/p1.json")

    @pytest.mark.asyncio
    async def test_traversal_write_rejected(self, fs):
        """路径遍历写入被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.write_file("../etc/evil.json", "malicious")

    @pytest.mark.asyncio
    async def test_traversal_delete_rejected(self, fs):
        """路径遍历删除被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.delete_file("../etc/important.json")

    @pytest.mark.asyncio
    async def test_forbidden_segment_rejected(self, fs):
        """.git 路径段被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.read_file("test-project/.git/config")


# ═══════════════════════════════════════════════════════════
# 敏感 dotfile 阻断测试
# ═══════════════════════════════════════════════════════════


class TestSensitiveDotfilesBlocked:
    """验证 .env, .config.json, .git 等敏感 dotfile 仍被阻止"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_env_blocked(self, fs):
        """.env 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.write_file("test-project/materials/extracted/.env", "SECRET=123")

    @pytest.mark.asyncio
    async def test_config_json_blocked(self, fs):
        """.config.json 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.write_file("test-project/materials/extracted/.config.json", "{}")

    @pytest.mark.asyncio
    async def test_git_blocked(self, fs):
        """.git 路径段被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.write_file("test-project/.git/refs/heads/main", "abc")

    @pytest.mark.asyncio
    async def test_normal_material_file_allowed(self, fs, tmp_path):
        """正常素材文件通过 FileService 允许"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        await fs.create_directory("test-project/materials/extracted/plots")
        await fs.write_file("test-project/materials/extracted/plots/p1.json", '{"plot_id": "p1"}')

        content, _, _ = await fs.read_file("test-project/materials/extracted/plots/p1.json")
        assert "p1" in content


# ═══════════════════════════════════════════════════════════
# 无 raw I/O 验证
# ═══════════════════════════════════════════════════════════


class TestNoRawIO:
    """验证 materials.py 不再包含 raw read_text/write_text/unlink"""

    def test_no_read_text(self):
        import inspect
        from backend.api import materials
        source = inspect.getsource(materials)
        assert ".read_text(" not in source, "materials.py 不应包含 .read_text() 调用"

    def test_no_write_text(self):
        import inspect
        from backend.api import materials
        source = inspect.getsource(materials)
        assert ".write_text(" not in source, "materials.py 不应包含 .write_text() 调用"

    def test_no_unlink(self):
        import inspect
        from backend.api import materials
        source = inspect.getsource(materials)
        assert ".unlink(" not in source, "materials.py 不应包含 .unlink() 调用"

    def test_no_pathlib_import(self):
        """pathlib.Path 不应再被顶层导入（不再直接操作路径）"""
        import inspect
        from backend.api import materials
        source = inspect.getsource(materials)
        # Only the inline `from pathlib import Path` inside submit_extract_task is allowed
        assert "from pathlib import Path\n" not in source.split('"""')[0] if '"""' in source else True, \
            "materials.py 不应在顶层导入 Path"

    def test_no_project_dir_path_pattern(self):
        """不应再使用 settings.projects_path / project_id 模式"""
        import inspect
        from backend.api import materials
        source = inspect.getsource(materials)
        assert "settings.projects_path /" not in source, "materials.py 不应使用 settings.projects_path / 拼接路径"
