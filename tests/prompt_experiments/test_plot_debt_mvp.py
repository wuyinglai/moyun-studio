#!/usr/bin/env python3
"""
测试 Plot Debt MVP
"""

import json
import sys
from pathlib import Path


def test_plot_debt_json():
    """测试 Plot Debt JSON 结构"""
    json_path = Path("docs/testing/prompt-experiments/plot-debt-mvp-sample.json")
    
    assert json_path.exists(), f"Plot Debt JSON 不存在: {json_path}"
    
    with open(json_path, encoding="utf-8") as f:
        plot_debt = json.load(f)
    
    # 检查基本结构
    assert "phase" in plot_debt, "缺少 phase 字段"
    assert plot_debt["phase"] == "T3-D7.5.1", f"phase 不正确: {plot_debt['phase']}"
    
    assert "engine" in plot_debt, "缺少 engine 字段"
    assert plot_debt["engine"] == "memory_engine", f"engine 不正确: {plot_debt['engine']}"
    
    assert "artifact" in plot_debt, "缺少 artifact 字段"
    assert plot_debt["artifact"] == "plot_debt_table", f"artifact 不正确: {plot_debt['artifact']}"
    
    assert "llm_called" in plot_debt, "缺少 llm_called 字段"
    assert plot_debt["llm_called"] == False, "llm_called 应该为 False"
    
    assert "auto_write_settings" in plot_debt, "缺少 auto_write_settings 字段"
    assert plot_debt["auto_write_settings"] == False, "auto_write_settings 应该为 False"
    
    # 检查摘要
    assert "summary" in plot_debt, "缺少 summary 字段"
    assert "total_debts" in plot_debt["summary"], "缺少 total_debts 字段"
    assert "by_type" in plot_debt["summary"], "缺少 by_type 字段"
    assert "needs_user_confirmation" in plot_debt["summary"], "缺少 needs_user_confirmation 字段"
    assert "with_entity" in plot_debt["summary"], "缺少 with_entity 字段"
    
    # 检查 debts 列表
    assert "debts" in plot_debt, "缺少 debts 字段"
    assert isinstance(plot_debt["debts"], list), "debts 应该是列表"
    
    # 检查所有 debt 的状态都是 candidate
    for debt in plot_debt["debts"]:
        assert "debt_id" in debt, "debt 缺少 debt_id"
        assert "debt_type" in debt, "debt 缺少 debt_type"
        assert "status" in debt, "debt 缺少 status"
        assert debt["status"] == "candidate", f"debt {debt['debt_id']} 的状态不是 candidate"
        assert "priority" in debt, "debt 缺少 priority"
        assert "needs_user_confirmation" in debt, "debt 缺少 needs_user_confirmation"
    
    # 检查至少有一个债务类型
    assert len(plot_debt["debts"]) > 0, "debts 列表不应为空"
    
    print("✅ Plot Debt JSON 测试通过!")
    return True


def test_entity_extraction():
    """测试实体提取功能"""
    json_path = Path("docs/testing/prompt-experiments/plot-debt-mvp-sample.json")
    
    assert json_path.exists(), f"Plot Debt JSON 不存在: {json_path}"
    
    with open(json_path, encoding="utf-8") as f:
        plot_debt = json.load(f)
    
    # 收集所有实体
    entities = [debt["entity"] for debt in plot_debt["debts"] if debt["entity"]]
    
    print(f"📋 提取到的实体: {entities}")
    
    # 检查关键实体是否被提取
    expected_entities = ["玄黄秘录", "玄铁令牌", "青铜灯", "龙涎香", "五曜珠", "玄黄秘境", "天机阁"]
    
    missing_entities = []
    for expected in expected_entities:
        if expected not in entities:
            missing_entities.append(expected)
    
    if missing_entities:
        print(f"⚠️ 缺失的实体: {missing_entities}")
    
    # 至少应有部分关键实体被提取
    found_count = sum(1 for expected in expected_entities if expected in entities)
    assert found_count >= 5, f"至少应提取到 5 个关键实体，实际提取到 {found_count} 个"
    
    print(f"✅ 实体提取测试通过! 提取到 {len(entities)} 个实体")
    return True


def test_markdown_report():
    """测试 Markdown 报告"""
    md_path = Path("docs/testing/prompt-experiments/plot-debt-mvp-sample.md")
    
    assert md_path.exists(), f"Markdown 报告不存在: {md_path}"
    
    content = md_path.read_text(encoding="utf-8")
    
    assert "# Plot Debt 报告" in content, "报告标题不正确"
    assert "Phase**" in content and "T3-D7.5.1" in content, "缺少 Phase 信息"
    assert "LLM Called**" in content and ": No" in content, "LLM Called 状态不正确"
    assert "Auto Write Settings**" in content and ": No" in content, "Auto Write Settings 状态不正确"
    assert "已提取实体" in content, "缺少已提取实体统计"
    
    print("✅ Markdown 报告测试通过!")
    return True


def main():
    try:
        test_plot_debt_json()
        test_entity_extraction()
        test_markdown_report()
        print()
        print("🎉 所有测试通过!")
        return 0
    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"❌ 发生错误: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
