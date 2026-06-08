"""Scene Plan 持久化 API 测试"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.core.file_ops import FileService
from backend.config import get_settings

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


def test_save_scene_plan_success(valid_scene_plan_dict):
    """测试成功保存 Scene Plan"""
    with patch("backend.api.scene_plan.FileService") as mock_file_service_class:
        mock_file = MagicMock()
        # 第一次读取返回不存在
        mock_file.read_file.side_effect = Exception("File not found")
        # write_file 成功
        mock_file.write_file = AsyncMock()
        mock_file_service_class.return_value = mock_file

        response = client.post(
            "/api/scene-plan/save",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "scene_plan": valid_scene_plan_dict,
                "overwrite": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["data"]

        assert result["saved"] is True
        assert result["valid"] is True
        assert result["path"] is not None
        assert "materials/scene_plans/" in result["path"]
        assert ".scene-plan.json" in result["path"]
        assert result["conflict"] is False
        assert len(result["errors"]) == 0

        # 验证 write_file 被调用
        mock_file.write_file.assert_called_once()


def test_save_scene_plan_conflict_when_exists(valid_scene_plan_dict):
    """测试文件已存在时冲突"""
    with patch("backend.api.scene_plan.FileService") as mock_file_service_class:
        mock_file = MagicMock()
        # 文件已存在
        mock_file.read_file = AsyncMock(return_value=('{"test": "data"}', {}, 12345.67))
        mock_file_service_class.return_value = mock_file

        response = client.post(
            "/api/scene-plan/save",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "scene_plan": valid_scene_plan_dict,
                "overwrite": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        assert result["saved"] is False
        assert result["conflict"] is True
        assert "overwrite" in result["message"].lower()

        # 验证 write_file 未被调用
        mock_file.write_file.assert_not_called()


def test_save_scene_plan_overwrite_allowed(valid_scene_plan_dict):
    """测试 overwrite=true 时允许覆盖"""
    with patch("backend.api.scene_plan.FileService") as mock_file_service_class:
        mock_file = MagicMock()
        # 文件已存在
        mock_file.read_file.return_value = ('{"test": "old"}', {}, 12345.67)
        mock_file.write_file = AsyncMock()
        mock_file_service_class.return_value = mock_file

        response = client.post(
            "/api/scene-plan/save",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "scene_plan": valid_scene_plan_dict,
                "overwrite": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        assert result["saved"] is True
        assert result["conflict"] is False

        # 验证 write_file 被调用
        mock_file.write_file.assert_called_once()


def test_save_invalid_scene_plan_rejected(valid_scene_plan_dict):
    """测试 invalid Scene Plan 不保存"""
    invalid_dict = valid_scene_plan_dict.copy()
    invalid_dict["candidate_policy"]["allow_direct_write"] = True  # 危险：允许直接写入

    with patch("backend.api.scene_plan.FileService") as mock_file_service_class:
        mock_file = MagicMock()
        mock_file.read_file.side_effect = Exception("File not found")
        mock_file_service_class.return_value = mock_file

        response = client.post(
            "/api/scene-plan/save",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "scene_plan": invalid_dict,
                "overwrite": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        assert result["saved"] is False
        assert result["valid"] is False
        assert len(result["errors"]) >= 1

        # 验证 write_file 未被调用
        mock_file.write_file.assert_not_called()


def test_save_dangerous_path():
    """测试危险路径拒绝"""
    response = client.post(
        "/api/scene-plan/save",
        json={
            "project_id": "demo-novel",
            "target_file": "../.env",
            "scene_plan": {"test": "data"},
            "overwrite": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["saved"] is False
    assert len(result["errors"]) >= 1
    assert "target_file" in result["errors"][0]["field"]


def test_load_scene_plan_success(valid_scene_plan_dict):
    """测试成功加载 Scene Plan"""
    with patch("backend.api.scene_plan.FileService") as mock_file_service_class:
        mock_file = MagicMock()
        mock_file.read_file = AsyncMock(return_value=(
            json.dumps(valid_scene_plan_dict),
            {"mtime": 12345.67},
            {},
        ))
        mock_file_service_class.return_value = mock_file

        response = client.get(
            "/api/scene-plan/load",
            params={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["data"]

        assert result["exists"] is True
        assert result["scene_plan"] is not None
        assert result["path"] is not None
        assert result["mtime"] is not None
        assert len(result["errors"]) == 0


def test_load_scene_plan_not_exists():
    """测试加载不存在的 Scene Plan"""
    with patch("backend.api.scene_plan.FileService") as mock_file_service_class:
        mock_file = MagicMock()
        mock_file.read_file = AsyncMock(side_effect=Exception("File not found"))
        mock_file_service_class.return_value = mock_file

        response = client.get(
            "/api/scene-plan/load",
            params={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
            },
        )

        assert response.status_code == 200
        data = response.json()
        result = data["data"]

        assert result["exists"] is False
        assert result["scene_plan"] is None
        assert len(result["errors"]) == 0


def test_load_dangerous_path():
    """测试危险路径拒绝"""
    response = client.get(
        "/api/scene-plan/load",
        params={
            "project_id": "demo-novel",
            "target_file": "../../.env",
        },
    )

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert result["exists"] is False
    assert len(result["errors"]) >= 1
    assert "target_file" in result["errors"][0]["field"]


def test_no_side_effects(valid_scene_plan_dict):
    """测试无副作用：不影响正文和 candidate"""
    with patch("backend.api.scene_plan.FileService") as mock_file_service_class:
        mock_file = MagicMock()
        mock_file.read_file.side_effect = Exception("File not found")
        mock_file.write_file = AsyncMock()
        mock_file_service_class.return_value = mock_file

        response = client.post(
            "/api/scene-plan/save",
            json={
                "project_id": "demo-novel",
                "target_file": "chapters/vol-01/ch-001/sec-001.md",
                "scene_plan": valid_scene_plan_dict,
                "overwrite": False,
            },
        )

        assert response.status_code == 200

        # 验证没有调用危险操作
        # 验证 write_file 调用的是 Scene Plan 路径，不是正文路径
        call_args = mock_file.write_file.call_args
        if call_args:
            written_path = call_args.kwargs.get("path") or call_args[1].get("path")
            assert "materials/scene_plans/" in written_path
            assert "chapters/vol-01/" not in written_path


def test_path_mapping():
    """测试路径映射函数"""
    from backend.api.scene_plan import _map_target_file_to_scene_plan_path

    # 测试基本映射
    path = _map_target_file_to_scene_plan_path("chapters/vol-01/ch-001/sec-001.md")
    assert path == "materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json"

    # 测试反斜杠
    path = _map_target_file_to_scene_plan_path("chapters\\vol-01\\ch-001\\sec-001.md")
    assert "materials/scene_plans/" in path
    assert ".scene-plan.json" in path

    # 测试危险字符
    path = _map_target_file_to_scene_plan_path("chapters/../.env")
    assert ".." not in path
    assert ".env" not in path
