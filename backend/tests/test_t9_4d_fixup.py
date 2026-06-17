"""T9.4d-fixup additional cases: second repair + continuity anchors via service"""
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import get_settings
from backend.core.file_ops import FileService
from backend.core.candidate_service import CandidateService, CandidateAction, CandidateStatus
from backend.core.continuity_anchor_service import ContinuityAnchorService
from backend.schemas.continuity_anchor import ContinuityAnchor, ContinuityAnchorType, ContinuityAnchorScope, ContinuityAnchorPriority, ContinuityAnchorStatus
from backend.core.llm import LLMService, load_llm_config_from_workspace
from datetime import datetime, timezone


def get_llm_service() -> LLMService:
    settings = get_settings()
    llm_cfg = load_llm_config_from_workspace(settings)
    return LLMService.from_workspace_config(llm_cfg)


def build_repair_prompt(source_text: str, parent_content: str, warnings_text: str, required_beats=None, forbidden_beats=None) -> list[dict]:
    prompt = f"""你正在根据系统警告信息修复一个候选稿。
重要规则：
- 这是生成新的 child candidate，不是修改正式正文
- 正式正文事务点不可覆盖
- 父候选稿是待修复的内容，不是最终事实
- 不要自动覆盖正式正文
- 不要自动采用候选稿
- 输出修复后的完整候选稿正文
- 不要输出解释、评分、列表、标题或任何额外信息

## 源文件路径：chapters/vol-01/ch-007/sec-001.md

## 正式正文事务点：{source_text}

## 父候选稿：{parent_content}

## 系统警告信息：
{warnings_text}
"""
    if required_beats:
        prompt += "\n## 必须保留的信息点\n"
        for beat in required_beats:
            prompt += f"- {beat['text']}\n"
    if forbidden_beats:
        prompt += "\n## 必须避免的内容\n"
        for beat in forbidden_beats:
            prompt += f"- {beat['text']}\n"
    prompt += "\n请根据以上警告信息修复父候选稿。现在只输出修复后的候选稿正文："
    return [
        {"role": "system", "content": "你是一名小说修复助手。"},
        {"role": "user", "content": prompt},
    ]


def build_rewrite_prompt(source_text: str, continuity_anchors_text: list[str] = None, required_beats=None, forbidden_beats=None) -> list[dict]:
    system_prompt = """你是一名资深小说作者，擅长重写场景而不改变核心剧情。

## 重要规则
- 只输出重写后的场景正文，不要输出任何解释、标题、评分
- 目标字数：600-1000 字
- 保留原文的核心要素
"""
    user_prompt = f"""## 原文

{source_text}

"""
    if required_beats:
        user_prompt += "## 必须保留的信息点\n"
        for beat in required_beats:
            user_prompt += f"- {beat['text']}\n"
        user_prompt += "\n"
    if forbidden_beats:
        user_prompt += "## 必须避免的内容\n"
        for beat in forbidden_beats:
            user_prompt += f"- {beat['text']}\n"
        user_prompt += "\n"
    if continuity_anchors_text:
        user_prompt += "## 上下文约束（必须遵守）\n"
        for anchor in continuity_anchors_text:
            user_prompt += f"- {anchor}\n"
        user_prompt += "\n"
    user_prompt += "请重写上述场景，保持核心要素，输出正文。"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def case_7_second_repair(workspace: Path, project_id: str, llm: LLMService):
    """Case 7: Second Repair - Repair from Forbidden Reveal parent"""
    print("\n" + "="*60)
    print("Case 7: Second Repair - Forbidden Reveal Parent")
    print("="*60)

    # 构造一个带 forbidden warning 的 parent
    source_text = "主角看着芯片上的残缺坐标，隐约觉得它和失踪的师父有关。"
    parent_content = "主角盯着手中的芯片，残缺的坐标在微光中若隐若现。\n\n【警告：此版本未保留芯片细节，可能违反 required beat】"

    required_beats = [
        {"id": "beat-1", "text": "芯片必须保留", "status": "required"},
    ]
    forbidden_beats = [
        {"id": "fbeat-1", "text": "不能揭晓坐标完整目的地", "status": "forbidden"},
    ]

    project_dir = workspace / project_id
    source_path = "chapters/vol-01/ch-007/sec-001.md"
    full_path = project_dir / source_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(source_text, encoding="utf-8")

    fs = FileService(workspace)
    svc = CandidateService(fs)

    parent = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content=parent_content,
        beat_validation={
            "status": "warning",
            "summary": "missing required beat detail",
            "required_beats": required_beats,
            "forbidden_beats": forbidden_beats,
        },
        generation_context={"required_beats_input": required_beats, "forbidden_beats_input": forbidden_beats},
    )

    print(f"Parent ID: {parent.id}, Status: {parent.status}, Quality: {parent.quality}")

    parent_content_before = await svc.get_candidate_content(project_id, parent.id)
    source_before = (project_dir / source_path).read_text(encoding="utf-8")

    # Repair
    warnings_text = svc._build_repair_warnings(parent)
    messages = build_repair_prompt(source_text, parent_content, warnings_text, required_beats, forbidden_beats)
    child_content = await llm.complete_sync(messages, max_tokens=2000)
    child_content = re.sub(r'^#+.*$', '', child_content, flags=re.MULTILINE).strip()

    child = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REPAIR,
        content=child_content,
        parent_candidate_id=parent.id,
        revision_group_id=parent.id,
        revision_index=1,
    )

    parent_content_after = await svc.get_candidate_content(project_id, parent.id)
    source_after = (project_dir / source_path).read_text(encoding="utf-8")

    print(f"Repair Child ID: {child.id}")
    print(f"Child Action: {child.action}")
    print(f"Child Parent ID: {child.parent_candidate_id}")
    print(f"Child Status: {child.status}")
    print(f"Child Quality: {child.quality}")
    print(f"Parent content unchanged: {parent_content_before == parent_content_after}")
    print(f"Source unchanged: {source_before == source_after}")
    print(f"Child content (first 200 chars): {child_content[:200]}")
    return child


