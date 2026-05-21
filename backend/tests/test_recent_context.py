"""Recent-context API 测试

验证 recent_context.py 通过 FileService 进行文件读写，
.chapters-meta.json 访问安全，以及路径遍历防护。
"""

import json

import pytest

from backend.api.recent_context import (
    DEFAULT_RECENT_CONTEXT,
    _chapters_meta_rel_path,
    _load_chapters_meta,
    _make_file_service,
    _recent_context_rel_path,
    _save_chapters_meta,
    _update_recent_context_file,
    ChapterSummary,
)
from backend.core.exceptions import ValidationError
from backend.core.file_ops import FileService


# ═══════════════════════════════════════════════════════════
# _recent_context_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestRecentContextRelPath:
    """_recent_context_rel_path 构建安全相对路径"""

    def test_normal_project_id(self):
        assert _recent_context_rel_path("abc123") == "abc123/recent-context.md"

    def test_uuid_project_id(self):
        assert _recent_context_rel_path("a1b2c3d4") == "a1b2c3d4/recent-context.md"


# ═══════════════════════════════════════════════════════════
# _chapters_meta_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestChaptersMetaRelPath:
    """_chapters_meta_rel_path 构建安全相对路径"""

    def test_normal_project_id(self):
        assert _chapters_meta_rel_path("abc123") == "abc123/.chapters-meta.json"

    def test_uuid_project_id(self):
        assert _chapters_meta_rel_path("a1b2c3d4") == "a1b2c3d4/.chapters-meta.json"


# ═══════════════════════════════════════════════════════════
# FileService 正常读写测试
# ═══════════════════════════════════════════════════════════


class TestRecentContextFileService:
    """验证 FileService 正常读写 recent-context.md 和 .chapters-meta.json"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_normal_read_recent_context(self, fs, tmp_path):
        """正常读取 recent-context.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "recent-context.md").write_text("# 近期上下文\n\n测试内容", encoding="utf-8")

        content, _, mtime = await fs.read_file("test-project/recent-context.md")
        assert "测试内容" in content
        assert mtime is not None

    @pytest.mark.asyncio
    async def test_normal_write_recent_context(self, fs, tmp_path):
        """正常写入 recent-context.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        await fs.write_file("test-project/recent-context.md", DEFAULT_RECENT_CONTEXT)
        content, _, _ = await fs.read_file("test-project/recent-context.md")
        assert "近期上下文" in content

    @pytest.mark.asyncio
    async def test_chapters_meta_read(self, fs, tmp_path):
        """正常读取 .chapters-meta.json 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        meta_data = {"chapters": [{"path": "ch-001", "title": "第一章"}], "total_words": 1000}
        (project_dir / ".chapters-meta.json").write_text(json.dumps(meta_data), encoding="utf-8")

        content, _, _ = await fs.read_file("test-project/.chapters-meta.json")
        parsed = json.loads(content)
        assert parsed["total_words"] == 1000

    @pytest.mark.asyncio
    async def test_chapters_meta_write(self, fs, tmp_path):
        """正常写入 .chapters-meta.json 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        meta_data = {"chapters": [], "total_words": 0}
        await fs.write_file("test-project/.chapters-meta.json", json.dumps(meta_data))
        content, _, _ = await fs.read_file("test-project/.chapters-meta.json")
        parsed = json.loads(content)
        assert parsed["chapters"] == []


# ═══════════════════════════════════════════════════════════
# _load_chapters_meta / _save_chapters_meta 测试
# ═══════════════════════════════════════════════════════════


class TestChaptersMetaHelpers:
    """验证 _load_chapters_meta 和 _save_chapters_meta 通过 FileService"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_load_returns_default_when_missing(self, fs, tmp_path):
        """文件不存在时返回默认结构"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        result = await _load_chapters_meta(fs, "test-project")
        assert result == {"chapters": [], "total_words": 0}

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self, fs, tmp_path):
        """保存后再读取应一致"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        data = {"chapters": [{"path": "ch-001", "title": "第一章", "summary": "摘要", "word_count": 500, "created_at": "2025-01-01T00:00:00"}], "total_words": 500}
        await _save_chapters_meta(fs, "test-project", data)

        result = await _load_chapters_meta(fs, "test-project")
        assert result["total_words"] == 500
        assert len(result["chapters"]) == 1


