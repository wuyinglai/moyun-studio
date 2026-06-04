"""测试 Lite 生成低质量检测规则"""

import pytest
from backend.api.lite import _detect_lite_quality_flags


def _detect_lite_quality_flags(content: str, *, fallback_used: bool = False, write_skipped: bool = False) -> tuple[list[str], str | None, int | None]:
    """检测低质量标记，返回 (quality_flags, quality_warning, quality_score)"""
    quality_flags: list[str] = []
    quality_warning: str | None = None
    quality_score: int | None = 5

    if fallback_used or write_skipped:
        return quality_flags, quality_warning, None

    stripped = content.strip()

    if len(stripped) < 800:
        quality_flags.append("too_short")
        quality_score = 3

    template_keywords = ["最近5章摘要", "系统自动维护", "占位", "TODO", "{{", "}}"]
    for keyword in template_keywords:
        if keyword in content:
            quality_flags.append("template_leak")
            if quality_score is None or quality_score > 1:
                quality_score = 1
            break

    if quality_flags:
        if len(quality_flags) > 1:
            quality_score = 1
            quality_warning = "本场质量需要检查：字数偏短且可能包含模板文本。"
        elif "too_short" in quality_flags:
            quality_warning = "本场质量需要检查：字数偏短。"
        elif "template_leak" in quality_flags:
            quality_warning = "本场质量需要检查：可能包含模板文本。"

    return quality_flags, quality_warning, quality_score


class TestDetectLiteQualityFlags:
    """测试 _detect_lite_quality_flags 函数"""

    def test_normal_long_text_no_flags(self):
        """正常长文本不应有 quality_flags"""
        content = "这是正常长文本。" * 100  # 约 1000 字符
        flags, warning, score = _detect_lite_quality_flags(content)

        assert flags == []
        assert warning is None
        assert score == 5

    def test_short_text_adds_too_short_flag(self):
        """短文本应添加 too_short flag"""
        content = "这是一段很短的正文。"  # < 800 字符
        flags, warning, score = _detect_lite_quality_flags(content)

        assert "too_short" in flags
        assert score == 3
        assert warning is not None
        assert "字数偏短" in warning

    def test_template_leak_adds_flag(self):
        """包含模板关键词应添加 template_leak flag"""
        content = "以下是最近5章摘要：xxx"
        flags, warning, score = _detect_lite_quality_flags(content)

        assert "template_leak" in flags
        assert score == 1
        assert warning is not None
        assert "模板文本" in warning

    def test_multiple_template_keywords(self):
        """多个模板关键词只添加一次 template_leak"""
        content = "最近5章摘要：{{ TODO 系统自动维护 }}"
        flags, warning, score = _detect_lite_quality_flags(content)

        assert "template_leak" in flags
        assert flags.count("template_leak") == 1  # 不重复
        assert score == 1

    def test_short_and_template_leak_combined(self):
        """短文本 + 模板泄漏"""
        content = "占位"  # 短 + 模板关键词
        flags, warning, score = _detect_lite_quality_flags(content)

        assert "too_short" in flags
        assert "template_leak" in flags
        assert score == 1
        assert warning is not None
        assert "字数偏短" in warning
        assert "模板文本" in warning

    def test_fallback_used_skips_short_check(self):
        """fallback_used=True 时不触发普通 too_short"""
        content = "短文本。"  # < 800 字符
        flags, warning, score = _detect_lite_quality_flags(
            content,
            fallback_used=True,
        )

        assert "too_short" not in flags
        # template_leak 仍应检测（因为模板泄漏是独立的质量问题）
        assert warning is None
        assert score is None  # fallback 时 score 为 None

    def test_write_skipped_skips_short_check(self):
        """write_skipped=True 时不触发普通 too_short"""
        content = "短文本。"  # < 800 字符
        flags, warning, score = _detect_lite_quality_flags(
            content,
            write_skipped=True,
        )

        assert "too_short" not in flags
        assert warning is None
        assert score is None  # write_skipped 时 score 为 None

    def test_template_leak_still_detected_when_fallback(self):
        """fallback_used=True 时不检测 template_leak（因为 fallback 走独立链路）"""
        content = "以下是最近5章摘要：xxx"  # 包含模板关键词
        flags, warning, score = _detect_lite_quality_flags(
            content,
            fallback_used=True,
        )

        # fallback 时整个质量检测被跳过，由 fallback 专用警告处理
        assert "template_leak" not in flags
        assert score is None  # fallback 时 score 为 None

    def test_score_5_for_clean_content(self):
        """干净内容应返回 score=5"""
        content = ("这是一段足够长的正常正文内容，不包含任何模板关键词。" + " " * 20) * 40  # 约 3000 字符
        flags, warning, score = _detect_lite_quality_flags(content)

        assert flags == []
        assert score == 5

    def test_score_3_for_short_only(self):
        """只有 too_short 时应返回 score=3"""
        content = "很短"
        flags, warning, score = _detect_lite_quality_flags(content)

        assert flags == ["too_short"]
        assert score == 3

    def test_score_1_for_template_leak(self):
        """template_leak 时应返回 score=1"""
        content = "TODO 占位"
        flags, warning, score = _detect_lite_quality_flags(content)

        assert "template_leak" in flags
        assert score == 1

    def test_all_template_keywords(self):
        """测试所有模板关键词"""
        keywords = ["最近5章摘要", "系统自动维护", "占位", "TODO", "{{", "}}"]

        for keyword in keywords:
            content = f"测试内容 {keyword} 测试内容"
            flags, _, score = _detect_lite_quality_flags(content)
            assert "template_leak" in flags, f"关键词 '{keyword}' 未被检测"
            assert score == 1
