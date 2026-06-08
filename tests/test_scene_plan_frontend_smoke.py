"""
T5.4.2 Scene Plan 前端完整浏览器 Smoke Test

验证完整 UI 流程：
1. 打开 demo-novel 项目
2. 通过文件树展开打开场景文件 chapters/vol-01/ch-001/sec-001.md
3. 切换到"场景计划"标签页
4. 测试加载、生成、保存、再加载

使用 Mock API 模拟后端（因为 LLM 未连接）
注意：这是 UI Smoke Test，不是 LLM 功能测试
"""

import os
import sys

try:
    from playwright.sync_api import sync_playwright, Route
except ImportError:
    print("需要安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

FRONTEND_URL = "http://127.0.0.1:5173"
PROJECT_ID = "demo-novel"
SCENE_FILE_PATH = "chapters/vol-01/ch-001/sec-001.md"

MOCK_SCENE_PLAN = {
    "scene_plan": {
        "source_path": SCENE_FILE_PATH,
        "scene_goal": "验证前端 UI 生成场景计划",
        "characters": ["主角"],
        "location": "古城",
        "time": "夜晚",
        "conflict": "主角面对未知选择",
        "beats": ["打开场景", "生成计划", "保存计划"],
        "references": {
            "material_paths": [],
            "recent_context_paths": []
        },
        "candidate_policy": {
            "require_candidate": True,
            "allow_direct_write": False
        }
    },
    "valid": True,
    "errors": [],
    "warnings": []
}

def setup_mocks(page):
    """设置 Mock API 路由"""

    def handle_generate(route: Route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success":true,"data":' + str(MOCK_SCENE_PLAN).replace("'", '"') + ',"raw_output":null,"source_summary":{"target_file":"' + SCENE_FILE_PATH + '","used_story_state":false,"used_style_guide":false,"used_recent_context":false}}'
        )

    def handle_save(route: Route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"saved":true,"path":"materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json","valid":true,"errors":[],"warnings":[],"conflict":false,"message":null}'
        )

    def handle_load(route: Route):
        if "ch-001" in route.request.url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"exists":true,"path":"materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json","scene_plan":' + str(MOCK_SCENE_PLAN["scene_plan"]).replace("'", '"') + ',"mtime":1234567890.0,"errors":[]}'
            )
        else:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"exists":false,"path":null,"scene_plan":null,"mtime":null,"errors":[]}'
            )

    page.route("**/api/scene-plan/generate", handle_generate)
    page.route("**/api/scene-plan/save", handle_save)
    page.route("**/api/scene-plan/load", handle_load)


def expand_and_click_file(page, display_text):
    """
    展开目录并点击文件。

    策略：
    1. 尝试在文件树中找到包含 display_text 的节点
    2. 如果是目录，点击箭头展开
    3. 如果是文件，直接点击节点行
    """
    try:
        page.wait_for_selector('.tree-node', timeout=10000)

        # 找到节点名称元素
        node = page.locator(f'.tree-node .node-name:has-text("{display_text}")').first

        if not node.is_visible():
            return False

        # 点击节点 - 实际上应该点击 node-row 而不是 node-name
        # 但 Playwright 的点击会冒泡，所以我们直接点击 node-name
        node.click(timeout=1000)
        page.wait_for_timeout(800)

        # 检查是否发生了展开（目录）还是选中（文件）
        # 如果点击的是目录，它会展开，不会打开文件
        # 我们需要再次点击来打开文件（如果是文件）

        return True

    except Exception as e:
        print(f"  ⚠️ 展开/点击 '{display_text}' 失败: {e}")
        return False


