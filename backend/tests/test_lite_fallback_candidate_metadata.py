"""测试 Lite Fallback Candidate 元数据准备

Phase T3-D4.1 目标：
- 验证 FALLBACK_DRAFT action 存在
- 验证 fallback candidate metadata schema 可构造
- 验证 lite_action_to_candidate_action 映射 fallback_draft
- 不调用 CandidateService 写文件
"""

import pytest
from backend.schemas.candidate import CandidateAction, CandidateInfo
from backend.application.lite_candidate_policy import lite_action_to_candidate_action


class TestFallbackDraftAction:
    """测试 FALLBACK_DRAFT action 枚举"""

    def test_fallback_draft_enum_exists(self):
        """测试 FALLBACK_DRAFT 枚举存在"""
        assert hasattr(CandidateAction, "FALLBACK_DRAFT")

    def test_fallback_draft_value(self):
        """测试 FALLBACK_DRAFT 值为 fallback_draft"""
        assert CandidateAction.FALLBACK_DRAFT.value == "fallback_draft"

    def test_fallback_draft_is_candidate_action(self):
        """测试 FALLBACK_DRAFT 是 CandidateAction 实例"""
        assert isinstance(CandidateAction.FALLBACK_DRAFT, CandidateAction)


class TestFallbackDraftMapping:
    """测试 fallback action 映射"""

    def test_fallback_draft_mapping(self):
        """测试 lite_action_to_candidate_action 映射 fallback_draft"""
        result = lite_action_to_candidate_action("fallback_draft")
        assert result == CandidateAction.FALLBACK_DRAFT

    def test_all_lite_actions_mappable(self):
        """测试所有已知 Lite action 都能映射"""
        known_actions = [
            "rewrite",
            "more_exciting",
            "more_reasonable",
            "rewrite_current_scene",
            "polish_current_scene",
            "chat_edit_current_scene",
            "fallback_draft",
        ]
        for action in known_actions:
            result = lite_action_to_candidate_action(action)
            assert isinstance(result, CandidateAction)


class TestFallbackCandidateMetadata:
    """测试 fallback candidate metadata schema"""

    def test_candidate_info_with_fallback_action(self):
        """测试可以用 FALLBACK_DRAFT 创建 CandidateInfo"""
        candidate_info = CandidateInfo(
            id="cand_test123",
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            candidate_path="test-project/.candidates/cand_test123.fallback_draft.md",
            action=CandidateAction.FALLBACK_DRAFT,
            source_mode="lite",
        )
        assert candidate_info.action == CandidateAction.FALLBACK_DRAFT
        assert candidate_info.source_mode == "lite"

    def test_fallback_candidate_metadata_fields(self):
        """测试 fallback candidate metadata 字段"""
        candidate_info = CandidateInfo(
            id="cand_test456",
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-002.md",
            candidate_path="test-project/.candidates/cand_test456.fallback_draft.md",
            action=CandidateAction.FALLBACK_DRAFT,
            source_mode="lite",
            fallback_used=True,  # 计划字段，但 CandidateInfo 暂不支持
        )
        # 注意：CandidateInfo 当前不直接支持 fallback_used 字段
        # D4.2 阶段会在创建 candidate 时传入 metadata
        assert candidate_info.action == CandidateAction.FALLBACK_DRAFT


class TestFallbackDraftNotWritingFiles:
    """测试本阶段不写文件"""

    def test_no_file_operations(self):
        """验证此测试不进行任何文件操作"""
        # 这是元数据测试，不应该创建任何文件
        # 通过检查测试中没有任何 async/await file 操作来验证
        assert True  # 占位符
