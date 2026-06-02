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

from backend.application.lite_project_service import LiteProjectService
from backend.application.lite_scene_service import (
    CHAPTERS_PER_VOLUME,
    SECTIONS_PER_CHAPTER,
    chapter_path,
    extract_chapter_number,
    next_section_path,
    path_parts,
    section_label,
    section_path,
)
from backend.application.lite_story_metadata_service import LiteStoryMetadataService
from backend.application.lite_candidate_policy import lite_action_to_candidate_action
from backend.application.lite_option_cards_service import LiteOptionCardsService, GENRES
from backend.application.lite_llm_service import LiteLLMService
from backend.application.lite_prompt_builder import LitePromptBuilder
from backend.application.lite_quality_service import LiteQualityService
from backend.config import Settings, get_settings
from backend.core.candidate_service import CandidateService
from backend.core.exceptions import ProjectNotFoundError
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.project_service import ProjectService
from backend.core.prompt_engine import PromptEngine
from backend.core.quality_service import QualityService
from backend.domain.events import make_candidate_created_event
from backend.policies.candidate_policy import should_create_candidate
from backend.schemas.candidate import CandidateAction
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

logger = logging.getLogger(__name__)
router = APIRouter(tags=["lite"])




SECTIONS_PER_CHAPTER = 5
CHAPTERS_PER_VOLUME = 12
HIGH_RISK_LITE_ACTIONS = {"rewrite", "more_exciting", "more_reasonable", "rewrite_current_scene", "polish_current_scene", "chat_edit_current_scene"}

# Map new action names to existing behavior
LITE_ACTION_ALIAS = {
    "write_next_scene": "write",
    "write_current_scene": "write",
    "rewrite_current_scene": "rewrite",
    "polish_current_scene": "rewrite",  # polish uses same flow as rewrite in lite
}


async def _create_lite_candidate(
    file_service: FileService,
    project_id: str,
    source_path: str,
    action: str,
    content: str,
) -> "CandidateInfo":
    """通过 CandidateService 创建 Lite 候选稿，返回 CandidateInfo"""
    candidate_service = CandidateService(file_service)
    cand_action = lite_action_to_candidate_action(action)
    return await candidate_service.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=cand_action,
        content=content,
        source_mode="lite",
    )


def _should_use_candidate(
    action: str,
    target_file: str,
    requested_content: str,
    is_blank_requested: bool,
) -> bool:
    """判断是否应该使用候选稿机制"""
    if not target_file:
        return False
    effective_action = LITE_ACTION_ALIAS.get(action, action)
    target_has_content = bool(requested_content and not is_blank_requested)
    return (
        effective_action in HIGH_RISK_LITE_ACTIONS
        and should_create_candidate(effective_action, target_file, bool(requested_content), target_has_content)
    )


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





_FORBIDDEN_SEGMENTS = frozenset({".git", "node_modules", "__pycache__", ".env", ".config.json"})


class LitePathError(ValueError):
    """Raised when a Lite path fails safety validation."""


def _validate_project_id(project_id: str) -> str:
    """Validate project_id is safe (no traversal, no forbidden segments)."""
    if not project_id or not project_id.strip():
        raise LitePathError("project_id 不能为空")
    # Reject absolute paths and traversal
    if "/" in project_id or "\\" in project_id:
        raise LitePathError(f"project_id 包含非法路径分隔符: {project_id!r}")
    if project_id.startswith("."):
        raise LitePathError(f"project_id 不能以点号开头: {project_id!r}")
    if ".." in project_id:
        raise LitePathError(f"project_id 包含路径遍历: {project_id!r}")
    return project_id


def _validate_rel_path(rel_path: str) -> str:
    """Validate a user-supplied relative path is safe (no traversal, no forbidden segments)."""
    if not rel_path:
        return rel_path
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith("/"):
        raise LitePathError(f"不允许绝对路径: {rel_path!r}")
    if len(normalized) >= 2 and normalized[1] == ":":
        raise LitePathError(f"不允许 Windows 盘符路径: {rel_path!r}")
    segments = [s for s in normalized.split("/") if s]
    for seg in segments:
        if seg == "..":
            raise LitePathError(f"路径包含遍历段 '..': {rel_path!r}")
        seg_lower = seg.lower()
        if seg_lower in _FORBIDDEN_SEGMENTS:
            raise LitePathError(f"路径包含禁止段 {seg!r}: {rel_path!r}")
    return rel_path


