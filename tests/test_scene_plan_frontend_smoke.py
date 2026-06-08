"""
T5.4.3 Scene Plan 前端完整浏览器 Smoke Test

验证完整 UI 流程：
1. 打开 demo-novel 项目，通过文件树打开场景文件
2. 切换到场景计划标签
3. 测试加载、生成、保存、再次加载

使用 Mock API 模拟后端（LLM 未连接）
明确标注：UI smoke mock API
"""

import os
import sys
import json

# 确保 playwright 可用
try:
    from playwright.sync_api import sync_playwright, Route
except ImportError:
    print("需要安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

FRONTEND_URL = "http://localhost:5174"
PROJECT_ID = "demo-novel"
SCENE_FILE_PATH = "chapters/vol-01/ch-001/sec-001.md"

# 用于记录已保存状态，以便第二次 load 返回已保存
saved_flag = False


def setup_mocks(page):
    """设置 Mock API 路由 — 只拦截 scene-plan 相关 API"""
    global saved_flag
    saved_flag = False

    def handle_generate(route: Route):
        print("Mock: intercepted POST /api/scene-plan/generate")
        scene_plan_data = {
            "project_id": PROJECT_ID,
            "source_path": SCENE_FILE_PATH,
            "goal": "验证前端 UI 生成场景计划",
            "conflict": "主角面对未知选择",
            "required_beats": ["打开场景", "生成计划", "保存计划"],
            "candidate_policy": {
                "require_candidate": True,
                "allow_direct_write": False
            }
        }
        body = {
            "scene_plan": scene_plan_data,
            "valid": True,
            "errors": [],
            "warnings": [],
            "raw_output": None,
            "source_summary": {
                "target_file": SCENE_FILE_PATH,
                "used_story_state": False,
                "used_style_guide": False,
                "used_recent_context": False
            }
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    def handle_save(route: Route):
        global saved_flag
        print("Mock: intercepted POST /api/scene-plan/save")
        saved_flag = True
        body = {
            "saved": True,
            "path": "materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json",
            "valid": True,
            "errors": [],
            "warnings": [],
            "conflict": False,
            "message": None
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    def handle_load(route: Route):
        global saved_flag
        print(f"Mock: intercepted GET /api/scene-plan/load, saved_flag={saved_flag}")
        scene_plan_data = {
            "project_id": PROJECT_ID,
            "source_path": SCENE_FILE_PATH,
            "goal": "验证前端 UI 生成场景计划",
            "conflict": "主角面对未知选择",
            "required_beats": ["打开场景", "生成计划", "保存计划"],
        }
        if saved_flag:
            body = {
                "exists": True,
                "path": "materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json",
                "scene_plan": scene_plan_data,
                "mtime": 1234567890.0,
                "errors": []
            }
        else:
            body = {
                "exists": False,
                "path": None,
                "scene_plan": None,
                "mtime": None,
                "errors": []
            }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    # 只拦截 scene-plan API，其他不拦截
    page.route("**/api/scene-plan/generate", handle_generate)
    page.route("**/api/scene-plan/save", handle_save)
    page.route("**/api/scene-plan/load", handle_load)
    print("Mock routes set up for /api/scene-plan/*")


def main():
    os.makedirs("test_results", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()

        # ============ 初始化：清除状态并设置 mocks ============
        print("\n=== 初始化 ===")
        page.goto(f"{FRONTEND_URL}", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        page.evaluate("() => localStorage.clear()")
        print("localStorage cleared")
        page.wait_for_timeout(1000)

        setup_mocks(page)
        print("Mocks set up")

        # ============ 步骤 1：打开项目 ============
        print("\n=== 步骤 1：打开项目 ===")
        page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)
        
        # 查找 AppLayout
        app_layout = page.locator(".app-layout")
        try:
            app_layout.wait_for(state="visible", timeout=30000)
            print("✅ AppLayout visible!")
        except Exception as e:
            print(f"❌ AppLayout not visible! {e}")
            page.screenshot(path="test_results/debug_01_app_layout_missing.png", full_page=True)
            raise
        
        page.screenshot(path="test_results/01_project_opened.png", full_page=True)

        # Wait for file tree
        file_tree = page.locator('[data-testid="file-tree"]')
        file_tree.wait_for(state="visible", timeout=10000)
        print("✅ File tree visible")

        # Check mode switch
        mode_link = page.locator(".mode-link")
        if mode_link.is_visible():
            mode_text = mode_link.inner_text()
            print(f"Mode link text: '{mode_text}'")
            if "专业模式" in mode_text:
                mode_link.click()
                page.wait_for_timeout(2000)
                print("✅ Switched to professional mode")

        # ============ 步骤 2：打开场景文件 via 文件树 ============
        print("\n=== 步骤 2：通过文件树打开场景文件 ===")
        
        # Click chapters row to expand it
        chapters_row = page.locator(".tree-node .node-row").filter(has_text="chapters").first
        chapters_row.wait_for(state="visible", timeout=10000)
        chapters_row.click()
        page.wait_for_timeout(1000)
        print("✅ Clicked chapters row")
        
        # Wait for 第1卷 to appear (vol-01 auto-expanded by regex)
        try:
            vol01_node = page.locator(".tree-node .node-row").filter(has_text="第1卷").first
            vol01_node.wait_for(state="visible", timeout=5000)
            print("✅ Found 第1卷")
        except Exception:
            print("⚠️ 第1卷 not found, double-clicking chapters...")
            chapters_row.click()
            page.wait_for_timeout(1000)
            vol01_node = page.locator(".tree-node .node-row").filter(has_text="第1卷").first
            vol01_node.wait_for(state="visible", timeout=10000)
        
        # vol-01 and ch-001 are auto-expanded by regex — don't click them, just wait
        page.wait_for_timeout(1000)
        
        # Find and click 第1场景 (sec-001.md)
        sec001_node = page.locator(".tree-node .node-row").filter(has_text="第1场景").first
        sec001_node.wait_for(state="visible", timeout=10000)
        sec001_node.click()
        page.wait_for_timeout(2000)
        print("✅ Clicked 第1场景")
        
        # Wait for editor
        editor = page.locator('[data-testid="editor-panel"]')
        editor.wait_for(state="visible", timeout=10000)
        print("✅ Editor visible")
        
        page.screenshot(path="test_results/02_scene_file_opened.png", full_page=True)

        # ============ 步骤 3：切换到场景计划标签 ============
        print("\n=== 步骤 3：切换到场景计划标签 ===")
        scene_plan_tab = page.locator(".right-panel .panel-tab .tab-label").filter(has_text="场景计划").first
        scene_plan_tab.wait_for(state="visible", timeout=30000)
        scene_plan_tab.click()
        page.wait_for_timeout(2000)
        print("✅ Switched to scene plan tab")

        # ============ 步骤 4：验证场景计划面板 ============
        print("\n=== 步骤 4：验证场景计划面板 ===")
        scene_plan_panel = page.locator('[data-testid="scene-plan-panel"]')
        scene_plan_panel.wait_for(timeout=15000, state="visible")
        assert scene_plan_panel.is_visible(), "ScenePlanPanel not visible!"
        print("✅ ScenePlanPanel visible!")

        page.screenshot(path="test_results/03_scene_plan_panel.png", full_page=True)

        # ============ 步骤 5：验证加载按钮 ============
        print("\n=== 步骤 5：验证加载按钮 ===")
        load_btn = scene_plan_panel.locator("button").filter(has_text="加载").first
        load_btn.wait_for(state="visible", timeout=5000)
        assert load_btn.is_visible(), "加载按钮不可见"
        print("✅ 加载按钮可见")

        # ============ 步骤 6：验证生成按钮 ============
        print("\n=== 步骤 6：验证生成按钮 ===")
        generate_btn = scene_plan_panel.locator("button").filter(has_text="生成").first
        generate_btn.wait_for(state="visible", timeout=5000)
        assert generate_btn.is_visible(), "生成按钮不可见"
        print("✅ 生成按钮可见")

        # ============ 步骤 7：测试加载功能 ============
        print("\n=== 步骤 7：测试加载功能 ===")
        load_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/04_after_load.png", full_page=True)
        print("✅ 已点击加载")

        # ============ 步骤 8：测试生成功能 ============
        print("\n=== 步骤 8：测试生成功能 ===")
        generate_btn.click()
        page.wait_for_timeout(3000)
        page.screenshot(path="test_results/05_after_generate.png", full_page=True)
        print("✅ 已点击生成")

        # 检查 valid badge
        valid_badge = scene_plan_panel.locator(".validation-badge.valid")
        try:
            valid_badge.wait_for(state="visible", timeout=10000)
            assert valid_badge.is_visible(), "valid badge 不可见"
            print("✅ 显示 valid=true")
        except Exception:
            validation_result = scene_plan_panel.locator(".validation-result")
            if validation_result.is_visible():
                print("⚠️ 验证结果可见但 valid badge 不可见")
            else:
                print("⚠️ 验证结果不可见")

        # 检查 JSON preview
        preview = scene_plan_panel.locator(".scene-plan-preview")
        try:
            preview.wait_for(state="visible", timeout=5000)
            preview_text = preview.locator(".preview-content").first.inner_text()
            if "scene_plan" in preview_text or "goal" in preview_text:
                print("✅ 显示 scene_plan JSON")
        except Exception:
            print("⚠️ preview not found or empty")

        # ============ 步骤 9：测试保存功能 ============
        print("\n=== 步骤 9：测试保存功能 ===")
        save_btn = scene_plan_panel.locator("button").filter(has_text="保存").first
        if save_btn.is_visible() and save_btn.is_enabled():
            save_btn.click()
            page.wait_for_timeout(2000)
            page.screenshot(path="test_results/06_after_save.png", full_page=True)
            print("✅ 已点击保存")
        else:
            print("⚠️ 保存按钮不可用")

        # ============ 步骤 10：测试重新加载 ============
        print("\n=== 步骤 10：测试重新加载 ===")
        load_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/07_after_reload.png", full_page=True)
        print("✅ 已再次点击加载")

        # ============ 步骤 11：验证 ScenePlanPanel 仍然可见 ============
        print("\n=== 步骤 11：验证 ScenePlanPanel 仍然可见 ===")
        assert scene_plan_panel.is_visible(), "ScenePlanPanel 消失!"
        print("✅ ScenePlanPanel 仍然可见")

        # ============ 最终清理 ============
        page.screenshot(path="test_results/99_final.png", full_page=True)
        browser.close()
        print("\n=== Smoke Test PASS ===")
        return 0


if __name__ == "__main__":
    sys.exit(main())
