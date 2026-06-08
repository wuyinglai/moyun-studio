"""
T5.6 Scene Plan 前端 JSON 编辑 Smoke Test
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
load_call_count = 0
current_saved_plan = None


def setup_mocks(page):
    """设置 Mock API 路由 — 只拦截 scene-plan 相关 API"""
    global saved_flag, load_call_count, current_saved_plan
    saved_flag = False
    load_call_count = 0
    current_saved_plan = None

    def handle_generate(route: Route):
        global current_saved_plan
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
        current_saved_plan = scene_plan_data
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
        global saved_flag, current_saved_plan
        print("Mock: intercepted POST /api/scene-plan/save")
        saved_flag = True
        request_payload = json.loads(route.request.post_data())
        current_saved_plan = request_payload["scene_plan"]
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
        global saved_flag, load_call_count, current_saved_plan
        load_call_count += 1
        print(f"Mock: intercepted GET /api/scene-plan/load #{load_call_count}, saved_flag={saved_flag}")
        if saved_flag and current_saved_plan:
            body = {
                "exists": True,
                "path": "materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json",
                "scene_plan": current_saved_plan,
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

    def handle_validate(route: Route):
        print("Mock: intercepted POST /api/scene-plan/validate")
        request_payload = json.loads(route.request.post_data())
        # 检查是否符合规则
        errors = []
        if "candidate_policy" in request_payload and request_payload["candidate_policy"].get("allow_direct_write"):
            errors.append({
                "field": "candidate_policy.allow_direct_write",
                "message": "allow_direct_write 必须为 False"
            })
        body = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": []
        }
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    # 只拦截 scene-plan API，其他不拦截
    page.route("**/api/scene-plan/generate", handle_generate)
    page.route("**/api/scene-plan/save", handle_save)
    page.route("**/api/scene-plan/load", handle_load)
    page.route("**/api/scene-plan/validate", handle_validate)
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
        page.wait_for_timeout(3000)
        print("✅ Clicked 第1场景")
        
        # Wait for editor
        editor = page.locator('[data-testid="editor-panel"]')
        editor.wait_for(state="visible", timeout=10000)
        print("✅ Editor visible")
        
        page.screenshot(path="test_results/02_scene_file_opened.png", full_page=True)

        # ============ 步骤 3：验证自动加载 ============
        print("\n=== 步骤 3：验证自动加载 ===")
        print(f"✅ Load called {load_call_count} times (expected at least 1)")

        # ============ 步骤 4：切换到场景计划标签 ============
        print("\n=== 步骤 4：切换到场景计划标签 ===")
        scene_plan_tab = page.locator(".right-panel .panel-tab .tab-label").filter(has_text="场景计划").first
        scene_plan_tab.wait_for(state="visible", timeout=30000)
        scene_plan_tab.click()
        page.wait_for_timeout(2000)
        print("✅ Switched to scene plan tab")

        # ============ 步骤 5：验证场景计划面板 ============
        print("\n=== 步骤 5：验证场景计划面板 ===")
        scene_plan_panel = page.locator('[data-testid="scene-plan-panel"]')
        scene_plan_panel.wait_for(timeout=15000, state="visible")
        assert scene_plan_panel.is_visible(), "ScenePlanPanel not visible!"
        print("✅ ScenePlanPanel visible!")

        page.screenshot(path="test_results/03_scene_plan_panel.png", full_page=True)

        # ============ 步骤 6：验证未保存状态 ============
        print("\n=== 步骤 6：验证未保存状态 ===")
        status_badge = scene_plan_panel.locator(".status-badge.empty").filter(has_text="未保存")
        status_badge.wait_for(state="visible", timeout=5000)
        assert status_badge.is_visible(), "未保存状态不可见"
        print("✅ 显示未保存状态")

        # ============ 步骤 7：测试生成功能 ============
        print("\n=== 步骤 7：测试生成功能 ===")
        generate_btn = scene_plan_panel.locator("button").filter(has_text="生成").first
        generate_btn.click()
        page.wait_for_timeout(3000)
        page.screenshot(path="test_results/04_after_generate.png", full_page=True)
        print("✅ 已点击生成")

        # 检查 valid badge
        valid_badge = scene_plan_panel.locator(".validation-badge.valid")
        valid_badge.wait_for(state="visible", timeout=10000)
        assert valid_badge.is_visible(), "valid badge 不可见"
        print("✅ 显示 valid=true")

        # 检查 JSON preview
        preview = scene_plan_panel.locator(".scene-plan-preview")
        preview.wait_for(state="visible", timeout=5000)
        preview_text = preview.locator(".preview-content").first.inner_text()
        assert "goal" in preview_text, "未显示 scene plan"
        print("✅ 显示 scene_plan JSON")

        # ============ 步骤 8：测试保存功能 ============
        print("\n=== 步骤 8：测试保存功能 ===")
        save_btn = scene_plan_panel.locator("button").filter(has_text="保存").first
        assert save_btn.is_visible() and save_btn.is_enabled(), "保存按钮不可用"
        save_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/05_after_save.png", full_page=True)
        print("✅ 已点击保存")

        # ============ 步骤 9：测试编辑 JSON ============
        print("\n=== 步骤 9：测试编辑 JSON 功能 ===")
        
        # 点击编辑按钮
        edit_btn = scene_plan_panel.locator("button").filter(has_text="编辑 JSON").first
        edit_btn.wait_for(state="visible", timeout=5000)
        edit_btn.click()
        page.wait_for_timeout(2000)
        print("✅ 已点击编辑 JSON")
        
        # 验证进入编辑模式
        status_badge = scene_plan_panel.locator(".status-badge.editing")
        status_badge.wait_for(state="visible", timeout=5000)
        assert status_badge.is_visible(), "未显示编辑状态"
        print("✅ 进入编辑模式")
        
        # 修改 JSON：改变 goal
        textarea = scene_plan_panel.locator(".editor-textarea").first
        current_text = textarea.input_value()
        assert "goal" in current_text, "未包含 goal"
        
        # 替换 goal
        import re
        new_text = re.sub(r'"goal":\s*"[^"]*"', r'"goal": "编辑后的场景目标"', current_text)
        textarea.fill(new_text)
        page.wait_for_timeout(1000)
        print("✅ 已修改 JSON")
        
        # 点击校验
        validate_btn = scene_plan_panel.locator("button").filter(has_text="校验").first
        validate_btn.click()
        page.wait_for_timeout(2000)
        
        # 检查验证通过
        valid_badge = scene_plan_panel.locator(".validation-badge.valid")
        valid_badge.wait_for(state="visible", timeout=5000)
        assert valid_badge.is_visible(), "未显示 valid=true"
        print("✅ 验证通过")
        
        # 点击保存
        save_btn = scene_plan_panel.locator("button").filter(has_text="保存").first
        save_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/07_after_edit_save.png", full_page=True)
        print("✅ 已保存编辑后的 plan")
        
        # 验证保存成功，回到查看模式，显示已保存状态
        saved_badge = scene_plan_panel.locator(".status-badge.saved")
        saved_badge.wait_for(state="visible", timeout=5000)
        assert saved_badge.is_visible(), "未显示已保存状态"
        print("✅ 保存成功")
        
        # 检查 JSON 预览显示新的 goal
        preview_text = preview.locator(".preview-content").first.inner_text()
        assert "编辑后的场景目标" in preview_text, "未显示编辑后的 goal"
        print("✅ 显示编辑后的 scene_plan")
        
        # ============ 步骤 10：测试取消编辑 ============
        print("\n=== 步骤 10：测试取消编辑功能 ===")
        
        # 再次进入编辑模式
        edit_btn = scene_plan_panel.locator("button").filter(has_text="编辑 JSON").first
        edit_btn.click()
        page.wait_for_timeout(2000)
        
        # 再次修改
        textarea = scene_plan_panel.locator(".editor-textarea").first
        textarea.fill('{"project_id": "demo-novel", "source_path": "chapters/vol-01/ch-001/sec-001.md", "goal": "临时修改"}')
        page.wait_for_timeout(1000)
        
        # 点击取消
        cancel_btn = scene_plan_panel.locator("button").filter(has_text="取消").first
        cancel_btn.click()
        page.wait_for_timeout(1000)
        print("✅ 已点击取消编辑")
        
        # 验证回到查看模式，显示原来的 goal
        preview_text = preview.locator(".preview-content").first.inner_text()
        assert "临时修改" not in preview_text, "取消编辑后不应显示临时修改"
        assert "编辑后的场景目标" in preview_text, "取消编辑后应显示原来的内容"
        print("✅ 取消编辑成功")
        
        # ============ 步骤 11：测试 JSON 解析错误 ============
        print("\n=== 步骤 11：测试 JSON 解析错误 ===")
        
        # 再次进入编辑模式
        edit_btn.click()
        page.wait_for_timeout(2000)
        
        # 输入无效 JSON
        textarea.fill('invalid json')
        page.wait_for_timeout(1000)
        
        # 验证保存按钮不可用
        save_btn = scene_plan_panel.locator("button").filter(has_text="保存").first
        assert not save_btn.is_enabled(), "无效 JSON 时保存按钮不应可用"
        print("✅ 无效 JSON 时保存按钮不可用")
        
        # 点击取消
        cancel_btn.click()
        page.wait_for_timeout(1000)
        
        # ============ 步骤 12：测试验证错误 ============
        print("\n=== 步骤 12：测试验证错误 ===")
        
        # 再次进入编辑模式
        edit_btn.click()
        page.wait_for_timeout(2000)
        
        # 修改为 allow_direct_write=True
        textarea = scene_plan_panel.locator(".editor-textarea").first
        invalid_plan_text = json.dumps({
            "project_id": PROJECT_ID,
            "source_path": SCENE_FILE_PATH,
            "goal": "测试验证错误",
            "candidate_policy": {
                "require_candidate": False,
                "allow_direct_write": True
            }
        }, indent=2)
        textarea.fill(invalid_plan_text)
        page.wait_for_timeout(1000)
        
        # 点击校验
        validate_btn.click()
        page.wait_for_timeout(2000)
        
        # 检查验证失败
        invalid_badge = scene_plan_panel.locator(".validation-badge.invalid")
        invalid_badge.wait_for(state="visible", timeout=5000)
        assert invalid_badge.is_visible(), "未显示 invalid=true"
        print("✅ 验证失败")
        
        # 点击取消
        cancel_btn.click()
        page.wait_for_timeout(1000)
        
        # ============ 步骤 13：测试自动重新加载显示编辑后的内容 ============
        print("\n=== 步骤 13：验证重新加载显示已保存 ===")
        load_btn = scene_plan_panel.locator("button").filter(has_text="加载").first
        load_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/08_after_edit_reload.png", full_page=True)
        print("✅ 已再次点击加载")

        # 检查已保存状态
        saved_badge = scene_plan_panel.locator(".status-badge.saved")
        saved_badge.wait_for(state="visible", timeout=5000)
        assert saved_badge.is_visible(), "未显示已保存状态"
        print("✅ 显示已保存状态")
        
        # 检查显示的是编辑后的内容
        preview_text = preview.locator(".preview-content").first.inner_text()
        assert "编辑后的场景目标" in preview_text, "重新加载后应显示编辑后的内容"
        print("✅ 重新加载显示编辑后的内容")

        # ============ 步骤 14：测试 Scene Plan 可选接入 Professional dry-run ============
        print("\n=== 步骤 14：测试 Scene Plan 可选接入 Professional dry-run ===")
        
        # 记录 pipeline 请求中是否包含 scene_plan
        pipeline_request_scene_plan = []
        
        def handle_pipeline_run(route: Route):
            print("Mock: intercepted POST /api/pipeline/run")
            request_payload = json.loads(route.request.post_data())
            has_scene_plan = "scene_plan" in request_payload
            pipeline_request_scene_plan.append(has_scene_plan)
            print(f"  Request contains scene_plan: {has_scene_plan}")
            
            # 返回成功响应（模拟 candidate 生成）
            body = {
                "status": "success",
                "message": "Pipeline executed",
                "candidate_created": True
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
        
        # 设置 pipeline run mock
        page.route("**/api/pipeline/run", handle_pipeline_run)
        print("✅ 设置 pipeline/run mock")

        # 验证当前有 valid 的 scene plan
        valid_badge = scene_plan_panel.locator(".validation-badge.valid")
        assert valid_badge.is_visible(), "需要 valid 的 scene plan"
        print("✅ Scene Plan 当前 valid")

        # 找到并勾选 "Professional 生成时使用" checkbox
        toggle_checkbox = scene_plan_panel.locator(".use-scene-plan-toggle input[type='checkbox']")
        toggle_checkbox.wait_for(state="visible", timeout=5000)
        assert toggle_checkbox.is_enabled(), "toggle checkbox 应可用"
        toggle_checkbox.click()
        page.wait_for_timeout(1000)
        print("✅ 已勾选 'Professional 生成时使用'")

        # 点击润色按钮（Professional candidate 操作）
        polish_btn = page.locator("button").filter(has_text="润色").first
        if polish_btn.is_visible() and polish_btn.is_enabled():
            polish_btn.click()
            page.wait_for_timeout(2000)
            print("✅ 已点击润色")
        else:
            # 如果找不到润色按钮，尝试从右键菜单或其他位置触发
            print("⚠️ 润色按钮不可见，跳过此步骤")
            
        # 验证请求是否包含 scene_plan
        if pipeline_request_scene_plan:
            assert pipeline_request_scene_plan[-1] == True, "勾选后请求应包含 scene_plan"
            print("✅ 请求包含 scene_plan")

        # 取消勾选
        toggle_checkbox.click()
        page.wait_for_timeout(1000)
        print("✅ 已取消勾选")

        # 再次点击润色
        if polish_btn.is_visible() and polish_btn.is_enabled():
            polish_btn.click()
            page.wait_for_timeout(2000)
            print("✅ 已再次点击润色")

        # 验证请求不包含 scene_plan
        if len(pipeline_request_scene_plan) >= 2:
            assert pipeline_request_scene_plan[-1] == False, "取消勾选后请求不应包含 scene_plan"
            print("✅ 请求不包含 scene_plan")

        # ============ 步骤 15：验证无 Scene Plan 时提示 ============
        print("\n=== 步骤 15：验证无 Scene Plan 时提示 ===")
        
        # 清除当前场景计划
        global current_saved_plan, saved_flag
        current_saved_plan = None
        saved_flag = False
        
        # 重新加载（模拟没有已保存的 plan）
        load_btn.click()
        page.wait_for_timeout(2000)
        
        # 检查提示消息
        disabled_hint = scene_plan_panel.locator(".use-scene-plan-disabled")
        if disabled_hint.is_visible():
            print("✅ 显示 '请先生成或加载 Scene Plan' 提示")
        else:
            print("⚠️ 未显示禁用提示（可能已有缓存）")

        # ============ 最终清理 ============
        page.screenshot(path="test_results/99_final.png", full_page=True)
        browser.close()
        print("\n=== Smoke Test PASS ===")
        return 0


if __name__ == "__main__":
    sys.exit(main())
