"""候选稿 Provenance 测试

验证候选稿创建时正确记录 Scene Plan provenance 信息。
"""

import hashlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from backend.core.candidate_service import CandidateService
from backend.core.file_ops import FileService
from backend.schemas.candidate import CandidateInfo, CandidateAction, CandidateStatus


@pytest.fixture
def mock_file_service():
    """Mock FileService"""
    mock = MagicMock(spec=FileService)
    
    async def mock_read_file(path):
        if ".candidates/metadata.json" in path:
            return ("{}", {}, 12345.67)
        return ("original content", {}, 12345.67)
    
    mock.read_file = mock_read_file
    mock.write_file = AsyncMock()
    return mock


@pytest.fixture
def candidate_service(mock_file_service):
    """创建 CandidateService 实例"""
    return CandidateService(mock_file_service)


@pytest.fixture
def mock_metadata():
    """Mock metadata"""
    return {}


@pytest.fixture
def scene_plan_dict():
    """测试用 Scene Plan"""
    return {
        "project_id": "demo-novel",
        "source_path": "chapters/vol-01/ch-001/sec-001.md",
        "title": "雨夜：旧港站的未知召唤",
        "goal": "测试场景目标",
        "conflict": "角色冲突",
        "required_beats": ["beat1", "beat2"],
    }


@pytest.mark.asyncio
async def test_create_candidate_with_scene_plan_provenance(candidate_service, mock_file_service):
    """测试创建候选稿时正确记录 Scene Plan provenance"""
    scene_plan = {
        "project_id": "demo-novel",
        "source_path": "chapters/vol-01/ch-001/sec-001.md",
        "title": "测试场景计划",
        "goal": "测试目标",
        "required_beats": ["beat1", "beat2"],
    }
    
    scene_plan_str = json.dumps(scene_plan, ensure_ascii=False, sort_keys=True)
    expected_hash = hashlib.md5(scene_plan_str.encode("utf-8")).hexdigest()
    
    candidate = await candidate_service.create_candidate(
        project_id="demo-novel",
        source_path="chapters/vol-01/ch-001/sec-001.md",
        action=CandidateAction.POLISH,
        content="测试候选稿内容",
        generation_context={"scene_plan_used": True},
        scene_plan_hash=expected_hash,
        scene_plan_path="chapters/vol-01/ch-001/sec-001.md",
    )
    
    assert candidate.scene_plan_hash == expected_hash
    assert candidate.scene_plan_path == "chapters/vol-01/ch-001/sec-001.md"
    assert candidate.generation_context.get("scene_plan_used") is True


@pytest.mark.asyncio
async def test_create_candidate_without_scene_plan(candidate_service, mock_file_service):
    """测试创建候选稿时不使用 Scene Plan 的情况"""
    candidate = await candidate_service.create_candidate(
        project_id="demo-novel",
        source_path="chapters/vol-01/ch-001/sec-001.md",
        action=CandidateAction.POLISH,
        content="测试候选稿内容",
    )
    
    assert candidate.scene_plan_hash == ""
    assert candidate.scene_plan_path == ""
    assert candidate.generation_context.get("scene_plan_used") is False or candidate.generation_context == {}


@pytest.mark.asyncio
async def test_candidate_info_schema_includes_provenance_fields():
    """测试 CandidateInfo schema 包含 provenance 字段"""
    candidate_info = CandidateInfo(
        id="cand_test123",
        project_id="demo-novel",
        source_path="chapters/vol-01/ch-001/sec-001.md",
        candidate_path=".candidates/cand_test123.polish.md",
        action=CandidateAction.POLISH,
        generation_context={"scene_plan_used": True},
        scene_plan_hash="abc123",
        scene_plan_path="chapters/vol-01/ch-001/sec-001.md",
    )
    
    # 验证字段存在且可序列化
    data = candidate_info.model_dump(mode="json")
    assert "generation_context" in data
    assert "scene_plan_hash" in data
    assert "scene_plan_path" in data
    assert data["scene_plan_hash"] == "abc123"
    assert data["generation_context"]["scene_plan_used"] is True


@pytest.mark.asyncio
async def test_pipeline_candidate_provenance_consistency(candidate_service, mock_file_service):
    """测试 pipeline 创建候选稿时 provenance 与输入一致"""
    scene_plan = {
        "project_id": "demo-novel",
        "source_path": "chapters/vol-01/ch-001/sec-001.md",
        "title": "测试场景计划",
    }
    
    # 模拟 pipeline 中的操作
    generation_context = {"scene_plan_used": True}
    scene_plan_str = json.dumps(scene_plan, ensure_ascii=False, sort_keys=True)
    scene_plan_hash = hashlib.md5(scene_plan_str.encode("utf-8")).hexdigest()
    scene_plan_path = scene_plan.get("source_path", "")
    
    candidate = await candidate_service.create_candidate(
        project_id="demo-novel",
        source_path="chapters/vol-01/ch-001/sec-001.md",
        action=CandidateAction.POLISH,
        content="pipeline 生成的内容",
        generation_context=generation_context,
        scene_plan_hash=scene_plan_hash,
        scene_plan_path=scene_plan_path,
    )
    
    # 验证一致性
    assert candidate.source_path == scene_plan_path
    assert candidate.scene_plan_path == scene_plan_path
    assert candidate.generation_context["scene_plan_used"] is True
    
    # 验证 hash 可验证
    re_computed_hash = hashlib.md5(scene_plan_str.encode("utf-8")).hexdigest()
    assert candidate.scene_plan_hash == re_computed_hash


def test_candidate_info_default_values():
    """测试 CandidateInfo 默认值"""
    candidate_info = CandidateInfo(
        id="cand_test",
        project_id="demo-novel",
        source_path="test.md",
        candidate_path=".candidates/test.md",
        action=CandidateAction.POLISH,
    )
    
    assert candidate_info.generation_context == {}
    assert candidate_info.scene_plan_hash == ""
    assert candidate_info.scene_plan_path == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])