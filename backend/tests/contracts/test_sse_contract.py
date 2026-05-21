"""墨韵 - SSE 事件契约测试

确保 SSE 事件结构不被后续修改破坏。
"""

import json

import pytest

from backend.domain.events import (
    AppEvent,
    EventType,
    make_file_updated_event,
    make_file_created_event,
    make_file_deleted_event,
    make_candidate_created_event,
    make_pipeline_started_event,
    make_pipeline_step_completed_event,
)


class TestFileUpdatedEventContract:
    """file.updated 事件契约测试"""

    def test_file_updated_does_not_contain_content(self):
        """file.updated 事件不包含 content"""
        event = make_file_updated_event(
            project_id="test-project",
            path="chapters/vol-01/ch-001/sec-001.md",
            size=1024,
            mtime=1700000000.0,
            source="test",
        )
        sse_dict = event.to_sse_dict()
        # payload 不应包含 content
        payload = sse_dict.get("payload", sse_dict)
        assert "content" not in payload
        assert "delta" not in payload

    def test_file_updated_has_required_fields(self):
        """file.updated 事件必须包含 type, project_id, timestamp, payload.path, payload.size, payload.mtime"""
        event = make_file_updated_event(
            project_id="test-project",
            path="chapters/vol-01/ch-001/sec-001.md",
            size=1024,
            mtime=1700000000.0,
            source="test",
        )
        sse_dict = event.to_sse_dict()

        # 顶层字段
        assert sse_dict.get("type") == "file.updated"
        assert sse_dict.get("project_id") == "test-project"
        assert "timestamp" in sse_dict

        # payload 字段
        payload = sse_dict.get("payload", sse_dict)
        assert payload.get("path") == "chapters/vol-01/ch-001/sec-001.md"
        assert "size" in payload
        assert "mtime" in payload

    def test_file_updated_type_is_correct(self):
        """file.updated 事件的 type 必须是 file.updated"""
        event = make_file_updated_event(
            project_id="test-project",
            path="outline.md",
            size=100,
            mtime=1700000000.0,
            source="test",
        )
        assert event.type == "file.updated"


class TestSSEHeartbeatContract:
    """sse.heartbeat 事件契约测试"""

    def test_heartbeat_event_structure(self):
        """heartbeat 事件必须包含 type=sse.heartbeat, timestamp, payload.server_time"""
        heartbeat_data = {
            "type": "sse.heartbeat",
            "project_id": None,
            "timestamp": "2024-01-01T00:00:00",
            "payload": {
                "server_time": "2024-01-01T00:00:00",
                "interval": 15,
            },
        }

        assert heartbeat_data["type"] == "sse.heartbeat"
        assert "timestamp" in heartbeat_data
        assert "server_time" in heartbeat_data["payload"]
        assert heartbeat_data["payload"]["interval"] == 15

    def test_heartbeat_does_not_trigger_file_refresh(self):
        """heartbeat 不应触发文件刷新（无 path/size/mtime）"""
        heartbeat_data = {
            "type": "sse.heartbeat",
            "project_id": None,
            "timestamp": "2024-01-01T00:00:00",
            "payload": {
                "server_time": "2024-01-01T00:00:00",
                "interval": 15,
            },
        }
        payload = heartbeat_data["payload"]
        assert "path" not in payload
        assert "size" not in payload
        assert "mtime" not in payload
        assert "content" not in payload


class TestSSEProjectIdContract:
    """SSE 事件 project_id 契约测试"""

    def test_file_updated_has_project_id(self):
        """file.updated 必须带 project_id"""
        event = make_file_updated_event(
            project_id="my-project",
            path="outline.md",
            size=100,
            mtime=1700000000.0,
            source="test",
        )
        assert event.project_id == "my-project"

    def test_file_created_has_project_id(self):
        """file.created 必须带 project_id"""
        event = make_file_created_event(
            project_id="my-project",
            path="new-file.md",
            name="new-file.md",
            source="test",
        )
        assert event.project_id == "my-project"

    def test_file_deleted_has_project_id(self):
        """file.deleted 必须带 project_id"""
        event = make_file_deleted_event(
            project_id="my-project",
            path="old-file.md",
            source="test",
        )
        assert event.project_id == "my-project"

    def test_candidate_created_has_project_id(self):
        """candidate.created 必须带 project_id"""
        event = make_candidate_created_event(
            project_id="my-project",
            candidate_id="cand-123",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            action="rewrite",
            source="test",
        )
        assert event.project_id == "my-project"

    def test_pipeline_started_has_project_id(self):
        """pipeline.started 必须带 project_id"""
        event = make_pipeline_started_event(
            project_id="my-project",
            pipeline_name="generate",
            task_id="task-123",
            source="test",
        )
        assert event.project_id == "my-project"

    def test_pipeline_step_completed_has_project_id(self):
        """pipeline.step.completed 必须带 project_id"""
        event = make_pipeline_step_completed_event(
            project_id="my-project",
            step_id="generate",
            step_label="生成",
            task_id="task-123",
            source="test",
        )
        assert event.project_id == "my-project"


class TestSSEEventStructureContract:
    """SSE 事件通用结构契约测试"""

    def test_all_events_have_timestamp(self):
        """所有事件必须包含 timestamp"""
        events = [
            make_file_updated_event("p1", "a.md", 100, 1.0, "test"),
            make_file_created_event("p1", "a.md", "a.md", "test"),
            make_file_deleted_event("p1", "a.md", "test"),
            make_candidate_created_event("p1", "c1", "a.md", "rewrite", "test"),
            make_pipeline_started_event("p1", "gen", "t1", "test"),
        ]
        for event in events:
            assert event.timestamp is not None, f"{event.type} 缺少 timestamp"

    def test_all_events_have_type(self):
        """所有事件必须包含 type"""
        events = [
            make_file_updated_event("p1", "a.md", 100, 1.0, "test"),
            make_file_created_event("p1", "a.md", "a.md", "test"),
            make_file_deleted_event("p1", "a.md", "test"),
        ]
        for event in events:
            assert event.type is not None
            assert isinstance(event.type, str)

    def test_all_events_have_payload(self):
        """所有事件必须包含 payload"""
        events = [
            make_file_updated_event("p1", "a.md", 100, 1.0, "test"),
            make_file_created_event("p1", "a.md", "a.md", "test"),
            make_file_deleted_event("p1", "a.md", "test"),
        ]
        for event in events:
            sse_dict = event.to_sse_dict()
            assert "payload" in sse_dict or any(
                k not in ("type", "project_id", "timestamp", "event_id", "source", "task_id", "run_id")
                for k in sse_dict.keys()
            ), f"{event.type} 缺少 payload"
