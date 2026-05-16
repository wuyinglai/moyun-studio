"""墨韵 - 工作流引擎单元测试

测试要点：
1. WorkflowContext 变量解析（普通变量、命名空间、pad 过滤器）
2. WorkflowRunner 工作流加载/列表/保存/删除
3. count_steps 递归统计
4. 异步执行（pipeline 步骤、file 步骤、loop 步骤）
"""

import asyncio
import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.workflow import (
    WorkflowContext,
    WorkflowRunner,
    WorkflowError,
)
from backend.schemas.workflow import (
    WorkflowDef,
    WorkflowStepDef,
    WorkflowSaveRequest,
)


# ─── General Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_service():
    svc = MagicMock()
    async def _complete(*args, **kwargs):
        for chunk in ["生成", "内容"]:
            yield chunk
    svc.complete = _complete
    svc.count_tokens = AsyncMock(return_value=100)
    return svc


@pytest.fixture
def mock_file_service():
    svc = MagicMock()
    svc.read_file = AsyncMock(return_value=("# 文件内容\n\n正文", None))
    svc.write_file = AsyncMock()
    svc.create_directory = AsyncMock()
    svc.delete_file = AsyncMock()
    svc.workspace = Path("/fake/workspace")
    return svc


@pytest.fixture
def workflows_dir(tmp_path):
    d = tmp_path / "workflows"
    d.mkdir()
    return d


@pytest.fixture
def prompts_dir(tmp_path):
    d = tmp_path / "prompts"
    d.mkdir()
    return d


@pytest.fixture
def runner(workflows_dir, prompts_dir, mock_llm_service, mock_file_service):
    return WorkflowRunner(
        workflows_path=workflows_dir,
        prompts_path=prompts_dir,
        llm_service=mock_llm_service,
        file_service=mock_file_service,
        state_dir=prompts_dir.parent / ".wf-states",
    )


# ─── Sample Workflow & Pipeline Fixtures ────────────────────────────────────

@pytest.fixture
def sample_workflow_yaml(workflows_dir):
    data = {
        "name": "test-wf",
        "label": "测试工作流",
        "description": "测试用",
        "steps": [
            {"id": "gen", "label": "生成章节", "type": "pipeline", "pipeline": "chapter-gen",
             "output": "chapters/{{variables.vol}}/ch-{{index|pad:3}}.md"},
            {"id": "loop1", "label": "循环", "type": "loop", "count": "{{variables.count}}",
             "var": "index", "steps": [
                {"id": "calc", "label": "计算", "type": "pipeline", "pipeline": "calc"}
            ]},
            {"id": "mk", "label": "创建目录", "type": "file", "action": "mkdir",
             "path": "chapters/vol-1"},
        ],
    }
    path = workflows_dir / "test-wf.yaml"
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def sample_pipeline_yaml(prompts_dir):
    """创建管线 YAML 和 prompt 文件，使 pipeline 步骤可正常执行"""
    pipeline_dir = prompts_dir / "pipeline"
    pipeline_dir.mkdir(exist_ok=True)

    # chapter-gen pipeline
    data = {
        "name": "chapter-gen",
        "label": "章节生成",
        "steps": [
            {"id": "generate", "label": "生成", "prompt": "pipeline/chapter-gen/generate"},
        ],
    }
    (pipeline_dir / "chapter-gen.yaml").write_text(
        yaml.dump(data, allow_unicode=True), encoding="utf-8"
    )
    gen_dir = pipeline_dir / "chapter-gen"
    gen_dir.mkdir(exist_ok=True)
    (gen_dir / "generate.md").write_text("生成第 {{ index }} 章内容", encoding="utf-8")

    # calc pipeline (for loop sub-steps)
    data2 = {
        "name": "calc",
        "label": "计算",
        "steps": [
            {"id": "calc", "label": "计算", "prompt": "pipeline/calc/calc"},
        ],
    }
    (pipeline_dir / "calc.yaml").write_text(
        yaml.dump(data2, allow_unicode=True), encoding="utf-8"
    )
    calc_dir = pipeline_dir / "calc"
    calc_dir.mkdir(exist_ok=True)
    (calc_dir / "calc.md").write_text("计算步骤", encoding="utf-8")


