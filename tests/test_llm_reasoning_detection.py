"""测试 LLM reasoning content 检测和清洗功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.llm import _is_reasoning_only_model_response, _clean_reasoning_channel_content


def test_reasoning_patterns():
    """测试常见的推理日志模式检测"""

    # 应该被识别为推理日志的文本
    reasoning_texts = [
        "*   Original phrase: \"雨没有停的意思\"",
        "*   Literal meaning: The rain has no intention of stopping",
        "*   Context: Likely a literary or descriptive",
        "*   Meaning: Something about the rain",
        "*   Strengths: Clear imagery",
        "*   Task: Provide the final output",
        "*   Constraint: Answer in Chinese",
        "*   Option 1: Literal translation",
        "Original phrase: test",
        "Literal meaning: test",
        "Analysis: This is analysis",
        "Task: Do something",
    ]

    for text in reasoning_texts:
        result = _is_reasoning_only_model_response(text)
        print(f"检测推理日志 '{text[:40]}...': {result}")
        assert result is True, f"应该识别为推理日志: {text[:40]}"

    # 不应该被识别为推理日志的文本（正常正文）
    normal_texts = [
        "雨没有停的意思。林澈站在旧港站入口的铁栅前。",
        "这是一个正常的句子，不包含任何分析标记。",
        "今天天气很好，适合出门散步。",
        "用户想要润色这段文字。",
        "我需要完成这个任务。",
    ]

    for text in normal_texts:
        result = _is_reasoning_only_model_response(text)
        print(f"检测正常正文 '{text[:40]}...': {result}")
        assert result is False, f"不应该识别为推理日志: {text[:40]}"

    print("\n✅ 所有测试通过!")


def test_edge_cases():
    """测试边界情况"""

    # 空字符串
    assert _is_reasoning_only_model_response("") is False

    # None
    assert _is_reasoning_only_model_response(None) is False

    print("\n✅ 边界情况测试通过!")


def test_clean_normal_chinese():
    """测试正常中文正文不应该被清洗坏"""
    normal_text = "夜色落在旧城墙上，风从破碎的旗帜间穿过。"
    result = _clean_reasoning_channel_content(normal_text)
    print(f"清洗正常中文 '{normal_text}' → '{result}'")
    assert result == normal_text, "正常中文不应该被改变"


def test_clean_multi_paragraph_chinese():
    """测试多段中文正文，当前实现会保留最后一句符合特征的"""
    multi_text = """夜色落在旧城墙上。
风从破碎的旗帜间穿过。
远处传来隐约的笛声。"""
    result = _clean_reasoning_channel_content(multi_text)
    print(f"清洗多段中文 → '{result}', 长度: {len(result)}")
    # 当前实现会优先找最后一句有足够中文的
    assert "笛声" in result
    assert len(result) >= 8


def test_clean_reasoning_format_none():
    """测试 reasoning_format=none 的混合输出应该提取到正确正文"""
    mixed_text = """<|channel|>thought: Let me analyze this
*   Original: 夜色落在旧城墙上
*   Meaning: Night falls on the old city wall
*   Task: Rewrite it
<|/channel|>
暮色笼罩着古老的城墙，晚风拂过残破的旗幡。"""
    result = _clean_reasoning_channel_content(mixed_text)
    print(f"清洗混合输出 → '{result}'")
    # 应该提取到最后的中文正文
    assert "暮色笼罩" in result or "晚风拂过" in result
    assert "<|channel|>" not in result
    assert "*   Original" not in result


def test_clean_pure_reasoning():
    """测试纯推理日志的处理"""
    pure_reasoning = """*   Original: test
*   Meaning: test meaning
*   Context: test context
*   Strengths: test strengths"""
    result = _clean_reasoning_channel_content(pure_reasoning)
    print(f"清洗纯推理日志 → '{result}'")
    # 可以返回空或原文，但至少不应该崩溃
    assert result is not None


def test_clean_english_text():
    """测试英文正文不应该被误删"""
    english_text = "The night falls on the ancient city walls. The wind passes through the broken flags."
    result = _clean_reasoning_channel_content(english_text)
    print(f"清洗英文正文 → '{result}'")
    # 英文正文应该保留
    assert "night falls" in result.lower()


if __name__ == "__main__":
    test_reasoning_patterns()
    test_edge_cases()
    test_clean_normal_chinese()
    test_clean_multi_paragraph_chinese()
    test_clean_reasoning_format_none()
    test_clean_pure_reasoning()
    test_clean_english_text()
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)
