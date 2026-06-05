#!/usr/bin/env python3
"""
Phase T3-D7.1.1: Diff Engine Existence MVP (降噪版)

只做存在性比对：
- 扫描正文提取候选实体
- 与设定库已有条目比对
- 输出 candidates
- 不调用 LLM
- 不自动入库
- 增加候选清洗，过滤明显无效候选
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple


# 无效候选过滤规则
INVALID_PREFIXES = [
    "：", "：\"", "，", "。", "！", "？", "、", "；",
    "\"", "'", "（", "）", "【", "】",
    "个", "了", "的", "和", "与", "或", "在", "是", "有"
]

INVALID_SUFFIXES = [
    "：", "\"", "'", "，", "。", "！", "？", "、", "；",
    "（", "）", "【", "】", "这", "是", "我", "找"
]

INVALID_CONTAINS = [
    "走进", "这是", "我找", "你知", "刻着", "黑衣"
]

MIN_ENTITY_LENGTH = 2
MAX_ENTITY_LENGTH = 10


def is_valid_candidate(entity: str, entity_type: str) -> bool:
    """
    判断候选是否有效
    """
    # 过滤过短或过长
    if len(entity) < MIN_ENTITY_LENGTH or len(entity) > MAX_ENTITY_LENGTH:
        return False
    
    # 过滤以无效前缀开头
    for prefix in INVALID_PREFIXES:
        if entity.startswith(prefix):
            return False
    
    # 过滤以无效后缀结尾
    for suffix in INVALID_SUFFIXES:
        if entity.endswith(suffix):
            return False
    
    # 过滤包含无效内容
    for invalid in INVALID_CONTAINS:
        if invalid in entity:
            return False
    
    # 过滤纯数字
    if entity.isdigit():
        return False
    
    # 过滤包含过多标点
    punct_count = sum(1 for c in entity if c in "：，。！？、；\"'（）【】")
    if punct_count > 0:
        return False
    
    return True


def clean_candidates(raw_candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    清洗候选，返回有效候选和过滤数量
    """
    filtered_count = 0
    cleaned = []
    
    for candidate in raw_candidates:
        entity = candidate["entity"]
        entity_type = candidate["entity_type"]
        
        if is_valid_candidate(entity, entity_type):
            cleaned.append(candidate)
        else:
            filtered_count += 1
    
    return cleaned, filtered_count


def deduplicate_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    按 entity_type + entity 去重，保留最早的 candidate_id
    """
    seen = {}
    for candidate in candidates:
        key = f"{candidate['entity_type']}-{candidate['entity']}"
        if key not in seen:
            seen[key] = candidate
    
    return list(seen.values())


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
        
        # 提取道具候选：书名《X》、X灯、X珠、X令牌、X香 等
        item_patterns = [
            r"《([^》]{2,10})》",  # 书名
            r"(\S{2,4})灯",       # 灯
            r"(\S{2,4})香",       # 香
            r"(\S{2,4})令牌",     # 令牌
            r"(\S{2,4})铁",       # 铁/金属
            r"(\S{2,4})剑",       # 剑
            r"(\S{2,4})刀"        # 刀
        ]
        for pattern in item_patterns:
            matches = re.findall(pattern, line)
            for item_name in matches:
                # 组合完整道具名
                if "令牌" in pattern:
                    full_item = f"{item_name}令牌"
                elif "灯" in pattern:
                    full_item = f"{item_name}灯"
                elif "香" in pattern:
                    full_item = f"{item_name}香"
                elif "铁" in pattern:
                    full_item = f"{item_name}铁"
                elif "剑" in pattern:
                    full_item = f"{item_name}剑"
                elif "刀" in pattern:
                    full_item = f"{item_name}刀"
                else:
                    full_item = item_name
                
                if full_item not in settings["item"]:
                    candidate_id = f"scene-line{line_num:03d}-new_item-{full_item}"
                    candidates.append({
                        "candidate_id": candidate_id,
                        "compare_type": "existence",
                        "source_file": scene_path.name,
                        "reference_file": "settings/items.md",
                        "line": line_num,
                        "entity": full_item,
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
        
        # 提取术语候选：X珠、X秘录、X秘境、X钥匙
        term_patterns = [
            r"(\S{2,3})珠",
            r"(\S{2,4})秘录",
            r"(\S{2,4})秘境",
            r"(\S{2,4})钥匙"
        ]
        for pattern in term_patterns:
            matches = re.findall(pattern, line)
            for term_name in matches:
                # 组合完整术语
                if "珠" in pattern:
                    full_term = f"{term_name}珠"
                elif "秘录" in pattern:
                    full_term = f"{term_name}秘录"
                elif "秘境" in pattern:
                    full_term = f"{term_name}秘境"
                elif "钥匙" in pattern:
                    full_term = f"{term_name}钥匙"
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


def extract_candidates_with_stats(scene_path: Path, settings: Dict[str, List[str]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    从场景中提取候选实体，并返回统计信息
    """
    raw_candidates = extract_candidates(scene_path, settings)
    raw_count = len(raw_candidates)
    
    # 清洗候选
    cleaned_candidates, filtered_by_noise = clean_candidates(raw_candidates)
    cleaned_count = len(cleaned_candidates)
    
    # 去重
    final_candidates = deduplicate_candidates(cleaned_candidates)
    final_count = len(final_candidates)
    
    # 计算总过滤数（噪声过滤 + 去重过滤）
    filtered_by_dedup = cleaned_count - final_count
    total_filtered = filtered_by_noise + filtered_by_dedup
    
    stats = {
        "raw_candidates": raw_count,
        "filtered_candidates": total_filtered,
        "final_candidates": final_count,
        "filtered_by_noise": filtered_by_noise,
        "filtered_by_dedup": filtered_by_dedup
    }
    
    return final_candidates, stats


