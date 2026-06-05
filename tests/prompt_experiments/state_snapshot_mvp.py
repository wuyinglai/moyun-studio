#!/usr/bin/env python3
"""
Phase T3-D7.4: State Snapshot MVP

- 从 scene markdown、diff-engine candidates、review-engine output 生成状态快照
- 不调用 LLM
- 不自动入库
- 只做结构化状态沉淀
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_scene(scene_path: Path) -> str:
    """加载场景 markdown"""
    if not scene_path.exists():
        raise FileNotFoundError(f"场景文件不存在: {scene_path}")
    return scene_path.read_text(encoding="utf-8")


def load_candidates(candidates_path: Path) -> Dict[str, Any]:
    """加载 candidates JSON"""
    if not candidates_path.exists():
        raise FileNotFoundError(f"Candidates 文件不存在: {candidates_path}")
    with open(candidates_path, encoding="utf-8") as f:
        return json.load(f)


def load_reviews(reviews_path: Path) -> Dict[str, Any]:
    """加载 reviews JSON"""
    if not reviews_path.exists():
        raise FileNotFoundError(f"Reviews 文件不存在: {reviews_path}")
    with open(reviews_path, encoding="utf-8") as f:
        return json.load(f)


def build_state_snapshot(
    scene_content: str,
    candidates: Dict[str, Any],
    reviews: Dict[str, Any]
) -> Dict[str, Any]:
    """构建 State Snapshot"""
    
    snapshot = {
        "phase": "T3-D7.4",
        "engine": "memory_engine",
        "artifact": "state_snapshot",
        "source_scene": None,
        "generated_from": {
            "candidates_json": None,
            "reviews_json": None
        },
        "llm_called": False,
        "auto_write_settings": False,
        "summary": {
            "confirmed_candidates": 0,
            "ignored_candidates": 0,
            "needs_user_confirmation": 0,
            "suggested_settings_updates": 0
        },
        "entities": {
            "characters": [],
            "locations": [],
            "items": [],
            "factions": [],
            "terms": []
        },
        "confirmed_candidates": [],
        "ignored_candidates": [],
        "needs_user_confirmation": [],
        "suggested_settings_updates": [],
        "open_threads": [],
        "warnings": []
    }

    # 提取场景标题
    if scene_content.startswith("# "):
        title_end = scene_content.find("\n")
        snapshot["source_scene"] = scene_content[2:title_end].strip()
    else:
        snapshot["source_scene"] = "未知场景"

    # 收集候选信息
    candidate_map = {}
    for item in candidates.get("items", []):
        candidate_map[item["candidate_id"]] = item

    # 处理 reviews
    reviews_list = reviews.get("reviews", [])
    review_candidate_ids = set()

    for review in reviews_list:
        candidate_id = review["candidate_id"]
        review_candidate_ids.add(candidate_id)
        candidate = candidate_map.get(candidate_id)

        confirmed = review.get("confirmed", False)
        action = review.get("action", "")
        needs_confirmation = review.get("needs_user_confirmation", False)
        suggested_entry = review.get("suggested_entry", {})
        suggested_target = review.get("suggested_target", "")

        # 构建记录项
        record = {
            "candidate_id": candidate_id,
            "confirmed": confirmed,
            "action": action,
            "reason": review.get("reason", ""),
            "severity": review.get("severity", "P3"),
            "confidence": review.get("confidence", 0.0)
        }

        if candidate:
            record["entity"] = candidate.get("entity", "")
            record["entity_type"] = candidate.get("entity_type", "")
            record["type"] = candidate.get("type", "")
            record["line"] = candidate.get("line", 0)

        # 分类处理
        if confirmed and action == "suggest_add_to_settings":
            snapshot["confirmed_candidates"].append(record)
            snapshot["needs_user_confirmation"].append(record)
            
            # 建议的设置更新
            if suggested_entry:
                update_item = {
                    "candidate_id": candidate_id,
                    "target_file": suggested_target,
                    "entry": suggested_entry,
                    "reason": review.get("reason", "")
                }
                snapshot["suggested_settings_updates"].append(update_item)
                
                # 归类到 entities
                entity_type = suggested_entry.get("type", "").lower()
                if entity_type == "character":
                    snapshot["entities"]["characters"].append(suggested_entry)
                elif entity_type == "item":
                    snapshot["entities"]["items"].append(suggested_entry)
                elif entity_type == "faction":
                    snapshot["entities"]["factions"].append(suggested_entry)
                elif entity_type == "term":
                    snapshot["entities"]["terms"].append(suggested_entry)

        elif not confirmed and action == "suggest_ignore":
            snapshot["ignored_candidates"].append(record)

        elif needs_confirmation:
            snapshot["needs_user_confirmation"].append(record)

    # 检查缺失的 review
    for candidate_id in candidate_map:
        if candidate_id not in review_candidate_ids:
            snapshot["warnings"].append({
                "type": "missing_review",
                "message": f"候选 {candidate_id} 没有对应的 review"
            })

    # 数量不一致警告
    if len(candidate_map) != len(reviews_list):
        snapshot["warnings"].append({
            "type": "count_mismatch",
            "message": f"Candidates 数量({len(candidate_map)})与 Reviews 数量({len(reviews_list)})不一致"
        })

    # 更新摘要统计
    snapshot["summary"]["confirmed_candidates"] = len(snapshot["confirmed_candidates"])
    snapshot["summary"]["ignored_candidates"] = len(snapshot["ignored_candidates"])
    snapshot["summary"]["needs_user_confirmation"] = len(snapshot["needs_user_confirmation"])
    snapshot["summary"]["suggested_settings_updates"] = len(snapshot["suggested_settings_updates"])

    # 提取开放线程（从场景内容和候选中推断）
    snapshot["open_threads"] = extract_open_threads(scene_content, candidates)

    return snapshot


def extract_open_threads(scene_content: str, candidates: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从场景内容和候选中提取开放线程/伏笔"""
    threads = []
    
    # 基于关键词提取潜在伏笔
    keywords = ["秘录", "令牌", "天机", "秘境", "珠", "古画", "玄机"]
    lines = scene_content.split("\n")
    
    for i, line in enumerate(lines, 1):
        for keyword in keywords:
            if keyword in line:
                threads.append({
                    "line": i,
                    "content": line.strip(),
                    "type": "potential_plot_thread",
                    "keyword": keyword
                })
    
    return threads


