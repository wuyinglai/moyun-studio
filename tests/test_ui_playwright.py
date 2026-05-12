"""
墨韵AI小说创作助手 - 完整UI自动化测试
使用Playwright模拟用户操作测试所有功能
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright, expect
import json
import time

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_ui_flow():
    """完整的UI测试流程"""
    
    print("=" * 80)
    print("墨韵AI小说创作助手 - 完整UI自动化测试")
    print("=" * 80)
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False, slow_mo=800)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        project_name = f"UI测试项目_{int(time.time())}"
        test_project_id = None
        
        try:
            # 1. 打开主页
            print("\n[1/12] 打开前端主页...")
            await page.goto('http://localhost:5173')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            print("✓ 主页加载成功")
            
            # 截图1
            await page.screenshot(path='test_screenshot_1_home.png')
            
            # 查看页面内容
            page_content = await page.content()
            print(f"✓ 页面内容长度: {len(page_content)} 字符")
            
            # 2. 检查页面基本内容
            print("\n[2/12] 检查页面标题和内容...")
            if '墨韵' in page_content:
                print("✓ 页面包含'墨韵'文字")
            else:
                print("⚠ 页面未找到'墨韵'文字")
            
            # 查找所有按钮
            all_buttons = await page.locator('button').all()
            print(f"✓ 找到 {len(all_buttons)} 个按钮")
            
            # 3. 测试设置功能
            print("\n[3/12] 测试设置功能...")
            
            # 点击设置按钮 - 查找图标按钮或设置按钮
            settings_button = None
            for selector in ['button:has-text("设置"), .btn-icon, button[title="设置"]']:
                try:
                    btn = page.locator(selector).first
                    if await btn.count() > 0:
                        settings_button = btn
                        break
                except:
                    continue
            
            if settings_button:
                await settings_button.click()
                await asyncio.sleep(1.5)
                print("✓ 打开设置对话框")
                await page.screenshot(path='test_screenshot_2_settings.png')
                
                # 填写DeepSeek配置
                try:
                    # 尝试填写输入框
                    all_inputs = await page.locator('input').all()
                    print(f"✓ 找到 {len(all_inputs)} 个输入框")
                    
                    # 简单的方式：尝试填写所有输入框
                    for i, inp in enumerate(all_inputs[:5]):
                        try:
                            inp_type = await inp.get_attribute('type') or 'text'
                            placeholder = await inp.get_attribute('placeholder') or ''
                            name = await inp.get_attribute('name') or ''
                            
                            if 'password' in inp_type or 'key' in placeholder.lower() or 'key' in name.lower():
                                await inp.fill('sk-4ea45b73004f44a98c2f472d354430d1')
                                print(f"✓ 填写API Key到输入框{i}")
                            elif 'url' in placeholder.lower() or 'url' in name.lower():
                                await inp.fill('https://api.deepseek.com')
                                print(f"✓ 填写API URL到输入框{i}")
                            elif 'model' in placeholder.lower() or 'model' in name.lower():
                                await inp.fill('deepseek-v4-flash')
                                print(f"✓ 填写模型名到输入框{i}")
                        except:
                            continue
                    
                    await page.screenshot(path='test_screenshot_3_settings_filled.png')
                    
                    # 保存设置 - 点击任意看起来像确认的按钮
                    for selector in ['button:has-text("保存"), button:has-text("确认"), button:has-text("Save"), button.btn-primary']:
                        try:
                            save_btn = page.locator(selector).first
                            if await save_btn.count() > 0:
                                await save_btn.click()
                                await asyncio.sleep(1.5)
                                print("✓ 点击保存按钮")
                                break
                        except:
                            continue
                    
                    await page.screenshot(path='test_screenshot_4_settings_saved.png')
                    
                except Exception as e:
                    print(f"⚠ 设置功能测试部分跳过: {e}")
            else:
                print("⚠ 未找到设置按钮")
            
            # 4. 测试创建新项目
            print("\n[4/12] 测试创建新项目...")
            
            # 点击新建项目按钮
            create_button = None
            for selector in ['button:has-text("新建项目"), button:has-text("创建"), button:has-text("New")']:
                try:
                    btn = page.locator(selector).first
                    if await btn.count() > 0:
                        create_button = btn
                        break
                except:
                    continue
            
            if create_button:
                await create_button.click()
                await asyncio.sleep(1.5)
                print("✓ 打开创建项目对话框")
                await page.screenshot(path='test_screenshot_5_create_project.png')
                
                # 填写项目信息
                try:
                    # 填写输入框
                    all_inputs = await page.locator('input, textarea').all()
                    for i, inp in enumerate(all_inputs):
                        try:
                            placeholder = await inp.get_attribute('placeholder') or ''
                            tag_name = await inp.evaluate('el => el.tagName')
                            
                            if '名称' in placeholder or 'name' in placeholder.lower() or tag_name == 'INPUT':
                                await inp.fill(project_name)
                                print(f"✓ 填写项目名称: {project_name}")
                            elif '描述' in placeholder or 'desc' in placeholder.lower() or tag_name == 'TEXTAREA':
                                await inp.fill('这是一个通过Playwright UI测试创建的项目。')
                                print("✓ 填写项目描述")
                        except:
                            continue
                    
                    await page.screenshot(path='test_screenshot_6_project_filled.png')
                    
                    # 确认创建
                    for selector in ['button:has-text("创建"), button:has-text("确认"), button:has-text("Create"), button.btn-primary']:
                        try:
                            confirm_btn = page.locator(selector).last
                            if await confirm_btn.count() > 0:
                                await confirm_btn.click()
                                await asyncio.sleep(3)
                                print("✓ 点击创建按钮")
                                break
                        except:
                            continue
                    
                    await page.screenshot(path='test_screenshot_7_project_created.png')
                    
                    current_url = page.url
                    print(f"✓ 当前页面: {current_url}")
                    
                except Exception as e:
                    print(f"⚠ 创建项目部分出现问题: {e}")
            else:
                print("⚠ 未找到创建项目按钮")
            
            # 5. 等待项目加载
            print("\n[5/12] 等待项目加载...")
            await asyncio.sleep(2)
            await page.screenshot(path='test_screenshot_8_project_loaded.png')
            
            # 6. 查找并点击文件
            print("\n[6/12] 测试文件树...")
            
            # 查找所有可点击的元素
            all_elements = await page.locator('[role="treeitem"], .file-tree *, .tree-node, .sidebar *').all()
            print(f"✓ 找到 {len(all_elements)} 个可能的文件项")
            
            for i, el in enumerate(all_elements[:5]):
                try:
                    await el.click()
                    await asyncio.sleep(0.5)
                    print(f"✓ 点击了元素{i}")
                    break
                except:
                    continue
            
            await page.screenshot(path='test_screenshot_9_file_tree.png')
            
            # 7. 测试编辑器
            print("\n[7/12] 测试编辑器功能...")
            
            # 查找编辑区域
            for selector in ['textarea, [contenteditable], .editor, .cm-content, .ProseMirror']:
                try:
                    editor = page.locator(selector).first
                    if await editor.count() > 0:
                        await editor.click()
                        await asyncio.sleep(0.5)
                        
                        # 输入一些内容
                        await page.keyboard.type('测试内容...', delay=100)
                        await asyncio.sleep(1)
                        print("✓ 编辑器输入成功")
                        break
                except:
                    continue
            
            await page.screenshot(path='test_screenshot_10_editor_input.png')
            
            # 8. 测试面板切换
            print("\n[8/12] 测试右侧面板...")
            
            # 点击所有找到的按钮
            all_buttons = await page.locator('button').all()
            for btn in all_buttons[-10:]:  # 只试后面的按钮
                try:
                    await btn.click()
                    await asyncio.sleep(0.5)
                except:
                    continue
            
            await page.screenshot(path='test_screenshot_11_right_panels.png')
            
            # 9. 测试AI/聊天
            print("\n[9/12] 测试AI相关功能...")
            
            for selector in ['button:has-text("生成"), button:has-text("AI"), button:has-text("Chat"), .chat-btn']:
                try:
                    ai_btn = page.locator(selector).first
                    if await ai_btn.count() > 0:
                        await ai_btn.click()
                        await asyncio.sleep(1.5)
                        print(f"✓ 点击AI按钮")
                        break
                except:
                    continue
            
            await page.screenshot(path='test_screenshot_12_ai_panel.png')
            
            # 10-12. 最终截图
            print("\n[10-12/12] 最终检查和截图...")
            await asyncio.sleep(1)
            await page.screenshot(path='test_screenshot_final.png')
            
            print("\n" + "=" * 80)
            print("UI自动化测试完成！")
            print("=" * 80)
            
            screenshots = list(Path().glob('test_screenshot_*.png'))
            print(f"\n共生成 {len(screenshots)} 张截图:")
            for screenshot in sorted(screenshots):
                print(f"  - {screenshot.name}")
            
        except Exception as e:
            print(f"\n✗ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='test_screenshot_error.png')
        finally:
            print("\n浏览器将在15秒后关闭...")
            await asyncio.sleep(15)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ui_flow())
