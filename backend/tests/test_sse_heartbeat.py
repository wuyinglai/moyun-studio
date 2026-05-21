"""墨韵 - SSE Heartbeat 测试

测试内容：
1. heartbeat 事件结构包含 type=sse.heartbeat
2. heartbeat 不包含 content
3. heartbeat 有 timestamp
"""

import json

from backend.api.sse import SSEManager


class TestHeartbeatMessage:
    """测试 heartbeat 消息构建"""

    def test_heartbeat_contains_type(self):
        """heartbeat 事件结构包含 type=sse.heartbeat"""
        manager = SSEManager()
        msg = manager.build_heartbeat_message()
        # 解析 SSE 格式: event: xxx\ndata: {...}\n\n
        lines = msg.strip().split("\n")
        assert lines[0].startswith("event: sse.heartbeat")
        data_line = lines[1]
        assert data_line.startswith("data: ")
        data = json.loads(data_line[6:])
        assert data["type"] == "sse.heartbeat"

    def test_heartbeat_no_content(self):
        """heartbeat 不包含 content 字段"""
        manager = SSEManager()
        msg = manager.build_heartbeat_message()
        lines = msg.strip().split("\n")
        data_line = lines[1]
        data = json.loads(data_line[6:])
        assert "content" not in data
        assert "delta" not in data

    def test_heartbeat_has_timestamp(self):
        """heartbeat 有 timestamp"""
        manager = SSEManager()
        msg = manager.build_heartbeat_message()
        lines = msg.strip().split("\n")
        data_line = lines[1]
        data = json.loads(data_line[6:])
        assert "timestamp" in data
        assert data["timestamp"] is not None
        assert len(data["timestamp"]) > 0

    def test_heartbeat_has_payload_with_interval(self):
        """heartbeat payload 包含 server_time 和 interval"""
        manager = SSEManager()
        msg = manager.build_heartbeat_message()
        lines = msg.strip().split("\n")
        data_line = lines[1]
        data = json.loads(data_line[6:])
        assert "payload" in data
        assert "server_time" in data["payload"]
        assert "interval" in data["payload"]
        assert data["payload"]["interval"] == SSEManager.HEARTBEAT_INTERVAL

    def test_heartbeat_project_id_is_null(self):
        """heartbeat 的 project_id 为 null"""
        manager = SSEManager()
        msg = manager.build_heartbeat_message()
        lines = msg.strip().split("\n")
        data_line = lines[1]
        data = json.loads(data_line[6:])
        assert data["project_id"] is None

    def test_heartbeat_event_name(self):
        """SSE event 名为 sse.heartbeat"""
        manager = SSEManager()
        msg = manager.build_heartbeat_message()
        lines = msg.strip().split("\n")
        assert lines[0] == "event: sse.heartbeat"

    def test_heartbeat_interval_config(self):
        """HEARTBEAT_INTERVAL 默认值为 15"""
        assert SSEManager.HEARTBEAT_INTERVAL == 15
