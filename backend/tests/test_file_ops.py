"""文件操作服务单元测试

测试要点：
1. read_file（普通文件、带 frontmatter 的 .md 文件）
2. write_file（普通、带 frontmatter）
3. list_directory
4. get_file_tree
5. delete_file、delete_directory
6. 文件不存在时的异常处理
7. exists、create_directory
8. get_project_info
"""

import pytest

from backend.core.file_ops import FileService
from backend.core.exceptions import FileNotFoundError as MoyunFileNotFoundError


class TestFileServiceInit:
    """初始化测试"""

    def test_workspace_path(self, temp_workspace):
        fs = FileService(temp_workspace)
        assert fs.workspace == temp_workspace


class TestFileServiceRead:
    """读取文件测试"""

    @pytest.mark.asyncio
    async def test_read_plain_file(self, fs, temp_workspace):
        # 写一个纯文本文件
        file_path = temp_workspace / "test.txt"
        file_path.write_text("Hello World", encoding="utf-8")
        content, fm = await fs.read_file("test.txt")
        assert content == "Hello World"
        assert fm is None

    @pytest.mark.asyncio
    async def test_read_markdown_with_frontmatter(self, fs):
        content, fm = await fs.read_file("projects/test-project/chapters/chapter-01.md")
        assert "第一章 开端" in content
        assert fm is not None
        assert fm["title"] == "第一章 - 开端"
        assert fm["word_count"] == 1200

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, fs):
        with pytest.raises(MoyunFileNotFoundError):
            await fs.read_file("nonexistent/file.md")

    @pytest.mark.asyncio
    async def test_read_project_file(self, fs):
        content, fm = await fs.read_file("projects/test-project/outline.md")
        assert "测试项目 - 大纲" in content
        assert fm is None or (isinstance(fm, dict) and len(fm) < 5)  # .md 无 frontmatter


class TestFileServiceWrite:
    """写入文件测试"""

    @pytest.mark.asyncio
    async def test_write_plain_file(self, fs, temp_workspace):
        await fs.write_file("new.txt", "新文件内容")
        content, _ = await fs.read_file("new.txt")
        assert content == "新文件内容"

    @pytest.mark.asyncio
    async def test_write_markdown_with_frontmatter(self, fs, temp_workspace):
        await fs.write_file(
            "new_chapter.md",
            "# 新章节\n\n内容",
            frontmatter_dict={"title": "新章节", "word_count": 500},
        )
        content, fm = await fs.read_file("new_chapter.md")
        assert "# 新章节" in content
        assert fm["title"] == "新章节"
        assert fm["word_count"] == 500

    @pytest.mark.asyncio
    async def test_write_creates_parent_dir(self, fs, temp_workspace):
        await fs.write_file("deep/nested/file.md", "深层文件")
        content, _ = await fs.read_file("deep/nested/file.md")
        assert content == "深层文件"

    @pytest.mark.asyncio
    async def test_write_overwrites_existing(self, fs, temp_workspace):
        await fs.write_file("overwrite.md", "原始内容")
        await fs.write_file("overwrite.md", "覆盖内容")
        content, _ = await fs.read_file("overwrite.md")
        assert content == "覆盖内容"


class TestFileServiceListDirectory:
    """列出目录测试"""

    @pytest.mark.asyncio
    async def test_list_empty_dir(self, fs, temp_workspace):
        empty_dir = temp_workspace / "empty"
        empty_dir.mkdir()
        items = await fs.list_directory("empty")
        assert items == []

    @pytest.mark.asyncio
    async def test_list_nonexistent_dir(self, fs):
        items = await fs.list_directory("nonexistent")
        assert items == []

    @pytest.mark.asyncio
    async def test_list_items_sorted(self, fs):
        items = await fs.list_directory("projects/test-project")
        # 文件夹在前，文件在后
        dirs = [i for i in items if i["is_dir"]]
        files = [i for i in items if not i["is_dir"]]
        assert len(dirs) > 0
        assert len(files) > 0
        # 验证排序：第一个是目录
        assert items[0]["is_dir"]

    @pytest.mark.asyncio
    async def test_list_returns_name_and_path(self, fs):
        items = await fs.list_directory("projects/test-project")
        for item in items:
            assert "name" in item
            assert "path" in item
            assert "is_dir" in item
            assert "size" in item


