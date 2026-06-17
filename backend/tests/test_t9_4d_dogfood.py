"""T9.4d Real LLM Dogfood Test Script

直接调用 backend 服务层进行 dogfood 测试。
"""
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
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.beat_validator import RequiredBeatValidator


def get_llm_service() -> LLMService:
    settings = get_settings()
    llm_cfg = load_llm_config_from_workspace(settings)
    return LLMService.from_workspace_config(llm_cfg)


def build_rewrite_prompt(source_text: str, continuity_anchors: list[str] = None, required_beats=None, forbidden_beats=None) -> list[dict]:
    """构建 rewrite prompt"""
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

    if continuity_anchors:
        user_prompt += "## 上下文约束（必须遵守）\n"
        for anchor in continuity_anchors:
            user_prompt += f"- {anchor}\n"
        user_prompt += "\n"

    user_prompt += "请重写上述场景，保持核心要素，输出正文。"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_polish_prompt(source_text: str) -> list[dict]:
    """构建 polish prompt"""
    system_prompt = """你是一名专业的文字润色编辑。请对以下场景正文进行文笔提升：

## 重要规则
- 只输出润色后的场景正文，不要输出任何解释、标题、评分
- 尽量保留原意和文风
- 目标字数：600-1000 字
- 不要改变剧情事实
"""

    user_prompt = f"""## 原文

{source_text}

请润色上述场景，输出正文。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def create_project(workspace: Path, project_id: str, title: str = "Dogfood Test"):
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": project_id,
        "title": title,
        "created_at": "2026-06-17T00:00:00Z",
    }
    (project_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return project_dir


async def write_source(project_dir: Path, source_path: str, content: str):
    full_path = project_dir / source_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return full_path


async def case_1_rewrite_continuity(workspace: Path, project_id: str, llm: LLMService):
    """Case 1: Rewrite + Continuity Anchors"""
    print("\n" + "="*60)
    print("Case 1: Rewrite + Continuity Anchors")
    print("="*60)

    source_text = "主角在旧码头捡起银色芯片。女主站在他身后，沉默地看着远处的雨幕。"
    continuity_anchors = [
        "女主右肩受伤，尚未痊愈，不能用右手持剑。",
        "银色芯片出现过，但完整坐标目的地尚未揭晓。",
        "女主对主角态度软化，但仍有戒心，不能突然表白。",
    ]

    project_dir = workspace / project_id
    source_path = "chapters/vol-01/ch-001/sec-001.md"
    await write_source(project_dir, source_path, source_text)

    messages = build_rewrite_prompt(source_text, continuity_anchors=continuity_anchors)
    content = await llm.complete_sync(messages, max_tokens=2000)

    # 清理 markdown 标记
    content = re.sub(r'^#+.*$', '', content, flags=re.MULTILINE).strip()

    fs = FileService(workspace)
    svc = CandidateService(fs)

    candidate = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content=content,
        continuity_anchors={"anchors": continuity_anchors},
    )

    # 验证
    source_now = (project_dir / source_path).read_text(encoding="utf-8")
    print(f"Candidate ID: {candidate.id}")
    print(f"Action: {candidate.action}")
    print(f"Status: {candidate.status}")
    print(f"Quality: {candidate.quality}")
    print(f"Continuity anchors: {candidate.continuity_anchors}")
    print(f"Source unchanged: {source_now == source_text}")
    print(f"Content (first 200 chars): {content[:200]}")
    return candidate


async def case_2_polish(workspace: Path, project_id: str, llm: LLMService):
    """Case 2: Polish Conservative"""
    print("\n" + "="*60)
    print("Case 2: Polish Conservative")
    print("="*60)

    source_text = "她靠在门边，右肩还疼，可她还是跟着主角往前走。雨水从屋檐落下来，砸在青石板上。"

    project_dir = workspace / project_id
    source_path = "chapters/vol-01/ch-002/sec-001.md"
    await write_source(project_dir, source_path, source_text)

    messages = build_polish_prompt(source_text)
    content = await llm.complete_sync(messages, max_tokens=2000)
    content = re.sub(r'^#+.*$', '', content, flags=re.MULTILINE).strip()

    fs = FileService(workspace)
    svc = CandidateService(fs)

    candidate = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.POLISH,
        content=content,
    )

    source_now = (project_dir / source_path).read_text(encoding="utf-8")
    print(f"Candidate ID: {candidate.id}")
    print(f"Action: {candidate.action}")
    print(f"Status: {candidate.status}")
    print(f"Quality: {candidate.quality}")
    print(f"Source unchanged: {source_now == source_text}")
    print(f"Content (first 200 chars): {content[:200]}")
    return candidate


async def case_3_forbidden_reveal(workspace: Path, project_id: str, llm: LLMService):
    """Case 3: Forbidden Reveal"""
    print("\n" + "="*60)
    print("Case 3: Forbidden Reveal")
    print("="*60)

    source_text = "主角看着芯片上的残缺坐标，隐约觉得它和失踪的师父有关。"
    required_beats = [
        {"id": "beat-1", "text": "芯片必须保留", "status": "required"},
        {"id": "beat-2", "text": "残缺坐标必须保留", "status": "required"},
        {"id": "beat-3", "text": "主角不能完全理解坐标含义", "status": "required"},
    ]
    forbidden_beats = [
        {"id": "fbeat-1", "text": "不能揭晓坐标完整目的地", "status": "forbidden"},
        {"id": "fbeat-2", "text": "不能揭晓师父真实身份", "status": "forbidden"},
        {"id": "fbeat-3", "text": "不能新增神秘组织", "status": "forbidden"},
    ]

    project_dir = workspace / project_id
    source_path = "chapters/vol-01/ch-003/sec-001.md"
    await write_source(project_dir, source_path, source_text)

    messages = build_rewrite_prompt(source_text, required_beats=required_beats, forbidden_beats=forbidden_beats)
    content = await llm.complete_sync(messages, max_tokens=2000)
    content = re.sub(r'^#+.*$', '', content, flags=re.MULTILINE).strip()

    # 检查 forbidden reveal
    forbidden_violated = any(fbeat['text'] in content for fbeat in forbidden_beats if '揭晓' in fbeat['text'] or '身份' in fbeat['text'] or '组织' in fbeat['text'])

    fs = FileService(workspace)
    svc = CandidateService(fs)

    beat_validation = {
        "status": "warning" if forbidden_violated else "pass",
        "summary": "forbidden reveal detected" if forbidden_violated else "ok",
        "forbidden_violations": [fbeat['text'] for fbeat in forbidden_beats if fbeat['text'] in content] if forbidden_violated else [],
    }

    candidate = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content=content,
        beat_validation=beat_validation,
        generation_context={"required_beats_input": required_beats, "forbidden_beats_input": forbidden_beats},
    )

    source_now = (project_dir / source_path).read_text(encoding="utf-8")
    print(f"Candidate ID: {candidate.id}")
    print(f"Action: {candidate.action}")
    print(f"Status: {candidate.status}")
    print(f"Quality: {candidate.quality}")
    print(f"Beat validation: {candidate.beat_validation}")
    print(f"Forbidden violated: {forbidden_violated}")
    print(f"Source unchanged: {source_now == source_text}")
    print(f"Content (first 200 chars): {content[:200]}")
    return candidate


async def case_4_relationship_jump(workspace: Path, project_id: str, llm: LLMService):
    """Case 4: Relationship Jump"""
    print("\n" + "="*60)
    print("Case 4: Relationship Jump")
    print("="*60)

    source_text = '女主把披风还给主角，只说了一句："下次别再逞强。"她没有看他，却也没有立刻离开。'
    continuity_anchors = [
        "两人关系暧昧但未确认。",
        "女主对主角有信任，但仍保持戒心。",
        "两人不能突然表白，也不能突然完全和解。",
    ]

    project_dir = workspace / project_id
    source_path = "chapters/vol-01/ch-004/sec-001.md"
    await write_source(project_dir, source_path, source_text)

    messages = build_rewrite_prompt(source_text, continuity_anchors=continuity_anchors)
    content = await llm.complete_sync(messages, max_tokens=2000)
    content = re.sub(r'^#+.*$', '', content, flags=re.MULTILINE).strip()

    # 简单检查表白/和解
    confession_words = ["表白", "爱", "我喜欢你", "嫁给你"]
    reconciliation_words = ["和解", "和好", "冰释前嫌"]
    violated = any(w in content for w in confession_words + reconciliation_words)

    fs = FileService(workspace)
    svc = CandidateService(fs)

    candidate = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content=content,
        continuity_anchors={"anchors": continuity_anchors},
        beat_validation={"status": "warning", "summary": "relationship jump detected" if violated else "ok"},
    )

    print(f"Candidate ID: {candidate.id}")
    print(f"Action: {candidate.action}")
    print(f"Status: {candidate.status}")
    print(f"Quality: {candidate.quality}")
    print(f"Continuity anchors: {candidate.continuity_anchors}")
    print(f"Relationship jump detected: {violated}")
    print(f"Content (first 200 chars): {content[:200]}")
    return candidate


async def case_5_feedback_revision(workspace: Path, project_id: str, llm: LLMService):
    """Case 5: Feedback Revision"""
    print("\n" + "="*60)
    print("Case 5: Feedback Revision")
    print("="*60)

    source_text = "主角在旧码头捡起银色芯片。女主站在他身后，沉默地看着远处的雨幕。"
    parent_content = "旧码头上，主角的手指触到冰凉的金属。他低头一看，是一枚银色芯片，表面布满细密的电路纹理。女主站在他身后，目光越过他的肩头，落在远处的雨幕上，一言不发。"

    project_dir = workspace / project_id
    source_path = "chapters/vol-01/ch-005/sec-001.md"
    await write_source(project_dir, source_path, source_text)

    # 创建 parent candidate
    fs = FileService(workspace)
    svc = CandidateService(fs)

    parent = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content=parent_content,
    )

    print(f"Parent ID: {parent.id}, Status: {parent.status}")

    parent_content_before = await svc.get_candidate_content(project_id, parent.id)

    # Feedback revision
    feedback_text = "补强女主受伤带来的行动限制，但不要新增人物，不要揭晓芯片坐标真相。"
    prompt_template = "你正在根据用户反馈修订候选稿。\n\n## 原文\n{parent_candidate_text}\n\n## 用户反馈\n{feedback_text}\n\n## 规则\n- 只输出修订后的正文，不要解释\n- 目标字数：600-1000 字\n\n请输出修订后的正文："

    messages = [
        {"role": "system", "content": "你是一名小说修订助手。"},
        {"role": "user", "content": prompt_template.format(parent_candidate_text=parent_content, feedback_text=feedback_text)},
    ]

    child_content = await llm.complete_sync(messages, max_tokens=2000)
    child_content = re.sub(r'^#+.*$', '', child_content, flags=re.MULTILINE).strip()

    child = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.FEEDBACK_REVISION,
        content=child_content,
        parent_candidate_id=parent.id,
        revision_group_id=parent.id,
        revision_index=1,
        generation_context={"feedback_text": feedback_text},
    )

    parent_content_after = await svc.get_candidate_content(project_id, parent.id)

    print(f"Child ID: {child.id}")
    print(f"Child Action: {child.action}")
    print(f"Child Parent ID: {child.parent_candidate_id}")
    print(f"Parent content unchanged: {parent_content_before == parent_content_after}")
    print(f"Child content (first 200 chars): {child_content[:200]}")
    return child


async def case_6_repair_candidate(workspace: Path, project_id: str, llm: LLMService):
    """Case 6: Repair Candidate"""
    print("\n" + "="*60)
    print("Case 6: Repair Candidate")
    print("="*60)

    source_text = "主角看着芯片上的残缺坐标，隐约觉得它和失踪的师父有关。"
    parent_content = "主角盯着手中的芯片，残缺的坐标在微光中若隐若现。他隐约觉得，这和失踪的师父有关。但具体是什么，他还无法理解。"

    required_beats = [
        {"id": "beat-1", "text": "芯片必须保留", "status": "required"},
    ]
    forbidden_beats = [
        {"id": "fbeat-1", "text": "不能揭晓坐标完整目的地", "status": "forbidden"},
    ]

    project_dir = workspace / project_id
    source_path = "chapters/vol-01/ch-006/sec-001.md"
    await write_source(project_dir, source_path, source_text)

    fs = FileService(workspace)
    svc = CandidateService(fs)

    # 创建带 warning 的 parent
    parent = await svc.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content=parent_content,
        beat_validation={
            "status": "warning",
            "summary": "missing required beat",
            "required_beats": required_beats,
        },
        generation_context={"required_beats_input": required_beats, "forbidden_beats_input": forbidden_beats},
    )

    print(f"Parent ID: {parent.id}, Status: {parent.status}, Quality: {parent.quality}")

    parent_content_before = await svc.get_candidate_content(project_id, parent.id)
    source_before = (project_dir / source_path).read_text(encoding="utf-8")

    # Repair
    prompt_template = """你正在根据系统警告信息修复一个候选稿。
