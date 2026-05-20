"""墨韵 - 场景记忆与故事状态服务

职责：
- recent-context.md：短期场景记忆（最近 N 个场景摘要）
- story-state.md：长期故事状态（仅全局重大变化）

不处理：候选稿、管线编排、LLM 调用。
"""

import logging
import re
from datetime import datetime

from backend.config import get_settings
from backend.core.file_ops import FileService

logger = logging.getLogger(__name__)


class MemoryService:
    """场景记忆与故事状态服务"""

    def __init__(self, file_service: FileService):
        self._fs = file_service

    # ─── recent-context（短期场景记忆）────────────────────

    async def append_scene_memory(
        self,
        project_id: str,
        scene_path: str,
        memory_text: str,
    ) -> None:
        """追加场景记忆到 recent-context.md

        保留最近 settings.recent_context_scene_limit 个场景记忆（默认 15）。

        Args:
            project_id: 项目 ID
            scene_path: 场景文件路径（如 chapters/vol-01/ch-001/sec-003.md）
            memory_text: 结构化摘要文本
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            file_name = scene_path.split("/")[-1]
            entry = f"\n## {timestamp} - {file_name}\n{memory_text}\n"

            try:
                content, _, _ = await self._fs.read_file(f"{project_id}/recent-context.md")
                blocks = [b for b in content.split("\n## ") if b.strip()]
                max_scenes = get_settings().recent_context_scene_limit
                blocks = blocks[-max_scenes:]
                new_content = "\n## ".join(blocks).strip()
                if not new_content.startswith("# "):
                    new_content = "# 近期上下文\n" + new_content
                new_content += entry
            except Exception:
                new_content = f"# 近期上下文\n{entry}"

            await self._fs.write_file(f"{project_id}/recent-context.md", new_content, None)
        except Exception as e:
            logger.warning("更新 recent-context.md 失败: %s", e)

    async def read_recent_context(self, project_id: str) -> str:
        """读取 recent-context.md 内容"""
        try:
            content, _, _ = await self._fs.read_file(f"{project_id}/recent-context.md")
            return content
        except Exception:
            return ""

    # ─── story-state（长期故事状态）────────────────────────

    async def read_story_state(self, project_id: str) -> str:
        """读取 story-state.md 内容"""
        try:
            content, _, _ = await self._fs.read_file(f"{project_id}/story-state.md")
            return content
        except Exception:
            return ""

    def build_scene_memory_prompt_output(
        self,
        target_file: str,
        content: str,
    ) -> str:
        """根据场景内容生成结构化摘要文本

        如果已有结构化文本，直接保存。不调用 LLM。

        Args:
            target_file: 场景文件路径
            content: 场景正文内容

        Returns:
            结构化摘要文本
        """
        lines = content.strip().split('\n')[:20]
        text_preview = '\n'.join(lines)

        chars = self._extract_characters(content)
        locations = self._extract_locations(content)

        summary = []

        # 场景摘要
        summary.append("【场景摘要】")
        summary.append(text_preview[:200].strip() + "..." if len(text_preview) > 200 else text_preview)

        # 人物
        if chars:
            summary.append("\n【人物】")
            summary.append(", ".join(chars[:5]))

        # 地点
        if locations:
            summary.append("\n【地点】")
            summary.append(", ".join(locations[:3]))

        # 下一场承接点（取最后几句）
        last_lines = content.strip().split('\n')[-3:]
        last_text = '\n'.join(last_lines).strip()
        if last_text:
            summary.append("\n【承接点】")
            summary.append(last_text[:100].strip())

        return '\n'.join(summary)

    def suggest_story_state_update(
        self,
        project_id: str,
        scene_memory: str,
    ) -> str:
        """根据场景记忆建议 story-state 更新内容

        当前为占位逻辑：仅返回建议文本，不自动写入。
        不把普通场景细节写入 story-state。
        """
        # 占位：仅当场景记忆中包含重大转折关键词时返回建议
        major_keywords = ["突破", "觉醒", "背叛", "死亡", "复活", "登基", "灭门", "结盟", "开战"]
        suggestions = [kw for kw in major_keywords if kw in scene_memory]
        if suggestions:
            return f"检测到重大变化关键词：{'、'.join(suggestions)}，建议更新故事状态。"
        return ""

    async def update_story_state(
        self,
        project_id: str,
        update_text: str,
    ) -> None:
        """更新 story-state.md，只写全局重大变化

        Args:
            project_id: 项目 ID
            update_text: 更新内容文本
        """
        try:
            existing = await self.read_story_state(project_id)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n## 更新于 {timestamp}\n{update_text}\n"
            new_content = (existing + entry) if existing else f"# 故事状态\n{entry}"
            await self._fs.write_file(f"{project_id}/story-state.md", new_content, None)
        except Exception as e:
            logger.warning("更新 story-state.md 失败: %s", e)

    # ─── 内部工具 ──────────────────────────────────────────

    @staticmethod
    def _extract_characters(content: str) -> list[str]:
        """简单提取人物名称（基于中文姓名模式和常见角色特征）"""
        chars = []
        name_pattern = re.compile(r'([\u4e00-\u9fa5]{2,4})(?=[：:，,。！!？?、])')
        matches = name_pattern.findall(content)
        chars.extend(matches)

        title_pattern = re.compile(r'(先生|小姐|夫人|公子|大侠|掌门|帮主|陛下|殿下|将军|丞相)\s*([\u4e00-\u9fa5]{1,4})')
        for match in title_pattern.findall(content):
            chars.append(f"{match[0]}{match[1]}")

        seen = set()
        unique = []
        for c in chars:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique[:10]

    @staticmethod
    def _extract_locations(content: str) -> list[str]:
        """简单提取地点名称"""
        location_pattern = re.compile(r'([\u4e00-\u9fa5]{2,6})(殿|阁|楼|院|城|山|谷|岛|宫|府|庄|寺|塔|洞|营|关|塞|境|域|界)')
        matches = location_pattern.findall(content)
        seen = set()
        unique = []
        for name, suffix in matches:
            full = f"{name}{suffix}"
            if full not in seen:
                seen.add(full)
                unique.append(full)
        return unique[:5]
