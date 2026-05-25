"""管线引擎单元测试

测试要点：
1. 加载管线 YAML 定义
2. 按步骤顺序执行 LLM 调用
3. 失败时自动 fallback
4. 变量解析（project_meta, chapter_vars, system_variables）
5. @{} 引用解析
6. Token 估算
"""

import json
from unittest.mock import AsyncMock, MagicMock

from jinja2 import Environment, FileSystemLoader
import pytest
import yaml

from backend.core.pipeline import REFERENCE_PATTERN, PipelineError, PipelineRunner

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_service():
    """Mock LLM Service"""
    service = MagicMock()

    # 使用 async generator function
    async def mock_complete(*args, **kwargs):
        for chunk in ["这是", "测试", "输出"]:
            yield chunk

    service.complete = mock_complete
    return service


@pytest.fixture
def mock_file_service(tmp_path):
    """Mock FileService with temp workspace"""
    service = MagicMock()

    # 设置项目目录
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # 模拟读取文件
    async def mock_read_file(path):
        path_str = str(path)
        if "meta.json" in path_str:
            return json.dumps({
                "project_id": "test-project",
                "name": "测试项目",
                "genre": "玄幻",
                "theme": "成长",
                "tone": "热血",
            }), None
        elif "style-guide.md" in path_str:
            return "# 文风指南\n测试风格", None
        elif "story-state.md" in path_str:
            return "# 故事状态\n测试状态", None
        elif "recent-context.md" in path_str:
            return "# 近期上下文\n测试上下文", None
        elif "outline.md" in path_str:
            return "# 大纲\n## 第一章", None
        elif "ch-meta.json" in path_str:
            return json.dumps({
                "pending_foreshadowing": ["伏笔1"],
                "active_quests": ["主线任务1"]
            }), None
        else:
            return "", None

    service.read_file = AsyncMock(side_effect=mock_read_file)
    service.write_file = AsyncMock()
    return service