def _safe_project_path(project_dir: Path, rel_path: str) -> Path:
    """Safely resolve a project-relative path, rejecting traversal and forbidden segments.

    - Rejects absolute paths
    - Rejects ``..`` path segments (POSIX and Windows forms)
    - Rejects forbidden segments (.git, node_modules, etc.)
    - Normalizes path separators
    - Verifies the resolved path stays inside project_dir
    """
    if not rel_path:
        raise LitePathError("相对路径不能为空")

    # Normalize separators
    normalized = rel_path.replace("\\", "/")

    # Reject absolute paths
    if normalized.startswith("/"):
        raise LitePathError(f"不允许绝对路径: {rel_path!r}")

    # Reject Windows drive letters
    if len(normalized) >= 2 and normalized[1] == ":":
        raise LitePathError(f"不允许 Windows 盘符路径: {rel_path!r}")

    # Split into segments and check each
    segments = [s for s in normalized.split("/") if s]
    for seg in segments:
        if seg == "..":
            raise LitePathError(f"路径包含遍历段 '..': {rel_path!r}")
        if seg == ".":
            continue
        # Check forbidden segments
        seg_lower = seg.lower()
        if seg_lower in _FORBIDDEN_SEGMENTS:
            raise LitePathError(f"路径包含禁止段 {seg!r}: {rel_path!r}")

    # Build the resolved path and verify it stays inside project_dir
    resolved = (project_dir / "/".join(segments)).resolve()
    if not str(resolved).startswith(str(project_dir.resolve())):
        raise LitePathError(f"路径逃逸出项目目录: {rel_path!r}")

    return resolved


async def _write_json(path: Path, data: dict) -> None:
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


async def _write_text(path: Path, content: str) -> None:
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_text, content, "utf-8")


def _ensure_section_heading(target_file: str, title: str, content: str) -> str:
    stripped = content.lstrip()
    expected = f"# {section_label(target_file)} {title}"
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
    if not await asyncio.to_thread(vol_meta.exists):
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
    if not await asyncio.to_thread(ch_meta.exists):
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
        if not await asyncio.to_thread(file_path.exists):
            await _write_text(file_path, f"# 第{volume_number}卷 第{chapter_number}章 {title} - 第{section_number}场景\n\n")
    return section_path(volume_number, chapter_number, 1)








def _fallback_section_content(
    target_file: str,
    selected_card: LiteNextOptionCard,
    prefs_text: str,
    story_engine: str,
) -> str:
    label = section_label(target_file)
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






