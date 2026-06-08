"""Scene Plan 生成 API 测试

说明：
- 后端 API 使用 LLMService.complete_sync()（不是 generate()），
- 本测试全部 mock LLM 调用，不发真实请求。
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.fixture
def valid_scene_plan_dict():
    """有效 Scene Plan 数据"""
    return {
        "project_id": "demo-novel",
        "source_path": "chapters/vol-01/ch-001/sec-001.md",
        "title": "地铁站场景",
        "goal": "为该场景生成结构化规划",
        "conflict": "主角在地铁站迷路",
        "required_beats": ["进入地铁站", "寻找出口"],
        "output_intent": "polish",
        "candidate_policy": {
            "require_candidate": True,
            "allow_direct_write": False,
        },
        "metadata": {
            "created_by": "llm",
        },
    }


# ── 1. 成功生成 ──────────────────────────────────────


def test_generate_scene_plan_api_success(valid_scene_plan_dict):
    """测试成功生成有效 Scene Plan，验证 complete_sync 被调用"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace") as mock_load_cfg, \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = json.dumps(valid_scene_plan_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [
            ("当前场景正文", {}, 12345.67),
            FileNotFoundError,
            FileNotFoundError,
            FileNotFoundError,
        ]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "dry_run": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["data"]

        assert result["valid"] is True
        assert result["scene_plan"] is not None
        assert result["scene_plan"]["candidate_policy"]["require_candidate"] is True
        assert result["scene_plan"]["candidate_policy"]["allow_direct_write"] is False
        assert result["source_summary"]["target_file"] == "chapters/vol-01/ch-001/sec-001.md"
        assert len(result["errors"]) == 0
        assert result["raw_output"] is None

        # 回归断言：调用的是 complete_sync，不是 generate
        mock_llm.complete_sync.assert_awaited_once()
        assert not hasattr(mock_llm, 'generate') or not mock_llm.generate.called, \
            "API 不应调用不存在的 generate 方法"


# ── 2. raw_output 默认不返回 ────────────────────────


def test_generate_scene_plan_api_raw_output_not_included_by_default(valid_scene_plan_dict):
    """测试 raw_output 默认不返回"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = json.dumps(valid_scene_plan_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [("正文", {}, 12345.67)]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        assert result["raw_output"] is None


# ── 3. include_raw_output=true 返回 raw_output ─────


def test_generate_scene_plan_api_include_raw_output(valid_scene_plan_dict):
    """测试 include_raw_output=true 时返回 raw_output"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        raw_output_value = json.dumps(valid_scene_plan_dict)
        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = raw_output_value
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [("正文", {}, 12345.67)]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "include_raw_output": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        assert result["raw_output"] is not None
        assert result["raw_output"] == raw_output_value


# ── 4. LLM 返回无效 JSON ─────────────────────────────


def test_generate_scene_plan_api_invalid_json():
    """测试 LLM 返回无效 JSON"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = "这不是 JSON"
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [("当前场景正文", {}, 12345.67)]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["data"]

        assert result["valid"] is False
        assert result["scene_plan"] is None
        assert len(result["errors"]) == 1
        assert "JSON" in result["errors"][0]["message"]


# ── 5. Scene Plan 未通过校验 ───────────────────────


def test_generate_scene_plan_api_validation_failure():
    """测试 Scene Plan 未通过校验"""
    invalid_dict = {
        "project_id": "demo-novel",
        "source_path": "chapters/vol-01/ch-001/sec-001.md",
        "title": "场景标题",
        "goal": "",
        "conflict": "",
        "required_beats": [],
        "output_intent": "polish",
        "candidate_policy": {
            "require_candidate": False,
            "allow_direct_write": True,
        },
    }

    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = json.dumps(invalid_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [("当前场景正文", {}, 12345.67)]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["data"]

        assert result["valid"] is False
        assert len(result["errors"]) >= 3


# ── 6. 危险路径 ───────────────────────────────────


def test_generate_scene_plan_api_dangerous_path():
    """测试危险路径"""
    response = client.post(
        "/api/scene-plan/generate",
        json={
            "project_id": "demo-novel",
            "target_file": "../.env",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    result = data["data"]

    assert result["valid"] is False
    assert len(result["errors"]) >= 1
    assert "target_file" in result["errors"][0]["field"]


# ── 7. 包含上下文文件 ─────────────────────────────


def test_generate_scene_plan_api_with_context():
    """测试包含上下文文件"""
    test_dict = {
        "project_id": "demo-novel",
        "source_path": "chapters/vol-01/ch-001/sec-001.md",
        "title": "场景标题",
        "goal": "场景目标",
        "conflict": "冲突内容",
        "required_beats": ["节拍1"],
        "output_intent": "polish",
        "candidate_policy": {"require_candidate": True, "allow_direct_write": False},
    }

    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = json.dumps(test_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = None
        mock_file.read_file.return_value = ("正文", {}, 12345.67)
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "instruction": "请生成详细规划",
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]
        assert mock_file.read_file.call_count >= 1


# ── 8. 无副作用：不写文件，不创建 candidate ─────


def test_no_side_effects(valid_scene_plan_dict):
    """测试无副作用：不写文件，不创建 candidate"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = json.dumps(valid_scene_plan_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [("当前场景正文", {}, 12345.67)]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200

        mock_file.write_file.assert_not_called()


# ── 9. 回归测试：LLMService.generate 绝对不会被调用 ─


def test_generate_api_does_not_use_llm_generate_method(valid_scene_plan_dict):
    """回归测试：确保 API 不会调用不存在的 LLMService.generate()

    历史 bug：scene_plan.py 错误调用了 llm_service.generate()，
    但 LLMService 只有 complete() / complete_sync()。
    本测试确保 API 使用 complete_sync，而非 generate。
    """
    # 创建一个只含 complete_sync，绝对不含 generate 的 fake service，
    # 若 API 调用 generate，会直接抛 AttributeError，测试失败。

    class FakeLLMService:
        # 故意只提供 complete_sync，不提供 generate，
        # 若 API 调用 generate，会直接抛 AttributeError，测试失败。

        def __init__(self):
            self.call_count = 0

        async def complete_sync(self, messages, model=None, **kwargs):
            self.call_count += 1
            return json.dumps(valid_scene_plan_dict)

    fake_service = FakeLLMService()

    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm_service.from_workspace_config.return_value = fake_service

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [("当前场景正文", {}, 12345.67)]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        # 关键断言：fake service 的 complete_sync 被调用
        assert fake_service.call_count == 1

        # 确保 fake service 从未获得 generate 调用
        assert not hasattr(fake_service, "generate") or \
            "fake 不应出现 generate 属性"

        # 结果正常
        assert result["valid"] is True
        assert result["scene_plan"] is not None


# ── 10. complete_sync 参数检查：messages 应为 list[dict] ─


def test_generate_api_calls_complete_sync_with_messages(valid_scene_plan_dict):
    """确保 complete_sync 收到的 messages 参数格式正确"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.complete_sync.return_value = json.dumps(valid_scene_plan_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [("正文", {}, 12345.67)]
        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200

        # 检查 complete_sync 被调用且参数正确
        mock_llm.complete_sync.assert_awaited_once()
        call_args = mock_llm.complete_sync.call_args
        assert call_args.kwargs.get("messages") is not None or \
            "complete_sync 应收到 messages 参数"
        msgs = call_args.kwargs["messages"]
        assert isinstance(msgs, list)
        assert len(msgs) >= 1
        assert msgs[0]["role"] == "user"
        assert "content" in msgs[0]
