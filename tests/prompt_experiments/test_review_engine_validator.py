#!/usr/bin/env python3
"""
Phase T3-D7.3a: Review Engine Validator 测试

测试内容：
- valid fixture 应通过
- missing_id fixture 应失败
- duplicate_id fixture 应失败
- invalid_action fixture 应失败
"""

import sys
from pathlib import Path

# 导入主脚本
sys.path.insert(0, str(Path(__file__).parent))
from review_engine_validator import validate_reviews


def test_valid_fixture():
    """
    测试 valid fixture（完整覆盖，应通过）
    """
    candidates_json = Path(__file__).parent.parent.parent / "docs" / "testing" / "prompt-experiments" / "diff-engine-existence-mvp-sample.json"
    reviews_json = Path(__file__).parent.parent / "fixtures" / "review_engine_validator" / "reviewed_candidates_valid.json"
    
    errors, stats = validate_reviews(candidates_json, reviews_json)
    
    if len(errors) == 0:
        print("✅ Valid fixture 测试通过")
        return True
    else:
        print(f"❌ Valid fixture 测试失败: {len(errors)} 个错误")
        for err in errors[:5]:
            print(f"   - {err}")
        return False


def test_missing_id_fixture():
    """
    测试 missing_id fixture（漏掉一个 candidate，应失败）
    """
    candidates_json = Path(__file__).parent.parent.parent / "docs" / "testing" / "prompt-experiments" / "diff-engine-existence-mvp-sample.json"
    reviews_json = Path(__file__).parent.parent / "fixtures" / "review_engine_validator" / "reviewed_candidates_missing_id.json"
    
    errors, stats = validate_reviews(candidates_json, reviews_json)
    
    # 应该有 MISSING_ID 错误
    missing_errors = [e for e in errors if e.error_type == "MISSING_ID"]
    
    if len(errors) > 0 and len(missing_errors) > 0:
        print(f"✅ Missing ID fixture 测试通过（正确检测到缺失）")
        print(f"   - 检测到 {len(missing_errors)} 个缺失 ID")
        return True
    else:
        print(f"❌ Missing ID fixture 测试失败: 应该有 MISSING_ID 错误")
        return False


def test_duplicate_id_fixture():
    """
    测试 duplicate_id fixture（重复 candidate_id，应失败）
    """
    candidates_json = Path(__file__).parent.parent.parent / "docs" / "testing" / "prompt-experiments" / "diff-engine-existence-mvp-sample.json"
    reviews_json = Path(__file__).parent.parent / "fixtures" / "review_engine_validator" / "reviewed_candidates_duplicate_id.json"
    
    errors, stats = validate_reviews(candidates_json, reviews_json)
    
    # 应该有 DUPLICATE_ID 错误
    dup_errors = [e for e in errors if e.error_type == "DUPLICATE_ID"]
    
    if len(errors) > 0 and len(dup_errors) > 0:
        print(f"✅ Duplicate ID fixture 测试通过（正确检测到重复）")
        print(f"   - 检测到 {len(dup_errors)} 个重复 ID")
        return True
    else:
        print(f"❌ Duplicate ID fixture 测试失败: 应该有 DUPLICATE_ID 错误")
        return False


def test_invalid_action_fixture():
    """
    测试 invalid_action fixture（非法 action，应失败）
    """
    candidates_json = Path(__file__).parent.parent.parent / "docs" / "testing" / "prompt-experiments" / "diff-engine-existence-mvp-sample.json"
    reviews_json = Path(__file__).parent.parent / "fixtures" / "review_engine_validator" / "reviewed_candidates_invalid_action.json"
    
    errors, stats = validate_reviews(candidates_json, reviews_json)
    
    # 应该有 INVALID_ENUM 错误
    enum_errors = [e for e in errors if e.error_type == "INVALID_ENUM"]
    
    if len(errors) > 0 and len(enum_errors) > 0:
        print(f"✅ Invalid Action fixture 测试通过（正确检测到非法枚举）")
        print(f"   - 检测到 {len(enum_errors)} 个非法枚举值")
        return True
    else:
        print(f"❌ Invalid Action fixture 测试失败: 应该有 INVALID_ENUM 错误")
        return False


def main():
    """
    运行所有测试
    """
    print("=" * 60)
    print("Phase T3-D7.3a: Review Engine Validator 测试")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # 测试 1: valid fixture
    print("测试 1: Valid fixture（完整覆盖，应通过）")
    print("-" * 40)
    if not test_valid_fixture():
        all_passed = False
    print()
    
    # 测试 2: missing_id fixture
    print("测试 2: Missing ID fixture（漏掉一个 candidate，应失败）")
    print("-" * 40)
    if not test_missing_id_fixture():
        all_passed = False
    print()
    
    # 测试 3: duplicate_id fixture
    print("测试 3: Duplicate ID fixture（重复 candidate_id，应失败）")
    print("-" * 40)
    if not test_duplicate_id_fixture():
        all_passed = False
    print()
    
    # 测试 4: invalid_action fixture
    print("测试 4: Invalid Action fixture（非法 action，应失败）")
    print("-" * 40)
    if not test_invalid_action_fixture():
        all_passed = False
    print()
    
    print("=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
        return 0
    else:
        print("❌ 存在测试失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
