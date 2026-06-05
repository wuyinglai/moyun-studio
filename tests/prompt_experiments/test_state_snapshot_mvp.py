#!/usr/bin/env python3
"""
测试 State Snapshot MVP
"""

import json
import sys
from pathlib import Path


def test_snapshot_json():
    """测试 snapshot JSON 结构"""
    snapshot_path = Path("docs/testing/prompt-experiments/state-snapshot-mvp-sample.json")
    
    assert snapshot_path.exists(), f"Snapshot JSON 不存在: {snapshot_path}"
    
    with open(snapshot_path, encoding="utf-8") as f:
        snapshot = json.load(f)
    
    # 检查基本结构
    assert "phase" in snapshot, "缺少 phase 字段"
    assert snapshot["phase"] == "T3-D7.4", f"phase 不正确: {snapshot['phase']}"
    
    assert "engine" in snapshot, "缺少 engine 字段"
    assert snapshot["engine"] == "memory_engine", f"engine 不正确: {snapshot['engine']}"
    
    assert "artifact" in snapshot, "缺少 artifact 字段"
    assert snapshot["artifact"] == "state_snapshot", f"artifact 不正确: {snapshot['artifact']}"
    
    assert "llm_called" in snapshot, "缺少 llm_called 字段"
    assert snapshot["llm_called"] == False, "llm_called 应该为 False"
    
    assert "auto_write_settings" in snapshot, "缺少 auto_write_settings 字段"
    assert snapshot["auto_write_settings"] == False, "auto_write_settings 应该为 False"
    
    # 检查摘要
    assert "summary" in snapshot, "缺少 summary 字段"
    assert "confirmed_candidates" in snapshot["summary"], "缺少 confirmed_candidates 字段"
    assert "ignored_candidates" in snapshot["summary"], "缺少 ignored_candidates 字段"
    assert "needs_user_confirmation" in snapshot["summary"], "缺少 needs_user_confirmation 字段"
    assert "suggested_settings_updates" in snapshot["summary"], "缺少 suggested_settings_updates 字段"
    
    # 检查实体
    assert "entities" in snapshot, "缺少 entities 字段"
    assert "characters" in snapshot["entities"], "缺少 characters 字段"
    assert "locations" in snapshot["entities"], "缺少 locations 字段"
    assert "items" in snapshot["entities"], "缺少 items 字段"
    assert "factions" in snapshot["entities"], "缺少 factions 字段"
    assert "terms" in snapshot["entities"], "缺少 terms 字段"
    
    # 检查列表字段
    assert "confirmed_candidates" in snapshot, "缺少 confirmed_candidates 列表"
    assert "ignored_candidates" in snapshot, "缺少 ignored_candidates 列表"
    assert "needs_user_confirmation" in snapshot, "缺少 needs_user_confirmation 列表"
    assert "suggested_settings_updates" in snapshot, "缺少 suggested_settings_updates 列表"
    assert "open_threads" in snapshot, "缺少 open_threads 列表"
    assert "warnings" in snapshot, "缺少 warnings 列表"
    
    # 检查内容
    assert len(snapshot["suggested_settings_updates"]) > 0, "suggested_settings_updates 不应为空"
    assert len(snapshot["ignored_candidates"]) > 0, "ignored_candidates 不应为空"
    
    print("✅ 所有测试通过!")
    return True


def test_markdown_report():
    """测试 Markdown 报告"""
    md_path = Path("docs/testing/prompt-experiments/state-snapshot-mvp-sample.md")
    
    assert md_path.exists(), f"Markdown 报告不存在: {md_path}"
    
    content = md_path.read_text(encoding="utf-8")
    
    assert "# State Snapshot 报告" in content, "报告标题不正确"
    assert "Phase**" in content and "T3-D7.4" in content, "缺少 Phase 信息"
    assert "LLM Called**" in content and ": No" in content, "LLM Called 状态不正确"
    assert "Auto Write Settings**" in content and ": No" in content, "Auto Write Settings 状态不正确"
    
    print("✅ Markdown 报告测试通过!")
    return True


def main():
    try:
        test_snapshot_json()
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
