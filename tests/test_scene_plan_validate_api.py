"""墨韵 - Scene Plan Validate API 测试

测试 /api/scene-plan/validate 端点
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """加载测试 fixture"""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def client():
    """创建 TestClient 实例"""
    app = create_app()
    return TestClient(app)


def test_valid_scene_plan_api(client):
    """测试有效的 Scene Plan 通过 API 校验"""
    data = load_fixture("scene_plan_valid.json")
    response = client.post("/api/scene-plan/validate", json=data)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["data"]["valid"] is True
    assert len(result["data"]["errors"]) == 0


def test_invalid_paths_api(client):
    """测试包含危险路径的 Scene Plan"""
    data = load_fixture("scene_plan_invalid_paths.json")
    response = client.post("/api/scene-plan/validate", json=data)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["data"]["valid"] is False
    assert len(result["data"]["errors"]) > 0


def test_direct_write_forbidden_api(client):
    """测试违反 candidate 策略的 Scene Plan"""
    data = load_fixture("scene_plan_direct_write_forbidden.json")
    response = client.post("/api/scene-plan/validate", json=data)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["data"]["valid"] is False
    assert len(result["data"]["errors"]) > 0


def test_missing_project_id_api(client):
    """测试缺少 project_id"""
    data = load_fixture("scene_plan_valid.json")
    del data["project_id"]
    response = client.post("/api/scene-plan/validate", json=data)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["data"]["valid"] is False


def test_missing_source_path_api(client):
    """测试缺少 source_path"""
    data = load_fixture("scene_plan_valid.json")
    del data["source_path"]
    response = client.post("/api/scene-plan/validate", json=data)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["data"]["valid"] is False


def test_empty_characters_warning_api(client):
    """测试 characters 为空产生警告"""
    data = load_fixture("scene_plan_valid.json")
    data["characters"] = []
    response = client.post("/api/scene-plan/validate", json=data)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["data"]["valid"] is True  # 警告不影响 valid
    assert len(result["data"]["warnings"]) > 0


def test_validate_api_returns_successfully(client):
    """测试 validate API 正常返回（注意：此测试不严格验证所有副作用）
    
    该测试仅验证 API 能够成功执行并返回结果，但不全面测试：
    - 是否调用 LLM
    - 是否创建 candidate
    - 是否写入文件
    
    这些安全约束在 API 实现的代码审查中验证。
    """
    data = load_fixture("scene_plan_valid.json")
    response = client.post("/api/scene-plan/validate", json=data)
    assert response.status_code == 200
    assert response.json()["data"]["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
