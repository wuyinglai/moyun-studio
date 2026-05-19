#!/usr/bin/env python3
"""
墨韵 - 用户故事测试

基于典型用户场景的端到端测试：

故事1: 新用户首次使用
  - 打开应用 → 创建新项目 → 设置文风指南 → 生成大纲

故事2: 作家创作流程
  - 打开项目 → 浏览文件树 → 编辑章节 → 使用AI续写 → 保存修改

故事3: 故事状态管理
  - 查看故事状态 → 更新人物欲望 → 管理伏笔

故事4: 质量审查
  - 运行质量审查 → 查看问题 → 应用修复建议
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime

import httpx

BASE_URL = "http://127.0.0.1:8000"

PASS = 0
FAIL = 0
STEPS = []


def step(name: str):
    """装饰器：记录测试步骤结果"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            global PASS, FAIL
            print(f"\n  [STEP] {name} ... ", end="", flush=True)
            ok = False
            msg = ""
            try:
                start = time.time()
                ok, msg = await func(*args, **kwargs)
                elapsed = time.time() - start
                if ok:
                    print(f"✅ ({elapsed:.1f}s)")
                    if msg:
                        for line in msg.split("\n"):
                            print(f"     {line}")
                    PASS += 1
                    STEPS.append({"name": name, "status": "PASS", "msg": msg})
                else:
                    print(f"❌ ({elapsed:.1f}s)")
                    print(f"     {msg}")
                    FAIL += 1
                    STEPS.append({"name": name, "status": "FAIL", "msg": msg})
            except Exception as e:
                elapsed = time.time() - start
                print(f"❌ ({elapsed:.1f}s)")
                print(f"     Exception: {e}")
                FAIL += 1
                STEPS.append({"name": name, "status": "FAIL", "msg": str(e)})
            return ok
        return wrapper
    return decorator


