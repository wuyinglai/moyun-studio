"""
Scene Plan 驱动生成质量对比 Smoke Test

功能：
- 对同一个场景执行两次 Professional candidate 生成
- 一次不带 scene_plan（baseline）
- 一次带 scene_plan
- 比较两个 candidate 的质量

依赖：
- 真实后端服务（http://localhost:8080）
- 真实 LLM API（通过环境变量配置）
- demo-novel 项目

安全：
- 不接受命令行参数
- 不写入真实 API key
- 不执行 adopt
- 不覆盖正文
"""

import os
import sys
import json
import time
import hashlib
import re
import requests
from datetime import datetime


def main():
    print("=" * 60)
    print("Scene Plan 驱动生成质量对比 Smoke Test")
    print("=" * 60)
    print()

    # 配置
    API_BASE = "http://localhost:8080"
    PROJECT_ID = "demo-novel"
    TARGET_FILE = "chapters/vol-01/ch-001/sec-001.md"

    # 记录执行前状态
    print("=== 执行前状态 ===")

    target_path = f"workspace/projects/{PROJECT_ID}/{TARGET_FILE}"
    with open(target_path, 'rb') as f:
        md5_before = hashlib.md5(f.read()).hexdigest()
    print(f"Target file MD5 (before): {md5_before}")
    print(f"Target file mtime (before): {os.path.getmtime(target_path)}")

    candidates_dir = f"workspace/projects/{PROJECT_ID}/.candidates"
    candidate_files_before = [
        f for f in os.listdir(candidates_dir)
        if f.endswith('.polish.md')
    ]
    print(f"Polish candidate 数量 (before): {len(candidate_files_before)}")

    # 先调用一次不带 scene_plan 的 baseline 生成
    print()
    print("=== Baseline 生成（不带 Scene Plan）===")

    data_baseline = {
        "pipeline": "polish",
        "project_id": PROJECT_ID,
        "target_file": TARGET_FILE,
        "output_mode": "candidate",
        "extra_vars": {}
    }

    print(f"请求体包含 scene_plan: {'scene_plan' in data_baseline}")

    response_baseline = requests.post(
        f"{API_BASE}/api/pipeline/run",
        json=data_baseline,
        stream=True,
        timeout=120
    )

    print(f"HTTP 状态码: {response_baseline.status_code}")

    baseline_candidate_id = None
    baseline_content = ""

    print("解析 SSE 响应...")
    for line in response_baseline.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if 'candidate_created' in decoded_line:
                # 尝试多种正则格式
                match = re.search(r'"candidate_id"\s*:\s*"([^"]+)"', decoded_line)
                if not match:
                    match = re.search(r'candidate_id["\s:]+([^"\'\s,}]+)', decoded_line)
                if match:
                    baseline_candidate_id = match.group(1).strip()
                    print(f"Baseline candidate_id: {baseline_candidate_id}")
            if decoded_line.startswith('data:'):
                try:
                    event_data = json.loads(decoded_line[5:].strip())
                    if event_data.get('delta'):
                        baseline_content += event_data['delta']
                except:
                    pass

    print(f"Baseline 内容长度: {len(baseline_content)} 字符")
    print(f"Baseline 内容预览:\n{baseline_content[:500]}...")
    print()

    # 调用带 scene_plan 的生成
    print("=== With Scene Plan 生成（带 Scene Plan）===")

    # 准备 scene_plan
    scene_plan = {
        "project_id": PROJECT_ID,
        "source_path": TARGET_FILE,
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
        },
        "metadata": {"created_by": "human"}
    }

    data_with_plan = {
        "pipeline": "polish",
        "project_id": PROJECT_ID,
        "target_file": TARGET_FILE,
        "output_mode": "candidate",
        "extra_vars": {},
        "scene_plan": scene_plan
    }

    print(f"请求体包含 scene_plan: {'scene_plan' in data_with_plan}")
    print(f"scene_plan.source_path: {scene_plan['source_path']}")
    print(f"scene_plan.goal: {scene_plan['goal']}")
    print(f"scene_plan.location: {scene_plan['location']}")
    print(f"scene_plan.time: {scene_plan['time']}")

    response_with_plan = requests.post(
        f"{API_BASE}/api/pipeline/run",
        json=data_with_plan,
        stream=True,
        timeout=120
    )

    print(f"HTTP 状态码: {response_with_plan.status_code}")

    plan_candidate_id = None
    plan_content = ""

    print("解析 SSE 响应...")
    for line in response_with_plan.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if 'candidate_created' in decoded_line:
                # 尝试多种正则格式
                match = re.search(r'"candidate_id"\s*:\s*"([^"]+)"', decoded_line)
                if not match:
                    match = re.search(r'candidate_id["\s:]+([^"\'\s,}]+)', decoded_line)
                if match:
                    plan_candidate_id = match.group(1).strip()
                    print(f"With-Plan candidate_id: {plan_candidate_id}")
            if decoded_line.startswith('data:'):
                try:
                    event_data = json.loads(decoded_line[5:].strip())
                    if event_data.get('delta'):
                        plan_content += event_data['delta']
                except:
                    pass

    print(f"With-Plan 内容长度: {len(plan_content)} 字符")
    print(f"With-Plan 内容预览:\n{plan_content[:500]}...")
    print()

    # 记录执行后状态
    print("=== 执行后验证 ===")

    with open(target_path, 'rb') as f:
        md5_after = hashlib.md5(f.read()).hexdigest()
    print(f"Target file MD5 (after): {md5_after}")
    print(f"MD5 保持不变: {md5_before == md5_after}")

    candidate_files_after = [
        f for f in os.listdir(candidates_dir)
        if f.endswith('.polish.md')
    ]
    print(f"Polish candidate 数量 (after): {len(candidate_files_after)}")
    print(f"Candidate 数量增加: {len(candidate_files_after) - len(candidate_files_before)}")

    # 质量对比
    print()
    print("=" * 60)
    print("质量对比分析")
    print("=" * 60)

    # 自动检查
    checks = []

    # 检查 location 关键词
    location_mentions_baseline = baseline_content.count("旧港站")
    location_mentions_plan = plan_content.count("旧港站")
    checks.append({
        "维度": "location 提及次数（目标：旧港站）",
        "baseline": f"{location_mentions_baseline} 次",
        "with_plan": f"{location_mentions_plan} 次",
        "更贴合": "✅ Plan" if location_mentions_plan > location_mentions_baseline else ("⚠️ 相近" if location_mentions_plan == location_mentions_baseline else "✅ Baseline")
    })

    # 检查 characters 关键词
    characters_mentions_baseline = baseline_content.count("林澈")
    characters_mentions_plan = plan_content.count("林澈")
    checks.append({
        "维度": "characters 提及次数（目标：林澈）",
        "baseline": f"{characters_mentions_baseline} 次",
        "with_plan": f"{characters_mentions_plan} 次",
        "更贴合": "✅ Plan" if characters_mentions_plan > characters_mentions_baseline else ("⚠️ 相近" if characters_mentions_plan == characters_mentions_baseline else "✅ Baseline")
    })

    # 检查雨夜氛围
    rain_mentions_baseline = baseline_content.count("雨")
    rain_mentions_plan = plan_content.count("雨")
    checks.append({
        "维度": "time/氛围 提及次数（目标：雨夜）",
        "baseline": f"{rain_mentions_baseline} 次",
        "with_plan": f"{rain_mentions_plan} 次",
        "更贴合": "✅ Plan" if rain_mentions_plan > rain_mentions_baseline else ("⚠️ 相近" if rain_mentions_plan == rain_mentions_baseline else "✅ Baseline")
    })

    # 检查 beats：第三根立柱
    pillar_mentions_baseline = baseline_content.count("立柱")
    pillar_mentions_plan = plan_content.count("立柱")
    beats_match_baseline = pillar_mentions_baseline >= 1
    beats_match_plan = pillar_mentions_plan >= 1
    checks.append({
        "维度": "beats 覆盖（目标：立柱/第三根）",
        "baseline": "✅ 包含" if beats_match_baseline else "❌ 不包含",
        "with_plan": "✅ 包含" if beats_match_plan else "❌ 不包含",
        "更贴合": "✅ Plan" if beats_match_plan and not beats_match_baseline else ("⚠️ 相近" if beats_match_plan == beats_match_baseline else "✅ Baseline")
    })

    # 检查是否有推理日志
    has_reasoning_baseline = bool(re.search(r'<\|channel\>|Original:|Reasoning:|思考:|推理:', baseline_content))
    has_reasoning_plan = bool(re.search(r'<\|channel\>|Original:|Reasoning:|思考:|推理:', plan_content))
    checks.append({
        "维度": "无推理日志",
        "baseline": "✅ 无" if not has_reasoning_baseline else "❌ 有",
        "with_plan": "✅ 无" if not has_reasoning_plan else "❌ 有",
        "更贴合": "✅ 相同"
    })

    # 打印对比表
    print(f"\n{'维度':<30} {'Baseline':<15} {'With Plan':<15} {'更贴合'}")
    print("-" * 80)
    for check in checks:
        print(f"{check['维度']:<30} {check['baseline']:<15} {check['with_plan']:<15} {check['更贴合']}")

    # 综合评估
    print()
    print("=" * 60)
    print("综合评估")
    print("=" * 60)

    plan_wins = sum(1 for c in checks if "Plan" in c["更贴合"] and "相同" not in c["更贴合"])
    baseline_wins = sum(1 for c in checks if "Baseline" in c["更贴合"] and "相同" not in c["更贴合"])

    print(f"Plan 胜出维度: {plan_wins}")
    print(f"Baseline 胜出维度: {baseline_wins}")

    if plan_wins > baseline_wins:
        conclusion = "✅ With-Plan 整体更贴合 Scene Plan"
    elif plan_wins < baseline_wins:
        conclusion = "⚠️ Baseline 表现更好，Scene Plan 可能未有效传递"
    else:
        conclusion = "⚠️ 两者表现相近，Scene Plan 影响不明显"

    print(f"结论: {conclusion}")

    # 输出测试结果
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"Baseline candidate_id: {baseline_candidate_id}")
    print(f"With-Plan candidate_id: {plan_candidate_id}")
    print(f"两个 candidate_id 不同: {baseline_candidate_id != plan_candidate_id}")
    print(f"正文 MD5 保持不变: {md5_before == md5_after}")
    print(f"Candidate 数量增加: {len(candidate_files_after) - len(candidate_files_before)}")

    return {
        "baseline_candidate_id": baseline_candidate_id,
        "plan_candidate_id": plan_candidate_id,
        "candidates_different": baseline_candidate_id != plan_candidate_id,
        "md5_unchanged": md5_before == md5_after,
        "candidates_increased": len(candidate_files_after) - len(candidate_files_before),
        "plan_wins": plan_wins,
        "baseline_wins": baseline_wins,
        "conclusion": conclusion
    }


if __name__ == '__main__':
    try:
        result = main()
        print()
        print("=== 测试完成 ===")
        all_pass = (
            result["candidates_different"] and
            result["md5_unchanged"] and
            result["candidates_increased"] >= 2
        )
        print(f"安全验证: {'✅ PASS' if all_pass else '❌ FAIL'}")
        print(f"质量对比: {result['conclusion']}")
        exit(0 if all_pass else 1)
    except Exception as e:
        print(f"测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)