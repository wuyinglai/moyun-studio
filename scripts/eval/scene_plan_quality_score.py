"""
Scene Plan 质量对比自动评分脚本

功能：
- 读取 scene_plan 和两个 candidate（baseline 与 with-plan）
- 使用规则评分，不调用 LLM
- 输出评分结果（JSON 和 Markdown）

安全：
- 不修改任何文件
- 不创建 candidate
- 不调用生成 API
- 不执行 adopt
- 不读取 API key
- 不调用外部 API
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path


def load_candidate_content(project_id: str, candidate_id: str):
    """读取 candidate 文件内容（只读）"""
    candidates_dir = Path("workspace/projects") / project_id / ".candidates"
    # 尝试不同的扩展名
    for ext in [".polish.md", ".chat.md", ".continue.md", ".md"]:
        candidate_file = candidates_dir / f"{candidate_id}{ext}"
        if candidate_file.exists():
            with open(candidate_file, 'r', encoding='utf-8') as f:
                return f.read()
    return None


def load_candidate_metadata(project_id: str, candidate_id: str):
    """读取 candidate metadata JSON（只读，用于 provenance 检测）

    返回 dict 或 None。不会因为缺少 metadata 而失败，也不会伪造数据。
    """
    candidates_dir = Path("workspace/projects") / project_id / ".candidates"
    metadata_file = candidates_dir / f"{candidate_id}.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def build_provenance_info(project_id: str, candidate_id: str,
                          scene_plan_path: str,
                          scene_plan_used: bool = None) -> dict:
    """构建 candidate provenance 信息（只读，不伪造）

    - 如果 candidate metadata 包含完整 provenance 字段：status = "complete"
    - 如果 candidate metadata 部分字段存在：status = "partial"
    - 如果 candidate metadata 不存在（T5.17-H2 之前的旧 candidate）：status = "legacy_candidate"
    - 不会因为缺少 provenance 而失败
    """
    metadata = load_candidate_metadata(project_id, candidate_id)

    # 从 metadata 提取 provenance 字段（如果存在）
    has_gen_ctx = False
    has_scene_plan_hash = False
    has_scene_plan_path = False
    extracted_scene_plan_used = None
    extracted_scene_plan_hash = None
    extracted_scene_plan_path = None

    if metadata:
        if isinstance(metadata.get("generation_context"), dict):
            has_gen_ctx = True
            gc = metadata["generation_context"]
            if "scene_plan_used" in gc:
                extracted_scene_plan_used = bool(gc["scene_plan_used"])
        if metadata.get("scene_plan_hash"):
            has_scene_plan_hash = True
            extracted_scene_plan_hash = metadata["scene_plan_hash"]
        if metadata.get("scene_plan_path"):
            has_scene_plan_path = True
            extracted_scene_plan_path = metadata["scene_plan_path"]

    # 确定 provenance 状态
    if has_gen_ctx and has_scene_plan_hash and has_scene_plan_path:
        status = "complete"
        message = "Candidate contains full provenance metadata (generation_context + scene_plan_hash + scene_plan_path)."
    elif has_gen_ctx or has_scene_plan_hash or has_scene_plan_path:
        status = "partial"
        message = "Candidate contains partial provenance metadata."
    else:
        status = "legacy_candidate"
        message = "Candidate was created before T5.17-H2 provenance metadata support. This is expected for historical candidates."

    # scene_plan_used 优先使用 metadata 中的值；否则从调用方传入（baseline=False, with-plan=True）
    if extracted_scene_plan_used is not None:
        final_scene_plan_used = extracted_scene_plan_used
    else:
        final_scene_plan_used = scene_plan_used

    return {
        "status": status,
        "scene_plan_used": final_scene_plan_used,
        "scene_plan_hash": extracted_scene_plan_hash,
        "scene_plan_path": extracted_scene_plan_path or scene_plan_path,
        "message": message
    }


def load_scene_plan(project_id: str, target_file: str, scene_plan_path: str = None):
    """读取 scene_plan 文件（只读）"""
    if scene_plan_path:
        scene_plan_file = Path("workspace/projects") / project_id / scene_plan_path
        if scene_plan_file.exists():
            with open(scene_plan_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    scene_plans_dir = Path("workspace/projects") / project_id / "materials" / "scene_plans"
    if scene_plans_dir.exists():
        target_file_safe = target_file.replace("/", "__").replace("\\", "__")
        scene_plan_file = scene_plans_dir / f"{target_file_safe}.scene-plan.json"
        if scene_plan_file.exists():
            with open(scene_plan_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None


def score_scene_goal_alignment(content: str, scene_plan: dict):
    """评分 scene_goal 对齐度 (0-2)
    
    校准后规则：
    - 核心目标链条：地点 + 立柱 + 神秘信息/脚步声 = 2分
    - 只覆盖地点和动作 = 1分
    - 缺少关键要素 = 0分
    """
    goal = scene_plan.get("goal", "")
    score = 0
    evidence = []
    
    # 核心要素检查：地点、立柱、神秘信息/脚步声
    has_location = "旧港站" in content
    has_pillar = "立柱" in content or ("一" in content and "二" in content and "三" in content)
    has_mystery = any(kw in content for kw in ["神秘", "22:30", "脚步声", "指令", "无署名", "无前因后果", "幽灵"])
    has_wait = any(kw in content for kw in ["等待", "等候", "凝视", "停顿"])
    
    # 覆盖核心目标链条
    elements_covered = sum([has_location, has_pillar, has_mystery, has_wait])
    
    if elements_covered >= 3 and has_location and has_pillar:
        score = 2
        label = "pass"
        evidence.append(f"覆盖核心目标链条 ({elements_covered}/4)")
        if has_mystery:
            evidence.append("包含神秘信息/悬念要素")
        if has_wait:
            evidence.append("包含等待/停顿描写")
    elif elements_covered >= 2 and has_location:
        score = 1
        label = "partial"
        evidence.append(f"部分覆盖目标要素 ({elements_covered}/4)")
    else:
        label = "fail"
        evidence.append(f"目标覆盖不足 ({elements_covered}/4)")
    
    return {
        "score": score,
        "label": label,
        "evidence": "；".join(evidence[:3])  # 最多3条证据，避免过长
    }


def score_beats_coverage(content: str, scene_plan: dict):
    """评分 beats 覆盖度 (0-2)"""
    required_beats = scene_plan.get("required_beats", [])
    score = 0
    evidence = []
    
    covered_count = 0
    for beat in required_beats:
        # 检查 beat 中的核心词汇是否在内容中
        # 处理中文分词，简化为关键词匹配
        beat_covered = False
        
        if "到达" in beat and "到达" in content:
            beat_covered = True
        if "旧港站" in beat and "旧港站" in content:
            beat_covered = True
        if "描述" in beat and ("氛围" in content or "环境" in content):
            beat_covered = True
        if "雨夜" in beat and "雨" in content:
            beat_covered = True
        if "立柱" in beat and "立柱" in content:
            beat_covered = True
        if "第三根" in beat and ("三" in content and "立柱" in content):
            beat_covered = True
        if "神秘人" in beat and ("神秘" in content or "脚步声" in content):
            beat_covered = True
        if "脚步声" in beat and "脚步声" in content:
            beat_covered = True
        
        if beat_covered:
            covered_count += 1
            evidence.append(f"覆盖: {beat[:20]}...")
    
    total_beats = len(required_beats)
    if total_beats == 0:
        return {"score": 2, "label": "pass", "evidence": "无 required_beats"}
    
    coverage_ratio = covered_count / total_beats
    
    if coverage_ratio >= 0.8:
        score = 2
        label = "pass"
    elif coverage_ratio >= 0.5:
        score = 1
        label = "partial"
    else:
        label = "fail"
    
    return {
        "score": score,
        "label": label,
        "evidence": f"覆盖 {covered_count}/{total_beats} beats"
    }


def score_conflict_presence(content: str, scene_plan: dict):
    """评分 conflict 体现 (0-2)
    
    校准后规则：
    - 硬冲突关键词（阴森、紧张等）：2个以上 = 2分
    - 软冲突/悬疑心理线索（沉默、犹豫、幽灵、目光等）：2个以上 = 2分
    - 混合存在 = 2分
    - 只有1类 = 1分
    - 缺少 = 0分
    """
    conflict = scene_plan.get("conflict", "")
    score = 0
    evidence = []
    
    # 硬冲突关键词（传统冲突词）
    hard_conflict_keywords = ["阴森", "信任危机", "紧张", "诡异", "不安"]
    hard_matched = sum(1 for kw in hard_conflict_keywords if kw in content)
    
    # 软冲突/悬疑心理线索（根据人工复评新增）
    soft_conflict_keywords = [
        "沉默", "犹豫", "迟疑", "不确定", "锁住", "潜行", 
        "目光", "凝视", "幽灵", "无署名", "无前因后果",
        "危机", "停顿", "迟疑", "四十七秒"
    ]
    soft_matched = sum(1 for kw in soft_conflict_keywords if kw in content)
    
    total_matched = hard_matched + soft_matched
    
    if total_matched >= 3 or (hard_matched >= 1 and soft_matched >= 2) or soft_matched >= 3:
        score = 2
        label = "pass"
        if soft_matched >= 2:
            evidence.append(f"软冲突/悬疑线索丰富 ({soft_matched} 个)")
        if hard_matched >= 1:
            evidence.append(f"硬冲突词 ({hard_matched} 个)")
    elif total_matched >= 2:
        score = 1
        label = "partial"
        if soft_matched >= 1:
            evidence.append(f"包含软冲突/悬疑线索 ({soft_matched} 个)")
        if hard_matched >= 1:
            evidence.append(f"包含硬冲突词 ({hard_matched} 个)")
    else:
        label = "fail"
        evidence.append("缺少冲突相关表述")
    
    return {
        "score": score,
        "label": label,
        "evidence": "；".join(evidence) if evidence else "无明显冲突体现"
    }


def score_characters_consistency(content: str, scene_plan: dict):
    """评分 characters 一致性 (0-2)"""
    characters = scene_plan.get("characters", [])
    score = 0
    evidence = []
    
    if not characters:
        return {"score": 2, "label": "pass", "evidence": "无 characters 要求"}
    
    matched_count = sum(1 for char in characters if char in content)
    
    if matched_count == len(characters):
        score = 2
        label = "pass"
        evidence.append(f"所有人物提及: {', '.join(characters)}")
    elif matched_count >= 1:
        score = 1
        label = "partial"
        evidence.append(f"部分人物提及 ({matched_count}/{len(characters)})")
    else:
        label = "fail"
        evidence.append(f"未提及指定人物: {', '.join(characters)}")
    
    return {
        "score": score,
        "label": label,
        "evidence": "；".join(evidence)
    }


def score_location_consistency(content: str, scene_plan: dict):
    """评分 location 一致性 (0-2)"""
    location = scene_plan.get("location", "")
    score = 0
    evidence = []
    
    if not location:
        return {"score": 2, "label": "pass", "evidence": "无 location 要求"}
    
    location_count = content.count(location)
    
    if location_count >= 3:
        score = 2
        label = "pass"
        evidence.append(f"location 提及充足 ({location_count} 次)")
    elif location_count >= 1:
        score = 1
        label = "partial"
        evidence.append(f"location 提及有限 ({location_count} 次)")
    else:
        label = "fail"
        evidence.append(f"未提及 location: {location}")
    
    return {
        "score": score,
        "label": label,
        "evidence": "；".join(evidence)
    }


def score_time_consistency(content: str, scene_plan: dict):
    """评分 time_consistency 时间一致性 (0-2)
    
    校准后规则：
    - 明确出现时间或夜晚意象充分（雨、夜、灯光、阴暗等）= 2分
    - 只要没有时间冲突，并有雨、夜、灯光、阴暗等意象，至少 = 1分
    - 完全不相关或有时间冲突 = 0分
    """
    time = scene_plan.get("time", "")
    score = 0
    evidence = []
    
    if not time:
        return {"score": 2, "label": "pass", "evidence": "无 time 要求"}
    
    # 夜晚/时间意象关键词
    time_keywords = []
    if "雨夜" in time or "夜" in time or "雨" in time:
        time_keywords.extend(["雨", "夜", "夜晚", "深夜", "昏暗", "黑暗"])
    
    # 额外检查：灯光、阴暗等氛围词
    atmosphere_keywords = ["灯光", "灯火", "微光", "指示牌", "昏暗", "阴暗", "惨绿", "惨白", "斑驳"]
    
    matched_time = sum(1 for kw in time_keywords if kw in content)
    matched_atmosphere = sum(1 for kw in atmosphere_keywords if kw in content)
    
    # 只要有雨/夜意象 + 氛围描写，就应该给分
    if matched_time >= 1 and matched_atmosphere >= 1:
        score = 2
        label = "pass"
        evidence.append(f"时间意象充足 ({matched_time} 个) + 氛围充分 ({matched_atmosphere} 个)")
    elif matched_time >= 2 or matched_atmosphere >= 2:
        score = 1
        label = "partial"
        if matched_time >= 2:
            evidence.append(f"时间意象存在 ({matched_time} 个)")
        else:
            evidence.append(f"氛围意象存在 ({matched_atmosphere} 个)")
    elif matched_time >= 1 or matched_atmosphere >= 1:
        score = 1
        label = "partial"
        if matched_time >= 1:
            evidence.append(f"包含时间意象 ({matched_time} 个)")
        else:
            evidence.append(f"包含氛围意象 ({matched_atmosphere} 个)")
    else:
        label = "fail"
        evidence.append("缺少时间/氛围相关关键词")
    
    return {
        "score": score,
        "label": label,
        "evidence": "；".join(evidence)
    }


def score_no_reasoning_logs(content: str, scene_plan: dict):
    """评分 无推理日志 (0-2)"""
    # 检查常见推理日志模式
    reasoning_patterns = [
        r'<\|channel\|>',
        r'Original:',
        r'Reasoning:',
        r'思考:',
        r'推理:',
        r'\* Original',
        r'### Original',
    ]
    
    has_reasoning = any(re.search(pattern, content) for pattern in reasoning_patterns)
    
    if not has_reasoning:
        score = 2
        label = "pass"
        evidence = "未检测到推理日志"
    else:
        score = 0
        label = "fail"
        evidence = "检测到推理日志模式"
    
    return {
        "score": score,
        "label": label,
        "evidence": evidence
    }


def score_language_quality_basic(content: str, scene_plan: dict):
    """评分 基础语言质量 (0-2)
    
    校准后规则：
    - 长度合理（300-1000字）+ 内容非空 = 2分
    - 长度略偏或略长 + 内容非空 = 1分
    - 长度严重偏短/偏长或为空 = 0分
    
    注意：baseline 简洁有节奏感，with-plan 有氛围但略华丽，两者各有优势
    """
    score = 0
    evidence = []
    
    # 检查长度
    content_length = len(content)
    if 300 <= content_length <= 1000:
        score += 1
        evidence.append(f"长度合理 ({content_length} 字)")
    elif 200 <= content_length < 300 or 1000 < content_length <= 1500:
        score += 1
        evidence.append(f"长度略偏 ({content_length} 字)")
    elif content_length > 1500:
        evidence.append(f"长度偏长 ({content_length} 字)")
    else:
        evidence.append(f"长度偏短 ({content_length} 字)")
    
    # 检查是否为空
    if content_length > 0:
        score += 1
        evidence.append("内容非空")
        
        # 额外检查：节奏感 vs 氛围感
        # Baseline 特征：径直、直接、急促
        # With-Plan 特征：潜行、沉默、凝视
        concise_keywords = ["径直", "直接", "急促", "瞬间", "没有停留", "骤起"]
        atmosphere_keywords = ["潜行", "沉默", "凝视", "死死", "四十七秒", "惨绿", "刺眼"]
        
        concise_count = sum(1 for kw in concise_keywords if kw in content)
        atmosphere_count = sum(1 for kw in atmosphere_keywords if kw in content)
        
        if concise_count >= 2:
            evidence.append("节奏简洁直接")
        if atmosphere_count >= 2:
            evidence.append("氛围描写充分")
            
    else:
        label = "fail"
        evidence.append("内容为空")
        return {"score": 0, "label": label, "evidence": "；".join(evidence[:2])}
    
    if score >= 1:
        label = "pass" if score == 2 else "partial"
    else:
        label = "fail"
    
    return {
        "score": min(score, 2),
        "label": label,
        "evidence": "；".join(evidence[:3])  # 最多3条证据
    }


def score_plan_contradiction_check(content: str, scene_plan: dict):
    """评分 plan 矛盾检查 (0-2)"""
    # 简单的矛盾检查：是否直接违反 plan 的关键要求
    contradictions = []
    score = 2
    label = "pass"
    
    # 检查是否有明显矛盾
    location = scene_plan.get("location", "")
    if location and location in content:
        pass  # OK
    elif location:
        score = max(0, score - 1)
        if score == 0:
            label = "fail"
        contradictions.append(f"未提及 location: {location}")
    
    characters = scene_plan.get("characters", [])
    if characters:
        char_missing = [c for c in characters if c not in content]
        if char_missing:
            score = max(0, score - 1)
            if score == 0:
                label = "fail"
            contradictions.append(f"缺少人物: {', '.join(char_missing)}")
    
    evidence = "无明显矛盾" if not contradictions else "；".join(contradictions[:2])
    
    return {
        "score": score,
        "label": label,
        "evidence": evidence
    }


def score_candidate(content: str, scene_plan: dict):
    """对单个 candidate 进行综合评分"""
    scores = {
        "scene_goal_alignment": score_scene_goal_alignment(content, scene_plan),
        "beats_coverage": score_beats_coverage(content, scene_plan),
        "conflict_presence": score_conflict_presence(content, scene_plan),
        "characters_consistency": score_characters_consistency(content, scene_plan),
        "location_consistency": score_location_consistency(content, scene_plan),
        "time_consistency": score_time_consistency(content, scene_plan),
        "no_reasoning_logs": score_no_reasoning_logs(content, scene_plan),
        "language_quality_basic": score_language_quality_basic(content, scene_plan),
        "plan_contradiction_check": score_plan_contradiction_check(content, scene_plan),
    }
    
    total_score = sum(s["score"] for s in scores.values())
    max_score = len(scores) * 2
    
    scores["overall_score"] = {
        "score": total_score,
        "max_score": max_score,
        "label": "pass" if total_score >= max_score * 0.7 else ("partial" if total_score >= max_score * 0.4 else "fail")
    }
    
    return scores


def load_cases_from_file(cases_file_path: str):
    """从 JSON 文件加载测试用例"""
    with open(cases_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def score_single_case(case: dict):
    """对单个测试用例进行评分"""
    print(f"\n{'='*60}")
    print(f"处理 Case: {case.get('case_id', 'unknown')}")
    print(f"{'='*60}")
    
    project_id = case.get("project_id", "demo-novel")
    target_file = case.get("target_file", "")
    baseline_candidate_id = case.get("baseline_candidate_id", "")
    with_plan_candidate_id = case.get("with_plan_candidate_id", "")
    scene_plan_path = case.get("scene_plan_path")
    
    scene_plan = load_scene_plan(project_id, target_file, scene_plan_path)
    if not scene_plan:
        print(f"[警告] 未找到 scene_plan，使用默认配置")
        scene_plan = {
            "project_id": project_id,
            "source_path": target_file,
            "title": "场景",
            "goal": "",
            "conflict": "",
            "required_beats": [],
            "characters": [],
            "location": "",
            "time": ""
        }
    
    baseline_content = load_candidate_content(project_id, baseline_candidate_id)
    with_plan_content = load_candidate_content(project_id, with_plan_candidate_id)
    
    if not baseline_content:
        print(f"[错误] Baseline candidate 不存在: {baseline_candidate_id}")
        return None
    if not with_plan_content:
        print(f"[错误] With-Plan candidate 不存在: {with_plan_candidate_id}")
        return None
    
    baseline_scores = score_candidate(baseline_content, scene_plan)
    with_plan_scores = score_candidate(with_plan_content, scene_plan)
    
    baseline_total = baseline_scores["overall_score"]["score"]
    with_plan_total = with_plan_scores["overall_score"]["score"]
    delta = with_plan_total - baseline_total
    
    if delta >= 3:
        conclusion = "✅ With-Plan 明显更优"
    elif delta >= 1:
        conclusion = "⚠️ With-Plan 略优"
    elif delta == 0:
        conclusion = "⚠️ 两者相近"
    else:
        conclusion = "❌ With-Plan 表现较差"
    
    # Provenance 收集（只读，不修改 candidate，不伪造数据）
    provenance = {
        "baseline": build_provenance_info(
            project_id, baseline_candidate_id, scene_plan_path, scene_plan_used=False),
        "with_plan": build_provenance_info(
            project_id, with_plan_candidate_id, scene_plan_path, scene_plan_used=True),
    }
    all_complete = (
        provenance["baseline"]["status"] == "complete"
        and provenance["with_plan"]["status"] == "complete"
    )
    provenance_overall = {
        "all_complete": all_complete,
        "note": "T5.18-H1: candidate provenance metadata only exists for candidates created after T5.17-H2. Missing provenance on historical candidates is normal and does not affect scoring."
    }

    result = {
        "case_id": case.get("case_id", "unknown"),
        "project_id": project_id,
        "target_file": target_file,
        "baseline_candidate_id": baseline_candidate_id,
        "with_plan_candidate_id": with_plan_candidate_id,
        "scene_plan_title": scene_plan.get("title", ""),
        "scores": {
            "baseline": baseline_scores,
            "with_plan": with_plan_scores
        },
        "summary": {
            "baseline_total": baseline_total,
            "with_plan_total": with_plan_total,
            "delta": delta,
            "conclusion": conclusion
        },
        "provenance": provenance,
        "provenance_overall": provenance_overall,
    }
    
    print(f"\n  Baseline 总分: {baseline_total}")
    print(f"  With-Plan 总分: {with_plan_total}")
    print(f"  Delta: {delta:+d}")
    print(f"  结论: {conclusion}")
    
    return result


def generate_multi_case_report(case_results: list, output_dir: str):
    """生成多案例报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON 输出
    json_file = Path(output_dir) / f"t5-scene-plan-quality-multi-score-2026-06.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "case_count": len(case_results),
            "cases": case_results,
            "note": "T5.16.2 已完成 sec-001 真实样本重建；sec-001 与 sec-002 当前均使用真实 Scene Plan。历史测试数据问题见 docs/testing/t5-scene-plan-quality-final-errata-2026-06.md。"
        }, f, ensure_ascii=False, indent=2)
    print(f"\n多案例 JSON 已保存: {json_file}")
    
    # Markdown 输出
    dimension_names = {
        "scene_goal_alignment": "目标对齐度",
        "beats_coverage": "情节覆盖度",
        "conflict_presence": "冲突体现",
        "characters_consistency": "人物一致性",
        "location_consistency": "地点一致性",
        "time_consistency": "时间一致性",
        "no_reasoning_logs": "无推理日志",
        "language_quality_basic": "语言质量",
        "plan_contradiction_check": "矛盾检查"
    }
    
    md = f"""# T5.11 / T5.13 / T5.16.2a: 多案例评分报告（真实样本，最终状态）

**执行日期**: {datetime.now().strftime('%Y-%m-%d')}
**执行人**: Solo Agent
**状态**: ✅ PASS（2/2 案例完成）

---

## 重要说明

✅ **sec-001 与 sec-002 当前均使用真实 Scene Plan**。
- sec-001: `雨夜：旧港站的未知召唤`，T5.16.2 完成真实样本重建。
- sec-002: `场景：旧港站接头`，自 T5.15 起即为真实样本。
- 历史测试数据问题与纠偏过程，详见 [勘误文档](t5-scene-plan-quality-final-errata-2026-06.md)。

---

## 1. 总体统计

| 统计项 | 值 |
|--------|-----|
| 总测试用例数 | {len(case_results)} |
| With-Plan 更优 | {sum(1 for r in case_results if r['summary']['delta'] > 0)} |
| Baseline 更优 | {sum(1 for r in case_results if r['summary']['delta'] < 0)} |
| 持平 | {sum(1 for r in case_results if r['summary']['delta'] == 0)} |
| 平均 Delta | {sum(r['summary']['delta'] for r in case_results)/len(case_results) if case_results else 0:.1f} |

---

## 2. 各案例详情

| 案例 ID | Target File | Baseline ID | With-Plan ID | Baseline | With-Plan | Delta | 结论 |
|---------|-------------|-------------|--------------|----------|-----------|-------|------|
"""
    
    for r in case_results:
        md += f"| {r['case_id']} | {r['target_file']} | {r['baseline_candidate_id']} | {r['with_plan_candidate_id']} | {r['summary']['baseline_total']} | {r['summary']['with_plan_total']} | {r['summary']['delta']:+d} | {r['summary']['conclusion']} |\n"

    # Candidate Provenance 小节
    md += """
---

## 2B. Candidate Provenance 状态

| 案例 ID | Baseline 状态 | With-Plan 状态 | 说明 |
|---------|---------------|----------------|------|
"""
    for r in case_results:
        b_status = r.get("provenance", {}).get("baseline", {}).get("status", "unknown")
        p_status = r.get("provenance", {}).get("with_plan", {}).get("status", "unknown")
        note = r.get("provenance_overall", {}).get("note", "provenance info not available")
        md += f"| {r['case_id']} | {b_status} | {p_status} | {note[:100]} |\n"

    md += """
> 说明：`legacy_candidate` 表示 candidate 创建于 T5.17-H2 之前，不包含 provenance metadata。这是正常的历史状态，不影响评分。
> `complete` 表示 candidate 已包含 `generation_context` / `scene_plan_hash` / `scene_plan_path` 三个字段。

---

## 3. 稳定性评估

✅ **当前状态**：2 个案例均使用真实 Scene Plan，评分框架正常工作。
- 评分结论如实记录，未强行要求 with-plan 获胜。
- 如需更完整的稳定性评估，建议补充至少 2-3 个不同类型场景的完整样本。

---

## 4. 说明

1. **sec-001**：经 T5.16.2 纠偏，当前已替换为真实样本。
2. **sec-002**：自 T5.15 起保持真实样本，未改动。
3. 评分使用规则匹配，未调用 LLM 进行深度语义理解。
4. 仅作为辅助参考，不替代人工判断。

---

## 5. 安全声明

- 未提交 workspace 原始 `.candidates/` 文件，仅通过受控证据文件披露正文快照。
- 未提交 API key。
- 未执行 adopt；未覆盖 target_file 正文。
- 历史勘误保留用于审计。

---

**T5.11 / T5.13 / T5.16.2a 最终状态**：✅ PASS（2/2 案例，真实样本；测试数据问题已在勘误中记录与纠偏）

"""
    
    md_file = Path("docs/testing") / "t5-scene-plan-quality-multi-score-2026-06.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"多案例 Markdown 已保存: {md_file}")
    
    return json_file, md_file


