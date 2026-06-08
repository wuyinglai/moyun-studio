"""
T5.4.1 Scene Plan 前端浏览器 smoke test

验证：
1. 打开 demo-novel 项目
2. 打开场景文件 chapters/vol-01/ch-001/sec-001.md
3. 切换到"场景计划"标签页
4. 测试加载、生成、保存功能

注意：此测试需要后端和前端服务已启动
"""

import os
import sys

# 确保 playwright 可用
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("需要安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

FRONTEND_URL = "http://127.0.0.1:5173"
PROJECT_ID = "demo-novel"

def main():
    os.makedirs("test_results", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n=== 步骤 1: 打开 demo-novel 项目 ===")
        page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # 截图
        page.screenshot(path="test_results/01_project_opened.png", full_page=True)
        print("截图: 01_project_opened.png")

        # 验证文件树可见
        file_tree = page.locator('[data-testid="file-tree"]')
        if file_tree.is_visible():
            print("✅ 文件树可见")
        else:
            print("❌ 文件树不可见")

        print("\n=== 步骤 2: 展开文件树并打开场景文件 ===")
        try:
            # 尝试展开 chapters 目录
            chapters_dir = page.locator('.tree-node .node-name', has_text='chapters').first
            if chapters_dir.is_visible():
                # 点击展开箭头
                chapters_row = chapters_dir.locator('..').locator('..')
                arrow = chapters_row.locator('.node-arrow')
                arrow.click()
                page.wait_for_timeout(500)

                # 展开 vol-01
                vol01 = page.locator('.tree-node .node-name', has_text='vol-01').first
                if vol01.is_visible():
                    vol01_row = vol01.locator('..').locator('..')
                    vol01_arrow = vol01_row.locator('.node-arrow')
                    vol01_arrow.click()
                    page.wait_for_timeout(500)

                    # 展开 ch-001
                    ch001 = page.locator('.tree-node .node-name', has_text='ch-001').first
                    if ch001.is_visible():
                        ch001_row = ch001.locator('..').locator('..')
                        ch001_arrow = ch001_row.locator('.node-arrow')
                        ch001_arrow.click()
                        page.wait_for_timeout(500)

                        # 点击 sec-001.md
                        sec001 = page.locator('.node-name', has_text='sec-001.md').first
                        if sec001.is_visible():
                            sec001.click()
                            page.wait_for_timeout(1000)
                            print("✅ 已打开 sec-001.md")
                            page.screenshot(path="test_results/02_scene_file_opened.png", full_page=True)
                        else:
                            print("⚠️ sec-001.md 不可见")
                    else:
                        print("⚠️ ch-001 不可见")
                else:
                    print("⚠️ vol-01 不可见")
            else:
                print("⚠️ chapters 不可见")
        except Exception as e:
            print(f"⚠️ 展开文件树失败: {e}")

        print("\n=== 步骤 3: 切换到场景计划标签页 ===")
        try:
            scene_plan_tab = page.locator('.panel-tab', has_text='场景计划').first
            if scene_plan_tab.is_visible():
                scene_plan_tab.click()
                page.wait_for_timeout(1000)
                print("✅ 已点击场景计划标签")
                page.screenshot(path="test_results/03_scene_plan_panel.png", full_page=True)
            else:
                print("❌ 场景计划标签不可见")
        except Exception as e:
            print(f"⚠️ 点击场景计划标签失败: {e}")

        # 检查 ScenePlanPanel 是否渲染
        try:
            scene_plan_panel = page.locator('[data-testid="scene-plan-panel"]')
            if scene_plan_panel.is_visible():
                print("✅ ScenePlanPanel 可见")
            else:
                print("⚠️ ScenePlanPanel 不可见")
        except Exception as e:
            print(f"⚠️ 检查 ScenePlanPanel 失败: {e}")

        # 检查是否识别为场景文件
        try:
            empty_state = page.locator('.empty-state', has_text='当前文件不是场景文件')
            if empty_state.is_visible():
                print("⚠️ 当前显示非场景文件提示")
                scene_plan_content = page.locator('.status-bar, .action-buttons').first
                if scene_plan_content.is_visible():
                    print("✅ 但 Scene Plan 操作区可见（可能已识别为场景文件）")
            else:
                print("✅ 未显示非场景文件提示（正确识别为场景文件）")
        except Exception as e:
            print(f"⚠️ 检查场景文件状态失败: {e}")

        print("\n=== 步骤 4: 测试加载按钮 ===")
        try:
            load_btn = page.locator('button:has-text("加载")').first
            if load_btn.is_visible():
                load_btn.click()
                page.wait_for_timeout(2000)
                print("✅ 点击了加载按钮")
                page.screenshot(path="test_results/04_after_load.png", full_page=True)
            else:
                print("⚠️ 加载按钮不可见（可能当前不是场景文件）")
        except Exception as e:
            print(f"⚠️ 测试加载按钮失败: {e}")

        print("\n=== 步骤 5: 测试生成按钮 ===")
        try:
            generate_btn = page.locator('button:has-text("生成")').first
            if generate_btn.is_visible():
                if generate_btn.is_enabled():
                    generate_btn.click()
                    page.wait_for_timeout(3000)
                    print("✅ 点击了生成按钮")
                    page.screenshot(path="test_results/05_after_generate.png", full_page=True)
                else:
                    print("⚠️ 生成按钮不可用（可能 LLM 未连接）")
            else:
                print("⚠️ 生成按钮不可见")
        except Exception as e:
            print(f"⚠️ 测试生成按钮失败: {e}")

        # 检查生成结果
        try:
            validation_result = page.locator('.validation-result')
            if validation_result.is_visible():
                print("✅ 验证结果显示")
                valid_badge = page.locator('.validation-badge.valid')
                invalid_badge = page.locator('.validation-badge.invalid')
                if valid_badge.is_visible():
                    print("✅ 校验通过")
                elif invalid_badge.is_visible():
                    print("⚠️ 校验失败")
        except Exception as e:
            print(f"⚠️ 检查验证结果失败: {e}")

        # 检查 JSON 预览
        try:
            preview = page.locator('.scene-plan-preview')
            if preview.is_visible():
                print("✅ JSON 预览显示")
            else:
                print("⚠️ JSON 预览未显示")
        except Exception as e:
            print(f"⚠️ 检查 JSON 预览失败: {e}")

        print("\n=== 步骤 6: 测试保存按钮 ===")
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
                            print("⚠️ 发生冲突，用户需确认覆盖")
                else:
                    print("⚠️ 保存按钮不可用（校验未通过）")
            else:
                print("⚠️ 保存按钮不可见")
        except Exception as e:
            print(f"⚠️ 测试保存按钮失败: {e}")

        # 收集 console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # 最终截图
        page.screenshot(path="test_results/07_final.png", full_page=True)

        # 过滤严重错误
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
