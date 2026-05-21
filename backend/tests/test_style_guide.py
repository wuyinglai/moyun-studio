"""Style-guide API 测试

验证 style_guide.py 通过 FileService 进行文件读写，
以及路径遍历防护。
"""

import json

import pytest

from backend.api.style_guide import (
    DEFAULT_STYLE_GUIDE,
    _make_file_service,
    _meta_rel_path,
    _style_guide_rel_path,
)
from backend.core.exceptions import ValidationError
from backend.core.file_ops import FileService


# ═══════════════════════════════════════════════════════════
# _style_guide_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestStyleGuideRelPath:
    """_style_guide_rel_path 构建安全相对路径"""

    def test_normal_project_id(self):
        assert _style_guide_rel_path("abc123") == "abc123/style-guide.md"

    def test_uuid_project_id(self):
        assert _style_guide_rel_path("a1b2c3d4") == "a1b2c3d4/style-guide.md"


# ═══════════════════════════════════════════════════════════
# _meta_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestMetaRelPath:
    """_meta_rel_path 构建安全相对路径"""

    def test_normal_project_id(self):
        assert _meta_rel_path("abc123") == "abc123/meta.json"

    def test_uuid_project_id(self):
        assert _meta_rel_path("a1b2c3d4") == "a1b2c3d4/meta.json"


# ═══════════════════════════════════════════════════════════
# FileService 正常读写测试
# ═══════════════════════════════════════════════════════════


class TestStyleGuideFileService:
    """验证 FileService 正常读写 style-guide.md"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_normal_read(self, fs, tmp_path):
        """正常读取 style-guide.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "style-guide.md").write_text("# 文风指南\n\n测试内容", encoding="utf-8")

        content, _, mtime = await fs.read_file("test-project/style-guide.md")
        assert "测试内容" in content
        assert mtime is not None

    @pytest.mark.asyncio
    async def test_normal_write(self, fs, tmp_path):
        """正常写入 style-guide.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        await fs.write_file("test-project/style-guide.md", DEFAULT_STYLE_GUIDE)
        content, _, _ = await fs.read_file("test-project/style-guide.md")
        assert "文风指南" in content

    @pytest.mark.asyncio
    async def test_meta_json_read(self, fs, tmp_path):
        """正常读取 meta.json 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        meta_data = {"genre": "玄幻", "theme": "修仙"}
        (project_dir / "meta.json").write_text(json.dumps(meta_data), encoding="utf-8")

        content, _, _ = await fs.read_file("test-project/meta.json")
        parsed = json.loads(content)
        assert parsed["genre"] == "玄幻"

    @pytest.mark.asyncio
    async def test_meta_json_write(self, fs, tmp_path):
        """正常写入 meta.json 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        meta_data = {"genre": "科幻", "tone": "冷峻"}
        await fs.write_file("test-project/meta.json", json.dumps(meta_data))
        content, _, _ = await fs.read_file("test-project/meta.json")
        parsed = json.loads(content)
        assert parsed["genre"] == "科幻"


# ═══════════════════════════════════════════════════════════
# FileService 路径遍历防护测试
# ═══════════════════════════════════════════════════════════


class TestStyleGuidePathTraversal:
    """验证 FileService 拒绝恶意 project_id 路径遍历"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_traversal_project_id_rejected(self, fs):
        """../project_id 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/passwd/style-guide.md")

    @pytest.mark.asyncio
    async def test_absolute_path_rejected(self, fs):
        """绝对路径被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("/etc/passwd/style-guide.md")

    @pytest.mark.asyncio
    async def test_windows_traversal_rejected(self, fs):
        """Windows 风格遍历被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("..\\etc\\passwd/style-guide.md")

    @pytest.mark.asyncio
    async def test_forbidden_segment_rejected(self, fs):
        """.git 路径段被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.read_file(".git/config")

    @pytest.mark.asyncio
    async def test_traversal_write_rejected(self, fs):
        """路径遍历写入被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.write_file("../etc/evil.md", "malicious content")

    @pytest.mark.asyncio
    async def test_meta_traversal_rejected(self, fs):
        """meta.json 路径遍历被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/meta.json")


# ═══════════════════════════════════════════════════════════
# 无 raw I/O 验证
# ═══════════════════════════════════════════════════════════


class TestNoRawIO:
    """验证 style_guide.py 不再包含 raw read_text/write_text"""

    def test_no_read_text(self):
        import inspect
        from backend.api import style_guide
        source = inspect.getsource(style_guide)
        assert ".read_text(" not in source, "style_guide.py 不应包含 .read_text() 调用"

    def test_no_write_text(self):
        import inspect
        from backend.api import style_guide
        source = inspect.getsource(style_guide)
        assert ".write_text(" not in source, "style_guide.py 不应包含 .write_text() 调用"

    def test_no_path_import(self):
        """Path 不应再被导入（不再直接操作路径）"""
        import inspect
        from backend.api import style_guide
        source = inspect.getsource(style_guide)
        assert "from pathlib import Path" not in source, "style_guide.py 不应导入 Path"
