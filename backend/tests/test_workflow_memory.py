"""Workflow memory update 测试

验证 workflows.py 通过 FileService 进行 story-state.md 和
recent-context.md 的读写，以及路径遍历防护。
"""

import pytest

from backend.api.workflows import (
    _make_file_service,
    _recent_context_rel_path,
    _story_state_rel_path,
)
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
# _recent_context_rel_path 测试
# ═══════════════════════════════════════════════════════════


class TestRecentContextRelPath:
    """_recent_context_rel_path 构建安全相对路径"""

    def test_normal_project_id(self):
        assert _recent_context_rel_path("abc123") == "abc123/recent-context.md"

    def test_uuid_project_id(self):
        assert _recent_context_rel_path("a1b2c3d4") == "a1b2c3d4/recent-context.md"


# ═══════════════════════════════════════════════════════════
# FileService 正常读写测试
# ═══════════════════════════════════════════════════════════


class TestWorkflowMemoryFileService:
    """验证 FileService 正常读写 story-state.md 和 recent-context.md"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_story_state_read(self, fs, tmp_path):
        """正常读取 story-state.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "story-state.md").write_text("# 故事状态\n\n测试内容", encoding="utf-8")

        content, _, mtime = await fs.read_file("test-project/story-state.md")
        assert "测试内容" in content
        assert mtime is not None

    @pytest.mark.asyncio
    async def test_story_state_write(self, fs, tmp_path):
        """正常写入 story-state.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        await fs.write_file("test-project/story-state.md", "# 故事状态\n\n更新内容")
        content, _, _ = await fs.read_file("test-project/story-state.md")
        assert "更新内容" in content

    @pytest.mark.asyncio
    async def test_recent_context_read(self, fs, tmp_path):
        """正常读取 recent-context.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "recent-context.md").write_text("# 近期上下文\n\n摘要", encoding="utf-8")

        content, _, mtime = await fs.read_file("test-project/recent-context.md")
        assert "摘要" in content

    @pytest.mark.asyncio
    async def test_recent_context_write(self, fs, tmp_path):
        """正常写入 recent-context.md 通过 FileService"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        await fs.write_file("test-project/recent-context.md", "# 近期上下文\n\n新摘要")
        content, _, _ = await fs.read_file("test-project/recent-context.md")
        assert "新摘要" in content

    @pytest.mark.asyncio
    async def test_story_state_append_via_read_write(self, fs, tmp_path):
        """模拟记忆更新：读取后追加内容再写入"""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "story-state.md").write_text("# 故事状态\n\n原始内容", encoding="utf-8")

        content, _, _ = await fs.read_file("test-project/story-state.md")
        updated = content + "\n\n## 更新\n追加内容"
        await fs.write_file("test-project/story-state.md", updated)

        result, _, _ = await fs.read_file("test-project/story-state.md")
        assert "原始内容" in result
        assert "追加内容" in result


# ═══════════════════════════════════════════════════════════
# FileService 路径遍历防护测试
# ═══════════════════════════════════════════════════════════


class TestWorkflowMemoryPathTraversal:
    """验证 FileService 拒绝恶意 project_id 路径遍历"""

    @pytest.fixture
    def fs(self, tmp_path):
        return FileService(tmp_path)

    @pytest.mark.asyncio
    async def test_traversal_story_state_rejected(self, fs):
        """../project_id story-state.md 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/story-state.md")

    @pytest.mark.asyncio
    async def test_traversal_recent_context_rejected(self, fs):
        """../project_id recent-context.md 被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("../etc/recent-context.md")

    @pytest.mark.asyncio
    async def test_absolute_path_rejected(self, fs):
        """绝对路径被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("/etc/story-state.md")

    @pytest.mark.asyncio
    async def test_windows_traversal_rejected(self, fs):
        """Windows 风格遍历被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.read_file("..\\etc\\recent-context.md")

    @pytest.mark.asyncio
    async def test_traversal_write_rejected(self, fs):
        """路径遍历写入被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="非法路径"):
            await fs.write_file("../etc/story-state.md", "malicious")

    @pytest.mark.asyncio
    async def test_forbidden_segment_rejected(self, fs):
        """.git 路径段被 FileService 拒绝"""
        with pytest.raises(ValidationError, match="禁止操作"):
            await fs.read_file(".git/story-state.md")


# ═══════════════════════════════════════════════════════════
# 无 raw I/O 验证
# ═══════════════════════════════════════════════════════════


class TestNoRawIO:
    """验证 workflows.py 不再包含 raw read_text/write_text 用于记忆文件"""

    def test_no_read_text_for_memory_files(self):
        import inspect
        from backend.api import workflows
        source = inspect.getsource(workflows)
        # 不应包含 .read_text() 调用
        assert ".read_text(" not in source, "workflows.py 不应包含 .read_text() 调用"

    def test_no_write_text_for_memory_files(self):
        import inspect
        from backend.api import workflows
        source = inspect.getsource(workflows)
        # 不应包含 .write_text() 调用
        assert ".write_text(" not in source, "workflows.py 不应包含 .write_text() 调用"

    def test_no_project_dir_path_for_memory(self):
        """不应再使用 project_dir / 'story-state.md' 模式"""
        import inspect
        from backend.api import workflows
        source = inspect.getsource(workflows)
        assert 'project_dir / "story-state.md"' not in source, "workflows.py 不应使用 project_dir / 'story-state.md'"
        assert 'project_dir / "recent-context.md"' not in source, "workflows.py 不应使用 project_dir / 'recent-context.md'"
