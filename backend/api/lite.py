"""墨韵 - 爽文模式 API"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import uuid

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.project_service import ProjectService
from backend.core.prompt_engine import PromptEngine
from backend.core.quality_service import QualityService
from backend.schemas.common import ApiResponse
from backend.schemas.lite import (
    LiteIdeaCard,
    LiteIdeasRequest,
    LiteIdeasResponse,
    LiteNextOptionCard,
    LiteNextOptionsRequest,
    LiteNextOptionsResponse,
    LiteProjectCreateRequest,
    LiteProjectCreateResponse,
    LiteWriteNextRequest,
    LiteWriteNextResponse,
)
from backend.schemas.project import ProjectCreateRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["lite"])


OPTION_TEMPLATES = [
    ("当众打脸", "公开场合", "让质疑者当场失态", "更大的后台人物注意到主角"),
    ("危机反杀", "险境现场", "主角用新能力破局", "敌人背后的真正目标露出一角"),
    ("收获升级", "资源争夺点", "主角拿到关键奖励", "奖励牵出下一轮争夺"),
]


# 硬编码兜底开局卡（AI 生成失败时使用）
FALLBACK_IDEA_BANK: list[LiteIdeaCard] = [
    LiteIdeaCard(
        id="xuanhuan-return",
        title="退婚现场，词条觉醒",
        genre="玄幻",
        one_liner="被当众退婚的废柴少年，觉醒神级词条，反手让全场闭嘴。",
        protagonist_hook="曾经被宗门认定灵根破碎，却能看见万物隐藏词条。",
        core_conflict="未婚妻与内门天才联手羞辱他，宗门长老也站在对面。",
        selling_point="退婚打脸、词条升级、宗门考核连续反转。",
    ),
    LiteIdeaCard(
        id="wuxia-sword",
        title="小捕快拔出禁剑",
        genre="武侠",
        one_liner="边城小捕快误拔禁剑，被迫卷入江湖与朝堂的双重追杀。",
        protagonist_hook="看似油滑怕事，实则记忆力惊人，能复刻见过的招式。",
        core_conflict="名门正派要夺剑，朝廷密探要灭口，旧案真相浮出水面。",
        selling_point="快意恩仇、刀光剑影、朝堂江湖双线压迫。",
    ),
    LiteIdeaCard(
        id="romance-contract",
        title="合约婚姻变真香",
        genre="言情",
        one_liner="她为救家族签下合约婚姻，却发现冷面男主一直在暗中护她。",
        protagonist_hook="事业心强、嘴硬心软，不愿把命运交给任何人。",
        core_conflict="豪门旧怨、事业竞争与误会同时压来，两人互相试探。",
        selling_point="暧昧拉扯、强强对抗、护短真香。",
    ),
    LiteIdeaCard(
        id="xianxia-master",
        title="师尊护短，全宗震动",
        genre="仙侠",
        one_liner="被外门欺辱的小弟子，意外成为闭关师尊唯一亲传。",
        protagonist_hook="天赋平平却心性极稳，能在绝境中看见破局生机。",
        core_conflict="各峰争夺资源，旧敌不服，师尊身份暗藏更大秘密。",
        selling_point="师徒羁绊、宗门打脸、秘境成长。",
    ),
    LiteIdeaCard(
        id="urban-rich",
        title="鉴宝直播翻身",
        genre="都市",
        one_liner="负债青年开直播鉴宝，意外看穿古董气运，从捡漏开始逆袭。",
        protagonist_hook="穷到被房东赶人，却有极强观察力和不服输的劲。",
        core_conflict="同行打压、富二代设局、家人误解同时爆发。",
        selling_point="捡漏暴富、直播打脸、都市逆袭。",
    ),
]


GENRES = ["玄幻", "武侠", "言情", "都市", "仙侠"]

SECTIONS_PER_CHAPTER = 4
CHAPTERS_PER_VOLUME = 10


def _prefs_to_text(prefs) -> str:
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


def _story_engine_template(card: LiteIdeaCard, prefs_text: str) -> str:
    return f"""# 故事引擎

## 人物欲望
- 当前目标：主角要从“{card.protagonist_hook}”出发，证明自己并拿到第一份真实收益。
- 长期目标：摆脱被动命运，获得足以改变处境的力量、身份或关系。
- 底层执念：不再被轻慢、误解或安排，必须亲手夺回选择权。

## 冲突推进
- 明面冲突：{card.core_conflict}
- 隐藏冲突：既得利益者不愿主角翻身，旁观者的态度会随战果变化。
- 下一步压力：把质疑和代价摆到台面上，让主角必须当场回应。

## 场景直觉
- 下一场景：选择能让人物正面碰撞、旁观者足够多、反馈足够快的场合。
- 可碰撞人物：主角、直接羞辱者、旁观势力、潜在盟友或更高层对手。
- 场景原则：每一节都要有明确行动、即时反馈、结尾钩子。

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
- 当前 5-10 节目标：完成开局压迫到第一次漂亮反击，并抬出更高层级冲突。
- 完成标志：主角得到明确收益，旧秩序第一次松动。
- 下一章规划触发：每完成 4 节，整理下一章 4 节方向。

