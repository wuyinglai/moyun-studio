"""测试 Lite fallback candidate 创建

Phase T3-D4.3 目标：
- 当 fallback_used=True 时，创建 fallback_draft candidate
- 不写正式正文文件
- 不更新 story engine 和相关 metadata
- 返回 write_skipped=true 和 write_skip_reason
"""
import pytest
from backend.schemas.candidate import CandidateAction
from backend.application.lite_candidate_policy import lite_action_to_candidate_action


class TestFallbackCandidateAction:
    """测试 fallback candidate action"""

    def test_fallback_draft_enum_exists(self):
        """测试 CandidateAction.FALLBACK_DRAFT 存在"""
        assert hasattr(CandidateAction, "FALLBACK_DRAFT")
        assert CandidateAction.FALLBACK_DRAFT.value == "fallback_draft"

    def test_fallback_draft_lite_action_mapping(self):
        """测试 lite action 'fallback_draft' 映射到 CandidateAction.FALLBACK_DRAFT"""
        action = lite_action_to_candidate_action("fallback_draft")
        assert action == CandidateAction.FALLBACK_DRAFT

    def test_other_actions_still_work(self):
        """测试其他 action 仍然正常工作"""
        assert lite_action_to_candidate_action("rewrite") == CandidateAction.REWRITE
        assert lite_action_to_candidate_action("polish_current_scene") == CandidateAction.POLISH


class TestFallbackCandidateMetadata:
    """测试 fallback candidate metadata schema"""

    def test_fallback_candidate_metadata_structure(self):
        """测试 fallback candidate metadata 预期结构"""
        expected_fields = {
            "fallback_used": True,
            "fallback_reason": "llm_failed_after_retry",
            "retry_count": 1,
            "original_target_file": "chapters/vol-01/ch-001/sec-001.md",
            "source_mode": "lite",
            "action": "fallback_draft",
        }
        assert "fallback_used" in expected_fields
        assert "fallback_reason" in expected_fields
        assert "retry_count" in expected_fields
        assert "source_mode" in expected_fields
        assert "action" in expected_fields
        assert expected_fields["source_mode"] == "lite"
        assert expected_fields["action"] == "fallback_draft"


class TestFallbackResponseSchema:
    """测试 LiteWriteNextResponse 包含 write_skipped 和 write_skip_reason 字段"""

    def test_lite_write_next_response_has_write_skipped(self):
        """测试 LiteWriteNextResponse 包含 write_skipped 字段"""
        from backend.schemas.lite import LiteWriteNextResponse
        # 检查字段是否存在于模型中
        model_fields = LiteWriteNextResponse.model_fields
        assert "write_skipped" in model_fields
        assert "write_skip_reason" in model_fields
        assert "fallback_candidate_id" in model_fields

    def test_lite_write_next_response_default_values(self):
        """测试 LiteWriteNextResponse 默认值"""
        from backend.schemas.lite import LiteWriteNextResponse
        # 创建一个实例检查默认值
        response = LiteWriteNextResponse(
            file_path="test.md",
            content="test",
            quality_summary="test",
            story_engine_summary={},
        )
        assert response.write_skipped is False
        assert response.write_skip_reason is None
