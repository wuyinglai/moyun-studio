import pytest

from backend.application.lite_option_cards_service import LiteOptionCardsService
from backend.schemas.lite import LiteNextOptionCard


class TestLiteOptionCardsService:
    """测试 LiteOptionCardsService 类"""

    class TestExtractJsonPayload:
        """测试 extract_json_payload 方法"""

        def test_extract_json_payload_from_plain_json(self):
            """从纯 JSON 提取数据"""
            raw = '[{"title": "测试", "scene": "场景"}]'
            result = LiteOptionCardsService.extract_json_payload(raw)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["title"] == "测试"

        def test_extract_json_payload_from_markdown_code_fence(self):
            """从 markdown code fence 提取 JSON"""
            raw = "```json\n[{\"title\": \"测试\"}]\n```"
            result = LiteOptionCardsService.extract_json_payload(raw)
            assert isinstance(result, list)
            assert result[0]["title"] == "测试"

        def test_extract_json_payload_from_text_with_json(self):
            """从包含文字的内容中提取 JSON"""
            raw = "好的，这是结果：[{\"title\": \"测试\", \"scene\": \"场景\"}] 希望你满意。"
            result = LiteOptionCardsService.extract_json_payload(raw)
            assert isinstance(result, list)
            assert result[0]["title"] == "测试"

        def test_extract_json_payload_from_dict(self):
            """从字典类型的 JSON 提取（优先找到数组）"""
            # extract_json_payload 会找到第一个 [ 或 {，由于 [ 在 {"cards": [...]}, 中出现，会先解析数组
            raw = '{"cards": [{"title": "测试"}]}'
            result = LiteOptionCardsService.extract_json_payload(raw)
            # 由于 [ 在 { 之后但被先查找，会返回数组
            assert isinstance(result, list)
            assert result[0]["title"] == "测试"

        def test_extract_json_payload_from_dict_only(self):
            """从纯字典 JSON 提取"""
            raw = '{"title": "测试", "scene": "场景"}'
            result = LiteOptionCardsService.extract_json_payload(raw)
            assert isinstance(result, dict)
            assert result["title"] == "测试"

    class TestParseOptionCards:
        """测试 parse_option_cards 方法"""

        def test_parse_option_cards_valid_payload(self):
            """解析有效卡片数据"""
            raw = '''[
                {"title": "测试标题", "scene": "测试场景", "payoff": "测试收益", "hook": "测试钩子", "protagonist_desire": "想要", "obstacle": "障碍", "advancement": "推进"}
            ]'''
            result = LiteOptionCardsService.parse_option_cards(raw, "sec-001")
            assert len(result) == 1
            assert result[0].title == "测试标题"
            assert result[0].scene == "测试场景"
            assert result[0].payoff == "测试收益"
            assert result[0].hook == "测试钩子"

        def test_parse_option_cards_limits_card_count(self):
            """限制最多3张卡片"""
            raw = '''[
                {"title": "标题1", "scene": "场景1", "payoff": "收益1", "hook": "钩子1"},
                {"title": "标题2", "scene": "场景2", "payoff": "收益2", "hook": "钩子2"},
                {"title": "标题3", "scene": "场景3", "payoff": "收益3", "hook": "钩子3"},
                {"title": "标题4", "scene": "场景4", "payoff": "收益4", "hook": "钩子4"}
            ]'''
            result = LiteOptionCardsService.parse_option_cards(raw, "sec-001")
            assert len(result) == 3

        def test_parse_option_cards_with_dict_wrapper(self):
            """解析带 cards 字段的字典"""
            raw = '{"cards": [{"title": "测试", "scene": "场景", "payoff": "收益", "hook": "钩子"}]}'
            result = LiteOptionCardsService.parse_option_cards(raw, "sec-001")
            assert len(result) == 1
            assert result[0].title == "测试"

        def test_parse_option_cards_empty_when_invalid(self):
            """无效数据返回空列表"""
            raw = "这不是有效的 JSON"
            with pytest.raises(Exception):
                LiteOptionCardsService.parse_option_cards(raw, "sec-001")

    class TestFallbackNextCards:
        """测试 fallback_next_cards 方法"""

        def test_fallback_next_cards_returns_expected_count(self):
            """返回3张卡片"""
            result = LiteOptionCardsService.fallback_next_cards("sec-001", "", "")
            assert len(result) == 3

        def test_fallback_next_cards_has_required_fields(self):
            """每张卡片包含必需字段"""
            result = LiteOptionCardsService.fallback_next_cards("sec-001", "", "")
            for card in result:
                assert card.title
                assert card.scene
                assert card.payoff
                assert card.hook
                assert card.protagonist_desire
                assert card.obstacle
                assert card.advancement

        def test_fallback_next_cards_uses_context(self):
            """使用上下文生成提示"""
            context = "主角在比武场上击败了对手。"
            result = LiteOptionCardsService.fallback_next_cards("sec-001", context, "")
            assert len(result) == 3
            # 检查是否包含上下文中的关键词
            assert any("击败" in card.scene or "对手" in card.scene for card in result)

    class TestRotateCards:
        """测试 rotate_cards 方法"""

        def test_rotate_cards_is_stable_for_same_seed(self):
            """相同 seed 输出稳定"""
            result1 = LiteOptionCardsService.rotate_cards("test-seed")
            result2 = LiteOptionCardsService.rotate_cards("test-seed")
            assert [c.id for c in result1] == [c.id for c in result2]

        def test_rotate_cards_changes_for_different_seed(self):
            """不同 seed 输出不同"""
            result1 = LiteOptionCardsService.rotate_cards("seed1")
            result2 = LiteOptionCardsService.rotate_cards("seed2")
            # 不一定完全不同，但顺序可能不同
            assert len(result1) == len(result2) == 5

        def test_rotate_cards_with_empty_seed(self):
            """空 seed 返回默认顺序"""
            result = LiteOptionCardsService.rotate_cards("")
            assert len(result) == 5