async def _next_writable_section_path(
    file_service: FileService,
    project_id: str,
    current_file: str | None,
) -> str:
    """找到当前文件之后第一个空场景，避免刷新后重复覆盖已写场景。"""
    candidate = next_section_path(current_file)
    metadata_svc = LiteStoryMetadataService(file_service)
    for _ in range(80):
        content = await metadata_svc.read_optional(project_id, candidate)
        if metadata_svc.is_blank_chapter(content):
            return candidate
        candidate = next_section_path(candidate)
    return candidate


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
        existing_plan, _, _ = await file_service.read_file(f"{project_id}/{existing_plan_path}")
        if not _is_blank_chapter(existing_plan):
            return existing_plan.strip()
    except Exception:
        logger.debug("读取已有章规划失败", exc_info=True)
    ch_title = ""
    try:
        meta_raw, _, _ = await file_service.read_file(f"{project_id}/{meta_path}")
        ch_meta = json.loads(meta_raw)
        ch_title = ch_meta.get("title", "")
    except Exception:
        logger.debug("读取章元数据失败", exc_info=True)

    messages = LitePromptBuilder.build_chapter_plan_messages(
        vol=vol,
        completed_ch=completed_ch,
        ch_title=ch_title,
        story_engine=story_engine,
        recent_context=recent_context,
        style_guide=style_guide,
        sections_per_chapter=SECTIONS_PER_CHAPTER,
    )
    try:
        content = (await llm_svc.complete_sync(
            messages,
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
        logger.debug("写入章规划文件失败", exc_info=True)


async def _generate_ideas_via_llm(
    settings,
    seed: str,
) -> list[LiteIdeaCard] | None:
    """用 LLM 动态生成 5 张开局爽文卡，失败返回 None"""
    try:
        llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, settings)
        llm_svc = LLMService.from_workspace_config(llm_cfg)
        lite_llm = LiteLLMService(llm_svc)
        messages = LitePromptBuilder.build_ideas_messages(
            genres=GENRES,
        )
        raw = await lite_llm.complete_with_deadline(
            messages,
            deadline=45,
            temperature=0.9,
            max_tokens=2000,
            timeout=40,
        )
        data = LiteOptionCardsService.extract_json_payload(raw)
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
        cards = LiteOptionCardsService.rotate_cards(req.seed)
    return ApiResponse.ok(LiteIdeasResponse(cards=cards))


@router.post("/lite/projects", response_model=ApiResponse[LiteProjectCreateResponse], status_code=201)
async def create_lite_project(
    req: LiteProjectCreateRequest,
    settings: Settings = Depends(get_settings),
):
    """根据开局卡创建无大纲爽文项目"""
    svc = LiteProjectService(settings)
    result = await svc.create_project(req)

    return ApiResponse.ok(result, message="爽文项目创建成功")


@router.post("/lite/next-options", response_model=ApiResponse[LiteNextOptionsResponse])
async def generate_next_options(
    req: LiteNextOptionsRequest,
    settings: Settings = Depends(get_settings),
):
    """生成下一章爽点卡"""
    _validate_project_id(req.project_id)
    if req.current_file:
        _validate_rel_path(req.current_file)
    project_dir = settings.projects_path / req.project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(req.project_id)

    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    metadata_svc = LiteStoryMetadataService(file_service)
    current_content = await metadata_svc.read_optional(req.project_id, req.current_file or "")
    current_no = max(1, extract_chapter_number(req.current_file) or 1)
    if req.current_file and metadata_svc.is_blank_chapter(current_content):
        next_file = req.current_file
    else:
        next_file = await _next_writable_section_path(file_service, req.project_id, req.current_file)
    next_label = section_label(next_file)
    story_engine = await metadata_svc.read_optional(req.project_id, "story-engine.md")
    recent_context = await metadata_svc.read_optional(req.project_id, "recent-context.md")
    vol, ch, _sec = path_parts(next_file)
    chapter_plan = await metadata_svc.read_optional(req.project_id, f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-plan.md")
    chapter_context = await metadata_svc.read_chapter_context(req.project_id, vol, ch, _sec)
    context_content = current_content if not metadata_svc.is_blank_chapter(current_content) else chapter_context

    cards = LiteOptionCardsService.fallback_next_cards(next_label, context_content, recent_context)
    try:
        llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, settings)
        llm_svc = LLMService.from_workspace_config(llm_cfg)
        lite_llm = LiteLLMService(llm_svc)
        messages = LitePromptBuilder.build_next_options_messages(
            next_label=next_label,
            preferences_text=LitePromptBuilder.format_preferences(req.prefs),
            context_content=context_content,
            story_engine=story_engine,
            recent_context=recent_context,
            chapter_plan=chapter_plan,
        )
        raw = await lite_llm.complete_with_deadline(
            messages,
            deadline=20,
            temperature=0.85,
            max_tokens=900,
            timeout=20,
        )
        parsed_cards = LiteOptionCardsService.parse_option_cards(raw, next_label)
        if len(parsed_cards) == 3:
            cards = parsed_cards
    except Exception as e:
        logger.warning("动态生成爽点卡失败，使用上下文兜底卡: %s", e)
    return ApiResponse.ok(LiteNextOptionsResponse(
        cards=cards,
        current_file=req.current_file or chapter_path(current_no),
        next_file=next_file,
    ))


@router.post("/lite/write-next", response_model=ApiResponse[LiteWriteNextResponse])
async def write_lite_next(
    req: LiteWriteNextRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """选卡生成章节，自动审稿并更新故事引擎"""
    _validate_project_id(req.project_id)
    if req.target_file:
        _validate_rel_path(req.target_file)
    project_dir = settings.projects_path / req.project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(req.project_id)

    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
    metadata_svc = LiteStoryMetadataService(file_service)
    requested_content = await metadata_svc.read_optional(req.project_id, req.target_file or "") if req.target_file else ""
    is_blank_requested = metadata_svc.is_blank_chapter(requested_content)
    effective_action = LITE_ACTION_ALIAS.get(req.action, req.action)
    if (effective_action != "write" and req.target_file) or (req.target_file and is_blank_requested):
        target_file = req.target_file
    else:
        target_file = await _next_writable_section_path(file_service, req.project_id, req.target_file)
    is_candidate = _should_use_candidate(req.action, target_file, requested_content, is_blank_requested)
    output_file = target_file
    vol, ch, _sec = path_parts(target_file)
    await _ensure_chapter(project_dir, vol, ch, req.selected_card.title)

    prev_content = await metadata_svc.read_chapter_context(req.project_id, vol, ch, _sec)
    target_content = await metadata_svc.read_optional(req.project_id, target_file)
    current_content = prev_content + target_content
    story_engine = await metadata_svc.read_optional(req.project_id, "story-engine.md")
    story_state = await metadata_svc.read_optional(req.project_id, "story-state.md")
    style_guide = await metadata_svc.read_optional(req.project_id, "style-guide.md")
    recent_context = await metadata_svc.read_optional(req.project_id, "recent-context.md")

    # 如果当前章有章规划，加入生成上下文
    chapter_plan = ""
    if ch and _sec:
        plan_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-plan.md"
        plan_content = await metadata_svc.read_optional(req.project_id, plan_path)
        if plan_content and not metadata_svc.is_blank_chapter(plan_content):
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
        LitePromptBuilder.format_preferences(req.prefs),
        ("章规划：\n" + chapter_plan) if chapter_plan else "",
        "故事引擎：",
        story_engine,
    ])

    # 读取章节记忆和待回收伏笔
    ch_meta_data = await metadata_svc.read_ch_meta(req.project_id, vol, ch)
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

    llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, settings)
    llm_svc = LLMService.from_workspace_config(llm_cfg)
    lite_llm = LiteLLMService(llm_svc)
    prefs_text = LitePromptBuilder.format_preferences(req.prefs)
    used_fallback = False
    try:
        content = await lite_llm.complete_with_deadline(
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
    candidate_info = None
    if is_candidate:
        candidate_info = await _create_lite_candidate(
            file_service, req.project_id, target_file, req.action, content,
        )
        output_file = candidate_info.candidate_path
        event_bus = getattr(request.app.state, "event_bus", None)
        if event_bus:
            evt = make_candidate_created_event(
                project_id=req.project_id,
                candidate_id=candidate_info.id,
                source_path=target_file,
                action=candidate_info.action,
                source="api/lite",
            )
            await event_bus.publish(evt.type, evt.to_sse_dict())
    else:
        await file_service.write_file(f"{req.project_id}/{output_file}", content)

    if not is_candidate:
        # 更新章节记忆和待回收伏笔
        await metadata_svc.update_ch_meta(req.project_id, vol, ch, _sec, req.selected_card.title, req.selected_card.payoff, req.selected_card.hook)

    quality_summary = ""
    if is_candidate:
        quality_summary = "候选稿已生成，确认满意后可采用替换原文。"
    elif used_fallback:
        quality_summary = "模型生成超时，已先写入临时草稿；可点“重写当前场景”补成正式正文。"
    else:
        try:
            quality = QualityService(settings)
            review = await asyncio.wait_for(
                quality.perform_review(req.project_id, target_file, req.selected_card.title),
                timeout=75,
            )
            await asyncio.to_thread(quality.save_review_result, req.project_id, target_file, str(uuid.uuid4())[:8], review)
            quality_summary = LiteQualityService.quality_one_line(review.summary, req.action)
            if LiteQualityService.needs_quality_repair(review):
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
                repaired = await lite_llm.complete_with_deadline(
                    [{"role": "user", "content": repair_prompt}],
                    deadline=75,
                    temperature=0.65,
                    max_tokens=6000,
                    timeout=60,
                )
                if repaired:
                    content = _ensure_section_heading(target_file, req.selected_card.title, repaired)
                    await file_service.write_file(f"{req.project_id}/{output_file}", content)
                    quality_summary = "已根据审稿意见自动补强逻辑、动机和爽点。"
        except Exception as e:
            logger.warning("爽文模式质量审查失败: %s", e)
            quality_summary = LiteQualityService.quality_one_line("", req.action)

    if is_candidate:
        updated_engine = story_engine
    else:
        updated_engine = metadata_svc.build_story_engine_update(story_engine, target_file, req.selected_card, content)
        await file_service.write_file(f"{req.project_id}/story-engine.md", updated_engine)
        await file_service.write_file(
            f"{req.project_id}/recent-context.md",
            recent_context.rstrip() + f"\n\n- {Path(target_file).parent.name}：{req.selected_card.title}，{req.selected_card.payoff}",
        )

    # 完成最后一场景（sec == SECTIONS_PER_CHAPTER）→ 整章写完，自动生成下一章章规划
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

    return ApiResponse.ok(LiteWriteNextResponse(
        file_path=output_file,
        content=content,
        quality_summary=quality_summary,
        story_engine_summary=metadata_svc.summarize_story_engine(updated_engine),
        chapter_plan=chapter_plan_result,
        candidate_id=candidate_info.id if candidate_info else None,
        source_file=target_file if candidate_info else None,
    ), message="场景已生成")


@router.post("/lite/write-next-stream")
async def write_lite_next_stream(
    req: LiteWriteNextRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """选卡生成章节，流式输出正文，再审稿并更新故事引擎"""

    async def _stream() -> AsyncGenerator[dict, None]:
        try:
            _validate_project_id(req.project_id)
            if req.target_file:
                _validate_rel_path(req.target_file)
        except LitePathError as e:
            yield _lite_stream_event("error", {"message": str(e)})
            return
        project_dir = settings.projects_path / req.project_id
        if not await asyncio.to_thread(project_dir.exists):
            yield _lite_stream_event("error", {"message": f"项目不存在：{req.project_id}"})
            return

        file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)
        metadata_svc = LiteStoryMetadataService(file_service)
        requested_content = await metadata_svc.read_optional(req.project_id, req.target_file or "") if req.target_file else ""
        is_blank_requested = metadata_svc.is_blank_chapter(requested_content)
        effective_action = LITE_ACTION_ALIAS.get(req.action, req.action)
        if (effective_action in ("continue", "rewrite", "more_exciting", "more_reasonable") and req.target_file) or (req.target_file and is_blank_requested):
            target_file = req.target_file
        else:
            target_file = await _next_writable_section_path(file_service, req.project_id, req.target_file)
        # 候选稿策略：高风险操作（rewrite/more_exciting/more_reasonable/continue）对已有内容的场景生成 candidate
        # 详见 backend/policies/candidate_policy.py
        is_candidate = _should_use_candidate(req.action, target_file, requested_content, is_blank_requested)
        output_file = target_file

        vol, ch, _sec = path_parts(target_file)
        await _ensure_chapter(project_dir, vol, ch, req.selected_card.title)
        yield _lite_stream_event("meta", {
            "file_path": output_file,
            "source_file": target_file,
            "is_candidate": is_candidate,
            "label": section_label(target_file),
        })

        try:
            prev_content = await metadata_svc.read_chapter_context(req.project_id, vol, ch, _sec)
            target_content = await metadata_svc.read_optional(req.project_id, target_file)
            current_content = prev_content + target_content
            story_engine = await metadata_svc.read_optional(req.project_id, "story-engine.md")
            story_state = await metadata_svc.read_optional(req.project_id, "story-state.md")
            style_guide = await metadata_svc.read_optional(req.project_id, "style-guide.md")
            recent_context = await metadata_svc.read_optional(req.project_id, "recent-context.md")

            chapter_plan = ""
            if ch and _sec:
                plan_path = f"chapters/vol-{vol:02d}/ch-{ch:03d}/ch-plan.md"
                plan_content = await metadata_svc.read_optional(req.project_id, plan_path)
                if plan_content and not metadata_svc.is_blank_chapter(plan_content):
                    chapter_plan = plan_content

            # 读取章节记忆和待回收伏笔
            ch_meta_data = await metadata_svc.read_ch_meta(req.project_id, vol, ch)
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

            prefs_text = LitePromptBuilder.format_preferences(req.prefs)
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

            llm_cfg = await asyncio.to_thread(load_llm_config_from_workspace, settings)
            llm_svc = LLMService.from_workspace_config(llm_cfg)
            lite_llm = LiteLLMService(llm_svc)
            content_parts: list[str] = []
            used_fallback = False
            yield _lite_stream_event("status", {"message": "AI 正在写正文..."})

            try:
                async for chunk in lite_llm.stream_llm_content(
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
            if effective_action == "continue" and target_content.strip():
                content = target_content.rstrip() + "\n\n" + generated_text
            else:
                content = generated_text
            yield _lite_stream_event("replace", {"content": content.strip()})  # AI_GUARDRAIL_ALLOW: lite streaming event, not file.updated

            content = _ensure_section_heading(target_file, req.selected_card.title, content.strip())
            candidate_info = None
            if is_candidate:
                candidate_info = await _create_lite_candidate(
                    file_service, req.project_id, target_file, req.action, content,
                )
                output_file = candidate_info.candidate_path
                event_bus = getattr(request.app.state, "event_bus", None)
                if event_bus:
                    evt = make_candidate_created_event(
                        project_id=req.project_id,
                        candidate_id=candidate_info.id,
                        source_path=target_file,
                        action=candidate_info.action,
                        source="api/lite",
                    )
                    await event_bus.publish(evt.type, evt.to_sse_dict())
            else:
                await file_service.write_file(f"{req.project_id}/{output_file}", content)

            if not is_candidate:
                # 更新章节记忆和待回收伏笔
                await metadata_svc.update_ch_meta(req.project_id, vol, ch, _sec, req.selected_card.title, req.selected_card.payoff, req.selected_card.hook)

            quality_summary = "候选稿已生成，确认满意后可采用替换原文。" if is_candidate else "模型生成超时，已先写入临时草稿；可点“重写当前场景”补成正式正文。" if used_fallback else "正文已写入，审稿将在后台完成。"

            async def _review_in_background() -> None:
                try:
                    quality = QualityService(settings)
                    review = await quality.perform_review(req.project_id, target_file, req.selected_card.title)
                    await asyncio.to_thread(quality.save_review_result, req.project_id, target_file, str(uuid.uuid4())[:8], review)
                except Exception as e:
                    logger.warning("爽文模式后台质量审查失败: %s", e)

            if not used_fallback and not is_candidate:
                asyncio.create_task(_review_in_background())

            if is_candidate:
                updated_engine = story_engine
            else:
                yield _lite_stream_event("status", {"message": "正在更新故事状态..."})
                updated_engine = metadata_svc.build_story_engine_update(story_engine, target_file, req.selected_card, content)
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
                "content": content,  # AI_GUARDRAIL_ALLOW: lite generation result, not file.updated
                "quality_summary": quality_summary,
                "story_engine_summary": metadata_svc.summarize_story_engine(updated_engine),
                "chapter_plan": chapter_plan_result,
                "candidate_id": candidate_info.id if candidate_info else None,
                "source_file": target_file if candidate_info else None,
            })
        except Exception as e:
            logger.exception("爽文流式生成异常: %s", e)
            yield _lite_stream_event("error", {"message": f"生成失败：{e!s}"})

    return EventSourceResponse(_stream())
