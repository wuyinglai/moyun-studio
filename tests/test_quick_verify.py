#!/usr/bin/env python3
"""
墨韵快速验证测试

直接验证项目结构和核心文件操作功能。
"""

import os
import sys
import json
from pathlib import Path

WORKSPACE_PATH = Path(".e2e-workspace")

def check_project_structure():
    """检查项目基本结构"""
    print("=" * 60)
    print("  墨韵项目结构验证")
    print("=" * 60)
    
    checks = [
        ("backend/main.py", "后端主入口"),
        ("backend/config.py", "配置模块"),
        ("backend/core/llm.py", "LLM服务"),
        ("backend/core/file_ops.py", "文件操作"),
        ("backend/api/projects.py", "项目API"),
        ("frontend/src/App.vue", "前端主组件"),
        ("frontend/src/main.ts", "前端入口"),
        ("prompts/pipeline/", "Prompt模板目录"),
        ("README.md", "项目说明"),
        (".gitignore", "Git忽略配置"),
    ]
    
    all_pass = True
    for path_str, desc in checks:
        path = Path(path_str)
        if path.exists():
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc} - 缺失")
            all_pass = False
    
    return all_pass


def test_file_operations():
    """测试文件操作功能"""
    print("\n" + "=" * 60)
    print("  文件操作测试")
    print("=" * 60)
    
    # 创建测试项目目录
    test_project = WORKSPACE_PATH / "projects" / "test-project-verify"
    test_project.mkdir(parents=True, exist_ok=True)
    
    try:
        # 测试创建 project.json
        project_data = {
            "name": "测试项目",
            "author": "测试作者",
            "created_at": "2026-05-19",
            "genre": "玄幻",
            "tone": "热血",
        }
        with open(test_project / "project.json", "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        print("✅ 创建 project.json")
        
        # 测试创建 story-state.md
        with open(test_project / "story-state.md", "w", encoding="utf-8") as f:
            f.write("# 故事状态\n\n## 主角\n- 姓名：林凡\n- 目标：寻找父母\n")
        print("✅ 创建 story-state.md