#!/usr/bin/env python3
"""
Phase T3-D7.8：D7 Pipeline dry-run 测试
"""

import json
import sys
from pathlib import Path


def test_pipeline_summary():
    """测试 Pipeline Summary"""
    print("=" * 60)
    print("测试: Pipeline Summary")
    print("=" * 60)
    print()
    
    summary_path = Path("docs/testing/prompt-experiments/d7-pipeline/pipeline-summary.json")
    assert summary_path.exists(), f"Pipeline summary 不存在: {summary_path}"
    
    with open(summary_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # 测试基本字段
    assert data.get("phase") == "T3-D7.8"
    assert data.get("pipeline") == "d7_quality_engine_dryrun"
    assert "llm_called" in data
    assert data.get("llm_called") is False, "llm_called 应该是 False"
    assert data.get("auto_write_scene") is False, "auto_write_scene 应该是 False"
    assert data.get("auto_write_settings") is False, "auto_write_settings 应该是 False"
    
    print(f"✅ 基本字段检查通过: {data.get('phase')} / {data.get('pipeline')}")
    print(f"   - LLM Called: {data.get('llm_called')}")
    print(f"   - Auto Write Scene: {data.get('auto_write_scene')}")
    print(f"   - Auto Write Settings: {data.get('auto_write_settings')}")
    print()
    
    # 测试步骤
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0, "steps 不应为空"
    
    print(f"✅ 步骤检查通过: {len(data['steps'])} 个步骤")
    print()
    
    # 测试每一步的状态
    for step in data["steps"]:
        assert "name" in step
        assert "status" in step
        assert step["status"] == "passed", f"步骤 {step['name']} 应该是 passed"
        print(f"   ✅ {step['name']}: {step['status']}")
    
    print()
    
    # 测试 summary
    assert "summary" in data
    summary = data["summary"]
    assert "candidates" in summary
    assert "reviews" in summary
    assert "snapshot_updates" in summary
    assert "plot_debts" in summary
    assert "rewrite_suggestions" in summary
    
    print("📊 Summary:")
    print(f"   - Candidates: {summary['candidates']}")
    print(f"   - Reviews: {summary['reviews']}")
    print(f"   - Snapshot Updates: {summary['snapshot_updates']}")
    print(f"   - Plot Debts: {summary['plot_debts']}")
    print(f"   - Rewrite Suggestions: {summary['rewrite_suggestions']}")
    print()
    
    # 测试关键产物数量
    assert summary['rewrite_suggestions'] > 0, "应该有 rewrite suggestions"
    assert summary['plot_debts'] > 0, "应该有 plot debts"
    
    print("✅ Pipeline Summary 测试通过!")
    return True


def test_pipeline_markdown():
    """测试 Pipeline Markdown 报告"""
    print()
    print("=" * 60)
    print("测试: Pipeline Markdown 报告")
    print("=" * 60)
    print()
    
    md_path = Path("docs/testing/prompt-experiments/d7-pipeline/pipeline-summary.md")
    assert md_path.exists(), f"Pipeline markdown 不存在: {md_path}"
    
    content = md_path.read_text(encoding="utf-8")
    
    # 调试输出
    print("Markdown 前 100 字符:")
    print(repr(content[:100]))
    
    # 检查关键内容
    assert "Phase" in content
    assert "LLM Called" in content
    assert "Auto Write Scene" in content
    assert "passed" in content
    
    print("✅ Pipeline Markdown 测试通过!")
    return True


def test_output_files():
    """测试输出文件"""
    print()
    print("=" * 60)
    print("测试: 输出文件")
    print("=" * 60)
    print()
    
    output_dir = Path("docs/testing/prompt-experiments/d7-pipeline")
    
    expected_files = [
        "diff-candidates.json",
        "diff-candidates.md",
        "review-output.json",
        "review-validator.md",
        "state-snapshot.json",
        "state-snapshot.md",
        "plot-debt.json",
        "plot-debt.md",
        "rewrite-suggestions.json",
        "rewrite-suggestions.md",
        "pipeline-summary.json",
        "pipeline-summary.md",
    ]
    
    missing_files = []
    for f in expected_files:
        file_path = output_dir / f
        if file_path.exists():
            print(f"   ✅ {f}")
        else:
            print(f"   ❌ {f} (missing)")
            missing_files.append(f)
    
    if missing_files:
        print(f"\n❌ 缺少 {len(missing_files)} 个文件")
        return False
    
    print()
    print("✅ 所有输出文件检查通过!")
    return True


def main():
    print()
    print("-" * 60)
    print("Phase T3-D7.8：D7 Pipeline dry-run 测试")
    print("-" * 60)
    print()
    
    try:
        passed = 0
        failed = 0
        
        # 运行测试
        if test_pipeline_summary():
            passed += 1
        else:
            failed += 1
        
        if test_pipeline_markdown():
            passed += 1
        else:
            failed += 1
        
        if test_output_files():
            passed += 1
        else:
            failed += 1
        
        print()
        print("=" * 60)
        if failed == 0:
            print("🎉 所有测试通过!")
            print("=" * 60)
            return 0
        else:
            print(f"❌ {failed} 个测试失败, {passed} 个通过")
            print("=" * 60)
            return 1
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
