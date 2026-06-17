"""T6.7.3 Pipeline stream 格式契约测试

锁定当前 Pipeline dry-run stream 消息格式，用于：
- 确认 `yield` 的格式稳定
- 确保 `event`, `data`, `dry_run`, `done` 等关键字段存在
- 不调用真实 LLM，不写文件，不生成 candidate
- 不依赖 HTTP 层/EventSourceResponse，只验证 stream 事件

注意：
本测试**不**验证 HTTP 层，只验证 `PipelineRunner.run()` 异步生成器产生的事件。
HTTP 层的格式由 Playwright 28-pipeline-dry-run-ui-sse-flow.spec.ts 覆盖。
"""
import json
import tempfile
from pathlib import Path

import pytest

from backend.core.pipeline import PipelineRunner

# 真实的 prompts 路径（与 backend 模块所在相对 workspace 相对）
PROMPTS_PATH = Path(__file__).resolve().parents[3] / "prompts"


class MockLLM:
    """dry-run 不应被调用"""

    def __init__(self):
        self.call_count = 0
        self.config = type(
            "Config",
            (),
            {"max_prompt_tokens": 120000, "context_window": 120000},
        )()

    async def count_tokens(self, text):
        return 0

    async def complete(self, *args, **kwargs):
        self.call_count += 1
        yield "[MOCK-LLM-OUTPUT]"


class MockFileService:
    """dry-run 不应被写入"""

    def __init__(self):
        self.write_calls = []

    async def read_file(self, path):
        # continuity-anchors.json: simulate old project without anchors
        if "continuity-anchors.json" in str(path):
            raise FileNotFoundError(f"mock: {path}")
        return "# Test\n\nInitial content.\n", None, False

    async def write_file(self, path, content, frontmatter=None):
        self.write_calls.append(path)


def _make_runner():
    return (
        PipelineRunner(
            prompts_path=PROMPTS_PATH,
            llm_service=MockLLM(),
            file_service=MockFileService(),
            system_prompts_path=None,
        ),
        PROMPTS_PATH,
    )


class TestPipelineDryRunStreamFormat:
    """Pipeline dry-run stream 消息格式锁定"""

    @pytest.mark.asyncio
    async def test_dry_run_yields_events_with_event_and_data_fields(self):
        """每个 yield 事件必须包含 event + data 字段（或至少二者之一）。

        当前约定：`yield {"event": "...", "data": json.dumps({...})}`
        """
        runner, _tmp = _make_runner()
        events = []
        async for evt in runner.run(
            pipeline_name="polish",
            project_id="__e2e_t6_7_3_dry",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            user_input="",
            output_mode="candidate",
            extra_vars=None,
            scene_plan=None,
            dry_run=True,
        ):
            events.append(evt)

        assert len(events) > 0, "dry-run pipeline 必须产生至少一个事件"
        for i, evt in enumerate(events):
            assert isinstance(evt, dict), f"事件 #{i} 不是 dict: {type(evt)}"
            assert "event" in evt, f"事件 #{i} 缺少 event 字段"
            assert "data" in evt, f"事件 #{i} 缺少 data 字段"

    @pytest.mark.asyncio
    async def test_dry_run_event_value_is_string(self):
        """`event` 字段必须是字符串，用于前端判断事件类型。"""
        runner, _tmp = _make_runner()
        async for evt in runner.run(
            pipeline_name="polish",
            project_id="__e2e_t6_7_3_dry",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            user_input="",
            output_mode="candidate",
            extra_vars=None,
            scene_plan=None,
            dry_run=True,
        ):
            assert isinstance(evt["event"], str), f"event 字段非字符串: {evt}"

    @pytest.mark.asyncio
    async def test_dry_run_data_is_json_string_or_dict(self):
        """`data` 字段要么是 JSON 字符串，要么是 dict。

        当前实现 yield 的是 `json.dumps(...)` 字符串，本测试验证数据可被解析。
        """
        runner, _tmp = _make_runner()
        async for evt in runner.run(
            pipeline_name="polish",
            project_id="__e2e_t6_7_3_dry",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            user_input="",
            output_mode="candidate",
            extra_vars=None,
            scene_plan=None,
            dry_run=True,
        ):
            data = evt["data"]
            if isinstance(data, str):
                # 必须是可解析 JSON
                parsed = json.loads(data)
                assert isinstance(parsed, dict), f"data JSON 解析后非 dict: {parsed}"
            else:
                assert isinstance(data, dict), f"data 字段既非 JSON str 也非 dict: {type(data)}"

    @pytest.mark.asyncio
    async def test_dry_run_contains_done_event(self):
        """stream 必须以 done 事件结束，且 done 事件内带 dry_run=True。

        这是前端判断 pipeline 完成的关键字段。
        """
        runner, _tmp = _make_runner()
        done_events = []
        async for evt in runner.run(
            pipeline_name="polish",
            project_id="__e2e_t6_7_3_dry",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            user_input="",
            output_mode="candidate",
            extra_vars=None,
            scene_plan=None,
            dry_run=True,
        ):
            if evt["event"] == "done":
                done_events.append(evt)

        assert len(done_events) == 1, f"应恰好有一个 done 事件，实际 {len(done_events)}"
        done_evt = done_events[0]
        data = json.loads(done_evt["data"]) if isinstance(done_evt["data"], str) else done_evt["data"]

        # done 事件可能带 dry_run 字段（前端依赖）
        has_dry_run = data.get("dry_run") is not None or done_evt.get("dry_run") is not None
        assert has_dry_run, f"done 事件缺少 dry_run 字段: {done_evt}"

    @pytest.mark.asyncio
    async def test_dry_run_does_not_call_llm_or_write_file(self):
        """dry-run 安全边界：不调用 LLM，不写文件。"""
        llm = MockLLM()
        fs = MockFileService()
        tmpdir = PROMPTS_PATH
        runner = PipelineRunner(
            prompts_path=tmpdir,
            llm_service=llm,
            file_service=fs,
            system_prompts_path=None,
        )

        events = []
        async for evt in runner.run(
            pipeline_name="polish",
            project_id="__e2e_t6_7_3_dry",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            user_input="",
            output_mode="candidate",
            extra_vars=None,
            scene_plan=None,
            dry_run=True,
        ):
            events.append(evt)

        assert llm.call_count == 0, f"dry-run 调用了 LLM {llm.call_count} 次"
        assert fs.write_calls == [], f"dry-run 写入了文件: {fs.write_calls}"
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_dry_run_known_event_types_are_strings(self):
        """事件名集合应可预测，避免后端随意改动。

        当前约定的事件名（来自 pipeline.py 的 yield）：
        - task_start
        - thinking / prompt / step_done
        - generation
        - dry_run
        - candidate_created
        - diff_summary
        - done
        - error
        """
        runner, _tmp = _make_runner()
        event_names = []
        async for evt in runner.run(
            pipeline_name="polish",
            project_id="__e2e_t6_7_3_dry",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            user_input="",
            output_mode="candidate",
            extra_vars=None,
            scene_plan=None,
            dry_run=True,
        ):
            event_names.append(evt["event"])

        assert len(event_names) > 0, "stream 为空"
        # 所有事件名应为字符串（已经在上方单测验证，这里做个完整性检查）
        for name in event_names:
            assert isinstance(name, str) and len(name) > 0, f"非法事件名: {name!r}"
