#!/usr/bin/env python3
"""
墨韵 API 和文件质量测试

直接通过 API 测试后端功能，并检查生成文件的质量。
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
WORKSPACE_PATH = Path(os.environ.get("MOYUN_WORKSPACE_PATH", "./.e2e-workspace"))

PASS = 0
FAIL = 0
RESULTS = []


def log_result(name: str, ok: bool, msg: str = ""):
    global PASS, FAIL
    icon = "✅" if ok else "❌"
    print(f"{icon} {name}")
    if msg:
        print(f"   {msg}")
    if ok:
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append({"name": name, "ok": ok, "msg": msg})


async def test_health():
    """测试1: 健康检查"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{BASE_URL}/docs")
            if r.status_code == 200:
                log_result("测试1: 后端服务运行正常", True)
            else:
                log_result("测试1: 后端服务运行正常", False, f"状态码: {r.status_code}")
    except Exception as e:
        log_result("测试1: 后端服务运行正常", False, str(e))


async def test_create_project():
    """测试2: 创建项目"""
    project_name = f"质量测试项目_{int(time.time())}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{BASE_URL}/api/projects", json={
                "name": project_name,
                "author": "测试作者",
                "genre": "玄幻",
                "tone": "热血",
                "background": "修仙世界",
                "theme": "成长与冒险",
                "writing_style": "网络小说",
                "target_word_count": 100000,
            })
            data = r.json()
            if r.status_code == 200 and data.get("success"):
                project_id = data["data"]["project_id"]
                log_result("测试2: 创建项目", True, f"project_id={project_id}")
                return project_id
            else:
                log_result("测试2: 创建项目", False, f"响应: {data}")
                return None
    except Exception as e:
        log_result("测试2: 创建项目", False, str(e))
        return None


async def test_file_operations(project_id: str):
    """测试3: 文件操作"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 创建文件
            r = await client.post(
                f"{BASE_URL}/api/file?project_id={project_id}",
                json={"path": "test-chapter.md", "content": "# 测试章节\n\n这是第一章的内容。"},
            )
            if r.status_code != 200:
                log_result("测试3: 文件操作", False, "创建文件失败")
                return False

            # 读取文件
            r = await client.get(f"{BASE_URL}/api/file?project_id={project_id}&path=test-chapter.md")
            data = r.json()
            if r.status_code == 200 and data.get("success"):
                content = data["data"]["content"]
                if "测试章节" in content:
                    log_result("测试3: 文件操作", True, "文件读写正常")
                    return True
                else:
                    log_result("测试3: 文件操作", False, "内容不匹配")
                    return False
            else:
                log_result("测试3: 文件操作", False, f"读取失败: {data}")
                return False
    except Exception as e:
        log_result("测试3: 文件操作", False, str(e))
        return False


async def test_project_structure(project_id: str):
    """测试4: 项目结构检查"""
    try:
        project_dir = WORKSPACE_PATH / "projects" / project_id
        if not project_dir.exists():
            log_result("测试4: 项目结构", False, "项目目录不存在")
            return False

        expected_files = ["project.json", "story-state.md", "recent-context.md"]
        missing_files = []
        for f in expected_files:
            if not (project_dir / f).exists():
                missing_files.append(f)

        if missing_files:
            log_result("测试4: 项目结构", False, f"缺失文件: {missing_files}")
            return False
        else:
            # 检查 chapters 目录
            chapters_dir = project_dir / "chapters"
            if chapters_dir.exists():
                log_result("测试4: 项目结构", True, "所有必需文件存在")
            else:
                log_result("测试4: 项目结构", True, "项目文件存在（chapters目录稍后创建）")
            return True
    except Exception as e:
        log_result("测试4: 项目结构", False, str(e))
        return False


async def test_file_content_quality(project_id: str):
    """测试5: 文件内容质量检查"""
    try:
        project_dir = WORKSPACE_PATH / "projects" / project_id
        
        # 检查 project.json
        project_json = project_dir / "project.json"
        if project_json.exists():
            with open(project_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "name" in data and "author" in data and "created_at" in data:
                    log_result("测试5: 文件内容质量", True, "project.json 结构完整")
                else:
                    log_result("测试5: 文件内容质量", False, "project.json 结构不完整")
                    return False
        else:
            log_result("测试5: 文件内容质量", False, "project.json 不存在")
            return False

        # 检查 story-state.md
        story_state = project_dir / "story-state.md"
        if story_state.exists():
            content = story_state.read_text(encoding="utf-8")
            if len(content) > 10:
                log_result("测试5: 文件内容质量", True, f"story-state.md 内容长度: {len(content)} 字符")
            else:
                log_result("测试5: 文件内容质量", False, "story-state.md 内容过短")
                return False
        else:
            log_result("测试5: 文件内容质量", False, "story-state.md 不存在")
            return False

        return True
    except Exception as e:
        log_result("测试5: 文件内容质量", False, str(e))
        return False


async def test_tree_api(project_id: str):
    """测试6: 文件树API"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{BASE_URL}/api/tree?project_id={project_id}")
            data = r.json()
            if r.status_code == 200 and data.get("success"):
                tree = data["data"]["tree"]
                log_result("测试6: 文件树API", True, f"文件数: {len(tree)}")
                return True
            else:
                log_result("测试6: 文件树API", False, f"响应: {data}")
                return False
    except Exception as e:
        log_result("测试6: 文件树API", False, str(e))
        return False


async def test_cleanup(project_id: str):
    """清理测试项目"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.delete(f"{BASE_URL}/api/projects/{project_id}")
            if r.status_code == 200:
                log_result("清理: 删除测试项目", True)
            else:
                log_result("清理: 删除测试项目", False, f"状态码: {r.status_code}")
    except Exception as e:
        log_result("清理: 删除测试项目", False, str(e))


async def main():
    print("=" * 60)
    print(f"  墨韵 API 和文件质量测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  后端: {BASE_URL}")
    print(f"  工作区: {WORKSPACE_PATH}")
    print("=" * 60)
    print()

    # 确保工作区存在
    WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)

    # 测试1: 健康检查
    await test_health()

    # 测试2: 创建项目
    project_id = await test_create_project()
    if not project_id:
        print("\n项目创建失败，终止测试")
        sys.exit(1)

    # 测试3: 文件操作
    await test_file_operations(project_id)

    # 测试4: 项目结构检查
    await test_project_structure(project_id)

    # 测试5: 文件内容质量
    await test_file_content_quality(project_id)

    # 测试6: 文件树API
    await test_tree_api(project_id)

    # 清理
    await test_cleanup(project_id)

    # 输出报告
    print("\n" + "=" * 60)
    print("  测试报告")
    print("=" * 60)
    print(f"\n  总计: {PASS + FAIL}")
    print(f"  通过: {PASS}")
    print(f"  失败: {FAIL}")

    print("\n  详情:")
    for r in RESULTS:
        icon = "✅" if r["ok"] else "❌"
        print(f"  {icon} {r['name']}")
        if r["msg"]:
            print(f"     {r['msg']}")

    print("\n" + "=" * 60)
    if FAIL == 0:
        print("  所有测试通过!")
    else:
        print(f"  {FAIL} 个测试失败")
    print("=" * 60)

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())