## 用户口味
{prefs_text}
"""


def _compact_line(value: str, limit: int = 90) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())[:limit]


def _rotate_cards(seed: str) -> list[LiteIdeaCard]:
    if not seed:
        return FALLBACK_IDEA_BANK[:5]
    offset = sum(ord(ch) for ch in seed) % len(FALLBACK_IDEA_BANK)
    return (FALLBACK_IDEA_BANK[offset:] + FALLBACK_IDEA_BANK[:offset])[:5]


def _project_file(project_dir: Path, rel_path: str) -> Path:
    return project_dir / rel_path.strip("/")


async def _write_json(path: Path, data: dict) -> None:
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


async def _write_text(path: Path, content: str) -> None:
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, content, "utf-8")


def _extract_chapter_number(file_path: str | None) -> int:
    if not file_path:
        return 0
    match = re.search(r"/ch-(\d+)/", file_path)
    return int(match.group(1)) if match else 0


def _path_parts(file_path: str | None) -> tuple[int, int, int]:
    if not file_path:
        return 1, 1, 0
    vol = int(re.search(r"vol-(\d+)", file_path).group(1)) if re.search(r"vol-(\d+)", file_path) else 1
    ch = int(re.search(r"ch-(\d+)", file_path).group(1)) if re.search(r"ch-(\d+)", file_path) else 1
    sec = int(re.search(r"sec-(\d+)", file_path).group(1)) if re.search(r"sec-(\d+)", file_path) else 0
    return vol, ch, sec


def _section_path(volume_number: int, chapter_number: int, section_number: int) -> str:
    return f"chapters/vol-{volume_number:02d}/ch-{chapter_number:03d}/sec-{section_number:03d}.md"


def _chapter_path(chapter_number: int) -> str:
    return _section_path(1, chapter_number, 1)


def _next_section_path(current_file: str | None) -> str:
    vol, ch, sec = _path_parts(current_file)
    if sec <= 0:
        return _section_path(vol, ch, 1)
    if sec < SECTIONS_PER_CHAPTER:
        return _section_path(vol, ch, sec + 1)
    if ch < CHAPTERS_PER_VOLUME:
        return _section_path(vol, ch + 1, 1)
    return _section_path(vol + 1, 1, 1)


def _section_label(file_path: str) -> str:
    vol, ch, sec = _path_parts(file_path)
    return f"第{vol}卷 第{ch}章 第{sec}节"


def _ensure_section_heading(target_file: str, title: str, content: str) -> str:
    stripped = content.lstrip()
    expected = f"# {_section_label(target_file)} {title}"
    if stripped.startswith("#"):
        lines = stripped.splitlines()
        lines[0] = expected
        return "\n".join(lines).strip()
    return f"{expected}\n\n{content.strip()}"


async def _ensure_chapter(project_dir: Path, volume_number: int, chapter_number: int, title: str) -> str:
    vol_dir = project_dir / "chapters" / f"vol-{volume_number:02d}"
    ch_dir = vol_dir / f"ch-{chapter_number:03d}"
    await asyncio.to_thread(vol_dir.mkdir, parents=True, exist_ok=True)
    vol_meta = vol_dir / "vol-meta.json"
    if not vol_meta.exists():
        await _write_json(vol_meta, {
            "volume_number": volume_number,
            "chapter_range": f"{chapter_number:03d}-{chapter_number:03d}",
            "total_chapters": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    await asyncio.to_thread(ch_dir.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread((ch_dir / "feedback").mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread((ch_dir / "revision-log").mkdir, parents=True, exist_ok=True)
    ch_meta = ch_dir / "ch-meta.json"
    if not ch_meta.exists():
        await _write_json(ch_meta, {
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
        if not file_path.exists():
            await _write_text(file_path, f"# 第{volume_number}卷 第{chapter_number}章 {title} - 第{section_number}节\n\n")
    return _section_path(volume_number, chapter_number, 1)


def _quality_one_line(summary: str, action: str) -> str:
    if summary:
        return summary.splitlines()[0][:80]
    if action == "continue":
        return "已续写草稿，并更新故事状态。"
    if action == "more_exciting":
        return "已增强冲突、爽点和结尾钩子。"
    if action == "more_reasonable":
        return "已补充人物动机和前文衔接。"
    return "已完成质量审查，并更新故事状态。"


def _needs_quality_repair(review) -> bool:
    scores = review.scores.model_dump() if review and review.scores else {}
    values = [v for v in scores.values() if isinstance(v, int)]
    avg = sum(values) / len(values) if values else 10
    has_serious_issue = any(issue.severity in ("critical", "major") for issue in review.issues)
    return avg < 6 or has_serious_issue


async def _complete_with_deadline(
    svc: LLMService,
    messages: list[dict],
    *,
    deadline: int,
    **kwargs,
) -> str:
    return (await asyncio.wait_for(
        svc.complete_sync(messages, **kwargs),
        timeout=deadline,
    )).strip()


def _fallback_section_content(
    target_file: str,
    selected_card: LiteNextOptionCard,
    prefs_text: str,
    story_engine: str,
) -> str:
    label = _section_label(target_file)
    _ = prefs_text
    desire_hint = next(
        (line.strip("- ").strip() for line in story_engine.splitlines() if line.strip().startswith("-")),
        "有人想把他按回尘埃里，可他偏要在所有人面前站起来。",
    )
    card_desire = selected_card.protagonist_desire or desire_hint
    card_obstacle = selected_card.obstacle or selected_card.scene
    card_advancement = selected_card.advancement or selected_card.payoff
    return "\n\n".join([
        f"# {label} {selected_card.title}",
        f"{selected_card.scene}里，人声原本很稳。直到门口那道身影出现，所有目光才像被一只看不见的手拨动，同时转了过去。",
        "最先笑出声的人没有压低音量。他把手里的茶盏轻轻一放，慢条斯理地说：“你还真敢来。”旁边几个人跟着露出笑意，那种笑不是惊讶，而是早就等着看人出丑的轻慢。",
        f"那道身影没有退。袖口沾着一路赶来的风尘，眼神却冷得很稳。{card_desire}这句话像一枚钉子，钉在心口，也钉住了脚下的位置。",
        f"真正的阻力不是几句冷嘲，而是{card_obstacle}。他明白，今天只要退半步，后面的每一步都会被人替他安排。",
        "对方把准备好的条件一条条抛出来：认错，低头，交出本该属于自己的东西。每一句都像是在给台阶，其实每一级都通向更深的泥里。",
        "场面安静下来。所有人都以为会听见求饶，或者至少听见一句辩解。",
        "可他只是抬眼，先问了一个很轻的问题。那问题轻得像随手一掸，却刚好掸在对方最怕被碰到的地方。笑声断了。茶盏边缘磕在桌面上，发出短促的一声响。",
        f"紧接着，证据、旧账和对方藏起来的破绽被一层层摆开。刚才还稳坐上风的人脸色终于变了，嘴唇动了几次，却一句完整的话也没接上。{selected_card.payoff}，而旁观的人也在这一刻明白，今天被逼到台前的人，未必就是该低头的人。",
        f"风从门外灌进来，吹得烛火一偏。有人在角落里悄悄收起笑意，也有人第一次认真打量他。{card_advancement}。更远处，一道沉默的视线停了很久，因为{selected_card.hook}。",
    ])


def _lite_stream_event(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _parse_option_cards(raw: str, next_label: str) -> list[LiteNextOptionCard]:
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("cards", [])
    cards: list[LiteNextOptionCard] = []
    for idx, item in enumerate(data[:3], 1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        scene = str(item.get("scene") or item.get("conflict_upgrade") or item.get("conflict") or "").strip()
        protagonist_desire = str(item.get("protagonist_desire") or item.get("desire") or item.get("goal") or "").strip()
        obstacle = str(item.get("obstacle") or item.get("resistance") or item.get("pressure") or "").strip()
        payoff = str(item.get("payoff") or item.get("beat") or "").strip()
        hook = str(item.get("hook") or "").strip()
        advancement = str(item.get("advancement") or item.get("push") or item.get("progress") or "").strip()
        if title and scene and payoff and hook:
            cards.append(LiteNextOptionCard(
                id=f"next-{next_label}-{idx}",
                title=title[:16],
                beat=payoff[:90],
                scene=scene[:90],
                protagonist_desire=protagonist_desire[:90] or "主角要拿到一个可见的阶段性收益。",
                obstacle=obstacle[:90] or scene[:90],
                payoff=payoff[:80],
                hook=hook[:80],
                advancement=advancement[:90] or "推动冲突升级，并让下一节有明确接力点。",
            ))
    return cards[:3]


def _fallback_next_cards(next_label: str, current_content: str, recent_context: str) -> list[LiteNextOptionCard]:
    source = current_content or recent_context
    useful_lines = [
        line.strip(" >-")
        for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and len(line.strip()) > 8
    ]
    context = " ".join(useful_lines)
    hint = (useful_lines[-1] if useful_lines else context)[:32] or "当前冲突"
    options = [
        ("当场反逼", f"对手借“{hint}”继续施压，把主角逼到众人面前。", "主角要当众守住尊严，并拿回被抢走的话语权。", "对手把旁观者和规矩都变成压力，逼主角低头认错。", "主角抓住对方话里的破绽，当众把主动权夺回来。", "幕后撑腰的人被迫露出一句关键口风。", "完成第一次正面反击，并把矛盾推向幕后人物。"),
        ("旧账翻面", "看似对主角不利的旧账，被对手拿来公开施压。", "主角要证明旧账另有隐情，洗掉眼前的污名。", "旧证据被对手抢先解释，旁观者暂时站在对面。", "主角顺势翻出被忽略的细节，让刚占上风的人反而失态。", "旧账牵出一个更大的交换条件。", "回收一条旧线索，同时制造新的利益交换。"),
        ("战果藏钩", "冲突暂时收束，但旁观者开始重新站队。", "主角要把胜势落成实物奖励，而不是只赢口舌。", "奖励被人暗中设限，拿到它反而会引来更高层注意。", "主角拿到实在奖励，同时让羞辱者付出可见代价。", "奖励里藏着下一节必须打开的新线索。", "把本节爽点变成下一节冲突的燃料。"),
    ]
    return [
        LiteNextOptionCard(
            id=f"next-{next_label}-{idx}",
            title=title,
            beat=payoff,
            scene=scene,
            protagonist_desire=protagonist_desire,
            obstacle=obstacle,
            payoff=payoff,
            hook=hook,
            advancement=advancement,
        )
        for idx, (title, scene, protagonist_desire, obstacle, payoff, hook, advancement) in enumerate(options, 1)
    ]


async def _stream_llm_content(
    svc: LLMService,
    messages: list[dict],
    *,
    first_token_timeout: int = 90,
    token_timeout: int = 45,
    **kwargs,
) -> AsyncGenerator[str, None]:
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def _produce() -> None:
        try:
            async for chunk in svc.complete(messages, stream=True, **kwargs):
                await queue.put(chunk)
        finally:
            await queue.put(None)

    task = asyncio.create_task(_produce())
    has_chunk = False
    try:
        while True:
            timeout = token_timeout if has_chunk else first_token_timeout
            item = await asyncio.wait_for(queue.get(), timeout=timeout)
            if item is None:
                break
            has_chunk = True
            yield item
    except Exception:
        task.cancel()
        raise
    finally:
        if not task.done():
            task.cancel()


async def _read_optional(file_service: FileService, project_id: str, rel_path: str) -> str:
    try:
        content, _ = await file_service.read_file(f"{project_id}/{rel_path}")
        return content
    except Exception:
        return ""


async def _read_chapter_context(file_service: FileService, project_id: str, vol: int, ch: int, current_sec: int) -> str:
    """读取当前章中所有已写的前序节内容，拼接为上下文，确保 LLM 感知前文。"""
    parts: list[str] = []
    for sec in range(1, current_sec):
        section_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/sec-{sec:03d}.md"
        content = await _read_optional(file_service, project_id, section_path)
        if content and not _is_blank_chapter(content):
            parts.append(f"--- 第{sec}节 ---\n{content.strip()}")
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n\n"


async def _read_ch_meta(file_service: FileService, project_id: str, vol: int, ch: int) -> dict:
    """读取章元数据。"""
    meta_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-meta.json"
    raw = await _read_optional(file_service, project_id, meta_path)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return {}


async def _update_ch_meta(
    file_service: FileService,
    project_id: str,
    vol: int,
    ch: int,
    sec: int,
    card_title: str,
    card_payoff: str,
    card_hook: str,
) -> None:
    """写入一节完成后更新章节记忆和待回收伏笔。"""
    ch_meta = await _read_ch_meta(file_service, project_id, vol, ch)
    # 章节记忆：按节累积
    memory = ch_meta.get("memory", [])
    if isinstance(memory, str):
        memory = [] if not memory else [memory]
    memory.append(f"第{sec}节「{card_title}」：{card_payoff}")
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
    await file_service.write_file(meta_path, json.dumps(ch_meta, ensure_ascii=False, indent=2))



async def _next_writable_section_path(
    file_service: FileService,
    project_id: str,
    current_file: str | None,
) -> str:
    """找到当前文件之后第一个空节，避免刷新后重复覆盖已写章节。"""
    candidate = _next_section_path(current_file)
    for _ in range(80):
        content = await _read_optional(file_service, project_id, candidate)
        if _is_blank_chapter(content):
            return candidate
        candidate = _next_section_path(candidate)
    return candidate


def _summarize_story_engine(text: str) -> dict[str, str]:
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


def _build_story_engine_update(
    story_engine: str,
    target_file: str,
    selected_card: LiteNextOptionCard,
    content: str,
) -> str:
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


def _is_blank_chapter(content: str) -> bool:
    body_lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
    return len("\n".join(body_lines)) < 20


def _chapter_vol_label(vol: int, ch: int) -> str:
    return f"第{vol}卷第{ch}章"


async def _generate_chapter_plan(
    file_service: FileService,
    llm_svc: LLMService,
    prompt_engine: PromptEngine,
    project_id: str,
    vol: int,
    completed_ch: int,
    story_engine: str,
    recent_context: str,
    style_guide: str,
    prefs_text: str,
) -> str:
    """当前章完成后，生成下一章的章规划"""
    next_ch = completed_ch + 1
    meta_path = f"chapters/vol-{vol:02d}/ch-{completed_ch:03d}/ch-meta.json"
    existing_plan_path = f"chapters/vol-{vol:02d}/ch-{next_ch:03d}/ch-plan.md"
    try:
        existing_plan, _ = await file_service.read_file(f"{project_id}/{existing_plan_path}")
        if not _is_blank_chapter(existing_plan):
            return existing_plan.strip()
    except Exception:
        pass
    ch_title = ""
    try:
        meta_raw, _ = await file_service.read_file(f"{project_id}/{meta_path}")
        ch_meta = json.loads(meta_raw)
        ch_title = ch_meta.get("title", "")
    except Exception:
        pass

    prompt = "\n".join([
        "你是一位擅长规划爽文的编辑。请为下一章写一份章规划（200 字以内）。",
        "",
        f"已完成章节：《{_chapter_vol_label(vol, completed_ch)} {ch_title}》",
        "读者期待：",
        story_engine,
        "近期上下文：",
        recent_context,
        "文风指南：",
        style_guide,
        "",
        "章规划格式：",
        "- 章名与核心冲突（一句话）",
        "- 4 节梗概（每节 1 句，标注谁在什么场景做什么）",
        "- 本章必须兑现的爽点",
        "- 结尾钩子",
    ])
    try:
        content = (await llm_svc.complete_sync(
            [{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
            timeout=60,
        )).strip()
    except Exception as e:
        logger.warning("生成章规划失败: %s", e)
        return ""
    plan_path = f"{project_id}/chapters/vol-{vol:02d}/ch-{next_ch:03d}/ch-plan.md"
    try:
        plan_dir = Path(plan_path).parent
        await asyncio.to_thread(plan_dir.mkdir, parents=True, exist_ok=True)
        await file_service.write_file(plan_path, content)
    except Exception:
        pass
    return content


async def _generate_ideas_via_llm(
    settings,
    seed: str,
) -> list[LiteIdeaCard] | None:
    """用 LLM 动态生成 5 张开局爽文卡，失败返回 None"""
    try:
        llm_cfg = load_llm_config_from_workspace(settings)
        svc = LLMService.from_workspace_config(llm_cfg)
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
            f"题材依次为：{', '.join(GENRES)}",
            "",
            "只返回 JSON 数组，不要多余文字，格式：",
            """[{"id": "xxx", "title": "...", "genre": "...", "one_liner": "...", "protagonist_hook": "...", "core_conflict": "...", "selling_point": "..."}]""",
        ])
        raw = await _complete_with_deadline(
            svc,
            [{"role": "user", "content": prompt}],
            deadline=45,
            temperature=0.9,
            max_tokens=2000,
            timeout=40,
        )
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("cards", data.get("ideas", []))
        cards: list[LiteIdeaCard] = []
        for item in data[:5]:
            genre = str(item.get("genre", "")).strip()
            if genre not in GENRES:
                continue
            card = LiteIdeaCard(
                id=f"ai-{seed}-{genre}" if seed else f"ai-{genre}",
                title=str(item.get("title", ""))[:16] or "未命名",
                genre=genre,
                one_liner=str(item.get("one_liner", ""))[:40] or "开局冲突",
                protagonist_hook=str(item.get("protagonist_hook", ""))[:50] or "有潜力的主角",
                core_conflict=str(item.get("core_conflict", ""))[:80] or "冲突待定",
                selling_point=str(item.get("selling_point", ""))[:60] or "爽点待定",
            )
            cards.append(card)
        if len(cards) >= 3:
            return cards[:5]
    except Exception as e:
        logger.warning("AI 生成开局卡失败: %s", e)
    return None


@router.post("/lite/ideas", response_model=ApiResponse[LiteIdeasResponse])
async def generate_lite_ideas(
    req: LiteIdeasRequest,
    settings: Settings = Depends(get_settings),
):
    """生成爽文模式开局卡（优先 AI 动态生成，失败使用兜底卡）"""
    cards = await _generate_ideas_via_llm(settings, req.seed)
    if not cards:
        cards = _rotate_cards(req.seed)
    return ApiResponse.ok(LiteIdeasResponse(cards=cards))


@router.post("/lite/projects", response_model=ApiResponse[LiteProjectCreateResponse], status_code=201)
async def create_lite_project(
    req: LiteProjectCreateRequest,
    settings: Settings = Depends(get_settings),
):
    """根据开局卡创建无大纲爽文项目"""
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
    project_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    project_dir = settings.projects_path / project_id
    svc = ProjectService(settings)

    await asyncio.to_thread(project_dir.mkdir, parents=True, exist_ok=True)
    meta = svc.create_project_meta(project_id, project_req.name, project_req)
    meta["lite_mode"] = True
    await asyncio.to_thread(svc.write_meta, project_dir, meta)
    await asyncio.to_thread(svc.write_context, project_dir, {
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
    await _write_json(project_dir / "chapters" / "vol-01" / "vol-meta.json", {
        "volume_number": 1,
        "chapter_range": "001-001",
        "total_chapters": 1,
        "created_at": now,
    })

    prefs_text = _prefs_to_text(req.prefs)
    story_engine = _story_engine_template(req.card, prefs_text)
    await _write_text(project_dir / "style-guide.md", f"# 文风指南\n\n{prefs_text}\n")
    await _write_text(project_dir / "story-state.md", "# 故事状态\n\n由故事引擎自动维护。\n")
    await _write_text(project_dir / "recent-context.md", "# 近期上下文\n\n（最近5章摘要，由系统自动维护）\n")
    await _write_text(project_dir / "story-engine.md", story_engine)
    await _write_text(project_dir / "outline.md", f"# {req.card.title} - 可选大纲\n\n本项目默认使用故事引擎驱动，不要求大纲。\n")
    first_file = await _ensure_chapter(project_dir, 1, 1, req.card.title)

    return ApiResponse.ok(LiteProjectCreateResponse(
        project_id=project_id,
        first_file=first_file,
        story_engine=story_engine,
    ), message="爽文项目创建成功")


@router.post("/lite/next-options", response_model=ApiResponse[LiteNextOptionsResponse])
async def generate_next_options(
    req: LiteNextOptionsRequest,
    settings: Settings = Depends(get_settings),
):
    """生成下一章爽点卡"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    file_service = FileService(settings.projects_path)
    current_content = await _read_optional(file_service, req.project_id, req.current_file or "")
    current_no = max(1, _extract_chapter_number(req.current_file) or 1)
    if req.current_file and _is_blank_chapter(current_content):
        next_file = req.current_file
    else:
        next_file = await _next_writable_section_path(file_service, req.project_id, req.current_file)
    next_label = _section_label(next_file)
    story_engine = await _read_optional(file_service, req.project_id, "story-engine.md")
    recent_context = await _read_optional(file_service, req.project_id, "recent-context.md")
    vol, ch, _sec = _path_parts(next_file)
    chapter_plan = await _read_optional(file_service, req.project_id, f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-plan.md")
    chapter_context = await _read_chapter_context(file_service, req.project_id, vol, ch, _sec)
    context_content = current_content if not _is_blank_chapter(current_content) else chapter_context

    cards = _fallback_next_cards(next_label, context_content, recent_context)
    try:
        llm_cfg = load_llm_config_from_workspace(settings)
        svc = LLMService.from_workspace_config(llm_cfg)
        prompt = "\n".join([
            "你是爽文连载编辑。请基于当前正文和故事状态，为下一节生成3张不同方向的爽点卡。",
            "不要使用固定模板，不要重复“当众打脸/危机反杀/收获升级”这类泛化标题。",
            "每张卡必须贴合前文已经发生的角色、冲突、伏笔和读者期待。",
            "每张卡必须至少引用一个前文出现的人名、地点、物件、组织、称呼或伏笔。",
            "三张卡方向要明显不同：一张强硬反击，一张反转揭底，一张拿奖励并埋钩子；标题必须根据剧情改写，不要直接写这些模板名。",
            "不要写“围绕某某推进、保持快节奏、标准爽点”这类说明书句式。",
            "只返回 JSON 数组，每项包含 title, conflict_upgrade, protagonist_desire, obstacle, payoff, hook, advancement。",
            "字段含义：conflict_upgrade=冲突升级，protagonist_desire=主角此刻想要什么，obstacle=谁/什么挡住他，payoff=爽点兑现，hook=结尾钩子，advancement=本节怎样推进故事。",
            "",
            f"下一节：{next_label}",
            f"偏好：{_prefs_to_text(req.prefs)}",
            "当前正文或本章前文：",
            context_content[-2500:],
            "故事引擎：",
            story_engine[-2500:],
            "近期上下文：",
            recent_context[-1500:],
            "章规划：",
            chapter_plan[-1500:],
        ])
        raw = await _complete_with_deadline(
            svc,
            [{"role": "user", "content": prompt}],
            deadline=20,
            temperature=0.85,
            max_tokens=900,
            timeout=20,
        )
        parsed_cards = _parse_option_cards(raw, next_label)
        if len(parsed_cards) == 3:
            cards = parsed_cards
    except Exception as e:
        logger.warning("动态生成爽点卡失败，使用上下文兜底卡: %s", e)
    return ApiResponse.ok(LiteNextOptionsResponse(
        cards=cards,
        current_file=req.current_file or _chapter_path(current_no),
        next_file=next_file,
    ))


@router.post("/lite/write-next", response_model=ApiResponse[LiteWriteNextResponse])
async def write_lite_next(
    req: LiteWriteNextRequest,
    settings: Settings = Depends(get_settings),
):
    """选卡生成章节，自动审稿并更新故事引擎"""
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(req.project_id)

    file_service = FileService(settings.projects_path)
    requested_content = await _read_optional(file_service, req.project_id, req.target_file or "") if req.target_file else ""
    is_blank_requested = _is_blank_chapter(requested_content)
    if (req.action != "write" and req.target_file) or (req.target_file and is_blank_requested):
        target_file = req.target_file
    else:
        target_file = await _next_writable_section_path(file_service, req.project_id, req.target_file)
    vol, ch, _sec = _path_parts(target_file)
    await _ensure_chapter(project_dir, vol, ch, req.selected_card.title)

    prev_content = await _read_chapter_context(file_service, req.project_id, vol, ch, _sec)
    target_content = await _read_optional(file_service, req.project_id, target_file)
    current_content = prev_content + target_content
    story_engine = await _read_optional(file_service, req.project_id, "story-engine.md")
    story_state = await _read_optional(file_service, req.project_id, "story-state.md")
    style_guide = await _read_optional(file_service, req.project_id, "style-guide.md")
    recent_context = await _read_optional(file_service, req.project_id, "recent-context.md")

    # 如果当前章有章规划，加入生成上下文
    chapter_plan = ""
    if ch and _sec:
        plan_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-plan.md"
        plan_content = await _read_optional(file_service, req.project_id, plan_path)
        if plan_content and not _is_blank_chapter(plan_content):
            chapter_plan = plan_content

    goal = "\n".join([
        f"本章爽点卡：{req.selected_card.title}",
        f"剧情节拍：{req.selected_card.beat}",
        f"场景：{req.selected_card.scene}",
        f"主角此刻想要：{req.selected_card.protagonist_desire}",
        f"阻力/对手：{req.selected_card.obstacle}",
        f"兑现：{req.selected_card.payoff}",
        f"结尾钩子：{req.selected_card.hook}",
        f"故事推进：{req.selected_card.advancement}",
        "写作偏好：",
        _prefs_to_text(req.prefs),
        ("章规划：\n" + chapter_plan) if chapter_plan else "",
        "故事引擎：",
        story_engine,
    ])

    # 读取章节记忆和待回收伏笔
    ch_meta_data = await _read_ch_meta(file_service, req.project_id, vol, ch)
    raw_memory = ch_meta_data.get("memory", [])
    if isinstance(raw_memory, list):
        chapter_memory = "\n".join(raw_memory)
    elif isinstance(raw_memory, str):
        chapter_memory = raw_memory
    else:
        chapter_memory = ""
    raw_foreshadowing = ch_meta_data.get("pending_foreshadowing", [])
    if isinstance(raw_foreshadowing, list):
        pending_foreshadowing = "\n".join(raw_foreshadowing)
    else:
        pending_foreshadowing = ""

    prompt_engine = PromptEngine(settings.prompts_path, file_service)
    prompt = await prompt_engine.render("generate/continuation", {
        "current_content": current_content,
        "chapter_memory": chapter_memory,
        "continuation_goal": goal,
        "story_state": story_state,
        "style_guide": style_guide,
        "recent_context": recent_context,
        "pending_foreshadowing": pending_foreshadowing,
    })

    llm_cfg = load_llm_config_from_workspace(settings)
    svc = LLMService.from_workspace_config(llm_cfg)
    prefs_text = _prefs_to_text(req.prefs)
    used_fallback = False
    try:
        content = await _complete_with_deadline(
            svc,
            [{"role": "user", "content": prompt}],
            deadline=90,
            temperature=0.75,
            max_tokens=6000,
            timeout=60,
        )
    except Exception as e:
        logger.warning("爽文模式正文生成超时或失败，使用临时草稿: %s", e)
        content = _fallback_section_content(target_file, req.selected_card, prefs_text, story_engine)
        used_fallback = True
    content = _ensure_section_heading(target_file, req.selected_card.title, content)
    await file_service.write_file(f"{req.project_id}/{target_file}", content)

    # 更新章节记忆和待回收伏笔
    await _update_ch_meta(file_service, req.project_id, vol, ch, _sec, req.selected_card.title, req.selected_card.payoff, req.selected_card.hook)

    quality_summary = ""
    if used_fallback:
        quality_summary = "模型生成超时，已先写入临时草稿；可点“重写这一章”补成正式正文。"
    else:
        try:
            quality = QualityService(settings)
            review = await asyncio.wait_for(
                quality.perform_review(req.project_id, target_file, req.selected_card.title),
                timeout=75,
            )
            quality.save_review_result(req.project_id, target_file, str(uuid.uuid4())[:8], review)
            quality_summary = _quality_one_line(review.summary, req.action)
            if _needs_quality_repair(review):
                repair_goal = "\n".join([
                    "请根据质量审查意见重写并补强当前章节，保留原本选卡方向。",
                    f"质量摘要：{review.summary}",
                    "主要建议：",
                    "\n".join(f"- {item}" for item in review.suggestions[:5]) or "- 补强逻辑、动机和爽点兑现。",
                    "原爽点卡：",
                    goal,
                ])
                repair_prompt = await prompt_engine.render("generate/continuation", {
                    "current_content": content,
                    "chapter_memory": chapter_memory,
                    "continuation_goal": repair_goal,
                    "story_state": story_state,
                    "style_guide": style_guide,
                    "recent_context": recent_context,
                    "pending_foreshadowing": pending_foreshadowing,
                })
                repaired = await _complete_with_deadline(
                    svc,
                    [{"role": "user", "content": repair_prompt}],
                    deadline=75,
                    temperature=0.65,
                    max_tokens=6000,
                    timeout=60,
                )
                if repaired:
                    content = _ensure_section_heading(target_file, req.selected_card.title, repaired)
                    await file_service.write_file(f"{req.project_id}/{target_file}", content)
                    quality_summary = "已根据审稿意见自动补强逻辑、动机和爽点。"
        except Exception as e:
            logger.warning("爽文模式质量审查失败: %s", e)
            quality_summary = _quality_one_line("", req.action)

    updated_engine = _build_story_engine_update(story_engine, target_file, req.selected_card, content)
    await file_service.write_file(f"{req.project_id}/story-engine.md", updated_engine)
    await file_service.write_file(
        f"{req.project_id}/recent-context.md",
        recent_context.rstrip() + f"\n\n- {Path(target_file).parent.name}：{req.selected_card.title}，{req.selected_card.payoff}",
    )

    # 完成第4节 → 整章写完，自动生成下一章章规划
    chapter_plan_result = None
    if _sec == SECTIONS_PER_CHAPTER:
        chapter_plan_result = await _generate_chapter_plan(
            file_service=file_service,
            llm_svc=svc,
            prompt_engine=prompt_engine,
            project_id=req.project_id,
            vol=vol,
            completed_ch=ch,
            story_engine=updated_engine,
            recent_context=recent_context,
            style_guide=style_guide,
            prefs_text=prefs_text,
        )

    return ApiResponse.ok(LiteWriteNextResponse(
        file_path=target_file,
        content=content,
        quality_summary=quality_summary,
        story_engine_summary=_summarize_story_engine(updated_engine),
        chapter_plan=chapter_plan_result,
    ), message="章节已生成")


@router.post("/lite/write-next-stream")
async def write_lite_next_stream(
    req: LiteWriteNextRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """选卡生成章节，流式输出正文，再审稿并更新故事引擎"""

    async def _stream() -> AsyncGenerator[dict, None]:
        project_dir = settings.projects_path / req.project_id
        if not project_dir.exists():
            yield _lite_stream_event("error", {"message": f"项目不存在：{req.project_id}"})
            return

        file_service = FileService(settings.projects_path)
        requested_content = await _read_optional(file_service, req.project_id, req.target_file or "") if req.target_file else ""
        is_blank_requested = _is_blank_chapter(requested_content)
        if (req.action in ("continue", "rewrite", "more_exciting", "more_reasonable") and req.target_file) or (req.target_file and is_blank_requested):
            target_file = req.target_file
        else:
            target_file = await _next_writable_section_path(file_service, req.project_id, req.target_file)
        output_file = req.output_file or target_file
        is_candidate = output_file != target_file

        vol, ch, _sec = _path_parts(target_file)
        await _ensure_chapter(project_dir, vol, ch, req.selected_card.title)
        yield _lite_stream_event("meta", {
            "file_path": output_file,
            "source_file": target_file,
            "is_candidate": is_candidate,
            "label": _section_label(target_file),
        })

        try:
            prev_content = await _read_chapter_context(file_service, req.project_id, vol, ch, _sec)
            target_content = await _read_optional(file_service, req.project_id, target_file)
            current_content = prev_content + target_content
            story_engine = await _read_optional(file_service, req.project_id, "story-engine.md")
            story_state = await _read_optional(file_service, req.project_id, "story-state.md")
            style_guide = await _read_optional(file_service, req.project_id, "style-guide.md")
            recent_context = await _read_optional(file_service, req.project_id, "recent-context.md")

            chapter_plan = ""
            if ch and _sec:
                plan_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-plan.md"
                plan_content = await _read_optional(file_service, req.project_id, plan_path)
                if plan_content and not _is_blank_chapter(plan_content):
                    chapter_plan = plan_content

            # 读取章节记忆和待回收伏笔
            ch_meta_data = await _read_ch_meta(file_service, req.project_id, vol, ch)
            raw_memory = ch_meta_data.get("memory", [])
            if isinstance(raw_memory, list):
                chapter_memory = "\n".join(raw_memory)
            elif isinstance(raw_memory, str):
                chapter_memory = raw_memory
            else:
                chapter_memory = ""
            raw_foreshadowing = ch_meta_data.get("pending_foreshadowing", [])
            if isinstance(raw_foreshadowing, list):
                pending_foreshadowing = "\n".join(raw_foreshadowing)
            else:
                pending_foreshadowing = ""

            prefs_text = _prefs_to_text(req.prefs)
            goal = "\n".join([
                f"本章爽点卡：{req.selected_card.title}",
                f"剧情节拍：{req.selected_card.beat}",
                f"场景：{req.selected_card.scene}",
                f"主角此刻想要：{req.selected_card.protagonist_desire}",
                f"阻力/对手：{req.selected_card.obstacle}",
                f"兑现：{req.selected_card.payoff}",
                f"结尾钩子：{req.selected_card.hook}",
                f"故事推进：{req.selected_card.advancement}",
                "如果这是续写草稿：只能从当前草稿末尾自然接着写，不要重写开头，不要重复已经写过的句子。",
                "写作偏好：",
                prefs_text,
                ("章规划：\n" + chapter_plan) if chapter_plan else "",
                "故事引擎：",
                story_engine,
            ])

            prompt_engine = PromptEngine(settings.prompts_path, file_service)
            prompt = await prompt_engine.render("generate/continuation", {
            "current_content": current_content,
            "chapter_memory": chapter_memory,
            "continuation_goal": goal,
            "story_state": story_state,
            "style_guide": style_guide,
            "recent_context": recent_context,
            "pending_foreshadowing": pending_foreshadowing,
            })

            llm_cfg = load_llm_config_from_workspace(settings)
            svc = LLMService.from_workspace_config(llm_cfg)
            content_parts: list[str] = []
            used_fallback = False
            yield _lite_stream_event("status", {"message": "AI 正在写正文..."})

            try:
                async for chunk in _stream_llm_content(
                    svc,
                    [{"role": "user", "content": prompt}],
                    first_token_timeout=8,
                    token_timeout=12,
                    temperature=0.75,
                    max_tokens=6000,
                    timeout=60,
                ):
                    if await request.is_disconnected():
                        return
                    content_parts.append(chunk)
                    yield _lite_stream_event("delta", {"delta": chunk})
            except Exception as e:
                logger.warning("爽文模式流式正文生成超时或失败，使用临时草稿: %s", e)
                fallback = _fallback_section_content(target_file, req.selected_card, prefs_text, story_engine)
                content_parts = [fallback]
                used_fallback = True
            generated_text = "".join(content_parts).strip()
            if req.action == "continue" and target_content.strip():
                content = target_content.rstrip() + "\n\n" + generated_text
            else:
                content = generated_text
            yield _lite_stream_event("replace", {"content": content.strip()})

            content = _ensure_section_heading(target_file, req.selected_card.title, content.strip())
            await file_service.write_file(f"{req.project_id}/{output_file}", content)

            if not is_candidate:
                # 更新章节记忆和待回收伏笔
                await _update_ch_meta(file_service, req.project_id, vol, ch, _sec, req.selected_card.title, req.selected_card.payoff, req.selected_card.hook)

            quality_summary = "候选稿已生成，确认满意后可采用替换原文。" if is_candidate else "模型生成超时，已先写入临时草稿；可点“重写这一章”补成正式正文。" if used_fallback else "正文已写入，审稿将在后台完成。"

            async def _review_in_background() -> None:
                try:
                    quality = QualityService(settings)
                    review = await quality.perform_review(req.project_id, target_file, req.selected_card.title)
                    quality.save_review_result(req.project_id, target_file, str(uuid.uuid4())[:8], review)
                except Exception as e:
                    logger.warning("爽文模式后台质量审查失败: %s", e)

            if not used_fallback and not is_candidate:
                asyncio.create_task(_review_in_background())

            if is_candidate:
                updated_engine = story_engine
            else:
                yield _lite_stream_event("status", {"message": "正在更新故事状态..."})
                updated_engine = _build_story_engine_update(story_engine, target_file, req.selected_card, content)
                await file_service.write_file(f"{req.project_id}/story-engine.md", updated_engine)
                await file_service.write_file(
                    f"{req.project_id}/recent-context.md",
                    recent_context.rstrip() + f"\n\n- {Path(target_file).parent.name}：{req.selected_card.title}，{req.selected_card.payoff}",
                    )

            chapter_plan_result = None
            if not is_candidate and _sec == SECTIONS_PER_CHAPTER:
                chapter_plan_result = await _generate_chapter_plan(
                    file_service=file_service,
                    llm_svc=svc,
                    prompt_engine=prompt_engine,
                    project_id=req.project_id,
                    vol=vol,
                    completed_ch=ch,
                    story_engine=updated_engine,
                    recent_context=recent_context,
                    style_guide=style_guide,
                    prefs_text=prefs_text,
                )

            yield _lite_stream_event("done", {
                "file_path": output_file,
                "content": content,
                "quality_summary": quality_summary,
                "story_engine_summary": _summarize_story_engine(updated_engine),
                "chapter_plan": chapter_plan_result,
            })
        except Exception as e:
            logger.exception("爽文流式生成异常: %s", e)
            yield _lite_stream_event("error", {"message": f"生成失败：{e!s}"})

    return EventSourceResponse(_stream())