# ============ 故事1: 新用户首次使用 ============
@step("故事1: 创建新项目")
async def story1_create_project():
    async with httpx.AsyncClient(timeout=30) as c:
        project_name = f"测试项目_{int(time.time())}"
        r = await c.post(f"{BASE_URL}/api/projects", json={
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
        if r.status_code in (200, 201) and data.get("success"):
            project_id = data["data"]["project_id"]
            return True, f"project_id={project_id}, name={project_name}"
        return False, f"响应: {data}"


@step("故事1: 设置文风指南")
async def story1_set_style_guide(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{BASE_URL}/api/file?project_id={project_id}",
            json={
                "path": "style-guide.md",
                "content": "# 文风指南\n\n## 叙事视角\n- 第三人称有限视角\n- 跟随主角视角\n\n## 语言风格\n- 简洁有力\n- 对话生动\n- 战斗场面有张力\n",
            },
        )
        if r.status_code == 200:
            return True, "文风指南设置成功"
        return False, r.text


# ============ 故事2: 作家创作流程 ============
@step("故事2: 获取文件树")
async def story2_get_file_tree(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/tree?project_id={project_id}")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            tree = data["data"]["tree"]
            names = [n["name"] for n in tree]
            return True, f"文件数: {len(tree)}, 文件: {names}"
        return False, f"响应: {data}"


@step("故事2: 读取大纲文件")
async def story2_read_outline(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/file?project_id={project_id}&path=outline.md")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            content = data["data"]["content"]
            return True, f"大纲长度: {len(content)} 字符"
        return False, f"响应: {data}"


@step("故事2: 更新大纲内容")
async def story2_update_outline(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{BASE_URL}/api/file?project_id={project_id}",
            json={
                "path": "outline.md",
                "content": "# 第一卷：初入江湖\n\n## 第一章：山村少年\n主角林凡在山村的平凡生活被打破。\n\n## 第二章：神秘奇遇\n得到神秘传承，踏上修仙之路。\n",
            },
        )
        if r.status_code == 200:
            return True, "大纲更新成功"
        return False, r.text


# ============ 故事3: 故事状态管理 ============
@step("故事3: 查看故事状态")
async def story3_get_story_state(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/story-state/{project_id}")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            state = data["data"]
            return True, f"状态版本: {state.get('version', 'unknown')}"
        return False, f"响应: {data}"


@step("故事3: 更新故事状态")
async def story3_update_story_state(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE_URL}/api/story-state/{project_id}", json={
            "protagonist_desire": "寻找失散的父母",
            "current_conflict": "与宗门敌对势力的斗争",
            "pending_foreshadowing": ["神秘玉佩的秘密", "主角的身世之谜"],
            "active_quests": ["前往青玄宗", "寻找修炼资源"],
        })
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            return True, "故事状态更新成功"
        return False, f"响应: {data}"


# ============ 故事4: 质量审查 ============
@step("故事4: 获取质量指标")
async def story4_get_quality(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/quality/{project_id}")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            metrics = data["data"]
            return True, f"章节数: {metrics.get('chapter_count', 0)}, 总字数: {metrics.get('total_words', 0)}"
        return False, f"响应: {data}"


# ============ 辅助功能测试 ============
@step("辅助: 健康检查")
async def test_health():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/docs")
        if r.status_code == 200:
            return True, "后端服务运行正常"
        return False, f"状态码: {r.status_code}"


@step("辅助: 获取项目列表")
async def test_list_projects():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/projects")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            total = data["data"]["total"]
            return True, f"当前 {total} 个项目"
        return False, f"响应: {data}"


@step("辅助: 删除测试项目")
async def cleanup_project(project_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.delete(f"{BASE_URL}/api/projects/{project_id}")
        if r.status_code == 200:
            return True, "项目已删除"
        return False, f"删除失败: {r.text}"


# ============ 主控逻辑 ============
def print_banner():
    print("=" * 72)
    print("   Moyun - 用户故事测试")
    print(f"  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Backend: {BASE_URL}")
    print("=" * 72)


def print_report():
    global PASS, FAIL
    print("\n" + "=" * 72)
    print("  [REPORT] 测试结果")
    print("=" * 72)
    print(f"\n  总计: {PASS + FAIL}")
    print(f"  通过: {PASS}")
    print(f"  失败: {FAIL}")

    print(f"\n  {'步骤':<50} {'结果'}")
    print(f"  {'-'*50} {'-'*8}")
    for s in STEPS:
        icon = "✅" if s["status"] == "PASS" else "❌"
        print(f"  {s['name'][:48]:<50} {icon}")

    print("\n" + "=" * 72)
    if FAIL == 0:
        print("  所有测试通过!")
    else:
        print(f"  {FAIL} 个测试失败")
    print("=" * 72)


async def wait_for_backend(max_retries=15, interval=2):
    """等待后端启动"""
    print(f"\n  等待后端启动...", end="", flush=True)
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{BASE_URL}/docs")
                if r.status_code == 200:
                    print(f" 就绪! (尝试{i+1}次)")
                    return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        print(".", end="", flush=True)
        await asyncio.sleep(interval)
    print(" 超时!")
    return False


async def main():
    global PASS, FAIL
    print_banner()

    # 等待后端
    ready = await wait_for_backend()
    if not ready:
        print("\n  [错误] 后端未启动，请先运行:")
        print("\n     cd backend && uvicorn backend.main:app --reload")
        sys.exit(1)

    # 先检查健康状态
    await test_health()
    await test_list_projects()

    # 故事1: 新用户首次使用
    project_id = None
    ok = await story1_create_project()
    if ok:
        project_id = STEPS[-1]["msg"].split("=")[1].split(",")[0].strip()
        await story1_set_style_guide(project_id)

        # 故事2: 作家创作流程
        await story2_get_file_tree(project_id)
        await story2_read_outline(project_id)
        await story2_update_outline(project_id)

        # 故事3: 故事状态管理
        await story3_get_story_state(project_id)
        await story3_update_story_state(project_id)

        # 故事4: 质量审查
        await story4_get_quality(project_id)

        # 清理
        await cleanup_project(project_id)

    print_report()
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())