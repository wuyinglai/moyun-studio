"""Tests for LiteQualityService.

Phase 3.4C 范围：验证 quality 判断逻辑与原逻辑等价。
"""


from unittest.mock import MagicMock

from backend.application.lite_quality_service import LiteQualityService


class TestLiteQualityService:
    """测试 LiteQualityService 类"""

    class TestQualityOneLine:
        """测试 quality_one_line 方法"""

        def test_returns_summary_first_line(self):
            """返回摘要的第一行（最多80字符）"""
            result = LiteQualityService.quality_one_line("这是第一行\n这是第二行", "continue")
            assert result == "这是第一行"

        def test_truncates_long_summary(self):
            """长摘要被截断到80字符"""
            long_summary = "A" * 100
            result = LiteQualityService.quality_one_line(long_summary, "continue")
            assert len(result) == 80

        def test_returns_continue_action_text(self):
            """空摘要 + continue action 返回特定文本"""
            result = LiteQualityService.quality_one_line("", "continue")
            assert result == "已续写草稿，并更新故事状态。"

        def test_returns_more_exciting_action_text(self):
            """空摘要 + more_exciting action 返回特定文本"""
            result = LiteQualityService.quality_one_line("", "more_exciting")
            assert result == "已增强冲突、爽点和结尾钩子。"

        def test_returns_more_reasonable_action_text(self):
            """空摘要 + more_reasonable action 返回特定文本"""
            result = LiteQualityService.quality_one_line("", "more_reasonable")
            assert result == "已补充人物动机和前文衔接。"

        def test_returns_default_text_for_unknown_action(self):
            """空摘要 + 未知 action 返回默认文本"""
            result = LiteQualityService.quality_one_line("", "unknown_action")
            assert result == "已完成质量审查，并更新故事状态。"

    class TestNeedsQualityRepair:
        """测试 needs_quality_repair 方法"""

        def test_returns_false_for_none_review(self):
            """None review 返回 False"""
            result = LiteQualityService.needs_quality_repair(None)
            assert result is False

        def test_returns_false_for_empty_review(self):
            """空 review 返回 False"""
            review = MagicMock()
            review.scores = None
            review.issues = []
            result = LiteQualityService.needs_quality_repair(review)
            assert result is False

        def test_returns_false_for_high_score(self):
            """高分返回 False"""
            review = MagicMock()
            review.scores = MagicMock()
            review.scores.model_dump.return_value = {"grammar": 8, "style": 9, "logic": 7}
            review.issues = []
            result = LiteQualityService.needs_quality_repair(review)
            assert result is False

        def test_returns_true_for_low_average_score(self):
            """平均分低于6返回 True"""
            review = MagicMock()
            review.scores = MagicMock()
            review.scores.model_dump.return_value = {"grammar": 3, "style": 4, "logic": 5}
            review.issues = []
            result = LiteQualityService.needs_quality_repair(review)
            assert result is True

        def test_returns_true_for_critical_issue(self):
            """critical 级别的 issue 返回 True"""
            issue = MagicMock()
            issue.severity = "critical"
            review = MagicMock()
            review.scores = MagicMock()
            review.scores.model_dump.return_value = {"grammar": 8, "style": 9}
            review.issues = [issue]
            result = LiteQualityService.needs_quality_repair(review)
            assert result is True

        def test_returns_true_for_major_issue(self):
            """major 级别的 issue 返回 True"""
            issue = MagicMock()
            issue.severity = "major"
            review = MagicMock()
            review.scores = MagicMock()
            review.scores.model_dump.return_value = {"grammar": 8, "style": 9}
            review.issues = [issue]
            result = LiteQualityService.needs_quality_repair(review)
            assert result is True

        def test_returns_false_for_minor_issue(self):
            """minor 级别的 issue 不触发 repair"""
            issue = MagicMock()
            issue.severity = "minor"
            review = MagicMock()
            review.scores = MagicMock()
            review.scores.model_dump.return_value = {"grammar": 8, "style": 9}
            review.issues = [issue]
            result = LiteQualityService.needs_quality_repair(review)
            assert result is False

        def test_returns_false_for_empty_scores(self):
            """空 scores 返回 False（默认平均分10）"""
            review = MagicMock()
            review.scores = MagicMock()
            review.scores.model_dump.return_value = {}
            review.issues = []
            result = LiteQualityService.needs_quality_repair(review)
            assert result is False