class TestFileServiceTree:
    """文件树测试"""

    @pytest.mark.asyncio
    async def test_get_file_tree_root(self, fs):
        tree = await fs.get_file_tree("projects/test-project", max_depth=2)
        assert tree["name"] is not None
        assert len(tree["children"]) > 0

    @pytest.mark.asyncio
    async def test_get_file_tree_depth_limits_children(self, fs):
        # max_depth=1 时，第一层目录的子项应该为空
        tree = await fs.get_file_tree("projects/test-project", max_depth=1)
        for child in tree["children"]:
            if child["children"] is not None and child["name"] in ("chapters", "characters"):
                # 深度为1时，目录的子节点不应该被展开
                assert len(child["children"]) == 0

    @pytest.mark.asyncio
    async def test_get_file_tree_skips_dot_files(self, fs, temp_workspace):
        # 创建一个点文件
        (temp_workspace / ".hidden").write_text("hidden", encoding="utf-8")
        tree = await fs.get_file_tree("")
        names = [c["name"] for c in tree["children"]]
        assert ".hidden" not in names


class TestFileServiceDelete:
    """删除测试"""

    @pytest.mark.asyncio
    async def test_delete_file(self, fs, temp_workspace):
        await fs.write_file("to_delete.txt", "待删除")
        assert await fs.exists("to_delete.txt")
        await fs.delete_file("to_delete.txt")
        assert not await fs.exists("to_delete.txt")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_safe(self, fs):
        await fs.delete_file("nonexistent.txt")  # 不抛异常

    @pytest.mark.asyncio
    async def test_delete_directory(self, fs, temp_workspace):
        dir_path = temp_workspace / "to_delete_dir"
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("content")
        await fs.delete_directory("to_delete_dir")
        assert not await fs.exists("to_delete_dir")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_directory_safe(self, fs):
        await fs.delete_directory("nonexistent_dir")  # 不抛异常


class TestFileServiceExists:
    """存在性检查测试"""

    @pytest.mark.asyncio
    async def test_exists_true(self, fs):
        assert await fs.exists("projects/test-project/meta.json")

    @pytest.mark.asyncio
    async def test_exists_false(self, fs):
        assert not await fs.exists("nonexistent.txt")


class TestFileServiceCreateDir:
    """创建目录测试"""

    @pytest.mark.asyncio
    async def test_create_directory(self, fs, temp_workspace):
        await fs.create_directory("new_dir")
        assert (temp_workspace / "new_dir").is_dir()

    @pytest.mark.asyncio
    async def test_create_nested_directory(self, fs, temp_workspace):
        await fs.create_directory("a/b/c")
        assert (temp_workspace / "a" / "b" / "c").is_dir()


class TestFileServiceProjectInfo:
    """项目信息测试"""

    @pytest.mark.asyncio
    async def test_get_project_info(self, fs, temp_workspace):
        # FileService.get_project_info 查找 .project.json
        proj_dir = temp_workspace / "projects" / "test-project"
        (proj_dir / ".project.json").write_text(
            '{"project_id": "test-project", "name": "测试项目"}', encoding="utf-8"
        )
        info = await fs.get_project_info("projects/test-project")
        assert info is not None
        assert info["project_id"] == "test-project"

    @pytest.mark.asyncio
    async def test_get_project_info_nonexistent(self, fs):
        info = await fs.get_project_info("nonexistent")
        assert info is None


class TestFileServiceEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_read_frontmatter_no_metadata(self, fs, temp_workspace):
        """没有 frontmatter 的 .md 文件"""
        file_path = temp_workspace / "no_fm.md"
        file_path.write_text("# 无元数据\n\n内容", encoding="utf-8")
        content, fm = await fs.read_file("no_fm.md")
        assert "无元数据" in content
        assert fm is None

    @pytest.mark.asyncio
    async def test_write_without_frontmatter_on_non_md(self, fs, temp_workspace):
        """非 .md 文件不会添加 frontmatter"""
        await fs.write_file("data.json", '{"key": "value"}', frontmatter_dict={"should": "ignore"})
        content, fm = await fs.read_file("data.json")
        assert content == '{"key": "value"}'
        assert fm is None