# ─── WorkflowContext Tests ──────────────────────────────────────────────────

class TestWorkflowContext:
    """工作流上下文测试"""

    def test_init_with_variables(self):
        ctx = WorkflowContext("proj-1", {"vol": "vol-01", "count": "3"})
        assert ctx.project_id == "proj-1"
        assert ctx.variables["vol"] == "vol-01"

    def test_init_empty_variables(self):
        ctx = WorkflowContext("proj-1")
        assert ctx.variables == {}

    def test_resolve_project_id(self):
        ctx = WorkflowContext("proj-1")
        assert ctx.resolve("{{project_id}}") == "proj-1"

    def test_resolve_variable(self):
        ctx = WorkflowContext("proj-1", {"vol": "vol-01"})
        assert ctx.resolve("chapters/{{variables.vol}}/main.md") == "chapters/vol-01/main.md"

    def test_resolve_loop_var_with_pad(self):
        ctx = WorkflowContext("proj-1")
        ctx.set_loop_var("index", 3)
        assert ctx.resolve("ch-{{index|pad:3}}.md") == "ch-003.md"

    def test_resolve_loop_var_no_pad(self):
        ctx = WorkflowContext("proj-1")
        ctx.set_loop_var("index", 3)
        assert ctx.resolve("ch-{{index}}.md") == "ch-3.md"

    def test_resolve_step_output(self):
        ctx = WorkflowContext("proj-1")
        ctx.step_outputs["gen1"] = "chapters/vol-01/ch-001.md"
        assert ctx.resolve("output: {{steps.gen1.output}}") == "output: chapters/vol-01/ch-001.md"

    def test_resolve_unknown_variable_empty(self):
        ctx = WorkflowContext("proj-1")
        assert ctx.resolve("{{unknown}}") == ""

    def test_resolve_none_returns_empty(self):
        ctx = WorkflowContext("proj-1")
        assert ctx.resolve(None) == ""

    def test_resolve_int_success(self):
        ctx = WorkflowContext("proj-1", {"count": "3"})
        assert ctx.resolve_int("{{variables.count}}") == 3

    def test_resolve_int_failure_returns_zero(self):
        ctx = WorkflowContext("proj-1", {"count": "abc"})
        assert ctx.resolve_int("{{variables.count}}") == 0

    def test_resolve_int_none_returns_zero(self):
        ctx = WorkflowContext("proj-1")
        assert ctx.resolve_int(None) == 0

    def test_set_loop_var(self):
        ctx = WorkflowContext("proj-1")
        ctx.set_loop_var("vol", 2)
        assert ctx.loop_vars["vol"] == 2

    def test_resolve_variables_ns_with_pad(self):
        """命名空间变量 + pad 过滤器"""
        ctx = WorkflowContext("proj-1", {"count": "5"})
        result = ctx.resolve("{{variables.count|pad:3}}")
        assert result == "005"


# ─── WorkflowRunner Init Tests ──────────────────────────────────────────────

class TestWorkflowRunnerInit:
    """初始化测试"""

    def test_init_creates_paths(self, tmp_path, mock_llm_service, mock_file_service):
        runner = WorkflowRunner(
            workflows_path=tmp_path / "wf",
            prompts_path=tmp_path / "prompts",
            llm_service=mock_llm_service,
            file_service=mock_file_service,
        )
        assert runner.workflows_path == tmp_path / "wf"
        assert runner.prompts_path == tmp_path / "prompts"


# ─── Workflow Loader Tests ──────────────────────────────────────────────────