def generate_json_output(candidates: List[Dict[str, Any]], scene_path: Path, stats: Dict[str, int]) -> Dict[str, Any]:
    """
    生成 JSON 输出
    """
    output = {
        "phase": "T3-D7.1.1",
        "engine": "diff_engine",
        "compare_type": "existence",
        "mode": "candidates_only",
        "llm_called": False,
        "auto_write_settings": False,
        "noise_reduction": {
            "raw_candidates": stats["raw_candidates"],
            "filtered_by_noise": stats["filtered_by_noise"],
            "filtered_by_dedup": stats["filtered_by_dedup"],
            "filtered_candidates": stats["filtered_candidates"],
            "final_candidates": stats["final_candidates"]
        },
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


def generate_markdown_report(candidates: List[Dict[str, Any]], scene_path: Path, stats: Dict[str, int], output_path: Path):
    """
    生成 Markdown 报告
    """
    report_lines = [
        "# Diff Engine Existence MVP Report",
        "",
        f"- **Phase**: T3-D7.1.1",
        f"- **Engine**: diff_engine",
        f"- **Compare Type**: existence",
        f"- **Scene**: {scene_path.name}",
        f"- **LLM Called**: No",
        f"- **Auto Write Settings**: No",
        "",
        "## 噪声过滤统计",
        "",
        f"- **原始候选数**: {stats['raw_candidates']}",
        f"- **噪声过滤数**: {stats['filtered_by_noise']}",
        f"- **去重过滤数**: {stats['filtered_by_dedup']}",
        f"- **总过滤数**: {stats['filtered_candidates']}",
        f"- **最终候选数**: {stats['final_candidates']}",
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
    
    # 提取 candidates（带统计）
    candidates, stats = extract_candidates_with_stats(args.scene, settings)
    
    # 限制数量
    if len(candidates) > args.max_items:
        candidates = candidates[:args.max_items]
        print(f"⚠️ 限制 candidate 数量为 {args.max_items}")
    
    print(f"✅ 提取候选:")
    print(f"   - 原始候选: {stats['raw_candidates']} 个")
    print(f"   - 过滤候选: {stats['filtered_candidates']} 个")
    print(f"   - 最终候选: {stats['final_candidates']} 个")
    
    # 生成 JSON
    json_output = generate_json_output(candidates, args.scene, stats)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON 输出: {args.output_json}")
    
    # 生成 Markdown 报告
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    generate_markdown_report(candidates, args.scene, stats, args.output_md)
    
    print(f"✅ Markdown 报告: {args.output_md}")
    print("\n✨ Phase T3-D7.1.1 完成！注意：")
    print("   - 所有条目均为 candidate，未确认")
    print("   - 没有调用 LLM")
    print("   - 没有自动更新设定库")
    print("   - 已过滤明显无效候选")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
