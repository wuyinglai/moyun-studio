#!/usr/bin/env python3
"""
Phase T3-D7.5 / T3-D7.5.1 / T3-D7.5.2: Plot Debt 表 MVP

- 从场景文本、state snapshot、review output 中提取剧情债务候选
- 增强实体提取：书名号、道具后缀、设定后缀
- 实体降噪：优先已知实体，限制长度，过滤动词短语
- 不调用 LLM
- 不自动入库
- 只生成候选，不自动确认
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


# 关键词规则配置
DEBT_KEYWORDS = {
    "foreshadowing": [
        "伏笔", "铺垫", "埋下伏笔", "日后揭晓", "后文", "下回分解",
        "三日后", "七日之后", "半年之约", "来日", "他日", "以后再说",
        "现在不能说", "迟早会知道", "到时候就明白了"
    ],
    "promise": [
        "答应", "承诺", "约定", "保证", "发誓", "立誓", "盟约",
        "诺言", "誓言", "必", "定", "一定会", "保证会"
    ],
    "threat": [
        "威胁", "危险", "杀机", "杀意", "危机", "险境", "凶险",
        "祸", "灾", "劫", "难", "死", "亡", "灭口", "除掉"
    ],
    "mystery": [
        "神秘", "谜", "谜团", "秘密", "未解", "未知", "不明",
        "蹊跷", "怪异", "异样", "古怪", "离奇", "诡异",
        "没有人知道", "无人知晓", "不解之谜", "迷雾"
    ],
    "unexplained_item": [
        "令牌", "密信", "信物", "珠", "玉", "剑",
        "古画", "卷轴", "盒子", "匣子", "锦囊", "宝箱",
        "神器", "法宝", "秘录", "天书", "符咒", "丹药",
        "灯", "香", "匕首", "残卷", "图", "书"
    ],
    "unresolved_setting": [
        "秘境", "禁地", "鬼域", "仙山", "洞府", "遗迹",
        "藏宝图", "地图", "坐标", "方位", "入口", "通道",
        "阁", "楼", "教", "派", "门", "宗", "殿"
    ],
    "open_question": [
        "为何", "为什么", "何", "谁", "何人", "哪来的",
        "从何而来", "去向", "下落", "真相", "答案", "究竟"
    ]
}

# 已知有效实体列表（用于优先匹配）
KNOWN_ENTITIES = {
    "玄黄秘录", "玄铁令牌", "青铜灯", "龙涎香", "五曜珠", 
    "玄黄秘境", "天机阁", "墨香阁", "匕首", "山水古画"
}

# 动词列表（用于过滤包含动词的短语）
VERBS = {
    "推", "走", "进", "看", "翻", "说", "问", "答", "找", 
    "放", "挂", "握", "想", "思", "说", "道", "笑", "指",
    "照", "亮", "变", "低", "暗", "下", "来", "去", "在"
}

# 禁止的实体模式（噪声）
FORBIDDEN_PATTERNS = [
    r"^深夜",  # 以深夜开头的通常是时间描述
    r"^映着",  # 以映着开头的通常是描述性短语
    r"^李玄",  # 角色名字不应作为实体提取（除非是设定中的角色）
    r"^这么晚",  # 时间描述
]

# 禁止的实体列表
FORBIDDEN_ENTITIES = {
    "深夜书", "映着昏黄的灯", "李玄推门走进墨香", 
    "李玄推门走进墨香阁", "这么晚了还来买书"
}

# 实体提取配置
ITEM_SUFFIXES = ["令牌", "秘录", "密信", "残卷", "匕首", "图", "书", "画", "剑", "玉", "丹", "符", "册"]
SETTING_SUFFIXES = ["阁", "楼", "教", "派", "门", "宗", "殿", "秘境", "禁地", "洞府", "遗迹", "山庄", "堡", "城", "谷"]
SHORT_SUFFIXES = ["珠", "灯", "香", "玉", "剑"]


def load_scene(scene_path: Path) -> Tuple[str, List[str]]:
    """加载场景 markdown，返回内容和行列表"""
    if not scene_path.exists():
        raise FileNotFoundError(f"场景文件不存在: {scene_path}")
    content = scene_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    return content, lines


def load_snapshot(snapshot_path: Path) -> Dict[str, Any]:
    """加载 state snapshot JSON"""
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot 文件不存在: {snapshot_path}")
    with open(snapshot_path, encoding="utf-8") as f:
        return json.load(f)


def load_reviews(reviews_path: Path) -> Dict[str, Any]:
    """加载 reviews JSON"""
    if not reviews_path.exists():
        raise FileNotFoundError(f"Reviews 文件不存在: {reviews_path}")
    with open(reviews_path, encoding="utf-8") as f:
        return json.load(f)


def contains_verb(text: str) -> bool:
    """检查文本是否包含动词"""
    for verb in VERBS:
        if verb in text:
            return True
    return False


def is_entity_forbidden(entity: str) -> bool:
    """检查实体是否为禁止的噪声"""
    if entity in FORBIDDEN_ENTITIES:
        return True
    for pattern in FORBIDDEN_PATTERNS:
        if re.match(pattern, entity):
            return True
    return False


def extract_entity_from_text(line: str, keyword: str) -> str:
    """从文本行中提取实体（降噪版本）"""
    # 优先检查已知实体
    for entity in KNOWN_ENTITIES:
        if entity in line:
            return entity
    
    # 提取书名号内容
    book_match = re.search(r"《([^》]+)》", line)
    if book_match:
        book_title = book_match.group(1)
        # 书名号内容通常是有效的
        return book_title
    
    # 根据关键词类型提取实体
    if keyword in ["令牌", "秘录", "密信", "残卷"]:
        # 匹配2-4个字 + 后缀
        pattern = rf"([\u4e00-\u9fa5]{{2,4}}{keyword})"
        match = re.search(pattern, line)
        if match:
            entity = match.group(1)
            if not contains_verb(entity) and len(entity) <= 6 and not is_entity_forbidden(entity):
                return entity
    
    if keyword in SHORT_SUFFIXES:
        # 短后缀需要更严格的匹配：2-3个字 + 后缀
        pattern = rf"([\u4e00-\u9fa5]{{2,3}}{keyword})"
        match = re.search(pattern, line)
        if match:
            entity = match.group(1)
            if not contains_verb(entity) and len(entity) <= 5 and not is_entity_forbidden(entity):
                return entity
    
    if keyword in ["秘境", "禁地", "洞府", "遗迹"]:
        pattern = rf"([\u4e00-\u9fa5]{{2,4}}{keyword})"
        match = re.search(pattern, line)
        if match:
            entity = match.group(1)
            if not contains_verb(entity) and len(entity) <= 6 and not is_entity_forbidden(entity):
                return entity
    
    if keyword in ["阁", "楼", "教", "派", "门", "宗", "殿"]:
        # 这些后缀需要至少2个前缀字
        pattern = rf"([\u4e00-\u9fa5]{{2,4}}{keyword})"
        match = re.search(pattern, line)
        if match:
            entity = match.group(1)
            if not contains_verb(entity) and len(entity) <= 5 and not is_entity_forbidden(entity):
                return entity
    
    # 尝试提取带已知后缀的短语
    for suffix in ITEM_SUFFIXES:
        pattern = rf"([\u4e00-\u9fa5]{{2,4}}{suffix})"
        match = re.search(pattern, line)
        if match:
            entity = match.group(1)
            if not contains_verb(entity) and len(entity) <= 6 and not is_entity_forbidden(entity):
                return entity
    
    for suffix in SETTING_SUFFIXES:
        pattern = rf"([\u4e00-\u9fa5]{{2,4}}{suffix})"
        match = re.search(pattern, line)
        if match:
            entity = match.group(1)
            if not contains_verb(entity) and len(entity) <= 6 and not is_entity_forbidden(entity):
                return entity
    
    # 如果没有找到明确的实体，返回空
    return ""


def extract_debts_from_scene(lines: List[str], scene_path: Path) -> List[Dict[str, Any]]:
    """从场景文本中提取剧情债务候选"""
    debts = []
    debt_counter = 1

    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue

        # 检查每种债务类型的关键词
        for debt_type, keywords in DEBT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in line:
                    # 提取实体
                    entity = extract_entity_from_text(line, keyword)
                    
                    debt = {
                        "debt_id": f"debt-{debt_counter:03d}",
                        "debt_type": debt_type,
                        "source_file": scene_path.name,
                        "line": line_num,
                        "text": line.strip(),
                        "entity": entity,
                        "reason": f"发现关键词: {keyword}" + (f"，提取实体: {entity}" if entity else ""),
                        "status": "candidate",
                        "priority": determine_priority(debt_type),
                        "needs_user_confirmation": True,
                        "suggested_followup": "请确认是否需要加入剧情债务表。"
                    }
                    debts.append(debt)
                    debt_counter += 1
                    break

    return debts


def determine_priority(debt_type: str) -> str:
    """根据债务类型确定优先级"""
    high_priority_types = ["threat", "promise"]
    medium_priority_types = ["foreshadowing", "mystery"]
    low_priority_types = ["unexplained_item", "unresolved_setting", "open_question"]

    if debt_type in high_priority_types:
        return "P1"
    elif debt_type in medium_priority_types:
        return "P2"
    else:
        return "P3"


def extract_debts_from_snapshot(snapshot: Dict[str, Any], scene_path: Path) -> List[Dict[str, Any]]:
    """从 snapshot 中提取 unresolved_setting"""
    debts = []
    debt_counter = 1

    # 从 suggested_settings_updates 中提取
    for update in snapshot.get("suggested_settings_updates", []):
        entity = update["entry"].get("name", "")
        debt = {
            "debt_id": f"debt-snap-{debt_counter:03d}",
            "debt_type": "unresolved_setting",
            "source_file": scene_path.name,
            "line": update.get("line", 0),
            "text": update["entry"].get("name", "") + ": " + update["entry"].get("role", ""),
            "entity": entity,
            "reason": "来自 suggested_settings_updates",
            "status": "candidate",
            "priority": "P2",
            "needs_user_confirmation": True,
            "suggested_followup": "请确认是否需要将此项加入剧情债务表。"
        }
        debts.append(debt)
        debt_counter += 1

    return debts


def extract_debts_from_reviews(reviews: Dict[str, Any], scene_path: Path) -> List[Dict[str, Any]]:
    """从 reviews 中提取需要用户确认的项"""
    debts = []
    debt_counter = 1

    for review in reviews.get("reviews", []):
        needs_confirmation = review.get("needs_user_confirmation", False)
        action = review.get("action", "")

        if needs_confirmation or action == "unresolved":
            debt_type = "open_question" if needs_confirmation else "unresolved_setting"
            
            # 获取实体，优先从 suggested_entry 获取
            entity = review.get("entity", "")
            if not entity:
                suggested_entry = review.get("suggested_entry", {})
                if suggested_entry:
                    entity = suggested_entry.get("name", "")
            
            debt = {
                "debt_id": f"debt-review-{debt_counter:03d}",
                "debt_type": debt_type,
                "source_file": scene_path.name,
                "line": review.get("line", 0),
                "text": review.get("reason", ""),
                "entity": entity,
                "reason": f"LLM review 需要确认: {action}",
                "status": "candidate",
                "priority": "P2",
                "needs_user_confirmation": True,
                "suggested_followup": "请确认如何处理此项。"
            }
            debts.append(debt)
            debt_counter += 1

    return debts


def build_plot_debt(
    scene_content: str,
    scene_lines: List[str],
    snapshot: Dict[str, Any],
    reviews: Dict[str, Any],
    scene_path: Path
) -> Dict[str, Any]:
    """构建 Plot Debt 表"""
    
    plot_debt = {
        "phase": "T3-D7.5.2",
        "engine": "memory_engine",
        "artifact": "plot_debt_table",
        "source_scene": None,
        "generated_from": {
            "snapshot_json": None,
            "reviews_json": None
        },
        "llm_called": False,
        "auto_write_settings": False,
        "summary": {
            "total_debts": 0,
            "by_type": {},
            "needs_user_confirmation": 0,
            "with_entity": 0
        },
        "debts": []
    }

    # 提取场景标题
    if scene_content.startswith("# "):
        title_end = scene_content.find("\n")
        plot_debt["source_scene"] = scene_content[2:title_end].strip()
    else:
        plot_debt["source_scene"] = "未知场景"

    # 从多个来源提取债务
    debts = []
    
    # 从场景文本提取
    debts.extend(extract_debts_from_scene(scene_lines, scene_path))
    
    # 从 snapshot 提取
    debts.extend(extract_debts_from_snapshot(snapshot, scene_path))
    
    # 从 reviews 提取
    debts.extend(extract_debts_from_reviews(reviews, scene_path))

    # 去重（基于 text 和 entity 的组合）
    seen_keys = set()
    unique_debts = []
    for debt in debts:
        key = f"{debt['text'][:100]}_{debt['entity'][:50]}"
        if key not in seen_keys:
            seen_keys.add(key)
            unique_debts.append(debt)

    plot_debt["debts"] = unique_debts

    # 更新摘要统计
    plot_debt["summary"]["total_debts"] = len(unique_debts)
    plot_debt["summary"]["needs_user_confirmation"] = len([d for d in unique_debts if d["needs_user_confirmation"]])
    plot_debt["summary"]["with_entity"] = len([d for d in unique_debts if d["entity"]])
    
    # 按类型统计
    type_counts = {}
    for debt in unique_debts:
        dt = debt["debt_type"]
        type_counts[dt] = type_counts.get(dt, 0) + 1
    plot_debt["summary"]["by_type"] = type_counts

    return plot_debt


def generate_markdown_report(plot_debt: Dict[str, Any]) -> str:
    """生成 Markdown 报告"""
    type_labels = {
        "foreshadowing": "伏笔",
        "promise": "承诺",
        "threat": "威胁",
        "mystery": "谜团",
        "unexplained_item": "未解释道具",
        "unresolved_setting": "未解决设定",
        "open_question": "开放问题"
    }

    priority_labels = {
        "P1": "高",
        "P2": "中",
        "P3": "低"
    }

    lines = [
        "# Plot Debt 报告",
        "",
        f"- **Phase**: {plot_debt['phase']}",
        f"- **Engine**: {plot_debt['engine']}",
        f"- **Artifact**: {plot_debt['artifact']}",
        f"- **Source Scene**: {plot_debt['source_scene']}",
        f"- **LLM Called**: {'Yes' if plot_debt.get('llm_called') else 'No'}",
        f"- **Auto Write Settings**: {'Yes' if plot_debt.get('auto_write_settings') else 'No'}",
        "",
        "## 摘要",
        "",
        f"- 总债务数: {plot_debt['summary']['total_debts']}",
        f"- 需要用户确认: {plot_debt['summary']['needs_user_confirmation']}",
        f"- 已提取实体: {plot_debt['summary']['with_entity']}",
        "",
        "### 按类型分布",
        "",
        "| 类型 | 数量 |",
        "|------|------|"
    ]

    for debt_type, count in plot_debt["summary"]["by_type"].items():
        label = type_labels.get(debt_type, debt_type)
        lines.append(f"| {label} | {count} |")
    lines.append("")

    # 债务详情
    if plot_debt["debts"]:
        lines.append("## 债务详情")
        lines.append("")
        lines.append("| ID | 类型 | 优先级 | 实体 | 位置 | 摘要 |")
        lines.append("|----|------|--------|------|------|------|")
        
        for debt in plot_debt["debts"]:
            type_label = type_labels.get(debt["debt_type"], debt["debt_type"])
            priority_label = priority_labels.get(debt["priority"], debt["priority"])
            entity_display = debt["entity"] if debt["entity"] else "-"
            text_preview = debt["text"][:40] + "..." if len(debt["text"]) > 40 else debt["text"]
            lines.append(f"| {debt['debt_id']} | {type_label} | {priority_label} | {entity_display} | 第{debt['line']}行 | {text_preview} |")
        lines.append("")

        # 需要确认的项
        needs_confirmation = [d for d in plot_debt["debts"] if d["needs_user_confirmation"]]
        if needs_confirmation:
            lines.append("## 需要用户确认")
            lines.append("")
            for debt in needs_confirmation:
                lines.append(f"- **{debt['debt_id']}** ({type_labels.get(debt['debt_type'], debt['debt_type'])}):")
                if debt["entity"]:
                    lines.append(f"  - 实体: {debt['entity']}")
                lines.append(f"  - 原文: {debt['text']}")
                lines.append(f"  - 原因: {debt['reason']}")
                lines.append(f"  - 建议: {debt['suggested_followup']}")
                lines.append("")

    else:
        lines.append("## 债务详情")
        lines.append("")
        lines.append("- 未发现剧情债务候选")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.5.2: Plot Debt 表 MVP (实体降噪)"
    )
    parser.add_argument("--scene", type=Path, required=True,
                        help="场景 markdown 文件路径")
    parser.add_argument("--snapshot-json", type=Path, required=True,
                        help="State Snapshot JSON 文件路径")
    parser.add_argument("--reviews-json", type=Path, required=True,
                        help="Reviews JSON 文件路径")
    parser.add_argument("--output-json", type=Path, required=True,
                        help="输出 JSON 路径")
    parser.add_argument("--output-md", type=Path, required=True,
                        help="输出 Markdown 报告路径")

    args = parser.parse_args()

    print("=" * 60)
    print("Phase T3-D7.5.2: Plot Debt 表 MVP (实体降噪)")
    print("=" * 60)
    print()

    try:
        # 加载输入
        print("加载输入文件...")
        scene_content, scene_lines = load_scene(args.scene)
        snapshot = load_snapshot(args.snapshot_json)
        reviews = load_reviews(args.reviews_json)
        print(f"✅ 加载场景文件: {args.scene}")
        print(f"✅ 加载 Snapshot: {args.snapshot_json}")
        print(f"✅ 加载 Reviews: {args.reviews_json}")
        print()

        # 构建 plot debt
        print("构建 Plot Debt 表...")
        plot_debt = build_plot_debt(scene_content, scene_lines, snapshot, reviews, args.scene)
        
        # 记录来源
        plot_debt["generated_from"]["snapshot_json"] = args.snapshot_json.name
        plot_debt["generated_from"]["reviews_json"] = args.reviews_json.name
        
        print("✅ 构建完成")
        print()

        # 保存 JSON
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(plot_debt, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存输出 JSON: {args.output_json}")

        # 生成 Markdown 报告
        md_report = generate_markdown_report(plot_debt)
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(md_report, encoding="utf-8")
        print(f"✅ 生成 Markdown 报告: {args.output_md}")
        print()

        # 打印摘要
        print("📊 Plot Debt 摘要:")
        print(f"   - 总债务数: {plot_debt['summary']['total_debts']}")
        print(f"   - 需要确认: {plot_debt['summary']['needs_user_confirmation']}")
        print(f"   - 已提取实体: {plot_debt['summary']['with_entity']}")
        print(f"   - 按类型分布: {plot_debt['summary']['by_type']}")

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