class TestWorkflowLoader:
    """工作流加载测试"""

    def test_load_workflow(self, runner, sample_workflow_yaml):
        wf = runner.load_workflow("test-wf")
        assert wf.name == "test-wf"
        assert wf.label == "测试工作流"
        assert len(wf.steps) == 3

    def test_load_nonexistent_raises_error(self, runner):
        with pytest.raises(WorkflowError, match="工作流不存在"):
            runner.load_workflow("nonexistent")

    def test_load_invalid_yaml_raises_error(self, runner, workflows_dir):
        (workflows_dir / "bad.yaml").write_text("invalid: yaml: [: broken", encoding="utf-8")
        with pytest.raises(WorkflowError, match="加载工作流失败"):
            runner.load_workflow("bad")

    def test_list_workflows(self, runner, sample_workflow_yaml):
        workflows = runner.list_workflows()
        assert len(workflows) == 1
        assert workflows[0].name == "test-wf"

    def test_list_workflows_empty(self, runner):
        workflows = runner.list_workflows()
        assert workflows == []

    def test_list_workflows_skips_invalid(self, runner, workflows_dir):
        (workflows_dir / "good.yaml").write_text(
            yaml.dump({"name": "good", "label": "好的", "steps": []}, allow_unicode=True),
            encoding="utf-8",
        )
        (workflows_dir / "bad.yaml").write_text("invalid", encoding="utf-8")
        workflows = runner.list_workflows()
        assert len(workflows) == 1
        assert workflows[0].name == "good"


# ─── Workflow Saver Tests ──────────────────────────────────────────────────

class TestWorkflowSaver:
    """工作流保存/删除测试"""

    def test_save_workflow(self, runner, workflows_dir):
        steps = [
            WorkflowStepDef(id="s1", label="步骤1", type="pipeline", pipeline="gen"),
        ]
        req = WorkflowSaveRequest(
            name="new-wf", label="新工作流", description="desc", steps=steps,
        )
        wf = runner.save_workflow(req)
        assert wf.name == "new-wf"
        assert wf.label == "新工作流"
        assert (workflows_dir / "new-wf.yaml").exists()

    def test_save_and_reload(self, runner, workflows_dir):
        steps = [
            WorkflowStepDef(id="s1", label="生成", type="pipeline", pipeline="chapter"),
        ]
        runner.save_workflow(WorkflowSaveRequest(
            name="roundtrip", label="往返测试", steps=steps,
        ))
        loaded = runner.load_workflow("roundtrip")
        assert loaded.name == "roundtrip"
        assert loaded.label == "往返测试"
        assert len(loaded.steps) == 1

    def test_delete_workflow(self, runner, sample_workflow_yaml):
        runner.delete_workflow("test-wf")
        assert not sample_workflow_yaml.exists()

    def test_delete_nonexistent_raises_error(self, runner):
        with pytest.raises(WorkflowError, match="工作流不存在"):
            runner.delete_workflow("nonexistent")


# ─── Count Steps Tests ─────────────────────────────────────────────────────

class TestWorkflowStepCounter:
    """count_steps 递归统计测试"""

    def test_count_flat_steps(self):
        steps = [
            WorkflowStepDef(id="a", label="A", type="pipeline", pipeline="p1"),
            WorkflowStepDef(id="b", label="B", type="pipeline", pipeline="p2"),
        ]
        runner = WorkflowRunner.__new__(WorkflowRunner)
        assert runner.count_steps(steps) == 2

    def test_count_loop_as_one(self):
        steps = [
            WorkflowStepDef(id="loop1", label="Loop", type="loop", count="3",
                            steps=[
                                WorkflowStepDef(id="s1", label="S1", type="pipeline", pipeline="p1"),
                                WorkflowStepDef(id="s2", label="S2", type="pipeline", pipeline="p2"),
                            ]),
        ]
        runner = WorkflowRunner.__new__(WorkflowRunner)
        assert runner.count_steps(steps) == 1

    def test_count_empty_steps(self):
        runner = WorkflowRunner.__new__(WorkflowRunner)
        assert runner.count_steps([]) == 0


# ─── WorkflowRunner Run Tests ───────────────────────────────────────────────