# ═══════════════════════════════════════════════════════════
# _update_recent_context_file 测试
# ═══════════════════════════════════════════════════════════


class TestUpdateRecentContextFile:
    """验证 _update_recent_context_file 通过 FileService"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_write_default_when_no_chapters(self, fs, tmp_path):
        """空章节列表写入默认模板"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        await _update_recent_context_file(fs, "test-project", [])
        content, _, _ = await fs.read_file("test-project/recent-context.md")
        assert "近期上下文摘要" in content

    @pytest.mark.asyncio
    async def test_write_with_chapters(self, fs, tmp_path):
        """有章节时写入摘要内容"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        chapters = [
            ChapterSummary(path="ch-001", title="第一章", summary="测试摘要", word_count=800, created_at="2025-01-01T00:00:00")
        ]
        await _update_recent_context_file(fs, "test-project", chapters)
        content, _, _ = await fs.read_file("test-project/recent-context.md")
        assert "第一章" in content
        assert "800" in content


# ═══════════════════════════════════════════════════════════
# FileService 路径遍历防护测试
# ═══════════════════════════════════════════════════════════


class TestRecentContextPathTraversal:
    """验证 FileService 拒绝恶意 project_id 路径遍历"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_traversal_project_id_rejected(self, fs):
        """../project_id 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/passwd/recent-context.md")

    @pytest.mark.asyncio
    async def test_absolute_path_rejected(self, fs):
        """绝对路径被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("/etc/passwd/recent-context.md")

    @pytest.mark.asyncio
    async def test_windows_traversal_rejected(self, fs):
        """Windows 风格遍历被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("..\\etc\\passwd/recent-context.md")

    @pytest.mark.asyncio
    async def test_traversal_write_rejected(self, fs):
        """路径遍历写入被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.write_file("../etc/evil.md", "malicious content")

    @pytest.mark.asyncio
    async def test_meta_traversal_rejected(self, fs):
        """.chapters-meta.json 路径遍历被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/.chapters-meta.json")


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
            await fs.read_file("test-project/.env")

    @pytest.mark.asyncio
    async def test_config_json_blocked(self, fs):
        """.config.json 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.read_file("test-project/.config.json")

    @pytest.mark.asyncio
    async def test_git_blocked(self, fs):
        """.git 路径段被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.read_file("test-project/.git/config")

    @pytest.mark.asyncio
    async def test_chapters_meta_allowed(self, fs, tmp_path):
        """.chapters-meta.json 通过 FileService 允许"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / ".chapters-meta.json").write_text('{"chapters":[]}', encoding="utf-8")

        content, _, _ = await fs.read_file("test-project/.chapters-meta.json")
        assert "chapters" in content

    @pytest.mark.asyncio
    async def test_env_write_blocked(self, fs):
        """.env 写入被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.write_file("test-project/.env", "SECRET=123")


# ═══════════════════════════════════════════════════════════
# 无 raw I/O 验证
# ═══════════════════════════════════════════════════════════


class TestNoRawIO:
    """验证 recent_context.py 不再包含 raw read_text/write_text"""

    def test_no_read_text(self):
        import inspect
        from backend.api import recent_context
        source = inspect.getsource(recent_context)
        assert ".read_text(" not in source, "recent_context.py 不应包含 .read_text() 调用"

    def test_no_write_text(self):
        import inspect
        from backend.api import recent_context
        source = inspect.getsource(recent_context)
        assert ".write_text(" not in source, "recent_context.py 不应包含 .write_text() 调用"

    def test_no_path_import(self):
        """Path 不应再被导入（不再直接操作路径）"""
        import inspect
        from backend.api import recent_context
        source = inspect.getsource(recent_context)
        assert "from pathlib import Path" not in source, "recent_context.py 不应导入 Path"