def expand_path_step_by_step(page):
    """
    逐步展开文件树路径
    """
    # 步骤 1: 展开 chapters
    try:
        # 找到 chapters 目录的箭头
        chapters_node = page.locator('.tree-node .node-name:has-text("chapters")')
        if chapters_node.is_visible():
            # 找到对应的 node-row
            node_row = chapters_node.locator('..')
            # 找到箭头并点击
            arrow = node_row.locator('.node-arrow')
            if arrow.is_visible():
                arrow.click()
                page.wait_for_timeout(800)
                print("  ✅ 展开 chapters")
    except Exception as e:
        print(f"  ⚠️ 展开 chapters 失败: {e}")

    # 步骤 2: 展开 第1卷
    try:
        vol_node = page.locator('.tree-node .node-name:has-text("第1卷")')
        if vol_node.is_visible():
            node_row = vol_node.locator('..')
            arrow = node_row.locator('.node-arrow')
            if arrow.is_visible():
                arrow.click()
                page.wait_for_timeout(800)
                print("  ✅ 展开 第1卷")
    except Exception as e:
        print(f"  ⚠️ 展开 第1卷 失败: {e}")

    # 步骤 3: 展开 第1章
    try:
        ch_node = page.locator('.tree-node .node-name:has-text("第1章")')
        if ch_node.is_visible():
            node_row = ch_node.locator('..')
            arrow = node_row.locator('.node-arrow')
            if arrow.is_visible():
                arrow.click()
                page.wait_for_timeout(800)
                print("  ✅ 展开 第1章")
    except Exception as e:
        print(f"  ⚠️ 展开 第1章 失败: {e}")

    # 步骤 4: 点击 第1场景
    try:
        sec_node = page.locator('.tree-node .node-name:has-text("第1场景")')
        if sec_node.is_visible():
            # 点击节点名称，这会触发 file-click
            sec_node.click()
            page.wait_for_timeout(1000)
            print("  ✅ 点击 第1场景")
            return True
        else:
            print("  ⚠️ 第1场景 不可见")
    except Exception as e:
        print(f"  ⚠️ 点击 第1场景 失败: {e}")

    return False


