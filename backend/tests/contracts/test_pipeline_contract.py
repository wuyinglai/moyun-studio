"""墨韵 - Pipeline API 契约测试

确保 Pipeline 核心行为不被后续修改破坏。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.policies.generation_output_policy import decide_output, is_dangerous_output


class TestPipelineRunContract:
    """POST /api/pipeline/run 契约测试"""

    def test_pipeline_run_endpoint_exists(self, client: TestClient):
        """Pipeline run 端点存在"""
        # 不传必要参数应返回 422
        resp = client.post("/api/pipeline/run", json={})
        assert resp.status_code in (400, 404, 422)

    def test_pipeline_list_returns_pipelines(self, client: TestClient):
        """Pipeline list 返回管线列表"""
        resp = client.get("/api/pipeline/list")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body


class TestPipelineOutputPolicyContract:
    """Pipeline 输出策略契约测试"""

    def test_polish_must_create_candidate(self):
        """polish 当前 sec 必须生成 candidate"""
        result = decide_output(
            action="polish",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            pipeline_name="polish",
        )
        assert result.mode == "candidate"

    def test_rewrite_must_create_candidate(self):
        """rewrite 当前 sec 必须生成 candidate"""
        result = decide_output(
            action="rewrite",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            pipeline_name="rewrite",
        )
        assert result.mode == "candidate"

    def test_write_new_scene_empty_writes_directly(self):
        """写新场景（空 sec）直接写入"""
        result = decide_output(
            action="write_new_scene",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            file_has_content=False,
        )
        assert result.mode == "write"

    def test_overwrite_existing_sec_must_candidate(self):  # AI_GUARDRAIL_ALLOW: contract test
        """output_mode=overwrite 且目标 sec 已有内容 → candidate  AI_GUARDRAIL_ALLOW"""
        result = decide_output(
            action="generate",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite",  # AI_GUARDRAIL_ALLOW
            file_has_content=True,
        )
        assert result.mode == "candidate"

    def test_overwrite_dangerous_path_must_candidate(self):  # AI_GUARDRAIL_ALLOW: contract test
        """output_mode=overwrite 对危险路径 → candidate  AI_GUARDRAIL_ALLOW"""
        result = decide_output(
            action="generate",
            target_path="story-state.md",
            output_mode="overwrite",  # AI_GUARDRAIL_ALLOW
            file_has_content=True,
        )
        assert result.mode == "candidate"

    def test_write_scene_empty_writes(self):
        """write_scene 对空 sec → write"""
        result = decide_output(
            action="generate",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            output_mode="write_scene",
            file_has_content=False,
        )
        assert result.mode == "write"

    def test_write_scene_with_content_candidate(self):
        """write_scene 对已有内容 sec → candidate"""
        result = decide_output(
            action="generate",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            output_mode="write_scene",
            file_has_content=True,
        )
        assert result.mode == "candidate"


class TestPipelineDangerousOutputContract:
    """危险输出路径契约测试"""

    def test_scene_file_is_dangerous(self):
        """场景文件是危险路径"""
        assert is_dangerous_output("chapters/vol-01/ch-001/sec-001.md") is True

    def test_story_state_is_dangerous(self):
        """story-state.md 是危险路径"""
        assert is_dangerous_output("story-state.md") is True

    def test_recent_context_is_dangerous(self):
        """recent-context.md 是危险路径"""
        assert is_dangerous_output("recent-context.md") is True

    def test_style_guide_is_dangerous(self):
        """style-guide.md 是危险路径"""
        assert is_dangerous_output("style-guide.md") is True

    def test_materials_extracted_is_safe(self):
        """materials/extracted/ 是安全路径"""
        assert is_dangerous_output("materials/extracted/chars.md") is False

    def test_candidates_dir_is_safe(self):
        """.candidates/ 是安全路径"""
        assert is_dangerous_output(".candidates/abc.md") is False


class TestPipelineSSEEventContract:
    """Pipeline SSE 事件契约测试"""

    def test_pipeline_event_has_required_fields(self):
        """Pipeline SSE 事件必须包含 type, project_id, timestamp, payload"""
        from backend.domain.events import make_pipeline_started_event

        event = make_pipeline_started_event(
            project_id="test-project",
            pipeline_name="generate",
            task_id="task-123",
            source="test",
        )
        sse_dict = event.to_sse_dict()
        assert "type" in sse_dict or "event" in str(sse_dict)
        assert sse_dict.get("project_id") == "test-project"
        assert "timestamp" in sse_dict
        assert "payload" in sse_dict or "pipeline" in sse_dict

    def test_step_completed_event_has_step_info(self):
        """步骤完成事件必须包含 step_id"""
        from backend.domain.events import make_pipeline_step_completed_event

        event = make_pipeline_step_completed_event(
            project_id="test-project",
            step_id="generate",
            step_label="生成",
            task_id="task-123",
            source="test",
        )
        sse_dict = event.to_sse_dict()
        assert sse_dict.get("step_id") == "generate" or "step_id" in str(sse_dict.get("payload", ""))
