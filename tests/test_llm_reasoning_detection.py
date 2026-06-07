"""测试 LLM reasoning content 检测功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.core.llm import _is_reasoning_only_model_response


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


if __name__ == "__main__":
    test_reasoning_patterns()
    test_edge_cases()
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)
