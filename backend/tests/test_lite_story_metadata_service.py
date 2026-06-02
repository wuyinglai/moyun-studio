"""墨韵 - Lite Story Metadata Service 测试

验证 Lite 故事元数据服务的行为。
"""

import json
import pytest

from backend.application.lite_story_metadata_service import LiteStoryMetadataService
from backend.core.file_ops import FileService
from backend.schemas.lite import LiteNextOptionCard


class TestLiteStoryMetadataService:
    """测试 LiteStoryMetadataService"""

    @pytest.fixture
    def file_service(self, tmp_path):
        """创建临时文件服务"""
        return FileService(tmp_path, max_file_write_size=1024 * 1024)

    @pytest.fixture
    def metadata_service(self, file_service):
        """创建元数据服务"""
        return LiteStoryMetadataService(file_service)

    @pytest.fixture
    def project_id(self):
        """项目 ID"""
        return "test-project"

    class TestReadOptional:
        """测试 read_optional 方法"""

        @pytest.mark.anyio
        async def test_read_optional_missing_file_returns_empty(self, metadata_service, project_id):
            """文件不存在时返回空字符串"""
            result = await metadata_service.read_optional(project_id, "nonexistent.txt")
            assert result == ""

        @pytest.mark.anyio
        async def test_read_optional_existing_file_returns_text(self, metadata_service, project_id, file_service):
            """文件存在时读取文本"""
            await file_service.write_file(f"{project_id}/test.txt", "Hello, World!")
            result = await metadata_service.read_optional(project_id, "test.txt")
            assert result == "Hello, World!"

    class TestReadChapterContext:
        """测试 read_chapter_context 方法"""

        @pytest.mark.anyio
        async def test_read_chapter_context_reads_previous_sections(self, metadata_service, project_id, file_service):
            """读取前序场景内容"""
            await file_service.write_file(f"{project_id}/chapters/vol-01/ch-001/sec-001.md", "# 第1卷 第1章 场景1\n\n这是第一个场景的正文内容，超过二十个字符")
            await file_service.write_file(f"{project_id}/chapters/vol-01/ch-001/sec-002.md", "# 第1卷 第1章 场景2\n\n这是第二个场景的正文内容，同样超过二十个字符")
            await file_service.write_file(f"{project_id}/chapters/vol-01/ch-001/sec-003.md", "# 第1卷 第1章 场景3\n\n")

            result = await metadata_service.read_chapter_context(project_id, 1, 1, 3)
            assert "--- 第1场景 ---" in result
            assert "第一个场景" in result
            assert "--- 第2场景 ---" in result
            assert "第二个场景" in result
            assert "--- 第3场景 ---" not in result

        @pytest.mark.anyio
        async def test_read_chapter_context_ignores_future_sections(self, metadata_service, project_id, file_service):
            """不包含当前场景之后的内容"""
            await file_service.write_file(f"{project_id}/chapters/vol-01/ch-001/sec-001.md", "# 第1卷 第1章 场景1\n\n这是第一个场景的正文内容，超过二十个字符")
            await file_service.write_file(f"{project_id}/chapters/vol-01/ch-001/sec-002.md", "# 第1卷 第1章 场景2\n\n这是第二个场景的正文内容，同样超过二十个字符")

            result = await metadata_service.read_chapter_context(project_id, 1, 1, 2)
            assert "第一个场景" in result
            assert "第二个场景" not in result

        @pytest.mark.anyio
        async def test_read_chapter_context_empty_when_no_content(self, metadata_service, project_id):
            """没有内容时返回空"""
            result = await metadata_service.read_chapter_context(project_id, 1, 1, 5)
            assert result == ""

    class TestReadChMeta:
        """测试 read_ch_meta 方法"""

        @pytest.mark.anyio
        async def test_read_ch_meta_missing_returns_empty(self, metadata_service, project_id):
            """ch-meta.json 不存在时返回空字典"""
            result = await metadata_service.read_ch_meta(project_id, 1, 1)
            assert result == {}

        @pytest.mark.anyio
        async def test_read_ch_meta_existing_returns_data(self, metadata_service, project_id, file_service):
            """读取存在的 ch-meta.json"""
            meta_data = {
                "chapter_number": 1,
                "title": "第一章",
                "memory": ["记忆1", "记忆2"],
                "pending_foreshadowing": ["伏笔1"]
            }
            await file_service.write_file(
                f"{project_id}/chapters/vol-01/ch-001/ch-meta.json",
                json.dumps(meta_data, ensure_ascii=False)
            )
            result = await metadata_service.read_ch_meta(project_id, 1, 1)
            assert result["chapter_number"] == 1
            assert result["title"] == "第一章"
            assert result["memory"] == ["记忆1", "记忆2"]

        @pytest.mark.anyio
        async def test_read_ch_meta_invalid_json_returns_empty(self, metadata_service, project_id, file_service):
            """无效 JSON 返回空字典"""
            await file_service.write_file(f"{project_id}/chapters/vol-01/ch-001/ch-meta.json", "not valid json")
            result = await metadata_service.read_ch_meta(project_id, 1, 1)
            assert result == {}

    class TestUpdateChMeta:
        """测试 update_ch_meta 方法"""

        @pytest.mark.anyio
        async def test_update_ch_meta_merges_patch(self, metadata_service, project_id, file_service):
            """写入 patch 后字段合并正确"""
            await metadata_service.update_ch_meta(project_id, 1, 1, 1, "场景1标题", "兑现内容", "钩子内容")

            result = await metadata_service.read_ch_meta(project_id, 1, 1)
            assert result["memory"] == ["第1场景「场景1标题」：兑现内容"]
            assert result["pending_foreshadowing"] == ["钩子内容"]

        @pytest.mark.anyio
        async def test_update_ch_meta_accumulates_memory(self, metadata_service, project_id, file_service):
            """记忆按场景累积"""
            await metadata_service.update_ch_meta(project_id, 1, 1, 1, "场景1", "兑现1", "钩子1")
            await metadata_service.update_ch_meta(project_id, 1, 1, 2, "场景2", "兑现2", "钩子2")

            result = await metadata_service.read_ch_meta(project_id, 1, 1)
            assert len(result["memory"]) == 2
            assert "第1场景「场景1」：兑现1" in result["memory"]
            assert "第2场景「场景2」：兑现2" in result["memory"]

        @pytest.mark.anyio
        async def test_update_ch_meta_limits_memory(self, metadata_service, project_id, file_service):
            """记忆超过20条时保留最新的"""
            for i in range(25):
                await metadata_service.update_ch_meta(project_id, 1, 1, i + 1, f"场景{i + 1}", f"兑现{i + 1}", None)

            result = await metadata_service.read_ch_meta(project_id, 1, 1)
            assert len(result["memory"]) == 20
            assert "第1场景" not in result["memory"][0]
            assert "第6场景" in result["memory"][0]

        @pytest.mark.anyio
        async def test_update_ch_meta_limits_foreshadowing(self, metadata_service, project_id, file_service):
            """伏笔超过10条时保留最新的"""
            for i in range(15):
                await metadata_service.update_ch_meta(project_id, 1, 1, i + 1, f"场景{i + 1}", f"兑现{i + 1}", f"钩子{i + 1}")

            result = await metadata_service.read_ch_meta(project_id, 1, 1)
            assert len(result["pending_foreshadowing"]) == 10

    class TestSummarizeStoryEngine:
        """测试 summarize_story_engine 方法"""

        def test_summarize_story_engine_limits_length(self, metadata_service):
            """摘要行为保持原有长度限制"""
            story_engine = """# 故事引擎

## 人物欲望
- 当前目标：测试目标
- 长期目标：长期测试

## 冲突推进
- 明面冲突：测试冲突

## 前文记忆
- 测试记忆

## 爽点账本
- 测试爽点

## 读者期待
- 测试期待

## 阶段性目标
- 测试阶段目标
"""
            result = metadata_service.summarize_story_engine(story_engine)
            assert result["protagonist_goal"] == "当前目标：测试目标"
            assert result["current_conflict"] == "明面冲突：测试冲突"
            assert result["foreshadowing"] == "测试记忆"
            assert result["payoff_ledger"] == "测试爽点"
            assert result["reader_expectation"] == "测试期待"
            assert result["stage_goal"] == "测试阶段目标"

        def test_summarize_story_engine_missing_section(self, metadata_service):
            """缺失的章节返回默认值"""
            result = metadata_service.summarize_story_engine("")
            assert result["protagonist_goal"] == "待更新"
            assert result["current_conflict"] == "待更新"

    class TestBuildStoryEngineUpdate:
        """测试 build_story_engine_update 方法"""

        def test_build_story_engine_update_contains_key_fields(self, metadata_service):
            """构建的更新文本包含关键字段"""
            selected_card = LiteNextOptionCard(
                id="test-card",
                title="测试标题",
                beat="测试拍",
                scene="测试场景",
                protagonist_desire="主角想要",
                obstacle="阻力",
                payoff="兑现",
                hook="钩子",
                advancement="推进"
            )
            content = "# 测试标题\n\n正文内容在这里"
            result = metadata_service.build_story_engine_update("", "chapters/vol-01/ch-001/sec-001.md", selected_card, content)

            assert "## 最近推进" in result
            assert "- 章节：chapters/vol-01/ch-001/sec-001.md" in result
            assert "- 选择：测试标题" in result
            assert "- 主角想要：主角想要" in result
            assert "- 阻力：阻力" in result
            assert "- 兑现：兑现" in result
            assert "- 钩子：钩子" in result
            assert "- 正文记忆：正文内容在这里" in result

    class TestIsBlankChapter:
        """测试 is_blank_chapter 方法"""

        def test_is_blank_chapter_true_for_empty_sections(self, metadata_service):
            """空章节返回 true"""
            content = "# 标题\n\n"
            assert metadata_service.is_blank_chapter(content) is True

            content = "# 标题\n\n\n"
            assert metadata_service.is_blank_chapter(content) is True

        def test_is_blank_chapter_false_when_any_section_has_content(self, metadata_service):
            """有足够内容时返回 false"""
            content = "# 标题\n\n这是一段足够长的正文内容，超过二十个字符肯定没问题"
            assert metadata_service.is_blank_chapter(content) is False

            content = "# 标题\n\n这段正文内容长度超过二十个字符所以不会被判定为空白"
            assert metadata_service.is_blank_chapter(content) is False

        def test_is_blank_chapter_true_when_short_content(self, metadata_service):
            """短内容仍被视为空白"""
            content = "# 标题\n\n短"
            assert metadata_service.is_blank_chapter(content) is True