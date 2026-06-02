"""墨韵 - Lite 项目服务

负责 Lite 爽文模式的项目创建和初始化逻辑。
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import uuid

from backend.config import Settings, get_settings
from backend.core.project_service import ProjectService
from backend.schemas.lite import LiteIdeaCard, LiteProjectCreateRequest, LiteProjectCreateResponse
from backend.schemas.project import ProjectCreateRequest
from backend.schemas.common import ApiResponse


SECTIONS_PER_CHAPTER = 5


def prefs_to_text(prefs) -> str:
    """将项目偏好转换为文风指南文本"""
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


def story_engine_template(card: LiteIdeaCard, prefs_text: str) -> str:
    """生成故事引擎模板内容"""
    return f"""# 故事引擎

## 人物欲望
- 当前目标：主角要从"{card.protagonist_hook}"出发，证明自己并拿到第一份真实收益。
- 长期目标：摆脱被动命运，获得足以改变处境的力量、身份或关系。
- 底层执念：不再被轻慢、误解或安排，必须亲手夺回选择权。

## 冲突推进
- 明面冲突：{card.core_conflict}
- 隐藏冲突：既得利益者不愿主角翻身，旁观者的态度会随战果变化。
- 下一步压力：把质疑和代价摆到台面上，让主角必须当场回应。

## 场景直觉
- 下一场景：选择能让人物正面碰撞、旁观者足够多、反馈足够快的场合。
- 可碰撞人物：主角、直接羞辱者、旁观势力、潜在盟友或更高层对手。
- 场景原则：每个场景都要有明确行动、即时反馈、结尾钩子。

## 爽点账本
- 已承诺爽点：{card.selling_point}
- 待兑现爽点：反击、成长、奖励、身份变化或关系反转。
- 正在铺垫：第一次漂亮反击之后，引出更高层级冲突。

## 伏笔账本
- 已埋伏笔：{card.one_liner}
- 待回收伏笔：主角能力来源、对手后台、关键奖励的真实价值。
- 已回收伏笔：暂无。

## 前文记忆
- 开局方向：{card.one_liner}
- 主角钩子：{card.protagonist_hook}
- 最近事件：尚未开始正文。

## 读者期待
- 期待兑现：主角不能空喊，要用行动拿到可见收益。
- 期待节奏：先压迫，再反击，再给奖励或新威胁。
- 期待边界：爽但不乱，胜利要有可感知的代价、证据或能力支撑。

## 阶段性目标
- 当前 5-10 个场景目标：完成开局压迫到第一次漂亮反击，并抬出更高层级冲突。
- 完成标志：主角得到明确收益，旧秩序第一次松动。
- 下一章规划触发：每完成 4 个场景，整理下一章 4 个场景方向。

