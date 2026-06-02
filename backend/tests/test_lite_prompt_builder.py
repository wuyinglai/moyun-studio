"""Tests for LitePromptBuilder service.

Phase 3.4B 范围：验证 prompt builder 输出的 messages 结构与原逻辑等价。
"""


from backend.application.lite_prompt_builder import LitePromptBuilder


class TestLitePromptBuilder:
    """测试 LitePromptBuilder 类"""

    class TestBuildChapterPlanMessages:
        """测试 build_chapter_plan_messages 方法"""

        def test_returns_user_role_message(self):
            """返回 user role 消息"""
            messages = LitePromptBuilder.build_chapter_plan_messages(
                vol=1,
                completed_ch=1,
                ch_title="测试章节",
                story_engine="引擎内容",
                recent_context="上下文",
                style_guide="文风",
                sections_per_chapter=5,
            )
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert "content" in messages[0]

        def test_contains_sections_per_chapter_dynamically(self):
            """动态包含 sections_per_chapter，不硬编码"""
            messages = LitePromptBuilder.build_chapter_plan_messages(
                vol=1,
                completed_ch=1,
                ch_title="测试章节",
                story_engine="引擎内容",
                recent_context="上下文",
                style_guide="文风",
                sections_per_chapter=5,
            )
            content = messages[0]["content"]
            assert "5 个场景梗概" in content

        def test_sections_per_chapter_can_change(self):
            """sections_per_chapter 可变（防止硬编码）"""
            messages = LitePromptBuilder.build_chapter_plan_messages(
                vol=1,
                completed_ch=1,
                ch_title="测试章节",
                story_engine="引擎内容",
                recent_context="上下文",
                style_guide="文风",
                sections_per_chapter=7,
            )
            content = messages[0]["content"]
            assert "7 个场景梗概" in content

        def test_contains_story_engine(self):
            """包含 story_engine 内容"""
            messages = LitePromptBuilder.build_chapter_plan_messages(
                vol=1,
                completed_ch=1,
                ch_title="测试章节",
                story_engine="特殊引擎标识XYZ",
                recent_context="上下文",
                style_guide="文风",
                sections_per_chapter=5,
            )
            content = messages[0]["content"]
            assert "特殊引擎标识XYZ" in content

        def test_contains_recent_context_and_style_guide(self):
            """包含近期上下文和文风指南"""
            messages = LitePromptBuilder.build_chapter_plan_messages(
                vol=1,
                completed_ch=1,
                ch_title="测试章节",
                story_engine="引擎",
                recent_context="近期内容ABC",
                style_guide="文风DEF",
                sections_per_chapter=5,
            )
            content = messages[0]["content"]
            assert "近期内容ABC" in content
            assert "文风DEF" in content

        def test_contains_chapter_vol_label(self):
            """包含章节标签"""
            messages = LitePromptBuilder.build_chapter_plan_messages(
                vol=1,
                completed_ch=1,
                ch_title="我的章节",
                story_engine="引擎",
                recent_context="上下文",
                style_guide="文风",
                sections_per_chapter=5,
            )
            content = messages[0]["content"]
            assert "我的章节" in content

    class TestBuildIdeasMessages:
        """测试 build_ideas_messages 方法"""

        def test_returns_user_role_message(self):
            """返回 user role 消息"""
            messages = LitePromptBuilder.build_ideas_messages(
                genres=["玄幻", "武侠"],
            )
            assert len(messages) == 1
            assert messages[0]["role"] == "user"

        def test_contains_genres(self):
            """包含所有 genre"""
            messages = LitePromptBuilder.build_ideas_messages(
                genres=["玄幻", "武侠", "言情"],
            )
            content = messages[0]["content"]
            assert "玄幻" in content
            assert "武侠" in content
            assert "言情" in content

        def test_contains_required_fields(self):
            """包含必要字段说明"""
            messages = LitePromptBuilder.build_ideas_messages(
                genres=["玄幻"],
            )
            content = messages[0]["content"]
            assert "title" in content
            assert "genre" in content
            assert "one_liner" in content
            assert "protagonist_hook" in content
            assert "core_conflict" in content
            assert "selling_point" in content

        def test_contains_fallback_avoidance(self):
            """包含避免兜底卡的说明"""
            messages = LitePromptBuilder.build_ideas_messages(
                genres=["玄幻"],
            )
            content = messages[0]["content"]
            assert "退婚觉醒" in content
            assert "小捕快禁剑" in content

    class TestBuildNextOptionsMessages:
        """测试 build_next_options_messages 方法"""

        def test_returns_user_role_message(self):
            """返回 user role 消息"""
            messages = LitePromptBuilder.build_next_options_messages(
                next_label="第1场景",
                preferences_text="偏好",
                context_content="当前正文",
                story_engine="引擎",
                recent_context="上下文",
                chapter_plan="章规划",
            )
            assert len(messages) == 1
            assert messages[0]["role"] == "user"

        def test_contains_next_label(self):
            """包含下一场景标签"""
            messages = LitePromptBuilder.build_next_options_messages(
                next_label="第3场景",
                preferences_text="偏好",
                context_content="当前正文",
                story_engine="引擎",
                recent_context="上下文",
                chapter_plan="章规划",
            )
            content = messages[0]["content"]
            assert "第3场景" in content

        def test_contains_preferences_text(self):
            """包含偏好"""
            messages = LitePromptBuilder.build_next_options_messages(
                next_label="第1场景",
                preferences_text="特殊偏好ABC",
                context_content="当前正文",
                story_engine="引擎",
                recent_context="上下文",
                chapter_plan="章规划",
            )
            content = messages[0]["content"]
            assert "特殊偏好ABC" in content

        def test_contains_story_engine_and_recent_context(self):
            """包含故事引擎和近期上下文"""
            messages = LitePromptBuilder.build_next_options_messages(
                next_label="第1场景",
                preferences_text="偏好",
                context_content="当前正文",
                story_engine="故事引擎XYZ",
                recent_context="近期上下文ABC",
                chapter_plan="章规划",
            )
            content = messages[0]["content"]
            assert "故事引擎XYZ" in content
            assert "近期上下文ABC" in content

        def test_contains_chapter_plan(self):
            """包含章规划"""
            messages = LitePromptBuilder.build_next_options_messages(
                next_label="第1场景",
                preferences_text="偏好",
                context_content="当前正文",
                story_engine="引擎",
                recent_context="上下文",
                chapter_plan="章规划内容XYZ",
            )
            content = messages[0]["content"]
            assert "章规划内容XYZ" in content

        def test_contains_required_card_fields(self):
            """包含 cards 字段说明"""
            messages = LitePromptBuilder.build_next_options_messages(
                next_label="第1场景",
                preferences_text="偏好",
                context_content="当前正文",
                story_engine="引擎",
                recent_context="上下文",
                chapter_plan="章规划",
            )
            content = messages[0]["content"]
            assert "title" in content
            assert "conflict_upgrade" in content
            assert "protagonist_desire" in content
            assert "obstacle" in content
            assert "payoff" in content
            assert "hook" in content
            assert "advancement" in content

        def test_truncates_long_content(self):
            """长内容被截断（context_content 后 2500 字符，recent_context 后 1500 字符）"""
            long_context = "X" * 5000
            long_recent = "Y" * 3000
            messages = LitePromptBuilder.build_next_options_messages(
                next_label="第1场景",
                preferences_text="偏好",
                context_content=long_context,
                story_engine="引擎",
                recent_context=long_recent,
                chapter_plan="章规划",
            )
            content = messages[0]["content"]
            # context_content[-2500:] 应包含最后 2500 个 X，不应包含前 2500 个
            assert content.count("X") == 2500
            # recent_context[-1500:] 应包含最后 1500 个 Y
            assert content.count("Y") == 1500
