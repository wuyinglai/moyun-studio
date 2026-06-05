#!/usr/bin/env python3
"""
Phase T3-D7.3a: Review Engine Validator

验证 LLM review 结果的完整性和正确性：
- 校验 candidate_id 全覆盖
- 校验无重复 candidate_id
- 校验无多余 candidate_id
- 校验必填字段齐全
- 校验字段类型合法
- 校验 action 属于枚举值
- 校验 confidence 在 0-1 之间
- 不调用 LLM
- 不自动入库
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple


# 有效的 action 枚举
VALID_ACTIONS = [
    "suggest_add_to_settings",
    "suggest_update_settings",
    "suggest_ignore",
    "suggest_user_confirm",
    "suggest_rewrite_text",
    "unresolved"
]

# 有效的 severity 枚举
VALID_SEVERITIES = ["P0", "P1", "P2", "P3"]


class ValidationError:
    """验证错误"""
    def __init__(self, error_type: str, message: str, candidate_id: str = None, field: str = None):
        self.error_type = error_type
        self.message = message
        self.candidate_id = candidate_id
        self.field = field
    
    def __str__(self):
        if self.candidate_id:
            return f"[{self.error_type}] {self.message} (candidate_id: {self.candidate_id})"
        return f"[{self.error_type}] {self.message}"


def load_candidates(candidates_json: Path) -> Dict[str, Any]:
    """加载 candidates JSON"""
    with open(candidates_json, encoding="utf-8") as f:
        return json.load(f)


def validate_structure(reviews_data: Dict[str, Any]) -> List[ValidationError]:
    """
    校验 JSON 结构
    """
    errors = []
    
    # 检查顶层字段
    required_fields = ["phase", "engine", "mode", "reviews"]
    for field in required_fields:
        if field not in reviews_data:
            errors.append(ValidationError("MISSING_FIELD", f"缺少必填字段: {field}"))
    
    # 检查 reviews 是否为数组
    if "reviews" in reviews_data and not isinstance(reviews_data["reviews"], list):
        errors.append(ValidationError("INVALID_TYPE", "reviews 必须是数组"))
    
    return errors


def validate_review_item(review: Dict[str, Any]) -> List[ValidationError]:
    """
    校验单条 review 条目
    """
    errors = []
    
    # 检查必填字段
    required_fields = ["candidate_id", "confirmed", "confidence", "severity", "action"]
    for field in required_fields:
        if field not in review:
            errors.append(ValidationError(
                "MISSING_FIELD",
                f"缺少必填字段: {field}",
                candidate_id=review.get("candidate_id", "UNKNOWN")
            ))
    
    # 校验 candidate_id 类型
    if "candidate_id" in review and not isinstance(review["candidate_id"], str):
        errors.append(ValidationError(
            "INVALID_TYPE",
            f"candidate_id 必须是字符串",
            candidate_id=review.get("candidate_id")
        ))
    
    # 校验 confirmed 类型
    if "confirmed" in review and not isinstance(review["confirmed"], bool):
        errors.append(ValidationError(
            "INVALID_TYPE",
            f"confirmed 必须是布尔值",
            candidate_id=review.get("candidate_id")
        ))
    
    # 校验 confidence 范围
    if "confidence" in review:
        conf = review["confidence"]
        if not isinstance(conf, (int, float)):
            errors.append(ValidationError(
                "INVALID_TYPE",
                f"confidence 必须是数字",
                candidate_id=review.get("candidate_id")
            ))
        elif conf < 0 or conf > 1:
            errors.append(ValidationError(
                "OUT_OF_RANGE",
                f"confidence 必须在 0-1 之间，当前值: {conf}",
                candidate_id=review.get("candidate_id"),
                field="confidence"
            ))
    
    # 校验 severity 枚举
    if "severity" in review:
        if review["severity"] not in VALID_SEVERITIES:
            errors.append(ValidationError(
                "INVALID_ENUM",
                f"severity 必须是 {VALID_SEVERITIES} 之一，当前值: {review['severity']}",
                candidate_id=review.get("candidate_id"),
                field="severity"
            ))
    
    # 校验 action 枚举
    if "action" in review:
        if review["action"] not in VALID_ACTIONS:
            errors.append(ValidationError(
                "INVALID_ENUM",
                f"action 必须是 {VALID_ACTIONS} 之一，当前值: {review['action']}",
                candidate_id=review.get("candidate_id"),
                field="action"
            ))
    
    return errors


def validate_coverage(
    candidate_ids: List[str],
    review_ids: List[str]
) -> Tuple[List[ValidationError], Dict[str, Any]]:
    """
    校验覆盖完整性
    """
    errors = []
    stats = {
        "total_candidates": len(candidate_ids),
        "total_reviews": len(review_ids),
        "unique_reviews": len(set(review_ids)),
        "missing_ids": [],
        "extra_ids": [],
        "duplicate_ids": []
    }
    
    # 检查缺失的 candidate_id
    candidate_set = set(candidate_ids)
    review_set = set(review_ids)
    
    missing = candidate_set - review_set
    if missing:
        stats["missing_ids"] = list(missing)
        errors.append(ValidationError(
            "MISSING_ID",
            f"缺少 {len(missing)} 个 candidate_id 的 review"
        ))
    
    # 检查多余的 candidate_id
    extra = review_set - candidate_set
    if extra:
        stats["extra_ids"] = list(extra)
        errors.append(ValidationError(
            "EXTRA_ID",
            f"发现 {len(extra)} 个不在 candidates 中的 candidate_id"
        ))
    
    # 检查重复的 candidate_id
    seen = {}
    for rid in review_ids:
        if rid in seen:
            if rid not in stats["duplicate_ids"]:
                stats["duplicate_ids"].append(rid)
            errors.append(ValidationError(
                "DUPLICATE_ID",
                f"candidate_id 重复: {rid} (出现 {review_ids.count(rid)} 次)",
                candidate_id=rid
            ))
        seen[rid] = True
    
    return errors, stats


def validate_reviews(
    candidates_json: Path,
    reviews_json: Path
) -> Tuple[List[ValidationError], Dict[str, Any]]:
    """
    验证 reviews JSON
    """
    all_errors = []
    
    # 加载数据
    candidates_data = load_candidates(candidates_json)
    with open(reviews_json, encoding="utf-8") as f:
        reviews_data = json.load(f)
    
    # 校验 JSON 结构
    errors = validate_structure(reviews_data)
    all_errors.extend(errors)
    if errors:
        return all_errors, {}
    
    # 提取 candidate_ids
    candidate_ids = [item["candidate_id"] for item in candidates_data.get("items", [])]
    review_ids = [review["candidate_id"] for review in reviews_data.get("reviews", [])]
    
    # 校验覆盖
    errors, stats = validate_coverage(candidate_ids, review_ids)
    all_errors.extend(errors)
    
    # 校验每条 review
    for review in reviews_data.get("reviews", []):
        errors = validate_review_item(review)
        all_errors.extend(errors)
    
    return all_errors, stats


def generate_report(
    candidates_json: Path,
    reviews_json: Path,
    errors: List[ValidationError],
    stats: Dict[str, Any],
    expect_valid: bool,
    output_path: Path
):
    """
    生成 Markdown 报告
    """
    is_valid = len(errors) == 0
    passed = is_valid == expect_valid
    
    lines = [
        "# Review Engine Validator Report",
        "",
        f"- **Phase**: T3-D7.3a",
        f"- **Engine**: review_engine",
        f"- **Mode**: validation",
        f"- **Candidates Source**: {candidates_json.name}",
        f"- **Reviews Source**: {reviews_json.name}",
        f"- **Expected**: {'Valid' if expect_valid else 'Invalid'}",
        f"- **Actual**: {'Valid' if is_valid else 'Invalid'}",
        f"- **Result**: {'✅ PASS' if passed else '❌ FAIL'}",
        "",
        "## 验证结果",
        "",
        f"- **验证状态**: {'通过' if passed else '失败'}",
        f"- **错误数量**: {len(errors)}",
        ""
    ]
    
    if stats:
        lines.extend([
            "### 统计信息",
            "",
            f"- **总 candidates 数**: {stats.get('total_candidates', 0)}",
            f"- **总 reviews 数**: {stats.get('total_reviews', 0)}",
            f"- **唯一 reviews 数**: {stats.get('unique_reviews', 0)}",
            ""
        ])
        
        if stats.get("missing_ids"):
            lines.extend([
                f"- **缺失 candidate_id 数**: {len(stats['missing_ids'])}",
                f"  - {', '.join(stats['missing_ids'][:5])}" + (" ..." if len(stats["missing_ids"]) > 5 else ""),
                ""
            ])
        
        if stats.get("extra_ids"):
            lines.extend([
                f"- **多余 candidate_id 数**: {len(stats['extra_ids'])}",
                f"  - {', '.join(stats['extra_ids'][:5])}" + (" ..." if len(stats["extra_ids"]) > 5 else ""),
                ""
            ])
        
        if stats.get("duplicate_ids"):
            lines.extend([
                f"- **重复 candidate_id 数**: {len(stats['duplicate_ids'])}",
                f"  - {', '.join(stats['duplicate_ids'])}",
                ""
            ])
    
    if errors:
        lines.extend([
            "## 错误列表",
            ""
        ])
        
        # 按错误类型分组
        errors_by_type = {}
        for err in errors:
            if err.error_type not in errors_by_type:
                errors_by_type[err.error_type] = []
            errors_by_type[err.error_type].append(err)
        
        for error_type, type_errors in errors_by_type.items():
            lines.append(f"### {error_type}")
            lines.append("")
            for err in type_errors[:10]:  # 最多显示10条
                lines.append(f"- {str(err)}")
            if len(type_errors) > 10:
                lines.append(f"- ... 还有 {len(type_errors) - 10} 条错误")
            lines.append("")
    
    lines.extend([
        "## 验证规则",
        "",
        "1. **candidate_id 全覆盖**: reviews 必须包含所有 candidates 的 candidate_id",
        "2. **无重复**: 同一个 candidate_id 不能出现多次",
        "3. **无多余**: reviews 中的 candidate_id 必须在 candidates 中存在",
        "4. **必填字段**: candidate_id, confirmed, confidence, severity, action",
        "5. **confidence 范围**: 必须在 0-1 之间",
        "6. **action 枚举**: 必须是 suggest_add_to_settings, suggest_update_settings, suggest_ignore, suggest_user_confirm, suggest_rewrite_text, unresolved",
        "7. **severity 枚举**: 必须是 P0, P1, P2, P3"
    ])
    
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    
    return passed


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.3a: Review Engine Validator - 校验 LLM review 结果的完整性和正确性"
    )
    parser.add_argument("--candidates-json", type=Path, required=True, help="candidates JSON 文件路径")
    parser.add_argument("--reviews-json", type=Path, required=True, help="reviews JSON 文件路径")
    parser.add_argument("--output-md", type=Path, required=True, help="输出 Markdown 报告路径")
    parser.add_argument("--expect-valid", type=lambda x: x.lower() == "true", default=False, help="期望结果是否有效 (true/false)")
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not args.candidates_json.exists():
        print(f"❌ candidates JSON 不存在: {args.candidates_json}")
        return 1
    if not args.reviews_json.exists():
        print(f"❌ reviews JSON 不存在: {args.reviews_json}")
        return 1
    
    # 验证
    print(f"✅ 加载 candidates: {args.candidates_json}")
    print(f"✅ 加载 reviews: {args.reviews_json}")
    
    errors, stats = validate_reviews(args.candidates_json, args.reviews_json)
    
    # 生成报告
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    passed = generate_report(args.candidates_json, args.reviews_json, errors, stats, args.expect_valid, args.output_md)
    
    print(f"✅ Markdown 报告: {args.output_md}")
    
    if passed:
        print("\n✅ 验证通过！")
        return 0
    else:
        print(f"\n❌ 验证失败！发现 {len(errors)} 个错误")
        for err in errors[:5]:
            print(f"   - {err}")
        if len(errors) > 5:
            print(f"   ... 还有 {len(errors) - 5} 个错误")
        return 1


if __name__ == "__main__":
    sys.exit(main())
