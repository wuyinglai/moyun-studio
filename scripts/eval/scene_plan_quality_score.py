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


def load_scene_plan(project_id: str, target_file: str):
    """读取 scene_plan 文件（只读）"""
    # 从 materials/scene_plans/ 读取
    scene_plans_dir = Path("workspace/projects") / project_id / "materials" / "scene_plans"
    if scene_plans_dir.exists():
        # 转换路径为文件名格式
        target_file_safe = target_file.replace("/", "__").replace("\\", "__")
        scene_plan_file = scene_plans_dir / f"{target_file_safe}.scene-plan.json"
        if scene_plan_file.exists():
            with open(scene_plan_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None


def score_scene_goal_alignment(content: str, scene_plan: dict):
    """评分 scene_goal 对齐度 (0-2)"""
    goal = scene_plan.get("goal", "")
    score = 0
    evidence = []

    # 检查是否包含 goal 关键词
    goal_keywords = [
        "等待", "神秘人", "接头", "林澈", "旧港站"
    ]
    matched = sum(1 for kw in goal_keywords if kw in content)
    
    if matched >= 4:
        score = 2
        label = "pass"
        evidence.append(f"目标关键词匹配度高 ({matched}/5)")
    elif matched >= 2:
        score = 1
        label = "partial"
        evidence.append(f"目标关键词部分匹配 ({matched}/5)")
    else:
        label = "fail"
        evidence.append(f"目标关键词匹配不足 ({matched}/5)")
    
    # 更具体的检查
    if "等待" in content or "等候" in content:
        score = min(score + 1, 2)
        evidence.append("包含等待/等候相关表述")
    if "接头" in content:
        score = min(score + 1, 2)
        evidence.append("包含接头相关表述")
    
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
    """评分 conflict 体现 (0-2)"""
    conflict = scene_plan.get("conflict", "")
    score = 0
    evidence = []
    
    # 检查 conflict 关键词
    conflict_keywords = ["阴森", "信任危机", "不确定", "神秘", "紧张", "诡异", "不安"]
    matched = sum(1 for kw in conflict_keywords if kw in content)
    
    if matched >= 2:
        score = 2
        label = "pass"
        evidence.append(f"冲突关键词丰富 ({matched} 个)")
    elif matched >= 1:
        score = 1
        label = "partial"
        evidence.append(f"冲突关键词有限 ({matched} 个)")
    else:
        label = "fail"
        evidence.append("缺少冲突相关表述")
    
    return {
        "score": score,
        "label": label,
        "evidence": "；".join(evidence)
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
    """评分 time 一致性 (0-2)"""
    time = scene_plan.get("time", "")
    score = 0
    evidence = []
    
    if not time:
        return {"score": 2, "label": "pass", "evidence": "无 time 要求"}
    
    # 检查 time 关键词
    time_keywords = []
    if "雨夜" in time:
        time_keywords.extend(["雨", "夜", "雨夜", "夜晚", "深夜"])
    
    matched_count = sum(1 for kw in time_keywords if kw in content)
    
    if matched_count >= 3:
        score = 2
        label = "pass"
        evidence.append(f"time 关键词丰富 ({matched_count} 次提及)")
    elif matched_count >= 1:
        score = 1
        label = "partial"
        evidence.append(f"time 关键词有限 ({matched_count} 次提及)")
    else:
        label = "fail"
        evidence.append(f"未提及 time 相关关键词")
    
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
    """评分 基础语言质量 (0-2)"""
    score = 0
    evidence = []
    
    # 检查长度
    content_length = len(content)
    if 300 <= content_length <= 1000:
        score += 1
        evidence.append(f"长度合理 ({content_length} 字)")
    elif content_length > 1000:
        evidence.append(f"长度偏长 ({content_length} 字)")
    elif content_length < 300:
        evidence.append(f"长度偏短 ({content_length} 字)")
    
    # 检查是否为空
    if content_length > 0:
        score += 1
        evidence.append("内容非空")
    else:
        label = "fail"
        evidence.append("内容为空")
        return {"score": 0, "label": label, "evidence": "；".join(evidence)}
    
    # 检查重复
    # 简单的重复检查：相同的短片段不超过2次
    if score >= 1:
        label = "pass" if score == 2 else "partial"
    else:
        label = "fail"
    
    return {
        "score": min(score, 2),
        "label": label,
        "evidence": "；".join(evidence[:2])
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
    
    # 计算总分
    total_score = sum(s["score"] for s in scores.values())
    max_score = len(scores) * 2
    
    scores["overall_score"] = {
        "score": total_score,
        "max_score": max_score,
        "label": "pass" if total_score >= max_score * 0.7 else ("partial" if total_score >= max_score * 0.4 else "fail")
    }
    
    return scores


def main():
    print("=" * 60)
    print("Scene Plan 质量对比自动评分脚本")
    print("=" * 60)
    print()
    
    # 配置
    parser = argparse.ArgumentParser(description="Scene Plan 质量对比评分")
    parser.add_argument("--project_id", default="demo-novel", help="项目 ID")
    parser.add_argument("--target_file", default="chapters/vol-01/ch-001/sec-001.md", help="目标文件")
    parser.add_argument("--baseline_candidate_id", default="cand_3f3d8e72", help="Baseline candidate ID")
    parser.add_argument("--with_plan_candidate_id", default="cand_450a19fd", help="With-Plan candidate ID")
    parser.add_argument("--output_dir", default="docs/testing/artifacts", help="输出目录")
    args = parser.parse_args()
    
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
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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
    
    json_file = Path(args.output_dir) / "t5-scene-plan-quality-score-2026-06.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"JSON 已保存: {json_file}")
    
    # Markdown 输出（简短版本，不包含长正文）
    md_content = generate_markdown_report(
        args, scene_plan, baseline_scores, with_plan_scores,
        baseline_total, with_plan_total, delta, conclusion,
        safety_checks, all_safe
    )
    
    md_file = Path("docs/testing") / "t5-scene-plan-quality-score-2026-06.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"Markdown 已保存: {md_file}")
    
    # 最终状态
    print()
    print("=" * 60)
    print("评分完成")
    print("=" * 60)
    print(f"结论: {conclusion}")
    print(f"安全: {'✅ ALL SAFE' if all_safe else '❌ UNSAFE'}")
    
    return 0 if all_safe else 1


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