def generate_markdown_report(snapshot: Dict[str, Any], scene_content: str) -> str:
    """生成 Markdown 报告"""
    lines = [
        "# State Snapshot 报告",
        "",
        f"- **Phase**: {snapshot['phase']}",
        f"- **Engine**: {snapshot['engine']}",
        f"- **Artifact**: {snapshot['artifact']}",
        f"- **Source Scene**: {snapshot['source_scene']}",
        f"- **LLM Called**: {'Yes' if snapshot.get('llm_called') else 'No'}",
        f"- **Auto Write Settings**: {'Yes' if snapshot.get('auto_write_settings') else 'No'}",
        "",
        "## 摘要",
        "",
        "| 类别 | 数量 |",
        "|------|------|",
        f"| 已确认候选 | {snapshot['summary']['confirmed_candidates']} |",
        f"| 已忽略候选 | {snapshot['summary']['ignored_candidates']} |",
        f"| 需要用户确认 | {snapshot['summary']['needs_user_confirmation']} |",
        f"| 建议设置更新 | {snapshot['summary']['suggested_settings_updates']} |",
        "",
    ]

    # 实体汇总
    lines.append("## 实体汇总")
    lines.append("")
    
    entity_types = ["characters", "locations", "items", "factions", "terms"]
    entity_labels = ["角色", "地点", "道具", "势力", "术语"]
    
    for et, label in zip(entity_types, entity_labels):
        entities = snapshot["entities"].get(et, [])
        lines.append(f"### {label} ({len(entities)})")
        lines.append("")
        if entities:
            for e in entities:
                lines.append(f"- **{e.get('name', '')}**: {e.get('role', '')}")
            lines.append("")
        else:
            lines.append("- 无")
            lines.append("")

    # 建议的设置更新
    if snapshot["suggested_settings_updates"]:
        lines.append("## 建议的设置更新")
        lines.append("")
        for update in snapshot["suggested_settings_updates"]:
            lines.append(f"### {update['entry'].get('name', '')}")
            lines.append(f"- **目标文件**: {update.get('target_file', '')}")
            lines.append(f"- **类型**: {update['entry'].get('type', '')}")
            lines.append(f"- **角色/描述**: {update['entry'].get('role', '')}")
            lines.append(f"- **原因**: {update.get('reason', '')}")
            lines.append("")

    # 需要用户确认的项
    if snapshot["needs_user_confirmation"]:
        lines.append("## 需要用户确认")
        lines.append("")
        for item in snapshot["needs_user_confirmation"]:
            lines.append(f"- **{item.get('entity', item.get('candidate_id', ''))}**: {item.get('reason', '')}")
        lines.append("")

    # 开放线程
    if snapshot["open_threads"]:
        lines.append("## 开放线程/伏笔")
        lines.append("")
        for thread in snapshot["open_threads"]:
            lines.append(f"- **第 {thread['line']} 行**: {thread['content']}")
        lines.append("")

    # 警告
    if snapshot["warnings"]:
        lines.append("## 警告")
        lines.append("")
        for warning in snapshot["warnings"]:
            lines.append(f"- ⚠️ {warning['message']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.4: State Snapshot MVP"
    )
    parser.add_argument("--scene", type=Path, required=True,
                        help="场景 markdown 文件路径")
    parser.add_argument("--candidates-json", type=Path, required=True,
                        help="Candidates JSON 文件路径")
    parser.add_argument("--reviews-json", type=Path, required=True,
                        help="Reviews JSON 文件路径")
    parser.add_argument("--output-json", type=Path, required=True,
                        help="输出 JSON 路径")
    parser.add_argument("--output-md", type=Path, required=True,
                        help="输出 Markdown 报告路径")

    args = parser.parse_args()

    print("=" * 60)
    print("Phase T3-D7.4: State Snapshot MVP")
    print("=" * 60)
    print()

    try:
        # 加载输入
        print("加载输入文件...")
        scene_content = load_scene(args.scene)
        candidates = load_candidates(args.candidates_json)
        reviews = load_reviews(args.reviews_json)
        print(f"✅ 加载场景文件: {args.scene}")
        print(f"✅ 加载 Candidates: {args.candidates_json}")
        print(f"✅ 加载 Reviews: {args.reviews_json}")
        print()

        # 构建 snapshot
        print("构建 State Snapshot...")
        snapshot = build_state_snapshot(scene_content, candidates, reviews)
        
        # 记录来源
        snapshot["generated_from"]["candidates_json"] = args.candidates_json.name
        snapshot["generated_from"]["reviews_json"] = args.reviews_json.name
        
        print("✅ 构建完成")
        print()

        # 保存 JSON
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存输出 JSON: {args.output_json}")

        # 生成 Markdown 报告
        md_report = generate_markdown_report(snapshot, scene_content)
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(md_report, encoding="utf-8")
        print(f"✅ 生成 Markdown 报告: {args.output_md}")
        print()

        # 打印摘要
        print("📊 Snapshot 摘要:")
        print(f"   - 已确认候选: {snapshot['summary']['confirmed_candidates']}")
        print(f"   - 已忽略候选: {snapshot['summary']['ignored_candidates']}")
        print(f"   - 需要确认: {snapshot['summary']['needs_user_confirmation']}")
        print(f"   - 建议更新: {snapshot['summary']['suggested_settings_updates']}")
        print(f"   - 警告数: {len(snapshot['warnings'])}")

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
