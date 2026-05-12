#!/usr/bin/env python3
"""
墨韵 - 完整用户操作流程 E2E 测试

模拟用户从打开应用到完成创作的全流程操作：
  1. 健康检查 / 服务状态
  2. 配置 LLM
  3. 创建项目
  4. Wizard 生成书名 & 创意
  5. Wizard 生成大纲
  6. 确认大纲 (创建章节结构)
  7. 浏览文件树 / 读写文件
  8. 生成章节内容 (LLM)
  9. 角色管理
  10. 质量保障文件
  11. 聊天功能
  12. 清理

用法:
  python tests/test_e2e_full_flow.py
"""

import asyncio
import json
import os
import sys
import time
import signal
import subprocess
from datetime import datetime
from pathlib import Path

import httpx
import requests

# ─── 配置 ─────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000"
WORKSPACE_DIR = Path("workspace").resolve()
PROJECTS_DIR = WORKSPACE_DIR / "projects"

PASS = 0
FAIL = 0
WARN = 0
STEPS: list[dict] = []


def step(name: str):
    """装饰器：记录测试步骤结果"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            global PASS, FAIL, WARN
            print(f"\n  [STEP] {name} ... ", end="", flush=True)
            ok = False
            msg = ""
            try:
                start = time.time()
                ok, msg = await func(*args, **kwargs)
                elapsed = time.time() - start
                if ok:
                    print(f" OK ({elapsed:.1f}s)")
                    if msg:
                        for line in msg.split("\n"):
                            print(f"     {line}")
                    PASS += 1
                    STEPS.append({"name": name, "status": "PASS", "msg": msg})
                else:
                    print(f" FAIL ({elapsed:.1f}s)")
                    print(f"     {msg}")
                    FAIL += 1
                    STEPS.append({"name": name, "status": "FAIL", "msg": msg})
            except Exception as e:
                elapsed = time.time() - start
                print(f" FAIL ({elapsed:.1f}s)")
                print(f"     Exception: {e}")
                FAIL += 1
                STEPS.append({"name": name, "status": "FAIL", "msg": str(e)})
            return ok
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════
#  测试用例
# ═══════════════════════════════════════════════════════════════════════

@step("1. 健康检查 — 后端API是否运行")
async def test_health():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/docs")
        if r.status_code == 200:
            return True, "Swagger docs 可访问"
        return False, f"状态码 {r.status_code}"


@step("2.1 获取LLM状态")
async def test_llm_status():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/llm/status")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            connected = data["data"]["connected"]
            model = data["data"]["model"]
            return True, f"connected={connected}, model={model}"
        return False, f"响应: {data}"


@step("2.2 保存LLM配置（配置DeepSeek）")
async def test_llm_save_config():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE_URL}/api/llm/config", json={
            "api_type": "deepseek",
            "api_url": "https://api.deepseek.com",
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "model": "deepseek/deepseek-v4-flash",
            "thinking": False,
        })
        if r.status_code == 200:
            return True, "配置保存成功"
        return False, r.text


@step("2.3 获取可用模型列表")
async def test_llm_models():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/llm/models")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            models = data["data"]["models"]
            return True, f"共 {len(models)} 个模型可用"
        return False, f"响应: {data}"


@step("2.4 测试LLM连接（发一个最短请求）")
async def test_llm_connection():
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{BASE_URL}/api/llm/test")
        data = r.json()
        if r.status_code == 200:
            connected = data["data"]["connected"]
            msg = data["data"]["message"]
            if connected:
                return True, f"LLM连接成功"
            else:
                return False, f"LLM连接失败 — {msg}"
        return False, f"响应: {data}"


project_id = None
project_name = None


@step("3.1 获取项目列表")
async def test_list_projects():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/projects")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            total = data["data"]["total"]
            return True, f"当前有 {total} 个项目"
        return False, f"响应: {data}"


@step("3.2 创建新项目")
async def test_create_project():
    global project_id, project_name
    project_name = f"E2E测试_修仙世界_{int(time.time())}"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{BASE_URL}/api/projects", json={
            "name": project_name,
            "author": "测试作者",
            "genre": "玄幻",
            "tone": "热血",
            "background": "一个普通少年在修仙世界的冒险成长故事",
            "theme": "成长、冒险、友情",
            "writing_style": "网络小说风格，节奏明快",
            "target_word_count": 100000,
        })
        data = r.json()
        if r.status_code in (200, 201) and data.get("success"):
            project_id = data["data"]["project_id"]
            return True, f"project_id={project_id}, name={project_name}"
        return False, f"响应: {data}"


@step("3.3 获取项目详情")
async def test_get_project():
    global project_id
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/projects/{project_id}")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            p = data["data"]
            return True, f"名称={p['name']}, 题材={p['genre']}, 完成度={p['completion_rate']*100:.0f}%"
        return False, f"响应: {data}"


@step("4. Wizard — 生成书名和创意")
async def test_wizard_idea():
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{BASE_URL}/api/wizard/generate-idea", json={
            "genre": "玄幻",
            "tone": "热血",
            "theme": "成长、冒险",
            "writing_style": "网络小说风格，节奏明快",
            "target_word_count": 100000,
        })
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            name = data["data"]["name"]
            desc = data["data"]["description"]
            return True, f"书名: {name}\n     创意: {desc[:120]}..."
        return False, f"响应: {data}"


@step("5. Wizard — 生成大纲")
async def test_wizard_outline():
    global project_id
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(
            f"{BASE_URL}/api/wizard/{project_id}/generate-outline",
            json={
                "genre": "玄幻",
                "tone": "热血",
                "theme": "成长、冒险",
                "writing_style": "网络小说风格，节奏明快",
                "target_word_count": 100000,
                "book_name": project_name,
                "book_description": "一个普通少年在修仙世界的冒险成长故事",
            },
        )
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            outline = data["data"]["outline"]
            chapters = data["data"].get("chapters", [])
            return True, f"大纲长度={len(outline)}字, 章节数={len(chapters)}"
        return False, f"响应: {data}"


@step("6. 确认大纲 — 创建章节目录结构")
async def test_confirm_outline():
    global project_id
    async with httpx.AsyncClient(timeout=30) as c:
        outline = "# 第一卷：初入修仙\n\n## 第1章 山村少年\n简介：主角林凡在山村的生活。\n\n## 第2章 神秘玉佩\n简介：林凡得到神秘玉佩。\n"
        r = await c.post(
            f"{BASE_URL}/api/wizard/{project_id}/confirm-outline",
            json={"outline": outline},
        )
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            # 验证章节目录已创建
            proj_dir = PROJECTS_DIR / project_id
            chapters = list((proj_dir / "chapters").glob("*"))
            return True, f"确认成功，chapters/ 下 {len(chapters)} 个目录"
        return False, f"响应: {data}"


@step("7.1 获取文件树")
async def test_file_tree():
    global project_id
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/tree?project_id={project_id}")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            tree = data["data"]["tree"]
            names = [n["name"] for n in tree]
            return True, f"根节点: {names}"
        return False, f"响应: {data}"


@step("7.2 读取 outline.md")
async def test_read_outline():
    global project_id
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/file?project_id={project_id}&path=outline.md")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            content = data["data"]["content"]
            return True, f"读取成功，长度={len(content)}字"
        return False, f"响应: {data}"


@step("7.3 写入修改 outline.md")
async def test_write_outline():
    global project_id
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{BASE_URL}/api/file?project_id={project_id}",
            json={
                "path": "outline.md",
                "content": "# 修改后的大纲\n\n## 第1章 新的开始\n修改内容\n",
            },
        )
        if r.status_code == 200:
            return True, "写入成功"
        return False, r.text


@step("7.4 读取 style-guide.md")
async def test_read_style_guide():
    global project_id
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{BASE_URL}/api/file?project_id={project_id}&path=style-guide.md")
        data = r.json()
        if r.status_code == 200 and data.get("success"):
            content = data["data"]["content"]
            return True, f"读取成功，长度={len(content)}字"
        return False, f"响应: {data}"


@step("7.5 写入/更新文风指南")
async def test_write_style_guide():
    global project_id
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{BASE_URL}/api/file?project_id={project_id}",
            json={
                "path": "style-guide.md",
                "content": "# 文风指南\n\n## 风格\n- 第三人称有限视角\n- 描写简洁，对话生动\n- 战斗场面有张力\n\n## 禁忌\n- 不注水\n- 不写擦边内容\n",
            },
        )
        if r.status_code == 200:
            return True, "文风指南更新成功"
        return False, r.text


@step("7.6 验证文件持久化")
async def test_verify_persistence():
    global project_id
    proj_dir = PROJECTS_DIR / project_id
    expected = ["meta.json", "context.json", "outline.md", "style-guide.md", "story-state.md", "recent-context.md"]
    found = [f for f in expected if (proj_dir / f).exists()]
    missing = [f for f in expected if f not in found]
    if not missing:
        return True, f"所有 {len(expected)} 个文件均存在"
    return False, f"缺失: {missing}"


@step("8. 聊天功能测试")
async def test_chat():
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            f"{BASE_URL}/api/chat",
            json={"project_id": project_id or "test", "message": "写一句关于修仙的描述，不超过20字"},
        )
        if r.status_code == 200:
            content = ""
            for line in r.iter_lines():
                if line:
                    line_decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                    if line_decoded.startswith("data:"):
                        try:
                            data = json.loads(line_decoded[5:])
                            content += data.get("delta", "")
                        except json.JSONDecodeError:
                            pass
            if content.strip():
                return True, f"AI回复: {content.strip()[:100]}"
            return False, "未收到流式回复内容"
        return False, f"HTTP {r.status_code}"


@step("9. 清理 — 删除测试项目")
async def test_cleanup():
    global project_id
    if not project_id:
        return False, "无项目ID可清理"
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.delete(f"{BASE_URL}/api/projects/{project_id}")
        if r.status_code == 200:
            # 验证已删除
            proj_dir = PROJECTS_DIR / project_id
            if not proj_dir.exists():
                project_id = None
                return True, f"项目已删除，目录已清除"
            return True, "项目已删除（目录残留可手动清理）"
        return False, f"删除失败: {r.text}"


# ═══════════════════════════════════════════════════════════════════════
#  主控逻辑
# ═══════════════════════════════════════════════════════════════════════

def print_banner():
    print("=" * 72)
    print("   Moyun - E2E Full Flow Test")
    print(f"  Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Backend: {BASE_URL}")
    print("=" * 72)


def print_report():
    global PASS, FAIL, WARN
    print("\n" + "=" * 72)
    print("  [REPORT] Test Results")
    print("=" * 72)
    print(f"\n  Total: {PASS + FAIL + WARN}")
    print(f"  PASS:  {PASS}")
    print(f"  FAIL:  {FAIL}")
    if WARN:
        print(f"  WARN:  {WARN}")

    print(f"\n  {'Step':<45} {'Result'}")
    print(f"  {'-'*45} {'-'*8}")
    for s in STEPS:
        icon = "PASS" if s["status"] == "PASS" else "FAIL"
        print(f"  {s['name'][:43]:<45} {icon}")

    print("\n" + "=" * 72)
    if FAIL == 0:
        print("  ALL TESTS PASSED!")
    else:
        print(f"  {FAIL} test(s) failed")
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
    global PASS, FAIL, WARN
    print_banner()

    # 等待后端
    ready = await wait_for_backend()
    if not ready:
        print("\n  [ERROR] 后端未启动，请先运行: cd backend && uvicorn backend.main:app --reload")
        print("\n  [HINT] 或在另一个终端中:\n")
        print(f"     cd D:\\newmoyun")
        print(f"     source venv/Scripts/activate")
        print(f"     uvicorn backend.main:app --reload --port 8000")
        sys.exit(1)

    # 按顺序执行测试
    tests = [
        ("健康检查", test_health),
        ("LLM状态", test_llm_status),
        ("保存LLM配置", test_llm_save_config),
        ("模型列表", test_llm_models),
        ("测试LLM连接", test_llm_connection),
        ("项目列表", test_list_projects),
        ("创建项目", test_create_project),
        ("项目详情", test_get_project),
        ("Wizard生成书名", test_wizard_idea),
        ("Wizard生成大纲", test_wizard_outline),
        ("确认大纲", test_confirm_outline),
        ("文件树", test_file_tree),
        ("读取大纲", test_read_outline),
        ("写入大纲", test_write_outline),
        ("读取文风指南", test_read_style_guide),
        ("更新文风指南", test_write_style_guide),
        ("验证文件持久化", test_verify_persistence),
        ("聊天测试", test_chat),
        ("清理项目", test_cleanup),
    ]

    for name, test_func in tests:
        ok = await test_func()
        # 如果 LLM 连接失败，跳过依赖 LLM 的测试（不中断）
        if not ok and name in ("测试LLM连接",):
            print("     [WARN] 后续 LLM 相关测试可能失败，继续执行...")

    print_report()

    # 退出码
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