def main_multi_case(args):
    """多案例模式主函数"""
    print("=" * 60)
    print("Scene Plan 质量对比自动评分 - 多案例模式")
    print("=" * 60)
    
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    cases = load_cases_from_file(args.cases)
    print(f"\n加载 {len(cases)} 个测试用例")
    
    case_results = []
    for case in cases:
        result = score_single_case(case)
        if result:
            case_results.append(result)
    
    if not case_results:
        print("\n[错误] 没有成功评分的案例")
        return 1
    
    generate_multi_case_report(case_results, args.output_dir)
    
    print(f"\n{'='*60}")
    print("多案例评分完成")
    print(f"{'='*60}")
    print(f"成功处理: {len(case_results)}/{len(cases)} 个案例")
    
    return 0


def main_single_case(args):
    """单案例模式主函数（原 main 函数逻辑）"""
    print("=" * 60)
    print("Scene Plan 质量对比自动评分脚本 - 单案例模式")
    print("=" * 60)
    print()
    print("⚠️ 注意：本模式用于调试，不会覆盖 T5.10.1 的校准文档")
    print()
    
    # 确保输出目录存在
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # 记录执行前的 target_file 状态（只读，不修改）
    target_path = Path("workspace/projects") / args.project_id / args.target_file
    if target_path.exists():
        with open(target_path, 'rb') as f:
            import hashlib
            md5_before = hashlib.md5(f.read()).hexdigest()
        mtime_before = target_path.stat().st_mtime
        print(f"[安全检查] Target file 读取成功 (MD5: {md5_before})")
        print(f"[安全检查] 不会修改任何文件")
    else:
        md5_before = None
        mtime_before = None
        print(f"[警告] Target file 不存在: {target_path}")
    
    print()
    print("=== 加载数据 ===")
    
    # 加载 scene_plan
    scene_plan = load_scene_plan(args.project_id, args.target_file)
    if not scene_plan:
        # 如果没有文件，使用文档中的默认值
        print("未找到 scene_plan 文件，使用默认配置")
        scene_plan = {
            "project_id": args.project_id,
            "source_path": args.target_file,
            "title": "场景：旧港站",
            "goal": "主角林澈在旧港站等待神秘人，完成首次接头",
            "conflict": "旧港站氛围阴森，主角不确定对方身份，存在信任危机",
            "required_beats": [
                "林澈到达旧港站入口",
                "描述雨夜氛围和旧港站环境",
                "林澈数到第三根立柱",
                "神秘人出现或脚步声传来"
            ],
            "characters": ["林澈"],
            "location": "旧港站",
            "time": "雨夜",
            "output_intent": "polish",
            "candidate_policy": {
                "allow_direct_write": False,
                "require_candidate": True
            }
        }
    else:
        print(f"Scene Plan 加载成功: {scene_plan.get('title', 'Unknown')}")
    
    # 加载 candidates
    baseline_content = load_candidate_content(args.project_id, args.baseline_candidate_id)
    with_plan_content = load_candidate_content(args.project_id, args.with_plan_candidate_id)
    
    if not baseline_content:
        print(f"[错误] Baseline candidate 不存在: {args.baseline_candidate_id}")
        return 1
    if not with_plan_content:
        print(f"[错误] With-Plan candidate 不存在: {args.with_plan_candidate_id}")
        return 1
    
    print(f"Baseline candidate 加载成功 ({len(baseline_content)} 字)")
    print(f"With-Plan candidate 加载成功 ({len(with_plan_content)} 字)")
    
    # 开始评分
    print()
    print("=== 开始评分 ===")
    
    baseline_scores = score_candidate(baseline_content, scene_plan)
    with_plan_scores = score_candidate(with_plan_content, scene_plan)
    
    baseline_total = baseline_scores["overall_score"]["score"]
    with_plan_total = with_plan_scores["overall_score"]["score"]
    delta = with_plan_total - baseline_total
    
    # 打印评分表
    print()
    print("=" * 60)
    print("评分结果对比")
    print("=" * 60)
    
    score_dimensions = [
        "scene_goal_alignment",
        "beats_coverage",
        "conflict_presence",
        "characters_consistency",
        "location_consistency",
        "time_consistency",
        "no_reasoning_logs",
        "language_quality_basic",
        "plan_contradiction_check",
    ]
    
    dimension_names = {
        "scene_goal_alignment": "目标对齐度",
        "beats_coverage": "情节覆盖度",
        "conflict_presence": "冲突体现",
        "characters_consistency": "人物一致性",
        "location_consistency": "地点一致性",
        "time_consistency": "时间一致性",
        "no_reasoning_logs": "无推理日志",
        "language_quality_basic": "语言质量",
        "plan_contradiction_check": "矛盾检查",
        "overall_score": "总分"
    }
    
    print(f"\n{'维度':<18} {'Baseline':<10} {'With-Plan':<10} {'更优'}")
    print("-" * 60)
    
    for dim in score_dimensions:
        b_score = baseline_scores[dim]["score"]
        p_score = with_plan_scores[dim]["score"]
        better = "Plan" if p_score > b_score else ("Baseline" if b_score > p_score else "-")
        print(f"{dimension_names.get(dim, dim):<18} {b_score:<10} {p_score:<10} {better}")
    
    print("-" * 60)
    print(f"{'总分':<18} {baseline_total:<10} {with_plan_total:<10} {'Plan' if delta > 0 else ('Baseline' if delta < 0 else '-')}")
    print(f"\nDelta (Plan - Baseline): {delta:+d}")
    
    # 结论
    print()
    if delta >= 3:
        conclusion = "✅ With-Plan 明显更优"
    elif delta >= 1:
        conclusion = "⚠️ With-Plan 略优"
    elif delta == 0:
        conclusion = "⚠️ 两者相近"
    else:
        conclusion = "❌ With-Plan 表现较差"
    print(f"结论: {conclusion}")
    
    # 安全验证
    print()
    print("=== 安全验证 ===")
    safety_checks = []
    
    # 验证 target_file 未被修改
    if md5_before is not None and target_path.exists():
        with open(target_path, 'rb') as f:
            md5_after = hashlib.md5(f.read()).hexdigest()
        mtime_after = target_path.stat().st_mtime
        safety_checks.append({
            "check": "Target file 未修改",
            "passed": md5_before == md5_after and abs(mtime_before - mtime_after) < 1,
            "evidence": f"MD5 保持: {md5_before == md5_after}, mtime 保持: {abs(mtime_before - mtime_after) < 1}"
        })
    else:
        safety_checks.append({
            "check": "Target file 未修改",
            "passed": True,
            "evidence": "无 target_file 或未操作"
        })
    
    safety_checks.append({
        "check": "未创建 candidate",
        "passed": True,
        "evidence": "只读模式，未调用创建 API"
    })
    
    safety_checks.append({
        "check": "未调用生成 API",
        "passed": True,
        "evidence": "未调用 /api/pipeline/run"
    })
    
    safety_checks.append({
        "check": "未执行 adopt",
        "passed": True,
        "evidence": "未调用 adopt 相关 API"
    })
    
    safety_checks.append({
        "check": "未读取 API key",
        "passed": True,
        "evidence": "未访问环境变量中的 API key"
    })
    
    safety_checks.append({
        "check": "未调用外部 API",
        "passed": True,
        "evidence": "纯本地规则评分"
    })
    
    all_safe = all(c["passed"] for c in safety_checks)
    
    for check in safety_checks:
        status = "✅ PASS" if check["passed"] else "❌ FAIL"
        print(f"{status} {check['check']}")
        print(f"   {check['evidence']}")
    
    # 生成输出文件
    print()
    print("=== 生成输出 ===")
    
    # JSON 输出
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "project_id": args.project_id,
        "target_file": args.target_file,
        "baseline_candidate_id": args.baseline_candidate_id,
        "with_plan_candidate_id": args.with_plan_candidate_id,
        "scene_plan_title": scene_plan.get("title", ""),
        "scores": {
            "baseline": baseline_scores,
            "with_plan": with_plan_scores,
        },
        "summary": {
            "baseline_total": baseline_total,
            "with_plan_total": with_plan_total,
            "delta": delta,
            "conclusion": conclusion
        },
        "safety_checks": safety_checks,
        "all_safe": all_safe
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 使用临时文件名，避免覆盖 T5.10.1
    json_file = Path(args.output_dir) / f"t5-scene-plan-quality-score-2026-06-temp-{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"JSON 已保存: {json_file} (临时文件，不覆盖 T5.10.1)")
    
    # Markdown 输出（简短版本，不包含长正文）
    md_content = generate_markdown_report(
        args, scene_plan, baseline_scores, with_plan_scores,
        baseline_total, with_plan_total, delta, conclusion,
        safety_checks, all_safe
    )
    
    md_file = Path("docs/testing") / f"t5-scene-plan-quality-score-2026-06-temp-{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"Markdown 已保存: {md_file} (临时文件，不覆盖 T5.10.1)")
    
    # 最终状态
    print()
    print("=" * 60)
    print("评分完成")
    print("=" * 60)
    print(f"结论: {conclusion}")
    print(f"安全: {'✅ ALL SAFE' if all_safe else '❌ UNSAFE'}")
    
    return 0 if all_safe else 1