class TestWorkflowRunnerRun:
    """工作流执行测试"""

    @pytest.mark.asyncio
    async def test_run_yields_start_and_done(
        self, runner, sample_workflow_yaml, sample_pipeline_yaml,
    ):
        events = []
        async for event in runner.run("test-wf", "test-project", variables={"count": "0"}):
            events.append(event)

        event_types = [e.get("event") for e in events]
        assert "workflow_start" in event_types
        assert "workflow_done" in event_types

    @pytest.mark.asyncio
    async def test_run_nonexistent_workflow_raises_error(self, runner):
        with pytest.raises(WorkflowError, match="工作流不存在"):
            async for _ in runner.run("nonexistent", "test-project"):
                pass

    @pytest.mark.asyncio
    async def test_run_with_file_step_mkdir(
        self, runner, sample_workflow_yaml, sample_pipeline_yaml, mock_file_service,
    ):
        events = []
        async for event in runner.run("test-wf", "test-project", variables={"count": "0"}):
            events.append(event)

        # mkdir 步骤应被执行
        mock_file_service.create_directory.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_step_skip_on_resume(
        self, runner, sample_workflow_yaml, sample_pipeline_yaml, mock_file_service,
    ):
        """断点续跑：已完成的步骤被跳过"""
        run_id = "test-resume"
        ctx = WorkflowContext("test-project", variables={"count": "0"})
        runner._save_state(
            run_id=run_id, workflow_name="test-wf", project_id="test-project",
            context=ctx, status="running",
            completed_paths={"test-resume.gen"},
        )

        events = []
        async for event in runner.run("test-wf", "test-project", run_id=run_id, variables={"count": "0"}):
            events.append(event)

        event_types = [e.get("event") for e in events]
        assert "step_skip" in event_types
        assert "workflow_done" in event_types

    @pytest.mark.asyncio
    async def test_run_with_stop_event(
        self, runner, sample_workflow_yaml, sample_pipeline_yaml,
    ):
        """stop_event 可提前终止工作流"""
        stop = asyncio.Event()
        events = []

        async for event in runner.run("test-wf", "test-project", variables={"count": "0"}, stop_event=stop):
            events.append(event)
            # 收到第一个事件后停止
            stop.set()

        assert len(events) > 0


# ─── File Step Tests ────────────────────────────────────────────────────────

class TestFileStep:
    """File 步骤测试"""

    @pytest.mark.asyncio
    async def test_mkdir(self, runner, mock_file_service):
        step = WorkflowStepDef(
            id="mkdir1", label="创建目录", type="file",
            action="mkdir", path="chapters/vol-1",
        )
        ctx = WorkflowContext("test-project")
        await runner._run_file_step(step, ctx)
        mock_file_service.create_directory.assert_called_once_with(
            "test-project/chapters/vol-1"
        )
        assert ctx.step_outputs["mkdir1"] == "chapters/vol-1"

    @pytest.mark.asyncio
    async def test_copy(self, runner, mock_file_service):
        step = WorkflowStepDef(
            id="copy1", label="复制文件", type="file",
            action="copy", input="src.md", output="dst.md",
        )
        ctx = WorkflowContext("test-project")
        await runner._run_file_step(step, ctx)
        mock_file_service.read_file.assert_called_once_with("test-project/src.md")
        mock_file_service.write_file.assert_called_once()
        assert ctx.step_outputs["copy1"] == "dst.md"

    @pytest.mark.asyncio
    async def test_delete(self, runner, mock_file_service):
        step = WorkflowStepDef(
            id="del1", label="删除文件", type="file",
            action="delete", path="chapters/old.md",
        )
        ctx = WorkflowContext("test-project")
        await runner._run_file_step(step, ctx)
        mock_file_service.delete_file.assert_called_once_with(
            "test-project/chapters/old.md"
        )

    @pytest.mark.asyncio
    async def test_unknown_action_logs_warning(self, runner, caplog):
        step = WorkflowStepDef(
            id="bad", label="未知操作", type="file",
            action="unknown", path="x.md",
        )
        ctx = WorkflowContext("test-project")
        await runner._run_file_step(step, ctx)
        assert "未知 file action" in caplog.text


# ─── Loop Step Tests ────────────────────────────────────────────────────────