重要规则：
- 这是生成新的 child candidate，不是修改正式正文
- 正式正文事务点不可覆盖
- 父候选稿是待修复的内容，不是最终事实
- 不要自动覆盖正式正文
- 不要自动采用候选稿
- 输出修复后的完整候选稿正文
- 不要输出解释、评分、列表、标题或任何额外信息

## 源文件路径：{source_path}

## 正式正文事务点：{official_source_text}

## 父候选稿：{parent_candidate_text}

## 系统警告信息：
{warnings_text}

请根据以上警告信息修复父候选稿。现在只输出修复后的候选稿正文："""

    warnings_text = svc._build_repair_warnings(parent)
    source_content = source_text

    messages = [
        {"role": "system", "content": "你是一名小说修复助手。"},
        {"role": "user", "content": prompt_template.format(
            source_path=source_path,
            official_source_text=source_content,
            parent_candidate_text=parent_content,
            warnings_text=warnings_text,
        )},
    ]

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


async def main():
    print("T9.4d Real LLM Dogfood Test")
    print("Model: agnes-2.0-flash")
    print("Endpoint: https://apihub.agnes-ai.com/v1")
    print("="*60)

    settings = get_settings()
    workspace = settings.workspace_path / "llm-dogfood"
    workspace.mkdir(parents=True, exist_ok=True)

    project_id = f"__llm_smoke_{uuid.uuid4().hex[:8]}"
    await create_project(workspace, project_id, "T9.4d Dogfood Test")

    llm = get_llm_service()
    print(f"LLM Config: {llm.config.provider}/{llm.config.model}")

    results = {}

    cases = [
        ("Case 1: Rewrite + Continuity", case_1_rewrite_continuity),
        ("Case 2: Polish Conservative", case_2_polish),
        ("Case 3: Forbidden Reveal", case_3_forbidden_reveal),
        ("Case 4: Relationship Jump", case_4_relationship_jump),
        ("Case 5: Feedback Revision", case_5_feedback_revision),
        ("Case 6: Repair Candidate", case_6_repair_candidate),
    ]

    for name, func in cases:
        try:
            result = await func(workspace, project_id, llm)
            results[name] = {
                "id": result.id,
                "action": result.action,
                "status": result.status,
                "quality": str(result.quality) if result.quality else None,
            }
        except Exception as e:
            print(f"ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = {"error": str(e)}

    print("\n" + "="*60)
    print("Dogfood Test Summary")
    print("="*60)
    for name, result in results.items():
        print(f"{name}: {result}")

    # 保存结果
    results_path = Path(__file__).parent.parent.parent / "docs" / "design" / "t9-4d-dogfood-results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
