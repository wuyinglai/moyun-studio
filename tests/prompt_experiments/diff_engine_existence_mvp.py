#!/usr/bin/env python3
"""
Phase T3-D7.1: Diff Engine Existence MVP

只做存在性比对：
- 扫描正文提取候选实体
- 与设定库已有条目比对
- 输出 candidates
- 不调用 LLM
- 不自动入库
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any


def load_settings(settings_dir: Path) -> Dict[str, List[str]]:
    """
    加载设定库，返回各类型的实体列表
    """
    settings = {
        "character": [],
        "location": [],
        "item": [],
        "faction": [],
        "term": []
    }
    
    # 角色设定
    char_file = settings_dir / "characters.md"
    if char_file.exists():
        content = char_file.read_text(encoding="utf-8")
        # 提取 ## 后面的角色名
        matches = re.findall(r"##\s+(\S+)", content)
        settings["character"].extend(matches)
    
    # 地点设定
    loc_file = settings_dir / "locations.md"
    if loc_file.exists():
        content = loc_file.read_text(encoding="utf-8")
        matches = re.findall(r"##\s+(\S+)", content)
        settings["location"].extend(matches)
    
    # 道具设定
    item_file = settings_dir / "items.md"
    if item_file.exists():
        content = item_file.read_text(encoding="utf-8")
        matches = re.findall(r"##\s+(\S+)", content)
        settings["item"].extend(matches)
    
    # 势力设定
    fact_file = settings_dir / "factions.md"
    if fact_file.exists():
        content = fact_file.read_text(encoding="utf-8")
        matches = re.findall(r"##\s+(\S+)", content)
        settings["faction"].extend(matches)
    
    # 术语设定
    term_file = settings_dir / "terms.md"
    if term_file.exists():
        content = term_file.read_text(encoding="utf-8")
        matches = re.findall(r"##\s+(\S+)", content)
        settings["term"].extend(matches)
    
    return settings


def extract_candidates(scene_path: Path, settings: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    从场景中提取候选实体
    """
    candidates = []
    
    scene_content = scene_path.read_text(encoding="utf-8")
    lines = scene_content.splitlines()
    
    # 简单的提取策略：
    # 1. 从角色相关词前面提取 2-3 字
    # 2. 从引号中提取书名
    # 3. 从专有名词模式提取
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        # 提取角色候选：掌柜X、X公子、X客 等模式
        char_patterns = [
            r"掌柜(\S{2,3})",
            r"(\S{2,3})公子",
            r"(\S{2,3})客"
        ]
        for pattern in char_patterns:
            matches = re.findall(pattern, line)
            for char_name in matches:
                if char_name not in settings["character"]:
                    candidate_id = f"scene-line{line_num:03d}-new_character-{char_name}"
                    candidates.append({
                        "candidate_id": candidate_id,
                        "compare_type": "existence",
                        "source_file": scene_path.name,
                        "reference_file": "settings/characters.md",
                        "line": line_num,
                        "entity": char_name,
                        "entity_type": "character",
                        "type": "new_character_candidate",
                        "text": line,
                        "reason": "正文出现疑似角色名，但角色设定库未记录",
                        "review_instruction": "请判断是否为新角色；若是，建议加入角色设定库。",
                        "priority": "P1"
                    })
        
        # 提取地点候选
        loc_patterns = [
            r"(\S{2,5})阁",
            r"(\S{2,5})楼",
            r"(\S{2,5})镇"
        ]
        for pattern in loc_patterns:
            matches = re.findall(pattern, line)
            for loc_name in matches:
                full_loc = f"{loc_name}阁" if "阁" in line[-2:] else f"{loc_name}"
                if full_loc not in settings["location"]:
                    candidate_id = f"scene-line{line_num:03d}-new_location-{full_loc}"
                    candidates.append({
                        "candidate_id": candidate_id,
                        "compare_type": "existence",
                        "source_file": scene_path.name,
                        "reference_file": "settings/locations.md",
                        "line": line_num,
                        "entity": full_loc,
                        "entity_type": "location",
                        "type": "new_location_candidate",
                        "text": line,
                        "reason": "正文出现疑似地点，但地点设定库未记录",
                        "review_instruction": "请判断是否为新地点；若是，建议加入地点设定库。",
                        "priority": "P2"
                    })
        
        # 提取道具候选：书名《X》、X灯、X珠 等
        book_matches = re.findall(r"《([^》]{2,10})》", line)
        for book_name in book_matches:
            if book_name not in settings["item"]:
                candidate_id = f"scene-line{line_num:03d}-new_item-{book_name}"
                candidates.append({
                    "candidate_id": candidate_id,
                    "compare_type": "existence",
                    "source_file": scene_path.name,
                    "reference_file": "settings/items.md",
                    "line": line_num,
                    "entity": book_name,
                    "entity_type": "item",
                    "type": "new_item_candidate",
                    "text": line,
                    "reason": "正文出现疑似道具/书籍，但道具设定库未记录",
                    "review_instruction": "请判断是否为新道具；若是，建议加入道具设定库。",
                    "priority": "P2"
                })
        
        # 提取势力候选：X阁、X门、X派、X会
        faction_patterns = [
            r"(\S{2,4})阁",
            r"(\S{2,4})门",
            r"(\S{2,4})派",
            r"(\S{2,4})会"
        ]
        for pattern in faction_patterns:
            matches = re.findall(pattern, line)
            for faction_name in matches:
                # 简单判断：如果后面跟"阁"且是专有名词
                if "阁" in line and faction_name in line:
                    full_faction = f"{faction_name}阁"
                    if full_faction not in settings["faction"]:
                        candidate_id = f"scene-line{line_num:03d}-new_faction-{full_faction}"
                        candidates.append({
                            "candidate_id": candidate_id,
                            "compare_type": "existence",
                            "source_file": scene_path.name,
                            "reference_file": "settings/factions.md",
                            "line": line_num,
                            "entity": full_faction,
                            "entity_type": "faction",
                            "type": "new_faction_candidate",
                            "text": line,
                            "reason": "正文出现疑似势力，但势力设定库未记录",
                            "review_instruction": "请判断是否为新势力；若是，建议加入势力设定库。",
                            "priority": "P1"
                        })
        
        # 提取术语候选：X珠、X秘录、X秘境
        term_patterns = [
            r"(\S{2,3})珠",
            r"(\S{2,4})秘录",
            r"(\S{2,4})秘境"
        ]
        for pattern in term_patterns:
            matches = re.findall(pattern, line)
            for term_name in matches:
                # 组合完整术语
                if "珠" in line:
                    full_term = f"{term_name}珠"
                elif "秘录" in line:
                    full_term = f"{term_name}秘录"
                elif "秘境" in line:
                    full_term = f"{term_name}秘境"
                else:
                    full_term = term_name
                
                if full_term not in settings["term"]:
                    candidate_id = f"scene-line{line_num:03d}-new_term-{full_term}"
                    candidates.append({
                        "candidate_id": candidate_id,
                        "compare_type": "existence",
                        "source_file": scene_path.name,
                        "reference_file": "settings/terms.md",
                        "line": line_num,
                        "entity": full_term,
                        "entity_type": "term",
                        "type": "new_term_candidate",
                        "text": line,
                        "reason": "正文出现疑似术语/特殊物品，但术语设定库未记录",
                        "review_instruction": "请判断是否为新术语；若是，建议加入术语设定库。",
                        "priority": "P2"
                    })
    
    # 去重（按 candidate_id）
    unique_candidates = list({c["candidate_id"]: c for c in candidates}.values())
    
    return unique_candidates