class TestLoopStep:
    """Loop 步骤测试"""

    @pytest.mark.asyncio
    async def test_loop_iterates_by_count(self, runner, sample_pipeline_yaml, mock_file_service):
        step = WorkflowStepDef(
            id="loop1", label="循环", type="loop", count="3", var="index",
            steps=[
                WorkflowStepDef(id="sub1", label="子步骤", type="pipeline", pipeline="chapter-gen"),
            ],
        )
        ctx = WorkflowContext("test-project")
        events = []
        async for event in runner._run_loop_step(step, ctx, None, step_path="loop1"):
            events.append(event)

        event_types = [e.get("event") for e in events]
        assert event_types.count("loop_iteration") == 3
        assert "step_done" in event_types

    @pytest.mark.asyncio
    async def test_loop_count_zero_skips(self, runner):
        step = WorkflowStepDef(
            id="loop0", label="空循环", type="loop", count="0", var="index", steps=[],
        )
        ctx = WorkflowContext("test-project")
        events = []
        async for event in runner._run_loop_step(step, ctx, None, step_path="loop0"):
            events.append(event)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_loop_stop_event(
        self, runner, sample_pipeline_yaml, mock_file_service,
    ):
        step = WorkflowStepDef(
            id="stop-loop", label="停止循环", type="loop", count="10", var="i",
            steps=[
                WorkflowStepDef(id="sub", label="子步骤", type="pipeline", pipeline="chapter-gen"),
            ],
        )
        stop = asyncio.Event()
        ctx = WorkflowContext("test-project")
        events = []
        async for event in runner._run_loop_step(step, ctx, stop, step_path="stop-loop"):
            events.append(event)
            if len(events) >= 2:
                stop.set()

        event_types = [e.get("event") for e in events]
        assert "workflow_stopped" in event_types


# ─── Pipeline Step Tests ────────────────────────────────────────────────────

class TestPipelineStep:
    """Pipeline 步骤测试"""

    @pytest.mark.asyncio
    async def test_run_pipeline_step(
        self, runner, sample_pipeline_yaml, mock_file_service,
    ):
        step = WorkflowStepDef(
            id="gen1", label="生成", type="pipeline",
            pipeline="chapter-gen",
            output="chapters/ch-001.md",
        )
        ctx = WorkflowContext("test-project")
        events = []
        async for event in runner._run_pipeline_step(step, ctx, None):
            events.append(event)

        assert len(events) > 0
        # 事件中应包含 step_id
        for ev in events:
            data = json.loads(ev["data"])
            assert "step_id" in data

    @pytest.mark.asyncio
    async def test_run_pipeline_step_with_input(
        self, runner, sample_pipeline_yaml, mock_file_service,
    ):
        step = WorkflowStepDef(
            id="edit1", label="编辑", type="pipeline",
            pipeline="chapter-gen",
            input="src.md", output="dst.md",
        )
        ctx = WorkflowContext("test-project")
        events = []
        async for event in runner._run_pipeline_step(step, ctx, None):
            events.append(event)

        # input 文件被读取作为 extra_vars.file_content
        mock_file_service.read_file.assert_any_call("test-project/src.md")
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_run_pipeline_step_nonexistent_pipeline(
        self, runner, mock_file_service,
    ):
        step = WorkflowStepDef(
            id="fail1", label="失败", type="pipeline",
            pipeline="nonexistent",
        )
        ctx = WorkflowContext("test-project")
        with pytest.raises(WorkflowError, match="管线 nonexistent 执行失败"):
            async for _ in runner._run_pipeline_step(step, ctx, None):
                pass


# ─── Error Handling Tests ──────────────────────────────────────────────────

class TestWorkflowErrorHandling:
    """工作流异常处理测试"""

    @pytest.mark.asyncio
    async def test_unknown_step_type_logs_warning(self, runner, caplog):
        step = WorkflowStepDef(
            id="bad", label="未知", type="unknown_type",
        )
        ctx = WorkflowContext("test-project")
        events = []
        async for event in runner._run_step(step, ctx, None):
            events.append(event)

        assert "未知步骤类型" in caplog.text
        event_types = [e.get("event") for e in events]
        assert "step_done" in event_types

    @pytest.mark.asyncio
    async def test_step_exception_wraps_in_workflow_error(self, runner):
        """步骤异常被包装为 WorkflowError"""
        step = WorkflowStepDef(
            id="crash", label="崩溃", type="pipeline",
            pipeline="nonexistent",
        )
        ctx = WorkflowContext("test-project")

        # _run_step 中 async for _run_pipeline_step 会抛出 WorkflowError
        with pytest.raises(WorkflowError, match="管线 nonexistent 执行失败"):
            async for _ in runner._run_step(step, ctx, None):
                pass
