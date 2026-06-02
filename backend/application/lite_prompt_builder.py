"""Lite Prompt Builder

集中管理 Lite 模式下向 LLM 发送的 messages / prompt 构造逻辑。
本模块只负责把输入数据组装成 messages 列表，不调用 LLM，不读写文件，不发 SSE。

Phase 3.4B 范围：
- build_chapter_plan_messages: 章规划 LLM prompt
- build_ideas_messages: 开局卡 LLM prompt
- build_next_options_messages: 下一步选项卡 LLM prompt

未迁移范围（与业务流程强耦合，留给后续 Phase）：
- write-section 主正文 prompt（使用 prompt_engine 模板引擎）
- quality repair prompt（依赖 review + 原 content，耦合较深）
"""


class LitePromptBuilder:
    """Build Lite LLM messages for low-risk scenarios."""

    @staticmethod
    def format_preferences(prefs) -> str:
        params = "；".join(f"{k}：{v}" for k, v in prefs.genre_params.items() if v)
        return "\n".join([
            f"- 文风：{prefs.style}",
            f"- 爽点强度：{prefs.intensity}",
            f"- 节奏：{prefs.pace}",
            f"- 主角性格：{prefs.protagonist}",
            f"- 喜欢的元素：{prefs.likes or '未指定'}",
            f"- 不要写的内容：{prefs.dislikes or '未指定'}",
            f"- 题材参数：{params or '未指定'}",
        ])

    @staticmethod
    def build_chapter_plan_messages(
        *,
        vol: int,
        completed_ch: int,
        ch_title: str,
        story_engine: str,
        recent_context: str,
        style_guide: str,
        sections_per_chapter: int,
    ) -> list[dict]:
        """Build messages for the next chapter plan generation."""
        from backend.application.lite_scene_service import chapter_vol_label

        prompt = "\n".join([
            "你是一位擅长规划爽文的编辑。请为下一章写一份章规划（200 字以内）。",
            "",
            f"已完成章节：《{chapter_vol_label(vol, completed_ch)} {ch_title}》",
            "读者期待：",
            story_engine,
            "近期上下文：",
            recent_context,
            "文风指南：",
            style_guide,
            "",
            "章规划格式：",
            "- 章名与核心冲突（一句话）",
            f"- {sections_per_chapter} 个场景梗概（每个场景 1 句，标注谁在什么场景做什么）",
            "- 本章必须兑现的爽点",
            "- 结尾钩子",
        ])
        return [{"role": "user", "content": prompt}]

    @staticmethod
    def build_ideas_messages(
        *,
        genres: list[str],
    ) -> list[dict]:
        """Build messages for AI-generated idea cards."""
        prompt = "\n".join([
            "你是一位网文爆款策划编辑。请为爽文模式设计5张不同的开局卡，每张对应一个题材。",
            "要求：",
            "- 每张卡必须是一个完整的、有冲突张力、有爽点承诺的开局构思。",
            "- 标题要吸睛、有网文感（6-10字）。",
            "- one_liner 是 20 字以内的核心钩子。",
            "- protagonist_hook 突出主角性格+能力。",
            "- core_conflict 必须写出具体压迫方和场景。",
            "- selling_point 列出2-3个爽点关键词。",
            "- 不要和下面兜底卡雷同：退婚觉醒/小捕快禁剑/合约婚姻/师尊护短/鉴宝直播",
            f"题材依次为：{', '.join(genres)}",
            "",
            "只返回 JSON 数组，不要多余文字，格式：",
            """[{"id": "xxx", "title": "...", "genre": "...", "one_liner": "...", "protagonist_hook": "...", "core_conflict": "...", "selling_point": "..."}]""",
        ])
        return [{"role": "user", "content": prompt}]

    @staticmethod
    def build_next_options_messages(
        *,
        next_label: str,
        preferences_text: str,
        context_content: str,
        story_engine: str,
        recent_context: str,
        chapter_plan: str,
    ) -> list[dict]:
        """Build messages for next-scene option cards generation."""
        prompt = "\n".join([
            "你是爽文连载编辑。请基于当前正文和故事状态，为下一场景生成3张不同方向的爽点卡。",
            "不要使用固定模板，不要重复“当众打脸/危机反杀/收获升级”这类泛化标题。",
            "每张卡必须贴合前文已经发生的角色、冲突、伏笔和读者期待。",
            "每张卡必须至少引用一个前文出现的人名、地点、物件、组织、称呼或伏笔。",
            "三张卡方向要明显不同：一张强硬反击，一张反转揭底，一张拿奖励并埋钩子；标题必须根据剧情改写，不要直接写这些模板名。",
            "不要写“围绕某某推进、保持快节奏、标准爽点”这类说明书句式。",
            "只返回 JSON 数组，每项包含 title, conflict_upgrade, protagonist_desire, obstacle, payoff, hook, advancement。",
            "字段含义：conflict_upgrade=冲突升级，protagonist_desire=主角此刻想要什么，obstacle=谁/什么挡住他，payoff=爽点兑现，hook=结尾钩子，advancement=本场景怎样推进故事。",
            "",
            f"下一场景：{next_label}",
            f"偏好：{preferences_text}",
            "当前正文或本章前文：",
            context_content[-2500:],
            "故事引擎：",
            story_engine[-2500:],
            "近期上下文：",
            recent_context[-1500:],
            "章规划：",
            chapter_plan[-1500:],
        ])
        return [{"role": "user", "content": prompt}]
