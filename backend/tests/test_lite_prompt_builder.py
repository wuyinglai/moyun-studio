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

    class TestFormatPreferences:
        """测试 format_preferences 方法（Phase 3.4E 迁移自 _prefs_to_text）"""

        def test_format_preferences_empty(self):
            """空 genre_params 时输出完整 7 行结构"""
            from backend.schemas.lite import LiteWritingPrefs

            prefs = LiteWritingPrefs()
            result = LitePromptBuilder.format_preferences(prefs)

            lines = result.split("\n")
            assert len(lines) == 7
            assert lines[0] == "- 文风：热血"
            assert lines[1] == "- 爽点强度：标准"
            assert lines[2] == "- 节奏：快节奏"
            assert lines[3] == "- 主角性格：张扬"
            assert lines[4] == "- 喜欢的元素：未指定"
            assert lines[5] == "- 不要写的内容：未指定"
            assert lines[6] == "- 题材参数：未指定"

        def test_format_preferences_full_values(self):
            """所有字段都有值时正确格式化"""
            from backend.schemas.lite import LiteWritingPrefs

            prefs = LiteWritingPrefs(
                style="冷峻",
                intensity="高强度",
                pace="稳扎稳打",
                protagonist="隐忍",
                likes="反转",
                dislikes="降智",
                genre_params={"修为": "筑基", "境界": "金丹"},
            )
            result = LitePromptBuilder.format_preferences(prefs)

            lines = result.split("\n")
            assert len(lines) == 7
            assert lines[0] == "- 文风：冷峻"
            assert lines[1] == "- 爽点强度：高强度"
            assert lines[2] == "- 节奏：稳扎稳打"
            assert lines[3] == "- 主角性格：隐忍"
            assert lines[4] == "- 喜欢的元素：反转"
            assert lines[5] == "- 不要写的内容：降智"
            assert "修为：筑基" in lines[6]
            assert "境界：金丹" in lines[6]
            assert "；" in lines[6]
            assert lines[6].startswith("- 题材参数：")

        def test_format_preferences_preserves_original_format(self):
            """完全等价于原 _prefs_to_text 行为（含换行/字段顺序/空值处理）"""
            from backend.schemas.lite import LiteWritingPrefs

            prefs = LiteWritingPrefs(
                style="热血",
                intensity="标准",
                pace="快节奏",
                protagonist="张扬",
                likes="升级打脸",
                dislikes="圣母",
                genre_params={"流派": "玄幻", "体系": "修真"},
            )
            expected = "\n".join([
                "- 文风：热血",
                "- 爽点强度：标准",
                "- 节奏：快节奏",
                "- 主角性格：张扬",
                "- 喜欢的元素：升级打脸",
                "- 不要写的内容：圣母",
                "- 题材参数：流派：玄幻；体系：修真",
            ])
            result = LitePromptBuilder.format_preferences(prefs)
            assert result == expected

        def test_format_preferences_filters_empty_genre_params(self):
            """空字符串值的 genre_params 不应出现在结果中"""
            from backend.schemas.lite import LiteWritingPrefs

            prefs = LiteWritingPrefs(
                style="热血",
                genre_params={"流派": "玄幻", "空字段": "", "体系": "修真"},
            )
            result = LitePromptBuilder.format_preferences(prefs)

            assert "流派：玄幻" in result
            assert "体系：修真" in result
            assert "空字段" not in result

        def test_format_preferences_empty_genre_dict(self):
            """空 dict 时显示 未指定"""
            from backend.schemas.lite import LiteWritingPrefs

            prefs = LiteWritingPrefs(genre_params={})
            result = LitePromptBuilder.format_preferences(prefs)
            assert "- 题材参数：未指定" in result
