#!/usr/bin/env python3
"""
Phase T3-D7.1.1: Diff Engine Existence MVP 测试

测试内容：
- 验证 expected entities 存在
- 验证 forbidden fragments 不存在
"""

import sys
from pathlib import Path

# 导入主脚本
sys.path.insert(0, str(Path(__file__).parent))
from diff_engine_existence_mvp import (
    load_settings,
    extract_candidates_with_stats,
    is_valid_candidate
)


# 期望出现的实体
EXPECTED_ENTITIES = [
    "沈鹤年",      # 角色
    "墨香阁",      # 地点
    "玄黄秘录",    # 道具/书籍
    "玄铁令牌",    # 道具
    "天机阁",      # 势力
    "青铜灯",      # 道具
    "龙涎香",      # 道具/术语
    "五曜珠",      # 术语
    "玄黄秘境"     # 术语
]

# 禁止出现的片段
FORBIDDEN_FRAGMENTS = [
    '："李',
    '，我找',
    '个黑衣',
    '了黑衣',
    '，你知',
    '门走进墨香',
    '香阁，这是',
    '刻着"天机'
]


def test_expected_entities():
    """
    测试期望实体是否被识别
    """
    scene_path = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "scene_with_new_settings.md"
    settings_dir = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "settings"
    
    if not scene_path.exists():
        print(f"❌ 场景文件不存在: {scene_path}")
        return False
    
    if not settings_dir.exists():
        print(f"❌ 设定库目录不存在: {settings_dir}")
        return False
    
    # 加载设定
    settings = load_settings(settings_dir)
    
    # 提取候选
    candidates, stats = extract_candidates_with_stats(scene_path, settings)
    
    # 获取所有实体
    entities = [c["entity"] for c in candidates]
    
    # 检查期望实体
    missing = []
    for expected in EXPECTED_ENTITIES:
        found = False
        for entity in entities:
            if expected in entity or entity in expected:
                found = True
                break
        if not found:
            missing.append(expected)
    
    if missing:
        print(f"❌ 缺少期望实体: {missing}")
        return False
    
    print(f"✅ 所有期望实体已识别")
    return True


def test_forbidden_fragments():
    """
    测试禁止片段是否被过滤
    """
    scene_path = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "scene_with_new_settings.md"
    settings_dir = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "settings"
    
    if not scene_path.exists():
        print(f"❌ 场景文件不存在: {scene_path}")
        return False
    
    if not settings_dir.exists():
        print(f"❌ 设定库目录不存在: {settings_dir}")
        return False
    
    # 加载设定
    settings = load_settings(settings_dir)
    
    # 提取候选
    candidates, stats = extract_candidates_with_stats(scene_path, settings)
    
    # 获取所有实体
    entities = [c["entity"] for c in candidates]
    
    # 检查禁止片段
    found_forbidden = []
    for forbidden in FORBIDDEN_FRAGMENTS:
        for entity in entities:
            if forbidden in entity:
                found_forbidden.append((forbidden, entity))
    
    if found_forbidden:
        print(f"❌ 发现禁止片段:")
        for forbidden, entity in found_forbidden:
            print(f"   - 禁止: '{forbidden}' → 实体: '{entity}'")
        return False
    
    print(f"✅ 所有禁止片段已过滤")
    return True


def test_noise_reduction():
    """
    测试噪声过滤统计
    """
    scene_path = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "scene_with_new_settings.md"
    settings_dir = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "settings"
    
    if not scene_path.exists():
        print(f"❌ 场景文件不存在: {scene_path}")
        return False
    
    if not settings_dir.exists():
        print(f"❌ 设定库目录不存在: {settings_dir}")
        return False
    
    # 加载设定
    settings = load_settings(settings_dir)
    
    # 提取候选
    candidates, stats = extract_candidates_with_stats(scene_path, settings)
    
    # 检查统计
    if stats["raw_candidates"] <= stats["final_candidates"]:
        print(f"❌ 统计异常: 原始候选数 ({stats['raw_candidates']}) 应大于最终候选数 ({stats['final_candidates']})")
        return False
    
    # 检查总过滤数是否正确
    expected_filtered = stats["filtered_by_noise"] + stats["filtered_by_dedup"]
    if stats["filtered_candidates"] != expected_filtered:
        print(f"❌ 统计不一致: 总过滤数 ({stats['filtered_candidates']}) != 噪声过滤 ({stats['filtered_by_noise']}) + 去重过滤 ({stats['filtered_by_dedup']})")
        return False
    
    # 检查原始 - 总过滤 = 最终
    if stats["raw_candidates"] - stats["filtered_candidates"] != stats["final_candidates"]:
        print(f"❌ 统计不一致: 原始 ({stats['raw_candidates']}) - 总过滤 ({stats['filtered_candidates']}) != 最终 ({stats['final_candidates']})")
        return False
    
    print(f"✅ 噪声过滤统计正确:")
    print(f"   - 原始候选: {stats['raw_candidates']} 个")
    print(f"   - 噪声过滤: {stats['filtered_by_noise']} 个")
    print(f"   - 去重过滤: {stats['filtered_by_dedup']} 个")
    print(f"   - 总过滤数: {stats['filtered_candidates']} 个")
    print(f"   - 最终候选: {stats['final_candidates']} 个")
    
    return True


def test_candidate_id_stability():
    """
    测试 candidate_id 稳定性
    """
    scene_path = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "scene_with_new_settings.md"
    settings_dir = Path(__file__).parent.parent / "fixtures" / "diff_engine_existence" / "settings"
    
    if not scene_path.exists():
        print(f"❌ 场景文件不存在: {scene_path}")
        return False
    
    if not settings_dir.exists():
        print(f"❌ 设定库目录不存在: {settings_dir}")
        return False
    
    # 加载设定
    settings = load_settings(settings_dir)
    
    # 提取候选（两次）
    candidates1, stats1 = extract_candidates_with_stats(scene_path, settings)
    candidates2, stats2 = extract_candidates_with_stats(scene_path, settings)
    
    # 检查 ID 一致性
    ids1 = [c["candidate_id"] for c in candidates1]
    ids2 = [c["candidate_id"] for c in candidates2]
    
    if ids1 != ids2:
        print(f"❌ candidate_id 不稳定")
        return False
    
    print(f"✅ candidate_id 稳定")
    return True


def main():
    """
    运行所有测试
    """
    print("=" * 60)
    print("Phase T3-D7.1.1: Diff Engine Existence MVP 测试")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # 测试 1: 期望实体
    print("测试 1: 期望实体识别")
    print("-" * 40)
    if not test_expected_entities():
        all_passed = False
    print()
    
    # 测试 2: 禁止片段
    print("测试 2: 禁止片段过滤")
    print("-" * 40)
    if not test_forbidden_fragments():
        all_passed = False
    print()
    
    # 测试 3: 噪声过滤统计
    print("测试 3: 噪声过滤统计")
    print("-" * 40)
    if not test_noise_reduction():
        all_passed = False
    print()
    
    # 测试 4: candidate_id 稳定性
    print("测试 4: candidate_id 稳定性")
    print("-" * 40)
    if not test_candidate_id_stability():
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