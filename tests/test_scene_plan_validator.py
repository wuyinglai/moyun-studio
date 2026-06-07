"""墨韵 - Scene Plan Validator 测试

测试 Scene Plan 校验器的各种场景：
- 有效的 Scene Plan 应该通过
- 缺少必填字段应该失败
- 非法 Candidate 策略应该失败
- 危险路径应该失败
- 空 Characters 应该警告
"""

import json
from pathlib import Path

import pytest

from backend.core.scene_plan_validator import (
    ScenePlanValidationError,
    ScenePlanValidationWarning,
    validate_scene_plan,
)
from backend.schemas.scene_plan import ScenePlan


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """加载测试 fixture"""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def test_valid_scene_plan_passes():
    """测试有效的 Scene Plan 通过校验"""
    data = load_fixture("scene_plan_valid.json")
    result = validate_scene_plan(data)
    assert result.valid is True
    assert len(result.errors) == 0


def test_missing_project_id_fails():
    """测试缺少 project_id 失败"""
    data = load_fixture("scene_plan_valid.json")
    del data["project_id"]
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any("project_id" in e.field for e in result.errors)


def test_missing_source_path_fails():
    """测试缺少 source_path 失败"""
    data = load_fixture("scene_plan_valid.json")
    del data["source_path"]
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any("source_path" in e.field for e in result.errors)


def test_empty_required_beats_fails():
    """测试 required_beats 为空失败"""
    data = load_fixture("scene_plan_valid.json")
    data["required_beats"] = []
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any(e.field == "required_beats" for e in result.errors)


def test_allow_direct_write_true_fails():
    """测试 allow_direct_write=True 失败"""
    data = load_fixture("scene_plan_direct_write_forbidden.json")
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any(e.field == "candidate_policy.allow_direct_write" for e in result.errors)


def test_require_candidate_false_fails():
    """测试 require_candidate=False 失败"""
    data = load_fixture("scene_plan_direct_write_forbidden.json")
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any(e.field == "candidate_policy.require_candidate" for e in result.errors)


def test_invalid_material_paths_fail():
    """测试 material_paths 包含危险路径失败"""
    data = load_fixture("scene_plan_invalid_paths.json")
    result = validate_scene_plan(data)
    assert result.valid is False
    # 检查是否有 material_paths 相关的错误
    assert any("material_paths" in e.field for e in result.errors)


def test_invalid_recent_context_paths_fail():
    """测试 recent_context_paths 包含危险路径失败"""
    data = load_fixture("scene_plan_invalid_paths.json")
    result = validate_scene_plan(data)
    assert result.valid is False
    # 检查是否有 recent_context_paths 相关的错误
    assert any("recent_context_paths" in e.field for e in result.errors)


def test_empty_characters_gives_warning():
    """测试 characters 为空产生警告"""
    data = load_fixture("scene_plan_valid.json")
    data["characters"] = []
    result = validate_scene_plan(data)
    assert result.valid is True  # 警告不影响 valid
    assert len(result.warnings) >= 1
    assert any(w.field == "characters" for w in result.warnings)


def test_validation_result_structure():
    """测试校验结果结构稳定"""
    data = load_fixture("scene_plan_valid.json")
    result = validate_scene_plan(data)
    assert hasattr(result, "valid")
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_accepts_scene_plan_object():
    """测试接受 ScenePlan 对象作为输入"""
    data = load_fixture("scene_plan_valid.json")
    scene_plan = ScenePlan(**data)
    result = validate_scene_plan(scene_plan)
    assert result.valid is True


def test_missing_title_fails():
    """测试缺少 title 失败"""
    data = load_fixture("scene_plan_valid.json")
    del data["title"]
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any("title" in e.field for e in result.errors)


def test_missing_goal_fails():
    """测试缺少 goal 失败"""
    data = load_fixture("scene_plan_valid.json")
    del data["goal"]
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any("goal" in e.field for e in result.errors)


def test_missing_conflict_fails():
    """测试缺少 conflict 失败"""
    data = load_fixture("scene_plan_valid.json")
    del data["conflict"]
    result = validate_scene_plan(data)
    assert result.valid is False
    assert any("conflict" in e.field for e in result.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
