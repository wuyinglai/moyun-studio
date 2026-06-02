"""Tests for Lite Candidate Policy.

Phase 3.4E 范围：验证 lite_action_to_candidate_action 函数
与原 _lite_action_to_candidate_action 行为完全一致。
"""

import pytest

from backend.application.lite_candidate_policy import lite_action_to_candidate_action
from backend.schemas.candidate import CandidateAction


class TestLiteActionToCandidateAction:
    """测试 lite_action_to_candidate_action 映射函数"""

    def test_lite_action_to_candidate_action_rewrite(self):
        """rewrite 映射为 REWRITE"""
        assert lite_action_to_candidate_action("rewrite") == CandidateAction.REWRITE

    def test_lite_action_to_candidate_action_polish(self):
        """polish_current_scene 映射为 POLISH"""
        assert lite_action_to_candidate_action("polish_current_scene") == CandidateAction.POLISH

    def test_lite_action_to_candidate_action_more_exciting(self):
        """more_exciting 映射为 REWRITE"""
        assert lite_action_to_candidate_action("more_exciting") == CandidateAction.REWRITE

    def test_lite_action_to_candidate_action_more_reasonable(self):
        """more_reasonable 映射为 REWRITE"""
        assert lite_action_to_candidate_action("more_reasonable") == CandidateAction.REWRITE

    def test_lite_action_to_candidate_action_unknown_fallback(self):
        """未知 action fallback 为 REWRITE"""
        assert lite_action_to_candidate_action("write_next_scene") == CandidateAction.REWRITE
        assert lite_action_to_candidate_action("unknown_action") == CandidateAction.REWRITE
        assert lite_action_to_candidate_action("") == CandidateAction.REWRITE
        assert lite_action_to_candidate_action("chat_edit") == CandidateAction.REWRITE


class TestLiteActionToCandidateActionExtended:
    """扩展测试，覆盖完整映射表"""

    def test_rewrite_current_scene_maps_to_rewrite(self):
        """rewrite_current_scene 映射为 REWRITE"""
        assert lite_action_to_candidate_action("rewrite_current_scene") == CandidateAction.REWRITE

    def test_chat_edit_current_scene_maps_to_chat(self):
        """chat_edit_current_scene 映射为 CHAT"""
        assert lite_action_to_candidate_action("chat_edit_current_scene") == CandidateAction.CHAT

    def test_all_known_actions_have_valid_mapping(self):
        """所有已知 action 必须映射到合法 CandidateAction"""
        known_actions = [
            "rewrite",
            "more_exciting",
            "more_reasonable",
            "rewrite_current_scene",
            "polish_current_scene",
            "chat_edit_current_scene",
        ]
        for action in known_actions:
            result = lite_action_to_candidate_action(action)
            assert isinstance(result, CandidateAction)
            assert result in {
                CandidateAction.REWRITE,
                CandidateAction.POLISH,
                CandidateAction.CHAT,
            }