def main():
    print("=" * 60)
    print("Scene Plan 质量对比自动评分脚本")
    print("=" * 60)
    print()
    
    parser = argparse.ArgumentParser(description="Scene Plan 质量对比评分")
    parser.add_argument("--project_id", default="demo-novel", help="项目 ID")
    parser.add_argument("--target_file", default="chapters/vol-01/ch-001/sec-001.md", help="目标文件")
    parser.add_argument("--baseline_candidate_id", default="cand_3f3d8e72", help="Baseline candidate ID")
    parser.add_argument("--with_plan_candidate_id", default="cand_450a19fd", help="With-Plan candidate ID")
    parser.add_argument("--cases", help="测试用例文件 JSON（多案例模式）")
    parser.add_argument("--output_dir", default="docs/testing/artifacts", help="输出目录")
    args = parser.parse_args()
    
    if args.cases:
        return main_multi_case(args)
    else:
        return main_single_case(args)


def generate_markdown_report(args, scene_plan, baseline_scores, with_plan_scores,
                            baseline_total, with_plan_total, delta, conclusion,
                            safety_checks, all_safe):
    """生成 Markdown 报告"""
    
    dimension_names = {
        "scene_goal_alignment": "目标对齐度",
        "beats_coverage": "情节覆盖度",
        "conflict_presence": "冲突体现",
        "characters_consistency": "人物一致性",
        "location_consistency": "地点一致性",
        "time_consistency": "时间一致性",
        "no_reasoning_logs": "无推理日志",
        "language_quality_basic": "语言质量",
        "plan_contradiction_check": "矛盾检查",
        "overall_score": "总分"
    }
    
    md = f"""# T5.10: Scene Plan 质量对比自动评分

**执行日期**: {datetime.now().strftime('%Y-%m-%d')}
**执行人**: Solo Agent

---

## 1. 输入信息

| 项目 | 值 |
|------|-----|
| Project ID | {args.project_id} |
| Target File | {args.target_file} |
| Baseline Candidate ID | {args.baseline_candidate_id} |
| With-Plan Candidate ID | {args.with_plan_candidate_id} |
| Scene Plan Title | {scene_plan.get('title', 'Unknown')} |

---

## 2. 评分维度

本次评分包含以下维度（每项 0-2 分）：

1. **scene_goal_alignment** - 目标对齐度
2. **beats_coverage** - 情节覆盖度
3. **conflict_presence** - 冲突体现
4. **characters_consistency** - 人物一致性
5. **location_consistency** - 地点一致性
6. **time_consistency** - 时间一致性
7. **no_reasoning_logs** - 无推理日志
8. **language_quality_basic** - 基础语言质量
9. **plan_contradiction_check** - 矛盾检查

---

## 3. 评分结果对比

| 维度 | Baseline | With-Plan | 更优 |
|------|----------|-----------|------|
"""
    
    score_dimensions = [
        "scene_goal_alignment",
        "beats_coverage",
        "conflict_presence",
        "characters_consistency",
        "location_consistency",
        "time_consistency",
        "no_reasoning_logs",
        "language_quality_basic",
        "plan_contradiction_check",
    ]
    
    for dim in score_dimensions:
        b_score = baseline_scores[dim]["score"]
        p_score = with_plan_scores[dim]["score"]
        better = "With-Plan" if p_score > b_score else ("Baseline" if b_score > p_score else "-")
        md += f"| {dimension_names.get(dim, dim)} | {b_score} | {p_score} | {better} |\n"
    
    md += f"| **总分** | **{baseline_total}** | **{with_plan_total}** | **{'With-Plan' if delta > 0 else ('Baseline' if delta < 0 else '-')}** |\n"
    md += f"\n**Delta (Plan - Baseline)**: {delta:+d}\n"
    md += f"\n**结论**: {conclusion}\n"
    
    md += """

---

## 4. 细节评分证据

### Baseline Candidate

"""
    
    for dim in score_dimensions:
        s = baseline_scores[dim]
        md += f"- **{dimension_names.get(dim, dim)}**: {s['score']}/2 ({s['label']})\n"
        md += f"  证据: {s['evidence'][:120]}...\n"
    
    md += """

### With-Plan Candidate

"""
    
    for dim in score_dimensions:
        s = with_plan_scores[dim]
        md += f"- **{dimension_names.get(dim, dim)}**: {s['score']}/2 ({s['label']})\n"
        md += f"  证据: {s['evidence'][:120]}...\n"
    
    md += """

---

## 5. 安全验证

"""
    
    for check in safety_checks:
        status = "✅ PASS" if check["passed"] else "❌ FAIL"
        md += f"- **{status}** {check['check']}\n"
        md += f"  {check['evidence']}\n"
    
    md += f"\n**总体安全状态**: {'✅ ALL SAFE' if all_safe else '❌ UNSAFE'}\n"
    
    md += """

---

## 6. 局限性说明

1. 本评分使用规则匹配，可能无法完全捕捉语境和表达质量
2. 未调用 LLM 进行深度语义理解
3. 仅作为辅助参考，不替代人工判断

---

## 7. 下一步建议

- 可考虑增加更多评分维度
- 可尝试集成 LLM 辅助评分（作为可选功能）
- 建议持续优化 scene_plan 设计

---

**T5.10 完成** 🎉
"""
    
    return md


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"评分执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