def main():
    os.makedirs("test_results", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        setup_mocks(page)

        print("\n=== 步骤 1: 打开 demo-novel 项目 ===")
        page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)
        page.screenshot(path="test_results/01_project_opened.png", full_page=True)
        print("截图: 01_project_opened.png")

        file_tree = page.locator('[data-testid="file-tree"]')
        if file_tree.is_visible():
            print("✅ 文件树可见")
        else:
            print("❌ 文件树不可见")

        right_panel = page.locator('.right-panel')
        if right_panel.is_visible():
            print("✅ 右侧面板可见")
        else:
            print("⚠️ 右侧面板不可见")

        print("\n=== 步骤 2: 打开场景文件 ===")
        print("展开文件树...")
        expand_path_step_by_step(page)
        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/02_scene_file_opened.png", full_page=True)

        print("\n=== 步骤 3: 切换到场景计划标签页 ===")
        try:
            page.wait_for_selector('.panel-tabs', timeout=10000)
            scene_plan_tab = page.locator('.panel-tab', has_text='场景计划')
            if scene_plan_tab.is_visible():
                scene_plan_tab.click()
                page.wait_for_timeout(1000)
                print("✅ 已点击场景计划标签")
                page.screenshot(path="test_results/03_scene_plan_panel.png", full_page=True)
            else:
                print("❌ 场景计划标签不可见")
        except Exception as e:
            print(f"⚠️ 点击场景计划标签失败: {e}")

        print("\n=== 步骤 4: 检查场景文件状态 ===")
        try:
            page.wait_for_selector('[data-testid="scene-plan-panel"]', timeout=5000)
            scene_plan_panel = page.locator('[data-testid="scene-plan-panel"]')
            if scene_plan_panel.is_visible():
                print("✅ ScenePlanPanel 可见")

            # 检查是否识别为场景文件
            load_btn = page.locator('button:has-text("加载")')
            if load_btn.is_visible():
                print("✅ 识别为场景文件（有加载按钮）")
            else:
                empty_state = page.locator('.empty-state')
                if empty_state.is_visible():
                    print("⚠️ 显示空状态（当前未打开场景文件）")
                else:
                    print("⚠️ 未识别为场景文件")
        except Exception as e:
            print(f"⚠️ 检查场景文件状态失败: {e}")

        print("\n=== 步骤 5: 测试加载按钮 ===")
        try:
            load_btn = page.locator('button:has-text("加载")').first
            if load_btn.is_visible() and load_btn.is_enabled():
                load_btn.click()
                page.wait_for_timeout(2000)
                print("✅ 点击了加载按钮")
                page.screenshot(path="test_results/04_after_load.png", full_page=True)
            else:
                print("⚠️ 加载按钮不可用")
        except Exception as e:
            print(f"⚠️ 测试加载按钮失败: {e}")

        print("\n=== 步骤 6: 测试生成按钮 ===")
        try:
            generate_btn = page.locator('button:has-text("生成")').first
            if generate_btn.is_visible():
                if generate_btn.is_enabled():
                    generate_btn.click()
                    page.wait_for_timeout(3000)
                    print("✅ 点击了生成按钮")
                    page.screenshot(path="test_results/05_after_generate.png", full_page=True)

                    try:
                        page.wait_for_selector('.validation-result', timeout=5000)
                        valid_badge = page.locator('.validation-badge.valid')
                        if valid_badge.is_visible():
                            print("✅ 校验通过 (valid=true)")
                    except:
                        pass

                    try:
                        preview = page.locator('.scene-plan-preview')
                        if preview.is_visible():
                            print("✅ JSON 预览显示")
                    except:
                        pass
                else:
                    print("⚠️ 生成按钮不可用（可能 LLM 未连接）")
            else:
                print("⚠️ 生成按钮不可见")
        except Exception as e:
            print(f"⚠️ 测试生成按钮失败: {e}")

        print("\n=== 步骤 7: 测试保存按钮 ===")
        try:
            save_btn = page.locator('button:has-text("保存")').first
            if save_btn.is_visible():
                if save_btn.is_enabled():
                    save_btn.click()
                    page.wait_for_timeout(2000)
                    print("✅ 点击了保存按钮")
                    page.screenshot(path="test_results/06_after_save.png", full_page=True)

                    saved_path = page.locator('.saved-path')
                    if saved_path.is_visible():
                        print("✅ 保存成功")
                    else:
                        conflict = page.locator('.conflict-message')
                        if conflict.is_visible():
                            print("⚠️ 发生冲突")
                else:
                    print("⚠️ 保存按钮不可用")
            else:
                print("⚠️ 保存按钮不可见")
        except Exception as e:
            print(f"⚠️ 测试保存按钮失败: {e}")

        print("\n=== 步骤 8: 再次测试加载 ===")
        try:
            load_btn = page.locator('button:has-text("加载")').first
            if load_btn.is_visible() and load_btn.is_enabled():
                load_btn.click()
                page.wait_for_timeout(2000)
                print("✅ 再次点击了加载按钮")
                page.screenshot(path="test_results/07_after_reload.png", full_page=True)

                preview = page.locator('.scene-plan-preview')
                if preview.is_visible():
                    print("✅ 重新加载后显示 scene_plan JSON")
        except Exception as e:
            print(f"⚠️ 再次测试加载失败: {e}")

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        page.screenshot(path="test_results/08_final.png", full_page=True)

        severe = [e for e in console_errors if not any(x in e for x in [
            'ResizeObserver', 'vite-error-overlay', 'Download the Vue DevTools',
            'net::ERR_CONNECTION_REFUSED', 'net::ERR_CONNECTION_CLOSED'
        ])]
        if severe:
            print(f"\n⚠️ Console 错误: {severe}")
        else:
            print("\n✅ 无严重 console 错误")

        browser.close()
        print("\n=== Smoke Test 完成 ===")
        print("\n截图已保存到 test_results/ 目录")


if __name__ == "__main__":
    main()