async def case_8_continuity_via_service(workspace: Path, project_id: str, llm: LLMService):
    """Case 8: Continuity Anchors via proper ContinuityAnchorService"""
    print("\n" + "="*60)
    print("Case 8: Continuity Anchors via ContinuityAnchorService")
    print("="*60)

    source_text = "主角在旧码头捡起银色芯片。女主站在他身后，沉默地看着远处的雨幕。"

    # Step 1: Write proper continuity anchors to the project file
    project_dir = workspace / project_id
    anchors_file = project_dir / "continuity-anchors.json"
    anchors_file.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    anchors = [
        ContinuityAnchor(
            id="anchor-1",
            status=ContinuityAnchorStatus.ACTIVE,
            type=ContinuityAnchorType.CHARACTER_STATE,
            title="女主右肩受伤",
            content="女主右肩受伤，尚未痊愈，不能用右手持剑。",
            scope=ContinuityAnchorScope.SCENE,
            priority=ContinuityAnchorPriority.HIGH,
            created_at=now,
            updated_at=now,
        ),
        ContinuityAnchor(
            id="anchor-2",
            status=ContinuityAnchorStatus.ACTIVE,
            type=ContinuityAnchorType.OBJECT_LOCATION,
            title="银色芯片",
            content="银色芯片出现过，但完整坐标目的地尚未揭晓。",
            scope=ContinuityAnchorScope.SCENE,
            priority=ContinuityAnchorPriority.NORMAL,
            created_at=now,
            updated_at=now,
        ),
        ContinuityAnchor(
            id="anchor-3",
            status=ContinuityAnchorStatus.ACTIVE,
            type=ContinuityAnchorType.RELATIONSHIP,
            title="女主戒心",
            content="女主对主角态度软化，但仍有戒心，不能突然表白。",
            scope=ContinuityAnchorScope.SCENE,
            priority=ContinuityAnchorPriority.NORMAL,
            created_at=now,
            updated_at=now,
        ),
        # Inactive anchor should be filtered out
        ContinuityAnchor(
            id="anchor-4",
            status=ContinuityAnchorStatus.ARCHIVED,
            type=ContinuityAnchorType.OBJECT_LOCATION,
            title="旧锚点",
            content="这个锚点已经失效。",
            scope=ContinuityAnchorScope.SCENE,
            priority=ContinuityAnchorPriority.LOW,
            created_at=now,
            updated_at=now,
        ),
    ]

    from backend.schemas.continuity_anchor import ContinuityAnchorsDocument
    doc = ContinuityAnchorsDocument(anchors=anchors)
    anchors_file.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote {len(anchors)} anchors to {anchors_file} (1 inactive)")

    # Step 2: Verify service reads correct count
    fs = FileService(workspace)
    anchor_svc = ContinuityAnchorService(fs)
    active_anchors = await anchor_svc.list_active(project_id)
    print(f"Active anchors from service: {len(active_anchors)}")
    for a in active_anchors:
        print(f"  - {a.id}: {a.title} ({a.status.value})")

    # Step 3: Call create_candidate WITHOUT manually passing continuity_anchors
    # Let the service compute it via list_active()
    source_path = "chapters/vol-01/ch-008/sec-001.md"
    full_path = project_dir / source_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(source_text, encoding="utf-8")

    svc = CandidateService(fs)

    # Build prompt including continuity anchors text
    continuity_texts = [a.content for a in active_anchors]
    messages = build_rewrite_prompt(source_text, continuity_anchors_text=continuity_texts)
    content = await llm.complete_sync(messages, max_tokens=2000)
    content = re.sub(r'^#+.*$', '', content, flags=re.MULTILINE).strip()

    # Create candidate without manually passing continuity_anchors
    # The service will use ContinuityAnchorService.list_active()
    candidate = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content=content,
        # NOTE: we do NOT pass continuity_anchors here
        # The service's create_candidate will call list_active() itself
    )

    source_now = (project_dir / source_path).read_text(encoding="utf-8")

    # Get continuity metadata from candidate
    continuity_meta = candidate.continuity_anchors
    print(f"Candidate ID: {candidate.id}")
    print(f"Continuity anchors metadata: {continuity_meta}")
    print(f"Active anchors used_count: {continuity_meta.get('used_count', 0) if continuity_meta else 0}")
    print(f"Quality: {candidate.quality}")
    print(f"Source unchanged: {source_now == source_text}")

    return {
        "candidate": candidate,
        "active_count": len(active_anchors),
        "continuity_meta": continuity_meta,
    }


