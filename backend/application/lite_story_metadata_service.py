"""墨韵 - Lite Story Metadata / Memory 读写服务

集中管理 Lite 爽文模式的故事元数据读写逻辑。
"""

from datetime import datetime, timezone
import json
import re
from typing import Any, Optional

from backend.core.file_ops import FileService
from backend.schemas.lite import LiteNextOptionCard


def _compact_line(value: str, limit: int = 90) -> str:
    """压缩文本行，去除多余空格并限制长度"""
    return re.sub(r"\s+", " ", (value or "").strip())[:limit]


class LiteStoryMetadataService:
    """Lite 故事元数据服务"""

    def __init__(self, file_service: FileService):
        self.file_service = file_service

    async def read_optional(self, project_id: str, rel_path: str) -> str:
        """读取可选文件，文件不存在时返回空字符串"""
        try:
            content, _, _ = await self.file_service.read_file(f"{project_id}/{rel_path}")
            return content
        except Exception:
            return ""

    async def read_chapter_context(
        self,
        project_id: str,
        vol: int,
        ch: int,
        current_sec: int,
        sections_per_chapter: int = 5,
    ) -> str:
        """读取当前章中所有已写的前序场景内容，拼接为上下文

        Args:
            project_id: 项目 ID
            vol: 卷号
            ch: 章号
            current_sec: 当前场景号
            sections_per_chapter: 每章场景数

        Returns:
            拼接好的上下文文本
        """
        parts: list[str] = []
        for sec in range(1, min(current_sec, sections_per_chapter + 1)):
            section_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/sec-{sec:03d}.md"
            content = await self.read_optional(project_id, section_path)
            if content and not self.is_blank_chapter(content):
                parts.append(f"--- 第{sec}场景 ---\n{content.strip()}")
        if not parts:
            return ""
        return "\n\n".join(parts) + "\n\n"

    async def read_ch_meta(self, project_id: str, vol: int, ch: int) -> dict[str, Any]:
        """读取章节元数据（ch-meta.json）

        Args:
            project_id: 项目 ID
            vol: 卷号
            ch: 章号

        Returns:
            章节元数据字典，文件不存在或解析失败时返回空字典
        """
        meta_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-meta.json"
        raw = await self.read_optional(project_id, meta_path)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return {}

    async def update_ch_meta(
        self,
        project_id: str,
        vol: int,
        ch: int,
        sec: int,
        card_title: str,
        card_payoff: str,
        card_hook: Optional[str] = None,
    ) -> None:
        """更新章节元数据（记忆和待回收伏笔）

        Args:
            project_id: 项目 ID
            vol: 卷号
            ch: 章号
            sec: 场景号
            card_title: 选卡标题
            card_payoff: 选卡兑现内容
            card_hook: 选卡钩子（可选）
        """
        ch_meta = await self.read_ch_meta(project_id, vol, ch)

        # 章节记忆：按场景累积
        memory = ch_meta.get("memory", [])
        if isinstance(memory, str):
            memory = [] if not memory else [memory]
        memory.append(f"第{sec}场景「{card_title}」：{card_payoff}")
        if len(memory) > 20:
            memory = memory[-20:]
        ch_meta["memory"] = memory

        # 待回收伏笔
        foreshadowing = ch_meta.get("pending_foreshadowing", [])
        if isinstance(foreshadowing, list) and card_hook and card_hook not in foreshadowing:
            foreshadowing.append(card_hook)
            if len(foreshadowing) > 10:
                foreshadowing = foreshadowing[-10:]
        ch_meta["pending_foreshadowing"] = foreshadowing

        meta_path = f"{project_id}/chapters/vol-{vol:02d}/ch-{ch:03d}/ch-meta.json"
        await self.file_service.write_file(meta_path, json.dumps(ch_meta, ensure_ascii=False, indent=2))

    def summarize_story_engine(self, text: str) -> dict[str, str]:
        """从 story-engine.md 中提取关键摘要

        Args:
            text: story-engine.md 内容

        Returns:
            包含各部分摘要的字典
        """

        def section(name: str) -> str:
            pattern = rf"## {re.escape(name)}\n(?P<body>.*?)(?=\n## |\Z)"
            match = re.search(pattern, text, re.S)
            if not match:
                return "待更新"
            line = next((ln.strip("- ").strip() for ln in match.group("body").splitlines() if ln.strip()), "")
            return line or "待更新"

        return {
            "protagonist_goal": section("人物欲望"),
            "current_conflict": section("冲突推进"),
            "foreshadowing": section("前文记忆"),
            "payoff_ledger": section("爽点账本"),
            "reader_expectation": section("读者期待"),
            "stage_goal": section("阶段性目标"),
        }

    def build_story_engine_update(
        self,
        story_engine: str,
        target_file: str,
        selected_card: LiteNextOptionCard,
        content: str,
    ) -> str:
        """构建 story-engine 更新内容

        Args:
            story_engine: 当前 story-engine.md 内容
            target_file: 目标场景文件路径
            selected_card: 选中的爽点卡
            content: 生成的正文内容

        Returns:
            更新后的 story-engine 文本
        """
        excerpt = _compact_line(" ".join(
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ), 140)
        update = "\n".join([
            f"## 最近推进 {datetime.now(timezone.utc).date().isoformat()}",
            f"- 章节：{target_file}",
            f"- 选择：{selected_card.title}",
            f"- 主角想要：{selected_card.protagonist_desire or '继续夺回主动权'}",
            f"- 阻力：{selected_card.obstacle or selected_card.scene}",
            f"- 兑现：{selected_card.payoff}",
            f"- 推进：{selected_card.advancement or '把当前冲突推到下一层'}",
            f"- 钩子：{selected_card.hook}",
            f"- 正文记忆：{excerpt or selected_card.beat}",
        ])
        return story_engine.rstrip() + "\n\n" + update + "\n"

    def is_blank_chapter(self, content: str) -> bool:
        """判断内容是否为空白章节

        Args:
            content: 章节内容

        Returns:
            True 表示空白章节（非标题内容少于 20 字符）
        """
        body_lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
        return len("\n".join(body_lines)) < 20