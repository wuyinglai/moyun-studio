#!/usr/bin/env python3
"""
Phase T3-D7.6：局部 Rewrite Engine MVP (Dry-Run 版本)

- 输入: scene markdown, state snapshot, plot debt, review output
- 输出: rewrite suggestions JSON 和 Markdown 报告
- 不调用 LLM, 不修改正文, 不自动入库
- 所有建议 status 都是 candidate
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


# 重写目标模板库
REWRITE_GOALS = {
    "unexplained_item": "明确设定道具的来源、功能或关联",
    "unresolved_setting": "补充设定细节，解释或建立设定",
    "open_question": "回答或铺垫伏笔问题，解决疑问",
    "foreshadowing": "铺垫后续剧情，保留悬念",
    "promise": "兑现或铺垫承诺",
    "threat": "处理潜在危机",
    "mystery": "逐步揭示谜团，保留悬念",
}

# 重写建议模板库
SUGGESTION_TEMPLATES = {
    "玄黄秘录": {
        "unexplained_item": "补充《玄黄秘录》的来源、内容或重要性描述",
        "suggestion": "可在附近段落简要提及《玄黄秘录》的来历或特殊之处",
    },
    "玄铁令牌": {
        "unexplained_item": "明确玄铁令牌的来源、持有者身份或象征意义",
        "suggestion": "可在黑衣客出现时暗示令牌的特殊身份或作用",
    },
    "青铜灯": {
        "unexplained_item": "解释青铜灯的特殊之处或用途",
        "suggestion": "可在描述青铜灯时暗示其不寻常的特性或用途",
    },
    "龙涎香": {
        "unexplained_item": "说明龙涎香的用途或来源",
        "suggestion": "可在描述灯油时简要提及龙涎香的稀有或特殊作用",
    },
    "五曜珠": {
        "unexplained_item": "介绍五曜珠的来历、作用或与玄黄秘境的关联",
        "suggestion": "可在沈鹤年提到五曜珠时简要补充相关背景",
    },
    "玄黄秘境": {
        "unresolved_setting": "建立玄黄秘境的初步设定",
        "suggestion": "可在对话中暗示玄黄秘境的大致位置或特征",
    },
    "天机阁": {
        "unresolved_setting": "介绍天机阁的身份或背景",
        "suggestion": "可在沈鹤年提到天机阁时暗示其势力或目的",
    },
    "墨香阁": {
        "unresolved_setting": "补充墨香阁的背景或设定",
        "suggestion": "可在进入墨香阁时简要描述其历史或特色",
    },
    "匕首": {
        "unexplained_item": "说明匕首的来历或特殊之处",
        "suggestion": "可在李玄握住匕首时暗示其特殊之处",
    },
}


def load_scene(scene_path: Path) -> Tuple[str, List[str]]:
    """加载场景 markdown，返回内容和行列表"""
    if not scene_path.exists():
        raise FileNotFoundError(f"场景文件不存在: {scene_path}")
    content = scene_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    return content, lines


def load_json_file(file_path: Path, file_type: str) -> Dict[str, Any]:
    """加载 JSON 文件"""
    if not file_path.exists():
        raise FileNotFoundError(f"{file_type} 文件不存在: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def generate_suggestion_from_debt(
    debt: Dict[str, Any],
    scene_lines: List[str],
    suggestion_id: str
) -> Dict[str, Any]:
    """从单个 plot debt 生成 rewrite suggestion"""
    debt_id = debt.get("debt_id", "")
    debt_type = debt.get("debt_type", "")
    entity = debt.get("entity", "")
    line_num = debt.get("line", 0)
    original_text = ""
    
    if 1 <= line_num <= len(scene_lines):
        original_text = scene_lines[line_num - 1].strip()
    
    rewrite_goal = REWRITE_GOALS.get(debt_type, "补充或修订相关内容")
    
    suggested_revision = ""
    if entity in SUGGESTION_TEMPLATES:
        suggested_revision = SUGGESTION_TEMPLATES[entity].get("suggestion", "")
    elif debt_type == "open_question":
        suggested_revision = "可在后续对话或段落中解释或铺垫这个问题"
    elif debt_type == "mystery":
        suggested_revision = "可在合适的地方逐步揭示这个谜团"
    elif debt_type == "foreshadowing":
        suggested_revision = "可在后续情节中铺垫或呼应这个伏笔"
    else:
        suggested_revision = "可考虑在后续段落中补充或修订相关内容"
    
    suggestion = {
        "suggestion_id": suggestion_id,
        "source_debt_id": debt_id,
        "target_line": line_num,
        "issue_type": debt_type,
        "entity": entity,
        "original_text": original_text,
        "rewrite_goal": rewrite_goal,
        "suggested_revision": suggested_revision,
        "risk_note": "此为自动建议，请人工审阅后再决定是否采纳",
        "needs_user_confirmation": True,
        "status": "candidate",
    }
    return suggestion


def build_rewrite_suggestions(
    scene_lines: List[str],
    plot_debt: Dict[str, Any],
    max_suggestions: int
) -> List[Dict[str, Any]]:
    """构建 rewrite suggestions"""
    debts = plot_debt.get("debts", [])
    
    # 优先选取有 entity 的 debt
    qualified_debts = [d for d in debts if d.get("entity")]
    
    # 按优先级排序：P1 > P2 > P3
    priority_order = {"P1": 0, "P2": 1, "P3": 2}
    qualified_debts.sort(key=lambda d: priority_order.get(d.get("priority", "P3"), 3))
    
    # 选取前 max_suggestions 个
    selected_debts = qualified_debts[:max_suggestions]
    
    suggestions = []
    for i, debt in enumerate(selected_debts, 1):
        suggestion_id = f"rewrite-suggestion-{i:03d}"
        suggestion = generate_suggestion_from_debt(debt, scene_lines, suggestion_id)
        suggestions.append(suggestion)
    
    return suggestions


def generate_markdown_report(
    rewrite_output: Dict[str, Any],
    scene_path: Path
) -> str:
    """生成 Markdown 报告"""
    lines = [
        "# 局部 Rewrite Engine 报告 (Dry-Run)",
        "",
        f"- **Phase**: {rewrite_output.get('phase')}",
        f"- **Engine**: {rewrite_output.get('engine')}",
        f"- **Source Scene**: {scene_path.name}",
        f"- **LLM Called**: {rewrite_output.get('llm_called')}",
        f"- **Auto Write Scene**: {rewrite_output.get('auto_write_scene')}",
        "",
        "## 摘要",
        "",
        f"- 总建议数: {len(rewrite_output.get('suggestions', []))}",
        f"- 需要用户确认: {sum(1 for s in rewrite_output.get('suggestions', []) if s.get('needs_user_confirmation'))}",
        "",
        "### 按 issue 类型分布",
        "",
        "| 类型 | 数量 |",
        "|------|------|",
    ]
    
    type_counts = {}
    for s in rewrite_output.get("suggestions", []):
        itype = s.get("issue_type", "unknown")
        type_counts[itype] = type_counts.get(itype, 0) + 1
    
    for itype, count in type_counts.items():
        lines.append(f"| {itype} | {count} |")
    
    lines.append("")
    
    if rewrite_output.get("suggestions"):
        lines.append("## 重写建议详情")
        lines.append("")
        
        for i, suggestion in enumerate(rewrite_output.get("suggestions", []), 1):
            lines.append(f"### 建议 {i}: {suggestion.get('suggestion_id')}")
            lines.append("")
            lines.append(f"- **源债务 ID**: {suggestion.get('source_debt_id')}")
            lines.append(f"- **目标行号**: {suggestion.get('target_line')}")
            lines.append(f"- **问题类型**: {suggestion.get('issue_type')}")
            lines.append(f"- **关联实体**: {suggestion.get('entity')}")
            lines.append("")
            lines.append("#### 原文")
            lines.append(f"```")
            lines.append(suggestion.get('original_text'))
            lines.append(f"```")
            lines.append("")
            lines.append("#### 重写目标")
            lines.append(f"{suggestion.get('rewrite_goal')}")
            lines.append("")
            lines.append("#### 建议修订")
            lines.append(f"{suggestion.get('suggested_revision')}")
            lines.append("")
            lines.append("#### 风险提示")
            lines.append(f"{suggestion.get('risk_note')}")
            lines.append("")
            lines.append(f"- **状态**: {suggestion.get('status')}")
            lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.6：局部 Rewrite Engine MVP (Dry-Run)"
    )
    parser.add_argument("--scene", type=Path, required=True,
                        help="场景 markdown 文件路径")
    parser.add_argument("--snapshot-json", type=Path, required=True,
                        help="State Snapshot JSON 文件路径")
    parser.add_argument("--plot-debt-json", type=Path, required=True,
                        help="Plot Debt JSON 文件路径")
    parser.add_argument("--reviews-json", type=Path, required=True,
                        help="Reviews JSON 文件路径")
    parser.add_argument("--output-json", type=Path, required=True,
                        help="输出 JSON 路径")
    parser.add_argument("--output-md", type=Path, required=True,
                        help="输出 Markdown 报告路径")
    parser.add_argument("--max-suggestions", type=int, default=5,
                        help="最大建议数 (默认: 5)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Phase T3-D7.6：局部 Rewrite Engine MVP (Dry-Run)")
    print("=" * 60)
    print()
    
    try:
        # 加载输入
        print("加载输入文件...")
        scene_content, scene_lines = load_scene(args.scene)
        snapshot = load_json_file(args.snapshot_json, "State Snapshot")
        plot_debt = load_json_file(args.plot_debt_json, "Plot Debt")
        reviews = load_json_file(args.reviews_json, "Reviews")
        print(f"✅ 加载场景文件: {args.scene}")
        print(f"✅ 加载 Snapshot: {args.snapshot_json}")
        print(f"✅ 加载 Plot Debt: {args.plot_debt_json}")
        print(f"✅ 加载 Reviews: {args.reviews_json}")
        print()
        
        # 构建 rewrite suggestions
        print("构建重写建议...")
        suggestions = build_rewrite_suggestions(
            scene_lines, plot_debt, args.max_suggestions
        )
        print(f"✅ 生成了 {len(suggestions)} 条重写建议")
        print()
        
        # 构建输出对象
        rewrite_output = {
            "phase": "T3-D7.6",
            "engine": "rewrite_engine",
            "source_scene": args.scene.name,
            "generated_from": {
                "snapshot_json": args.snapshot_json.name,
                "plot_debt_json": args.plot_debt_json.name,
                "reviews_json": args.reviews_json.name,
            },
            "llm_called": False,
            "auto_write_scene": False,
            "summary": {
                "total_suggestions": len(suggestions),
                "needs_user_confirmation": sum(1 for s in suggestions if s.get("needs_user_confirmation")),
            },
            "suggestions": suggestions,
        }
        
        # 保存 JSON
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(rewrite_output, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存输出 JSON: {args.output_json}")
        
        # 生成 Markdown 报告
        md_report = generate_markdown_report(rewrite_output, args.scene)
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(md_report, encoding="utf-8")
        print(f"✅ 生成 Markdown 报告: {args.output_md}")
        print()
        
        # 打印摘要
        print("📊 重写建议摘要:")
        print(f"   - 总建议数: {len(suggestions)}")
        print(f"   - 需要用户确认: {sum(1 for s in suggestions if s.get('needs_user_confirmation'))}")
        
    except Exception as e:
        print(f"❌ 发生错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("=" * 60)
    print("结果: ✅ SUCCESS")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