async def main():
    print("T9.4d-fixup: Second Repair + Continuity via Service")
    print("="*60)

    settings = get_settings()
    workspace = settings.workspace_path / "llm-dogfood"
    workspace.mkdir(parents=True, exist_ok=True)

    project_id = f"__llm_smoke_{uuid.uuid4().hex[:8]}"

    # Create project
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    meta = {"id": project_id, "title": "T9.4d-fixup Dogfood", "created_at": "2026-06-17T00:00:00Z"}
    (project_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    llm = get_llm_service()
    print(f"LLM: {llm.config.provider}/{llm.config.model}")

    results = {}

    # Case 7: Second Repair
    try:
        case_7 = await case_7_second_repair(workspace, project_id, llm)
        results["Case 7: Second Repair"] = {
            "id": case_7.id,
            "action": case_7.action,
            "status": case_7.status,
            "parent_id": case_7.parent_candidate_id,
            "quality": str(case_7.quality),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        results["Case 7: Second Repair"] = {"error": str(e)}

    # Case 8: Continuity via Service
    try:
        case_8 = await case_8_continuity_via_service(workspace, project_id, llm)
        results["Case 8: Continuity via Service"] = {
            "id": case_8["candidate"].id,
            "action": case_8["candidate"].action,
            "status": case_8["candidate"].status,
            "active_anchor_count": case_8["active_count"],
            "used_count": case_8["continuity_meta"].get("used_count", 0) if case_8["continuity_meta"] else 0,
            "anchor_ids": case_8["continuity_meta"].get("anchor_ids", []) if case_8["continuity_meta"] else [],
            "types": case_8["continuity_meta"].get("types", {}) if case_8["continuity_meta"] else {},
            "quality": str(case_8["candidate"].quality),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        results["Case 8: Continuity via Service"] = {"error": str(e)}

    print("\n" + "="*60)
    print("Fixup Summary")
    print("="*60)
    for name, result in results.items():
        print(f"{name}: {result}")

    # Save results
    results_path = Path(__file__).parent.parent.parent / "docs" / "design" / "t9-4d-fixup-results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