## 用户口味
{prefs_text}
"""


async def write_json(path: Path, data: dict) -> None:
    """异步写入 JSON 文件"""
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, __import__("json").dumps(data, ensure_ascii=False, indent=2), "utf-8")


async def write_text(path: Path, content: str) -> None:
    """异步写入文本文件"""
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, content, "utf-8")


def section_path(volume_number: int, chapter_number: int, section_number: int) -> str:
    """生成场景文件路径"""
    return f"chapters/vol-{volume_number:02d}/ch-{chapter_number:03d}/sec-{section_number:03d}.md"


class LiteProjectService:
    """Lite 爽文模式项目服务"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.project_service = ProjectService(settings)

    async def create_project(self, req: LiteProjectCreateRequest) -> LiteProjectCreateResponse:
        """创建 Lite 爽文项目"""
        project_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        project_dir = self.settings.projects_path / project_id

        await self._init_project_dir(project_id, req, project_dir, now)
        first_file = await self.ensure_chapter(project_dir, 1, 1, req.card.title)
        story_engine = story_engine_template(req.card, prefs_to_text(req.prefs))

        return LiteProjectCreateResponse(
            project_id=project_id,
            first_file=first_file,
            story_engine=story_engine,
        )

    async def _init_project_dir(
        self,
        project_id: str,
        req: LiteProjectCreateRequest,
        project_dir: Path,
        now: str,
    ) -> None:
        """初始化项目目录结构"""
        await asyncio.to_thread(project_dir.mkdir, parents=True, exist_ok=True)

        project_req = ProjectCreateRequest(
            name=req.card.title,
            genre=req.card.genre,
            theme=req.card.selling_point,
            tone="爽文",
            background=req.card.core_conflict,
            writing_style=req.prefs.style,
            target_word_count=50000,
            author="",
        )
        meta = self.project_service.create_project_meta(project_id, project_req.name, project_req)
        meta["lite_mode"] = True
        await asyncio.to_thread(self.project_service.write_meta, project_dir, meta)

        await asyncio.to_thread(self.project_service.write_context, project_dir, {
            "project_id": project_id,
            "stats": {
                "total_words": 0,
                "total_sections": SECTIONS_PER_CHAPTER,
                "completed_sections": 0,
                "chapter_count": 1,
                "volume_count": 1,
                "character_count": 0,
            },
            "updated_at": now,
        })

        for subdir in ["chapters/vol-01", "characters", "materials/extracted", "backup", "revision-log", "feedback"]:
            await asyncio.to_thread((project_dir / subdir).mkdir, parents=True, exist_ok=True)

        await write_json(project_dir / "chapters" / "vol-01" / "vol-meta.json", {
            "volume_number": 1,
            "chapter_range": "001-001",
            "total_chapters": 1,
            "created_at": now,
        })

        prefs_text = prefs_to_text(req.prefs)
        story_engine = story_engine_template(req.card, prefs_text)

        await write_text(project_dir / "style-guide.md", f"# 文风指南\n\n{prefs_text}\n")
        await write_text(project_dir / "story-state.md", "# 故事状态\n\n由故事引擎自动维护。\n")
        await write_text(project_dir / "recent-context.md", "# 近期上下文\n\n（最近5章摘要，由系统自动维护）\n")
        await write_text(project_dir / "story-engine.md", story_engine)
        await write_text(project_dir / "outline.md", f"# {req.card.title} - 可选大纲\n\n本项目默认使用故事引擎驱动，不要求大纲。\n")

    async def ensure_chapter(self, project_dir: Path, volume_number: int, chapter_number: int, title: str) -> str:
        """确保章节目录和文件存在，创建空白场景文件"""
        vol_dir = project_dir / "chapters" / f"vol-{volume_number:02d}"
        ch_dir = vol_dir / f"ch-{chapter_number:03d}"

        await asyncio.to_thread(vol_dir.mkdir, parents=True, exist_ok=True)

        vol_meta = vol_dir / "vol-meta.json"
        if not await asyncio.to_thread(vol_meta.exists):
            await write_json(vol_meta, {
                "volume_number": volume_number,
                "chapter_range": f"{chapter_number:03d}-{chapter_number:03d}",
                "total_chapters": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        await asyncio.to_thread(ch_dir.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread((ch_dir / "feedback").mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread((ch_dir / "revision-log").mkdir, parents=True, exist_ok=True)

        ch_meta = ch_dir / "ch-meta.json"
        if not await asyncio.to_thread(ch_meta.exists):
            await write_json(ch_meta, {
                "chapter_number": chapter_number,
                "title": title,
                "section_count": SECTIONS_PER_CHAPTER,
                "word_count": 0,
                "status": "draft",
                "memory": [],
                "story_state": "",
                "pending_foreshadowing": [],
                "active_quests": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        for section_number in range(1, SECTIONS_PER_CHAPTER + 1):
            file_path = ch_dir / f"sec-{section_number:03d}.md"
            if not await asyncio.to_thread(file_path.exists):
                await write_text(file_path, f"# 第{volume_number}卷 第{chapter_number}章 {title} - 第{section_number}场景\n\n")

        return section_path(volume_number, chapter_number, 1)
