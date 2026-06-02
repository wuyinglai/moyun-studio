import pytest

from backend.api.lite import (
    CHAPTERS_PER_VOLUME,
    SECTIONS_PER_CHAPTER,
    _ensure_chapter,
    _next_writable_section_path,
    _prefs_to_text,
    _story_engine_template,
)
from backend.application.lite_scene_service import path_parts
from backend.application.lite_story_metadata_service import LiteStoryMetadataService
from backend.core.file_ops import FileService
from backend.schemas.lite import LiteNextOptionCard


@pytest.mark.asyncio
async def test_lite_mode_advances_eight_sections_without_outline(tmp_path):
    projects_root = tmp_path / "projects"
    project_id = "lite-longform"
    project_dir = projects_root / project_id
    project_dir.mkdir(parents=True)
    file_service = FileService(projects_root)

    from backend.application.lite_option_cards_service import LiteOptionCardsService, FALLBACK_IDEA_BANK
    from backend.schemas.lite import LiteWritingPrefs

    story_engine = _story_engine_template(FALLBACK_IDEA_BANK[0], _prefs_to_text(LiteWritingPrefs()))
    await file_service.write_file(f"{project_id}/story-engine.md", story_engine)

    current_file = None
    written_files: list[str] = []
    for idx in range(SECTIONS_PER_CHAPTER * 2):
        target_file = await _next_writable_section_path(file_service, project_id, current_file)
        vol, ch, sec = path_parts(target_file)
        await _ensure_chapter(project_dir, vol, ch, f"测试第{ch}章")
        card = LiteNextOptionCard(
            id=f"card-{idx + 1}",
            title=f"第{idx + 1}节推进",
            beat="用当前事件继续制造压力和反馈。",
            scene=f"第{idx + 1}节冲突现场",
            protagonist_desire="主角要拿到一个明确收益。",
            obstacle="对手把规则和旁观者都变成阻力。",
            payoff="主角完成一次可见反击。",
            hook="更高层对手注意到主角。",
            advancement="把本节胜利接到下一节压力。",
        )
        content = f"# 测试第{idx + 1}节\n\n这是第{idx + 1}节的有效正文，主角完成行动并留下后续钩子。"
        await file_service.write_file(f"{project_id}/{target_file}", content)
        metadata_svc = LiteStoryMetadataService(file_service)
        story_engine = metadata_svc.build_story_engine_update(story_engine, target_file, card, content)
        await file_service.write_file(f"{project_id}/story-engine.md", story_engine)
        written_files.append(target_file)
        current_file = target_file

    assert written_files[0].endswith("vol-01/ch-001/sec-001.md")
    assert written_files[3].endswith("vol-01/ch-001/sec-004.md")
    assert written_files[4].endswith("vol-01/ch-001/sec-005.md")
    assert written_files[5].endswith("vol-01/ch-002/sec-001.md")
    assert written_files[9].endswith("vol-01/ch-002/sec-005.md")

    next_file = await _next_writable_section_path(file_service, project_id, current_file)
    assert next_file.endswith("vol-01/ch-003/sec-001.md")
    assert CHAPTERS_PER_VOLUME == 12

    metadata_svc = LiteStoryMetadataService(file_service)
    summary = metadata_svc.summarize_story_engine(story_engine)
    assert "protagonist_goal" in summary
    assert "payoff_ledger" in summary
    assert story_engine.count("## 最近推进") == SECTIONS_PER_CHAPTER * 2
    assert written_files[-1] in story_engine
    assert story_engine.count("- ") >= SECTIONS_PER_CHAPTER * 2