def generate_json_output(candidates: List[Dict[str, Any]], scene_path: Path) -> Dict[str, Any]:
    """
    生成 JSON 输出
    """
    output = {
        "phase": "T3-D7.1",
        "engine": "diff_engine",
        "compare_type": "existence",
        "mode": "candidates_only",
        "llm_called": False,
        "auto_write_settings": False,
        "summary": {
            "items_found": len(candidates),
            "types_found": {
                "new_character_candidate": len([c for c in candidates if c["type"] == "new_character_candidate"]),
                "new_location_candidate": len([c for c in candidates if c["type"] == "new_location_candidate"]),
                "new_item_candidate": len([c for c in candidates if c["type"] == "new_item_candidate"]),
                "new_faction_candidate": len([c for c in candidates if c["type"] == "new_faction_candidate"]),
                "new_term_candidate": len([c for c in candidates if c["type"] == "new_term_candidate"])
            }
        },
        "items": candidates
    }
    return output


def generate_markdown_report(candidates: List[Dict[str, Any]], scene_path: Path, output_path: Path):
    """
    生成 Markdown 报告
    """
    report_lines = [
        "# Diff Engine Existence MVP Report",
        "",
        f"- **Phase**: T3-D7.1",
        f"- **Engine**: diff_engine",
        f"- **Compare Type**: existence",
        f"- **Scene**: {scene_path.name}",
        f"- **Candidates Found**: {len(candidates)}",
        f"- **LLM Called**: No",
        f"- **Auto Write Settings**: No",
        "",
        "## 摘要",
        "",
        "本报告由 Diff Engine Existence MVP 自动生成。",
        "所有条目均为 candidate，需要人工或 LLM 审核确认。",
        "",
        "## Candidates 列表",
        ""
    ]
    
    # 按类型分组
    types = ["new_character_candidate", "new_location_candidate", "new_item_candidate", "new_faction_candidate", "new_term_candidate"]
    type_names = {
        "new_character_candidate": "新角色候选",
        "new_location_candidate": "新地点候选",
        "new_item_candidate": "新道具候选",
        "new_faction_candidate": "新势力候选",
        "new_term_candidate": "新术语候选"
    }
    
    for candidate_type in types:
        type_candidates = [c for c in candidates if c["type"] == candidate_type]
        if type_candidates:
            report_lines.append(f"### {type_names[candidate_type]}")
            report_lines.append("")
            for c in type_candidates:
                report_lines.append(f"- **{c['entity']}** (line {c['line']}, {c['priority']})")
                report_lines.append(f"  - Text: `{c['text']}`")
                report_lines.append(f"  - Reason: {c['reason']}")
                report_lines.append(f"  - Review: {c['review_instruction']}")
                report_lines.append("")
    
    report_content = "\n".join(report_lines)
    output_path.write_text(report_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.1: Diff Engine Existence MVP - 存在性比对，输出 candidates，不调用 LLM，不自动入库"
    )
    parser.add_argument("--scene", type=Path, required=True, help="场景文件路径")
    parser.add_argument("--settings-dir", type=Path, required=True, help="设定库目录路径")
    parser.add_argument("--output-json", type=Path, required=True, help="输出 JSON 文件路径")
    parser.add_argument("--output-md", type=Path, required=True, help="输出 Markdown 报告路径")
    parser.add_argument("--max-items", type=int, default=300, help="最大 candidate 数量（默认 300）")
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not args.scene.exists():
        print(f"❌ 场景文件不存在: {args.scene}")
        return 1
    if not args.settings_dir.exists():
        print(f"❌ 设定库目录不存在: {args.settings_dir}")
        return 1
    
    # 加载设定
    settings = load_settings(args.settings_dir)
    print(f"✅ 加载设定库:")
    print(f"   - 角色: {len(settings['character'])} 个")
    print(f"   - 地点: {len(settings['location'])} 个")
    print(f"   - 道具: {len(settings['item'])} 个")
    print(f"   - 势力: {len(settings['faction'])} 个")
    print(f"   - 术语: {len(settings['term'])} 个")
    
    # 提取 candidates
    candidates = extract_candidates(args.scene, settings)
    
    # 限制数量
    if len(candidates) > args.max_items:
        candidates = candidates[:args.max_items]
        print(f"⚠️ 限制 candidate 数量为 {args.max_items}")
    
    print(f"✅ 提取 {len(candidates)} 个 candidates")
    
    # 生成 JSON
    json_output = generate_json_output(candidates, args.scene)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON 输出: {args.output_json}")
    
    # 生成 Markdown 报告
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    generate_markdown_report(candidates, args.scene, args.output_md)
    
    print(f"✅ Markdown 报告: {args.output_md}")
    print("\n✨ Phase T3-D7.1 完成！注意：")
    print("   - 所有条目均为 candidate，未确认")
    print("   - 没有调用 LLM")
    print("   - 没有自动更新设定库")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
