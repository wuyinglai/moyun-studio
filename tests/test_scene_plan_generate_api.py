"""Scene Plan 生成 API 测试"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas.scene_plan import ScenePlan


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


def test_generate_scene_plan_api_success(valid_scene_plan_dict):
    """测试成功生成有效 Scene Plan"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace") as mock_load_cfg, \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        # Setup mocks
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = json.dumps(valid_scene_plan_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [
            ("当前场景正文", {}, 12345.67),  # target_file
            FileNotFoundError,  # story_state
            FileNotFoundError,  # style_guide
            FileNotFoundError,  # recent_context
        ]
        mock_file._resolve_path.return_value = "/fake/path"

        # Mock FileService
        mock_file_service.return_value = mock_file

        # Test request
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


def test_generate_scene_plan_api_invalid_json():
    """测试 LLM 返回无效 JSON"""
    with patch("backend.api.scene_plan.load_llm_config_from_workspace") as mock_load_cfg, \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "这不是 JSON"
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [
            ("当前场景正文", {}, 12345.67),
        ]
        mock_file._resolve_path.return_value = "/fake/path"

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


def test_generate_scene_plan_api_validation_failure():
    """测试 Scene Plan 未通过校验"""
    invalid_dict = {
        "project_id": "demo-novel",
        "source_path": "chapters/vol-01/ch-001/sec-001.md",
        "title": "场景标题",
        "goal": "",  # 空 goal
        "conflict": "",  # 空 conflict
        "required_beats": [],
        "output_intent": "polish",
        "candidate_policy": {
            "require_candidate": False,  # 错误：必须为 true
            "allow_direct_write": True,   # 错误：必须为 false
        },
    }

    with patch("backend.api.scene_plan.load_llm_config_from_workspace") as mock_load_cfg, \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = json.dumps(invalid_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [
            ("当前场景正文", {}, 12345.67),
        ]
        mock_file._resolve_path.return_value = "/fake/path"

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


def test_generate_scene_plan_api_dangerous_path():
    """测试危险路径"""
    response = client.post(
        "/api/scene-plan/generate",
        json={
            "project_id": "demo-novel",
            "target_file": "../.env",  # 危险路径
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    result = data["data"]

    assert result["valid"] is False
    assert len(result["errors"]) >= 1
    assert "target_file" in result["errors"][0]["field"]


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

    with patch("backend.api.scene_plan.load_llm_config_from_workspace") as mock_load_cfg, \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = json.dumps(test_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [
            ("场景正文", {}, 12345.67),  # target_file
            ("故事状态", {}, 12345.67),  # story_state
            ("风格指南", {}, 12345.67),  # style_guide
            ("最近上下文", {}, 12345.67),  # recent_context
        ]
        mock_file._resolve_path.return_value = "/fake/path"

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

        assert result["source_summary"]["used_story_state"] is True
        assert result["source_summary"]["used_style_guide"] is True
        assert result["source_summary"]["used_recent_context"] is True


def test_no_side_effects(valid_scene_plan_dict, tmp_path):
    """测试无副作用：不写文件，不创建 candidate"""
    # 这个测试主要验证 API 不会执行写操作
    with patch("backend.api.scene_plan.load_llm_config_from_workspace"), \
         patch("backend.api.scene_plan.LLMService") as mock_llm_service, \
         patch("backend.api.scene_plan.FileService") as mock_file_service:

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = json.dumps(valid_scene_plan_dict)
        mock_llm_service.from_workspace_config.return_value = mock_llm

        mock_file = MagicMock()
        mock_file.read_file.side_effect = [
            ("当前场景正文", {}, 12345.67),
        ]
        mock_file._resolve_path.return_value = "/fake/path"

        mock_file_service.return_value = mock_file

        response = client.post(
            "/api/scene-plan/generate",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200

        # 验证没有调用写操作
        mock_file.write_file.assert_not_called()
