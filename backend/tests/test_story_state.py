"""Story-state API 测试

验证 story_state.py 通过 FileService 进行文件读写，
以及路径遍历防护。
"""

import pytest

from backend.api.story_state import (
    DEFAULT_STORY_STATE,
    _make_file_service,
    _parse_story_state,
    _story_state_rel_path,
)
from backend.config import Settings
from backend.core.exceptions import ValidationError
from backend.core.file_ops import FileService


# ═══════════════════════════════════════════════════════════
# _story_state_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestStoryStateRelPath:
    """_story_state_rel_path 构建安全相对路径"""

    def test_normal_project_id(self):
        assert _story_state_rel_path("abc123") == "abc123/story-state.md"

    def test_uuid_project_id(self):
        assert _story_state_rel_path("a1b2c3d4") == "a1b2c3d4/story-state.md"


# ═══════════════════════════════════════════════════════════
# _parse_story_state 测试
# ═══════════════════════════════════════════════════════════


class TestParseStoryState:
    """_parse_story_state 简化解析"""

    def test_returns_empty_structure(self):
        result = _parse_story_state(DEFAULT_STORY_STATE)
        assert result.protagonist_status == {}
        assert result.factions == {}
        assert result.foreshadowing == []
        assert result.main_plot_progress == 0
        assert result.side_plots == []
        assert result.key_items == []
        assert result.last_modified is None

    def test_empty_string(self):
        result = _parse_story_state("")
        assert result.protagonist_status == {}


# ═══════════════════════════════════════════════════════════
# FileService 路径遍历防护测试
# ═══════════════════════════════════════════════════════════


class TestStoryStatePathTraversal:
    """验证 FileService 拒绝恶意 project_id 路径遍历"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_traversal_project_id_rejected(self, fs):
        """../project_id 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/passwd/story-state.md")

    @pytest.mark.asyncio
    async def test_absolute_path_rejected(self, fs):
        """绝对路径被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("/etc/passwd/story-state.md")

    @pytest.mark.asyncio
    async def test_windows_traversal_rejected(self, fs):
        """Windows 风格遍历被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("..\\etc\\passwd/story-state.md")

    @pytest.mark.asyncio
    async def test_forbidden_segment_rejected(self, fs):
        """.git 路径段被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.read_file(".git/config")

    @pytest.mark.asyncio
    async def test_normal_read_write(self, fs, tmp_path):
        """正常 project_id 的读写通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "story-state.md").write_text("# test content", encoding="utf-8")

        content, _, _ = await fs.read_file("test-project/story-state.md")
        assert "test content" in content

    @pytest.mark.asyncio
    async def test_normal_write(self, fs, tmp_path):
        """正常写入通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        await fs.write_file("test-project/story-state.md", DEFAULT_STORY_STATE)
        content, _, _ = await fs.read_file("test-project/story-state.md")
        assert "故事全局状态" in content


# ═══════════════════════════════════════════════════════════
# 无 raw I/O 验证
# ═══════════════════════════════════════════════════════════


class TestNoRawIO:
    """验证 story_state.py 不再包含 raw read_text/write_text"""

    def test_no_read_text(self):
        import inspect
        from backend.api import story_state
        source = inspect.getsource(story_state)
        # 不应包含 Path().read_text 或 file_path.read_text
        assert ".read_text(" not in source, "story_state.py 不应包含 .read_text() 调用"

    def test_no_write_text(self):
        import inspect
        from backend.api import story_state
        source = inspect.getsource(story_state)
        assert ".write_text(" not in source, "story_state.py 不应包含 .write_text() 调用"

    def test_no_path_import(self):
        """Path 不应再被导入（不再直接操作路径）"""
        import inspect
        from backend.api import story_state
        source = inspect.getsource(story_state)
        # 'from pathlib import Path' 不应出现
        assert "from pathlib import Path" not in source, "story_state.py 不应导入 Path"