@pytest.fixture
def pipeline_runner(mock_llm_service, mock_file_service, tmp_path):
    """PipelineRunner with mocked dependencies"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    return PipelineRunner(prompts_dir, mock_llm_service, mock_file_service)


@pytest.fixture
def sample_pipeline_files(tmp_path):
    """创建测试用的管线文件"""
    pipeline_dir = tmp_path / "prompts" / "pipeline" / "test-pipeline"
    pipeline_dir.mkdir(parents=True)

    # YAML 定义
    yaml_content = {
        "name": "test-pipeline",
        "label": "测试管线",
        "steps": [
            {
                "id": "step1",
                "label": "第一步",
                "prompt": "pipeline/test-pipeline/step1",
                "fallback": None
            },
            {
                "id": "step2",
                "label": "第二步",
                "prompt": "pipeline/test-pipeline/step2",
                "fallback": "step1"
            }
        ]
    }
    yaml_path = tmp_path / "prompts" / "pipeline" / "test-pipeline.yaml"
    yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")

    # Step prompts
    (pipeline_dir / "step1.md").write_text("第一步的prompt内容：{{ file_content }}", encoding="utf-8")
    (pipeline_dir / "step2.md").write_text("第二步的prompt内容：{{ file_content }}", encoding="utf-8")

    return tmp_path / "prompts"


# ─── PipelineRunner Init Tests ────────────────────────────────────────────────

class TestPipelineRunnerInit:
    """初始化测试"""

    def test_init_with_valid_args(self, pipeline_runner):
        assert pipeline_runner.prompts_path.exists()
        assert pipeline_runner.llm_service is not None
        assert pipeline_runner.file_service is not None

    def test_get_pipeline_dir(self, pipeline_runner):
        assert "pipeline" in str(pipeline_runner._get_pipeline_dir())


# ─── Pipeline Loading Tests ─────────────────────────────────────────────────

class TestPipelineLoading:
    """加载管线定义测试"""

    def test_load_pipeline(self, pipeline_runner, sample_pipeline_files):
        pipeline_runner.prompts_path = sample_pipeline_files

        # 重新创建 env
        from jinja2 import Environment, FileSystemLoader
        pipeline_runner.env = Environment(
            loader=FileSystemLoader(str(sample_pipeline_files)),
            autoescape=False,
        )

        pipeline = pipeline_runner.load_pipeline("test-pipeline")
        assert pipeline.name == "test-pipeline"
        assert pipeline.label == "测试管线"
        assert len(pipeline.steps) == 2

    def test_load_nonexistent_pipeline_raises_error(self, pipeline_runner):
        with pytest.raises(PipelineError) as exc_info:
            pipeline_runner.load_pipeline("nonexistent")
        assert "管线不存在" in str(exc_info.value)

    def test_load_invalid_yaml_raises_error(self, pipeline_runner, tmp_path):
        # 创建无效的 YAML 文件
        pipeline_dir = tmp_path / "prompts" / "pipeline"
        pipeline_dir.mkdir(parents=True)
        invalid_yaml = pipeline_dir / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [", encoding="utf-8")

        with pytest.raises(PipelineError) as exc_info:
            pipeline_runner.load_pipeline("invalid")
        assert "加载管线定义失败" in str(exc_info.value)

    def test_get_pipeline_detail_reads_system_prompt_path(self, mock_llm_service, mock_file_service, tmp_path):
        user_prompts = tmp_path / "workspace" / "prompts"
        system_prompts = tmp_path / "prompts"
        (user_prompts / "pipeline").mkdir(parents=True)
        (system_prompts / "pipeline").mkdir(parents=True)
        (system_prompts / "generate" / "title").mkdir(parents=True)

        (system_prompts / "pipeline" / "title.yaml").write_text(
            yaml.dump({
                "name": "title",
                "label": "生成书名与创意",
                "steps": [{
                    "id": "generate",
                    "label": "生成书名与创意",
                    "prompt": "generate/title/main",
                    "fallback": None,
                    "confirm": False,
                }],
            }, allow_unicode=True),
            encoding="utf-8",
        )
        (system_prompts / "generate" / "title" / "main.md").write_text(
            "系统书名 prompt",
            encoding="utf-8",
        )

        runner = PipelineRunner(
            user_prompts,
            mock_llm_service,
            mock_file_service,
            system_prompts_path=system_prompts,
        )

        detail = runner.get_pipeline_detail("title")

        assert detail["name"] == "title"
        assert detail["steps"][0]["prompt_content"] == "系统书名 prompt"


# ─── Reference Pattern Tests ─────────────────────────────────────────────────

class TestReferencePattern:
    """@{} 引用模式测试"""

    def test_reference_pattern_matches(self):
        text = "请参考 @{style-guide.md} 的内容"
        match = REFERENCE_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "style-guide.md"

    def test_reference_pattern_no_match(self):
        text = "没有引用的文本"
        match = REFERENCE_PATTERN.search(text)
        assert match is None

    def test_reference_pattern_multiple(self):
        text = "参考 @{file1.md} 和 @{file2.md}"
        matches = REFERENCE_PATTERN.findall(text)
        assert len(matches) == 2
        assert "file1.md" in matches
        assert "file2.md" in matches


# ─── Prompt Rendering Tests ───────────────────────────────────────────────────

class TestPromptRendering:
    """Prompt 渲染测试"""

    def test_render_prompt(self, pipeline_runner):
        # 创建临时模板
        template_path = pipeline_runner.prompts_path / "test.md"
        template_path.write_text("Hello {{ name }}!", encoding="utf-8")

        result = pipeline_runner.render_prompt("test.md", {"name": "World"})
        assert result == "Hello World!"

    def test_render_prompt_with_missing_var(self, pipeline_runner):
        template_path = pipeline_runner.prompts_path / "test.md"
        template_path.write_text("Hello {{ name }}!", encoding="utf-8")

        # Jinja2 默认会忽略缺失的变量
        result = pipeline_runner.render_prompt("test.md", {})
        assert "Hello" in result


# ─── AsyncGenerator Event Tests ──────────────────────────────────────────────

class TestPipelineRun:
    """管线执行测试"""

    @pytest.mark.asyncio
    async def test_run_pipeline_yields_events(self, pipeline_runner, mock_llm_service, sample_pipeline_files, tmp_path):
        pipeline_runner.prompts_path = sample_pipeline_files
        from jinja2 import Environment, FileSystemLoader
        pipeline_runner.env = Environment(
            loader=FileSystemLoader(str(sample_pipeline_files)),
            autoescape=False,
        )
        # 确保 mock config 属性正确
        pipeline_runner.llm_service.config.max_prompt_tokens = 120000
        pipeline_runner.llm_service.config.context_window = 128000

        events = []
        async for event in pipeline_runner.run(
            "test-pipeline",
            "test-project",
            "chapters/test.md",
            output_mode="overwrite"  # AI_GUARDRAIL_ALLOW: test param
        ):
            events.append(event)

        # 应该有 task_start, thinking, prompt, generation, step_done, done 等事件
        event_types = [e.get("event") for e in events]
        assert "task_start" in event_types
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_run_pipeline_resolves_references(self, pipeline_runner, mock_llm_service, mock_file_service, tmp_path):
        """测试 @{path} 引用解析"""
        # 创建带引用的 prompt
        pipeline_dir = tmp_path / "prompts" / "pipeline" / "ref-test"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "step1.md").write_text("参考 @{style-guide.md}", encoding="utf-8")

        yaml_content = {
            "name": "ref-test",
            "label": "引用测试",
            "steps": [{"id": "step1", "label": "测试", "prompt": "pipeline/ref-test/step1"}]
        }
        yaml_path = tmp_path / "prompts" / "pipeline" / "ref-test.yaml"
        yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")

        pipeline_runner.prompts_path = tmp_path / "prompts"
        pipeline_runner.env = Environment(
            loader=FileSystemLoader(str(tmp_path / "prompts")),
            autoescape=False,
        )
        # 使用新的 mock
        pipeline_runner.llm_service = mock_llm_service

        events = []
        async for event in pipeline_runner.run("ref-test", "test-project"):
            events.append(event)

        # 验证有事件产生
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_run_pipeline_with_fallback(self, pipeline_runner, mock_llm_service, mock_file_service, tmp_path):
        """测试 fallback 机制"""
        # 创建一个会失败的管线，fallback 到 step1
        pipeline_dir = tmp_path / "prompts" / "pipeline" / "fallback-test"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "step1.md").write_text("第一步输出", encoding="utf-8")
        (pipeline_dir / "step2.md").write_text("第二步输出", encoding="utf-8")

        yaml_content = {
            "name": "fallback-test",
            "label": "Fallback测试",
            "steps": [
                {"id": "step1", "label": "第一步", "prompt": "pipeline/fallback-test/step1"},
                {"id": "step2", "label": "第二步", "prompt": "pipeline/fallback-test/step2", "fallback": "step1"}
            ]
        }
        yaml_path = tmp_path / "prompts" / "pipeline" / "fallback-test.yaml"
        yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")

        pipeline_runner.prompts_path = tmp_path / "prompts"
        pipeline_runner.env = Environment(
            loader=FileSystemLoader(str(tmp_path / "prompts")),
            autoescape=False,
        )

        # Mock LLM 第二次调用失败
        call_count = 0
        async def mock_complete_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("LLM 调用失败")
            yield "第一步输出"

        pipeline_runner.llm_service.complete = mock_complete_fail
        # 确保 mock config 属性正确
        pipeline_runner.llm_service.config.max_prompt_tokens = 120000
        pipeline_runner.llm_service.config.context_window = 128000

        events = []
        async for event in pipeline_runner.run("fallback-test", "test-project"):
            events.append(event)

        event_types = [e.get("event") for e in events]
        # 应该有 step_done 事件
        assert "step_done" in event_types


# ─── Token Estimation Tests ──────────────────────────────────────────────────

class TestTokenEstimation:
    """Token 估算测试"""

    def test_estimate_tokens_chinese(self, pipeline_runner):
        text = "这是一个中文测试文本"
        tokens = pipeline_runner._estimate_tokens(text)
        assert tokens > 0
        # 验证估算结果合理（中文字符约 0.5 token）
        assert tokens <= len(text)  # 因为每个中文字符约 0.5 token

    def test_estimate_tokens_mixed(self, pipeline_runner):
        text = "Hello 世界 123"
        tokens = pipeline_runner._estimate_tokens(text)
        assert tokens > 0

    def test_estimate_tokens_empty(self, pipeline_runner):
        tokens = pipeline_runner._estimate_tokens("")
        assert tokens == 0


# ─── System Variables Tests ──────────────────────────────────────────────────

class TestSystemVariables:
    """系统变量加载测试"""

    @pytest.mark.asyncio
    async def test_load_project_meta(self, pipeline_runner, mock_file_service):
        meta = await pipeline_runner.load_project_meta("test-project")
        assert meta["genre"] == "玄幻"
        assert meta["theme"] == "成长"
        assert meta["tone"] == "热血"

    @pytest.mark.asyncio
    async def test_load_system_variables(self, pipeline_runner, mock_file_service):
        vars = await pipeline_runner.load_system_variables("test-project")
        assert "style_guide" in vars
        assert "story_state" in vars

    @pytest.mark.asyncio
    async def test_load_chapter_vars(self, pipeline_runner, mock_file_service):
        vars = await pipeline_runner.load_chapter_vars(
            "test-project",
            "chapters/vol-01/ch-001/sec-001.md"
        )
        assert "pending_foreshadowing" in vars
        assert "active_quests" in vars


# ─── Output Mode Normalization & Direct Write Protection Tests ────────────────

class TestNormalizeOutputMode:
    """_normalize_output_mode 防御性测试：legacy overwrite/rewrite 必须被规范化为安全模式"""

    @pytest.fixture
    def runner(self, mock_llm_service, mock_file_service, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        return PipelineRunner(prompts_dir, mock_llm_service, mock_file_service)

    @pytest.mark.asyncio
    async def test_overwrite_existing_scene_normalized_to_candidate(self, runner, mock_file_service):
        """overwrite + 已有内容的场景文件 → candidate（不直接覆盖）"""
        # Override mock to return content for sec-001.md
        async def mock_read_existing(path):
            path_str = str(path)
            if "sec-001.md" in path_str:
                return "已有场景内容", None, {}
            return "", None, {}

        mock_file_service.read_file = AsyncMock(side_effect=mock_read_existing)

        result = await runner._normalize_output_mode(
            pipeline_name="generate",
            project_id="test-project",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite",
        )
        assert result == "candidate"

    @pytest.mark.asyncio
    async def test_rewrite_existing_scene_normalized_to_candidate(self, runner, mock_file_service):
        """rewrite + 已有内容的场景文件 → candidate（不直接覆盖）"""
        async def mock_read_existing(path):
            path_str = str(path)
            if "sec-001.md" in path_str:
                return "已有场景内容", None, {}
            return "", None, {}

        mock_file_service.read_file = AsyncMock(side_effect=mock_read_existing)

        result = await runner._normalize_output_mode(
            pipeline_name="generate",
            project_id="test-project",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            output_mode="rewrite",
        )
        assert result == "candidate"

    @pytest.mark.asyncio
    async def test_overwrite_empty_scene_normalized_to_write_scene(self, runner):
        """overwrite + 空场景文件 → write_scene"""
        # mock_file_service returns empty content for unknown files
        result = await runner._normalize_output_mode(
            pipeline_name="generate",
            project_id="test-project",
            target_file="chapters/vol-01/ch-001/sec-099.md",
            output_mode="overwrite",
        )
        assert result == "write_scene"

    @pytest.mark.asyncio
    async def test_write_scene_empty_stays_write_scene(self, runner):
        """write_scene + 空场景文件 → write_scene"""
        result = await runner._normalize_output_mode(
            pipeline_name="generate",
            project_id="test-project",
            target_file="chapters/vol-01/ch-001/sec-099.md",
            output_mode="write_scene",
        )
        assert result == "write_scene"

    @pytest.mark.asyncio
    async def test_write_scene_scaffold_placeholder_stays_write_scene(self, runner, mock_file_service):
        """write_scene + scaffold placeholder -> write_scene for first-run project setup."""
        async def mock_read_placeholder(path):
            path_str = str(path)
            if "style-guide.md" in path_str:
                return "# 文风指南\n\n在此描述写作风格、语气、叙事视角等要求。", None
            return "", None

        mock_file_service.read_file = AsyncMock(side_effect=mock_read_placeholder)

        result = await runner._normalize_output_mode(
            pipeline_name="style-guide",
            project_id="test-project",
            target_file="style-guide.md",
            output_mode="write_scene",
        )
        assert result == "write_scene"

    @pytest.mark.asyncio
    async def test_overwrite_dangerous_path_normalized_to_candidate(self, runner):
        """overwrite + 危险路径（story-state.md）→ candidate"""
        result = await runner._normalize_output_mode(
            pipeline_name="generate",
            project_id="test-project",
            target_file="story-state.md",
            output_mode="overwrite",
        )
        assert result == "candidate"

    @pytest.mark.asyncio
    async def test_require_candidate_overrides_overwrite(self, runner):
        """require_candidate=True + overwrite → candidate"""
        result = await runner._normalize_output_mode(
            pipeline_name="generate",
            project_id="test-project",
            target_file="chapters/vol-01/ch-001/sec-099.md",
            output_mode="overwrite",
            require_candidate=True,
        )
        assert result == "candidate"


class TestDirectWriteBranchProtection:
    """验证管线直接写入分支不再接受 legacy overwrite/rewrite。

    即使 output_mode 未被规范化（防御性测试），直接写入分支也不应处理
    overwrite 或 rewrite，确保已有 sec 文件不会被静默覆盖。
    """

    @pytest.fixture
    def runner(self, mock_llm_service, mock_file_service, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        return PipelineRunner(prompts_dir, mock_llm_service, mock_file_service)

    @staticmethod
    def _make_mock_read(existing_sec: bool = False):
        """创建 mock read_file，返回 3-tuple (content, frontmatter, mtime)"""
        async def mock_read(path):
            path_str = str(path)
            if existing_sec and "sec-001.md" in path_str:
                return "已有场景内容，不应被覆盖", None, None
            elif ".candidates/metadata.json" in path_str:
                return "{}", None, None
            elif "meta.json" in path_str:
                return json.dumps({"name": "test", "genre": "玄幻"}), None, None
            elif "ch-meta.json" in path_str:
                return json.dumps({"pending_foreshadowing": [], "active_quests": []}), None, None
            return "", None, None
        return mock_read

    @pytest.mark.asyncio
    async def test_overwrite_mode_does_not_directly_write_existing_sec(self, runner, mock_file_service, tmp_path):
        """output_mode=overwrite 针对已有内容的 sec 文件不会直接写入文件"""
        mock_file_service.read_file = AsyncMock(side_effect=self._make_mock_read(existing_sec=True))

        write_calls = []
        async def mock_write(path, content, frontmatter=None):
            write_calls.append({"path": str(path), "content": content})
        mock_file_service.write_file = AsyncMock(side_effect=mock_write)

        pipeline_dir = tmp_path / "prompts" / "pipeline" / "test-ow"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "step1.md").write_text("测试输出", encoding="utf-8")

        yaml_content = {
            "name": "test-ow", "label": "覆盖测试",
            "steps": [{"id": "step1", "label": "测试", "prompt": "pipeline/test-ow/step1"}]
        }
        yaml_path = tmp_path / "prompts" / "pipeline" / "test-ow.yaml"
        yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")

        runner.prompts_path = tmp_path / "prompts"
        runner.env = Environment(loader=FileSystemLoader(str(tmp_path / "prompts")), autoescape=False)
        runner.llm_service.config.max_prompt_tokens = 120000
        runner.llm_service.config.context_window = 128000

        events = []
        async for event in runner.run(
            "test-ow", "test-project",
            "chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite",
        ):
            events.append(event)

        sec_writes = [c for c in write_calls if "sec-001.md" in c["path"]]
        assert len(sec_writes) == 0, "overwrite 不应直接写入已有 sec 文件"
        candidate_events = [e for e in events if e.get("event") == "candidate_created"]
        assert len(candidate_events) > 0, "overwrite 应生成候选稿而非直接覆盖"

    @pytest.mark.asyncio
    async def test_rewrite_mode_does_not_directly_write_existing_sec(self, runner, mock_file_service, tmp_path):
        """output_mode=rewrite 针对已有内容的 sec 文件不会直接写入文件"""
        mock_file_service.read_file = AsyncMock(side_effect=self._make_mock_read(existing_sec=True))

        write_calls = []
        async def mock_write(path, content, frontmatter=None):
            write_calls.append({"path": str(path), "content": content})
        mock_file_service.write_file = AsyncMock(side_effect=mock_write)

        pipeline_dir = tmp_path / "prompts" / "pipeline" / "test-rw"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "step1.md").write_text("测试输出", encoding="utf-8")

        yaml_content = {
            "name": "test-rw", "label": "改写测试",
            "steps": [{"id": "step1", "label": "测试", "prompt": "pipeline/test-rw/step1"}]
        }
        yaml_path = tmp_path / "prompts" / "pipeline" / "test-rw.yaml"
        yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")

        runner.prompts_path = tmp_path / "prompts"
        runner.env = Environment(loader=FileSystemLoader(str(tmp_path / "prompts")), autoescape=False)
        runner.llm_service.config.max_prompt_tokens = 120000
        runner.llm_service.config.context_window = 128000

        events = []
        async for event in runner.run(
            "test-rw", "test-project",
            "chapters/vol-01/ch-001/sec-001.md",
            output_mode="rewrite",
        ):
            events.append(event)

        sec_writes = [c for c in write_calls if "sec-001.md" in c["path"]]
        assert len(sec_writes) == 0, "rewrite 不应直接写入已有 sec 文件"
        candidate_events = [e for e in events if e.get("event") == "candidate_created"]
        assert len(candidate_events) > 0, "rewrite 应生成候选稿而非直接覆盖"

    @pytest.mark.asyncio
    async def test_write_scene_empty_target_works(self, runner, mock_file_service, tmp_path):
        """write_scene + 空目标文件 → 正常直接写入"""
        mock_file_service.read_file = AsyncMock(side_effect=self._make_mock_read(existing_sec=False))

        write_calls = []
        async def mock_write(path, content, frontmatter=None):
            write_calls.append({"path": str(path), "content": content})
        mock_file_service.write_file = AsyncMock(side_effect=mock_write)

        pipeline_dir = tmp_path / "prompts" / "pipeline" / "test-ws"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "step1.md").write_text("测试输出", encoding="utf-8")

        yaml_content = {
            "name": "test-ws", "label": "写入测试",
            "steps": [{"id": "step1", "label": "测试", "prompt": "pipeline/test-ws/step1"}]
        }
        yaml_path = tmp_path / "prompts" / "pipeline" / "test-ws.yaml"
        yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")

        runner.prompts_path = tmp_path / "prompts"
        runner.env = Environment(loader=FileSystemLoader(str(tmp_path / "prompts")), autoescape=False)
        runner.llm_service.config.max_prompt_tokens = 120000
        runner.llm_service.config.context_window = 128000

        async for event in runner.run(
            "test-ws", "test-project",
            "chapters/vol-01/ch-001/sec-001.md",
            output_mode="write_scene",
        ):
            pass

        sec_writes = [c for c in write_calls if "sec-001.md" in c["path"]]
        assert len(sec_writes) > 0, "write_scene + 空目标应直接写入"
