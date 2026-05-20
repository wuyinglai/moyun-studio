"""Prompt模板引擎单元测试

测试要点：
1. 模板加载（正常路径 + 模板不存在）
2. 变量渲染
3. 片段引用 @{path} 解析
4. 嵌套 dict/list 中的引用解析
5. file_service 为 None 时的降级行为
6. estimate_tokens（tiktoken + fallback 中文估算）
7. resolve_reference_sync
8. get_template_path
"""

from pathlib import Path

import pytest

from backend.core.prompt_engine import PromptEngine


class TestPromptEngineInit:
    """初始化测试"""

    def test_default_prompts_path(self):
        engine = PromptEngine(file_service=None)
        assert engine.prompts_path == Path("workspace/prompts")

    def test_custom_prompts_path(self):
        engine = PromptEngine(prompts_path="/custom/prompts", file_service=None)
        assert engine.prompts_path == Path("/custom/prompts")

    def test_set_file_service(self, mock_file_service):
        engine = PromptEngine(file_service=None)
        engine.set_file_service(mock_file_service)
        assert engine.file_service is mock_file_service


class TestPromptEngineLoadTemplate:
    """模板加载测试"""

    def test_load_template_success(self, prompt_engine):
        template = prompt_engine.load_template("generate", "chapter")
        assert template is not None

    def test_load_template_not_found(self, prompt_engine):
        with pytest.raises(Exception):  # jinja2 会抛 TemplateNotFound
            prompt_engine.load_template("nonexistent", "template")


class TestPromptEngineRender:
    """模板渲染测试"""

    @pytest.mark.asyncio
    async def test_render_with_variables(self, prompt_engine):
        result = await prompt_engine.render(
            "generate/chapter",
            {"genre": "玄幻", "theme": "成长", "tone": "热血"},
        )
        assert "玄幻" in result
        assert "成长" in result
        assert "热血" in result
        assert "小说作家" in result

    @pytest.mark.asyncio
    async def test_render_with_optional_variable(self, prompt_engine):
        result = await prompt_engine.render(
            "generate/chapter",
            {"genre": "玄幻", "theme": "成长", "tone": "热血", "chapter_title": "大结局"},
        )
        assert "大结局" in result

    @pytest.mark.asyncio
    async def test_render_without_optional_variable(self, prompt_engine):
        result = await prompt_engine.render(
            "generate/chapter",
            {"genre": "玄幻", "theme": "成长", "tone": "热血"},
        )
        # 章节标题条件块不应出现
        assert "章节标题：" not in result

    @pytest.mark.asyncio
    async def test_render_single_part_type(self, prompt_engine):
        """prompt_type 没有 / 时，默认 category=generate"""
        # 注意：这会尝试加载 generate/chapter/main.md，和 generate/chapter 一样
        result = await prompt_engine.render(
            "chapter",
            {"genre": "玄幻", "theme": "成长", "tone": "热血"},
        )
        assert "玄幻" in result

    @pytest.mark.asyncio
    async def test_render_unknown_template(self, prompt_engine):
        with pytest.raises(Exception):
            await prompt_engine.render("generate/nonexistent", {})


class TestPromptEngineReferenceResolution:
    """片段引用 @{path} 解析测试"""

    @pytest.mark.asyncio
    async def test_resolve_reference_in_string(self, prompt_engine, fs):
        # 创建一个引用文件
        prompt_engine.set_file_service(fs)
        result = await prompt_engine.render(
            "generate/chapter",
            {"genre": "玄幻", "theme": "@{projects/test-project/chapters/chapter-01.md}", "tone": "热血"},
        )
        # theme 应该被替换为 chapter-01.md 的内容
        assert "# 第一章 开端" in result or "第一章" in result
        assert "故事从这里开始" in result

    @pytest.mark.asyncio
    async def test_resolve_reference_in_dict(self, prompt_engine, fs):
        prompt_engine.set_file_service(fs)
        variables = {
            "genre": "玄幻",
            "nested": {
                "content": "@{projects/test-project/chapters/chapter-01.md}",
            },
            "tone": "热血",
        }
        # 直接测试 _resolve_references
        resolved = await prompt_engine._resolve_references(variables)
        assert "# 第一章" in resolved["nested"]["content"]

    @pytest.mark.asyncio
    async def test_resolve_reference_in_list(self, prompt_engine, fs):
        prompt_engine.set_file_service(fs)
        variables = {
            "genre": "玄幻",
            "sources": [
                "@{projects/test-project/chapters/chapter-01.md}",
                "普通文本",
            ],
            "tone": "热血",
        }
        resolved = await prompt_engine._resolve_references(variables)
        assert "# 第一章" in resolved["sources"][0]
        assert resolved["sources"][1] == "普通文本"

    @pytest.mark.asyncio
    async def test_resolve_reference_file_not_found(self, prompt_engine, fs):
        prompt_engine.set_file_service(fs)
        result = await prompt_engine.render(
            "generate/chapter",
            {"genre": "玄幻", "theme": "@{nonexistent/file.md}", "tone": "热血"},
        )
        # 文件不存在时，保持原始引用值
        assert "@{nonexistent/file.md}" in result


class TestPromptEngineNoFileService:
    """file_service 为 None 时的降级行为"""

    @pytest.mark.asyncio
    async def test_no_file_service_passthrough(self, prompt_engine_no_fs):
        result = await prompt_engine_no_fs.render(
            "generate/chapter",
            {"genre": "玄幻", "theme": "@{some/file.md}", "tone": "热血"},
        )
        # 不解析引用，原样保留
        assert "@{some/file.md}" in result

    @pytest.mark.asyncio
    async def test_no_file_service_render_works(self, prompt_engine_no_fs):
        result = await prompt_engine_no_fs.render(
            "generate/chapter",
            {"genre": "玄幻", "theme": "成长", "tone": "热血"},
        )
        assert "玄幻" in result


class TestPromptEngineEstimateTokens:
    """Token 估算测试"""

    @pytest.mark.asyncio
    async def test_estimate_tokens_english(self, prompt_engine):
        tokens = await prompt_engine.estimate_tokens("Hello, this is a test string.")
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_estimate_tokens_chinese(self, prompt_engine):
        tokens = await prompt_engine.estimate_tokens("你好世界这是一个测试字符串")
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_estimate_tokens_mixed(self, prompt_engine):
        tokens = await prompt_engine.estimate_tokens("Hello 你好 World 世界")
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_estimate_tokens_empty(self, prompt_engine):
        tokens = await prompt_engine.estimate_tokens("")
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_estimate_tokens_fallback_chinese(self, prompt_engine_no_fs):
        chinese_text = "你好世界这是一段中文测试文本" * 10
        tokens = await prompt_engine_no_fs.estimate_tokens(chinese_text)
        assert tokens > 0


class TestPromptEngineSyncMethods:
    """同步方法测试"""

    def test_resolve_reference_sync(self, prompt_engine):
        result = prompt_engine.resolve_reference_sync("这是 @{file/path.md} 的引用")
        assert "[file/path.md]" in result
        assert "@{" not in result

    def test_resolve_reference_sync_no_match(self, prompt_engine):
        result = prompt_engine.resolve_reference_sync("没有引用的普通文本")
        assert result == "没有引用的普通文本"

    def test_get_template_path(self, prompt_engine):
        path = prompt_engine.get_template_path("generate", "chapter")
        assert isinstance(path, Path)
        assert path.name == "main.md"
        assert "generate" in str(path)
        assert "chapter" in str(path)
