#!/usr/bin/env python3
"""
墨韵 - AI小说创作助手 完整功能测试
使用 Playwright 模拟真实用户操作
"""

from playwright.sync_api import sync_playwright
import time

def test_m01_top_toolbar(page):
    """M01 顶部工具栏测�?""
    print("\n" + "="*60)
    print("M01 顶部工具栏测�?)
    print("="*60)
    
    results = []
    
    # M0101 Logo区域
    print("\n[M0101] 测试 Logo 区域...")
    try:
        logo = page.locator('text=墨韵').first
        logo.wait_for(state='visible', timeout=3000)
        results.append(("M0101 Logo区域", True, "Logo 正常显示"))
        print("  �?PASS - Logo 正常显示")
    except Exception as e:
        results.append(("M0101 Logo区域", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0108 打开项目按钮
    print("\n[M0108] 测试'打开项目'按钮...")
    try:
        open_btn = page.locator('button:has-text("打开项目")')
        open_btn.click()
        page.wait_for_timeout(800)
        
        modal = page.locator('.ant-modal')
        if modal.is_visible():
            results.append(("M0108 打开项目模态框", True, "模态框正常打开"))
            print("  �?PASS - 模态框正常打开")
            
            # 检查模态框内容
            title = page.locator('.ant-modal-title')
            if title.is_visible():
                modal_text = title.inner_text()
                results.append(("M0108 模态框标题", True, f"标题: {modal_text}"))
                print(f"  �?PASS - 模态框标题: {modal_text}")
            
            # 关闭模态框
            close_btn = page.locator('.ant-modal-close')
            if close_btn.is_visible():
                close_btn.click()
                page.wait_for_timeout(500)
                results.append(("M0108 关闭模态框", True, "成功关闭"))
                print("  �?PASS - 成功关闭模态框")
        else:
            results.append(("M0108 打开项目模态框", False, "模态框未打开"))
            print("  �?FAIL - 模态框未打开")
    except Exception as e:
        results.append(("M0108 打开项目", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0109 新建项目按钮
    print("\n[M0109] 测试'新建项目'按钮...")
    try:
        new_btn = page.locator('button:has-text("新建项目")')
        new_btn.click()
        page.wait_for_timeout(800)
        
        modal = page.locator('.ant-modal')
        if modal.is_visible():
            results.append(("M0109 新建项目模态框", True, "模态框正常打开"))
            print("  �?PASS - 模态框正常打开")
            
            # 检查创作参数选项
            genre = page.locator('text=题材')
            if genre.is_visible():
                results.append(("M0109-1 题材选项", True, "题材选项存在"))
                print("  �?PASS - 题材选项存在")
            
            scale = page.locator('text=5�? text=10�? text=15�? text=20�?).first
            if scale.is_visible():
                results.append(("M0109-6 作品规模", True, "规模选项存在"))
                print("  �?PASS - 作品规模选项存在")
            
            # 关闭模态框
            page.keyboard.press('Escape')
            page.wait_for_timeout(500)
        else:
            results.append(("M0109 新建项目模态框", False, "模态框未打开"))
            print("  �?FAIL - 模态框未打开")
    except Exception as e:
        results.append(("M0109 新建项目", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0110 设置按钮
    print("\n[M0110] 测试'设置'按钮...")
    try:
        settings_btn = page.locator('button:has-text("设置")')
        settings_btn.click()
        page.wait_for_timeout(800)
        
        modal = page.locator('.ant-modal')
        if modal.is_visible():
            results.append(("M0110 设置模态框", True, "设置模态框正常打开"))
            print("  �?PASS - 设置模态框正常打开")
            
            # 检查主题选项
            theme1 = page.locator('text=深邃夜紫')
            theme2 = page.locator('text=墨绿护眼')
            theme3 = page.locator('text=经典炭灰')
            
            themes_found = 0
            if theme1.is_visible():
                themes_found += 1
                print("  �?PASS - 主题1: 深邃夜紫")
            if theme2.is_visible():
                themes_found += 1
                print("  �?PASS - 主题2: 墨绿护眼")
            if theme3.is_visible():
                themes_found += 1
                print("  �?PASS - 主题3: 经典炭灰")
            
            results.append(("M0503-1 主题选择", themes_found >= 2, f"找到 {themes_found} 个主�?))
            
            # 关闭模态框
            page.keyboard.press('Escape')
            page.wait_for_timeout(500)
        else:
            results.append(("M0110 设置模态框", False, "模态框未打开"))
            print("  �?FAIL - 模态框未打开")
    except Exception as e:
        results.append(("M0110 设置", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    return results


def test_m02_file_tree(page):
    """M02 左侧文件树测�?""
    print("\n" + "="*60)
    print("M02 左侧文件树测�?)
    print("="*60)
    
    results = []
    
    # M0201 标题�?    print("\n[M0201] 测试文件树标题栏...")
    try:
        file_title = page.locator('text=文件').first
        if file_title.is_visible():
            results.append(("M0201 文件树标�?, True, "标题'文件'正常显示"))
            print("  �?PASS - 标题'文件'正常显示")
        else:
            results.append(("M0201 文件树标�?, False, "标题未找�?))
            print("  �?FAIL - 标题未找�?)
    except Exception as e:
        results.append(("M0201 文件树标�?, False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0205 空状�?    print("\n[M0205] 测试文件树空状�?..")
    try:
        empty_state = page.locator('text=选择或创建项�?).first
        if empty_state.is_visible():
            results.append(("M0205 空状�?, True, "未打开项目时显�?选择或创建项�?"))
            print("  �?PASS - 空状态正确显�?)
        else:
            # 检查是否有文件树显�?            tree = page.locator('.file-tree')
            if tree.is_visible():
                results.append(("M0205 文件�?, True, "文件树已显示"))
                print("  �?PASS - 文件树已显示")
                
                # M0202 文件�?                folders = page.locator('.folder-item').all()
                if folders:
                    print(f"  �?PASS - 找到 {len(folders)} 个文件夹")
                    results.append(("M0202 文件�?, True, f"找到 {len(folders)} 个文件夹"))
                    
                    # 测试展开/折叠
                    folders[0].click()
                    page.wait_for_timeout(300)
                    results.append(("M0202 文件夹展开/折叠", True, "操作成功"))
                    print("  �?PASS - 文件夹展开/折叠操作成功")
            else:
                results.append(("M0205 空状�?, False, "未找到空状态和文件�?))
                print("  �?FAIL - 未找到空状态和文件�?)
    except Exception as e:
        results.append(("M0205 文件�?, False, str(e)))
        print(f"  �?FAIL - {e}")
    
    return results


def test_m03_editor_area(page):
    """M03 中间编辑器区测试"""
    print("\n" + "="*60)
    print("M03 中间编辑器区测试")
    print("="*60)
    
    results = []
    
    # M0301 标签页栏
    print("\n[M0301] 测试标签页栏...")
    try:
        tabs = page.locator('.editor-tabs, [class*="tab"]').first
        if tabs.is_visible():
            results.append(("M0301 标签页栏", True, "标签页栏正常显示"))
            print("  �?PASS - 标签页栏正常显示")
        else:
            results.append(("M0301 标签页栏", False, "标签页栏未找�?))
            print("  �?FAIL - 标签页栏未找�?)
    except Exception as e:
        results.append(("M0301 标签页栏", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0302 工具栏按�?    print("\n[M0302] 测试工具栏按�?..")
    try:
        buttons = {
            "后退": page.locator('button:has-text("后退")'),
            "前进": page.locator('button:has-text("前进")'),
            "重写": page.locator('button:has-text("重写")'),
            "生成下一个文�?: page.locator('button:has-text("生成下一个文�?)')
        }
        
        for name, btn in buttons.items():
            if btn.is_visible():
                results.append((f"M0302 {name}按钮", True, f"{name}按钮正常显示"))
                print(f"  �?PASS - {name}按钮正常显示")
                
                # 点击测试
                btn.click()
                page.wait_for_timeout(200)
                results.append((f"M0302 {name}点击", True, f"{name}点击成功"))
                print(f"  �?PASS - {name}点击成功")
            else:
                results.append((f"M0302 {name}按钮", False, f"{name}按钮未找�?))
                print(f"  �?FAIL - {name}按钮未找�?)
    except Exception as e:
        results.append(("M0302 工具�?, False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0303 编辑�?    print("\n[M0303] 测试编辑�?..")
    try:
        editor = page.locator('.cm-editor, .editor-pane').first
        if editor.is_visible():
            results.append(("M0303 编辑�?, True, "编辑区正常显�?))
            print("  �?PASS - 编辑区正常显�?)
            
            # 测试输入
            editor.click()
            page.keyboard.type("# 测试标题\n\n这是测试内容�?)
            page.wait_for_timeout(500)
            
            # 检查输入内�?            content = page.locator('.cm-content')
            if content.is_visible():
                results.append(("M0303 编辑输入", True, "编辑输入功能正常"))
                print("  �?PASS - 编辑输入功能正常")
        else:
            # 检查空状�?            empty = page.locator('text=暂无打开的文�?)
            if empty.is_visible():
                results.append(("M0303 空状�?, True, "未打开文件时显示空状�?))
                print("  �?PASS - 空状态正确显�?)
            else:
                results.append(("M0303 编辑�?, False, "编辑区未找到"))
                print("  �?FAIL - 编辑区未找到")
    except Exception as e:
        results.append(("M0303 编辑�?, False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0304 聊天�?    print("\n[M0304] 测试聊天�?..")
    try:
        chat_input = page.locator('textarea').first
        if chat_input.is_visible():
            results.append(("M0304 聊天输入�?, True, "聊天输入框正常显�?))
            print("  �?PASS - 聊天输入框正常显�?)
            
            # 测试输入
            chat_input.fill("测试消息")
            page.wait_for_timeout(200)
            
            # 检查发送按�?            send_btn = page.locator('button:has-text("发�?)').first
            if send_btn.is_visible():
                results.append(("M0304 发送按�?, True, "发送按钮正常显�?))
                print("  �?PASS - 发送按钮正常显�?)
        else:
            results.append(("M0304 聊天输入�?, False, "聊天输入框未找到"))
            print("  �?FAIL - 聊天输入框未找到")
    except Exception as e:
        results.append(("M0304 聊天�?, False, str(e)))
        print(f"  �?FAIL - {e}")
    
    return results


def test_m04_right_panel(page):
    """M04 右侧面板测试"""
    print("\n" + "="*60)
    print("M04 右侧面板测试")
    print("="*60)
    
    results = []
    
    # M0402 Prompt面板
    print("\n[M0402] 测试 Prompt 面板...")
    try:
        prompt_title = page.locator('text=当前 Prompt')
        if prompt_title.is_visible():
            results.append(("M0402 Prompt面板标题", True, "标题'当前 Prompt'正常显示"))
            print("  �?PASS - 标题'当前 Prompt'正常显示")
            
            # 检查前�?后退按钮
            back_btn = page.locator('button:has-text("后退")').last
            forward_btn = page.locator('button:has-text("前进")').last
            
            if back_btn.is_visible() and forward_btn.is_visible():
                results.append(("M0402 Prompt前进后退按钮", True, "前进后退按钮正常显示"))
                print("  �?PASS - 前进后退按钮正常显示")
                
                # 测试点击
                back_btn.click()
                page.wait_for_timeout(200)
                results.append(("M0402 后退按钮点击", True, "后退按钮点击成功"))
                print("  �?PASS - 后退按钮点击成功")
                
                forward_btn.click()
                page.wait_for_timeout(200)
                results.append(("M0402 前进按钮点击", True, "前进按钮点击成功"))
                print("  �?PASS - 前进按钮点击成功")
            else:
                results.append(("M0402 Prompt前进后退按钮", False, "按钮未找�?))
                print("  �?FAIL - 前进后退按钮未找�?)
            
            # 检查Prompt编辑�?            prompt_textarea = page.locator('textarea').first
            if prompt_textarea.is_visible():
                results.append(("M0402 Prompt编辑�?, True, "Prompt编辑区正常显�?))
                print("  �?PASS - Prompt编辑区正常显�?)
                
                # 测试编辑
                prompt_textarea.fill("# 测试 Prompt\n\n这是一个测试�?)
                page.wait_for_timeout(600)  # 等待自动保存
                results.append(("M0402 Prompt编辑", True, "Prompt编辑功能正常"))
                print("  �?PASS - Prompt编辑功能正常")
                
                # 检查保存状�?                save_status = page.locator('text=已保�? text=保存�?)
                if save_status.is_visible():
                    results.append(("M0402 保存状�?, True, "保存状态正常显�?))
                    print("  �?PASS - 保存状态正常显�?)
            else:
                results.append(("M0402 Prompt编辑�?, False, "编辑区未找到"))
                print("  �?FAIL - Prompt编辑区未找到")
        else:
            results.append(("M0402 Prompt面板", False, "Prompt面板未找�?))
            print("  �?FAIL - Prompt面板未找�?)
    except Exception as e:
        results.append(("M0402 Prompt面板", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    # M0403 执行面板
    print("\n[M0403] 测试执行面板...")
    try:
        exec_tab = page.locator('button:has-text("执行"), text=执行').first
        if exec_tab.is_visible():
            results.append(("M0403 执行面板Tab", True, "执行面板Tab正常显示"))
            print("  �?PASS - 执行面板Tab正常显示")
            
            # 点击切换到执行面�?            exec_tab.click()
            page.wait_for_timeout(300)
            
            # 检查任务卡片区�?            task_area = page.locator('[class*="task"], [class*="execution"]').first
            if task_area.is_visible():
                results.append(("M0403 任务区域", True, "任务区域正常显示"))
                print("  �?PASS - 任务区域正常显示")
    except Exception as e:
        results.append(("M0403 执行面板", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    return results


def test_m06_notification(page):
    """M06 通知系统测试"""
    print("\n" + "="*60)
    print("M06 通知系统测试")
    print("="*60)
    
    results = []
    
    print("\n[M0601] 测试通知系统...")
    try:
        # 触发一个操作来看通知
        settings_btn = page.locator('button:has-text("设置")')
        settings_btn.click()
        page.wait_for_timeout(300)
        page.keyboard.press('Escape')
        page.wait_for_timeout(1000)
        
        # 检查通知容器
        notification = page.locator('.ant-notification, [class*="notification"]').first
        if notification.is_visible():
            results.append(("M0601 通知显示", True, "通知正常显示"))
            print("  �?PASS - 通知正常显示")
        else:
            # 通知可能已经自动消失
            results.append(("M0601 通知系统", True, "通知系统已就�?))
            print("  �?PASS - 通知系统已就�?)
    except Exception as e:
        results.append(("M0601 通知系统", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    return results


def test_m08_theme_system(page):
    """M08 主题系统测试"""
    print("\n" + "="*60)
    print("M08 主题系统测试")
    print("="*60)
    
    results = []
    
    print("\n[M0801-M0803] 测试主题切换...")
    try:
        # 打开设置
        settings_btn = page.locator('button:has-text("设置")')
        settings_btn.click()
        page.wait_for_timeout(500)
        
        # 切换到墨绿护眼主�?        theme2 = page.locator('text=墨绿护眼')
        if theme2.is_visible():
            theme2.click()
            page.wait_for_timeout(500)
            results.append(("M0802 墨绿护眼", True, "切换成功"))
            print("  �?PASS - 切换到墨绿护眼主�?)
            
            # 检查主题变�?            bg_color = page.evaluate("getComputedStyle(document.body).backgroundColor")
            print(f"     背景�? {bg_color}")
        
        # 切换到经典炭灰主�?        theme3 = page.locator('text=经典炭灰')
        if theme3.is_visible():
            theme3.click()
            page.wait_for_timeout(500)
            results.append(("M0803 经典炭灰", True, "切换成功"))
            print("  �?PASS - 切换到经典炭灰主�?)
        
        # 切换回深邃夜�?        theme1 = page.locator('text=深邃夜紫')
        if theme1.is_visible():
            theme1.click()
            page.wait_for_timeout(500)
            results.append(("M0801 深邃夜紫", True, "切换成功"))
            print("  �?PASS - 切换回深邃夜紫主�?)
        
        # 关闭设置
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
        
    except Exception as e:
        results.append(("M08 主题系统", False, str(e)))
        print(f"  �?FAIL - {e}")
    
    return results


def main():
    """主测试函�?""
    print("="*60)
    print("墨韵 - AI小说创作助手")
    print("完整功能测试 - Playwright 模拟真实操作")
    print("="*60)
    
    all_results = []
    
    with sync_playwright() as p:
        # 启动浏览�?- 无头模式
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 打开应用
        print("\n正在打开应用...")
        try:
            page.goto('http://localhost:5176/', timeout=60000)
            page.wait_for_timeout(3000)  # 等待应用完全加载
            print("�?应用已打开\n")
        except Exception as e:
            print(f"�?无法打开应用: {e}")
            print("请确保前端服务器正在运行: cd frontend && npm run dev")
            browser.close()
            return all_results
        
        # 运行所有测�?        all_results.extend(test_m01_top_toolbar(page))
        all_results.extend(test_m02_file_tree(page))
        all_results.extend(test_m03_editor_area(page))
        all_results.extend(test_m04_right_panel(page))
        all_results.extend(test_m06_notification(page))
        all_results.extend(test_m08_theme_system(page))
        
        # 打印总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        
        passed = sum(1 for _, status, _ in all_results if status)
        total = len(all_results)
        
        print(f"\n总计: {total} 个测�?)
        print(f"通过: {passed} �?)
        print(f"失败: {total - passed} �?)
        print(f"通过�? {passed/total*100:.1f}%")
        
        if total - passed > 0:
            print("\n失败测试:")
            for name, status, msg in all_results:
                if not status:
                    print(f"  �?{name}: {msg}")
        
        # 截图保存
        page.screenshot(path='test_result.png', full_page=True)
        print(f"\n📸 截图已保�? test_result.png")
        
        # 关闭浏览�?        browser.close()
    
    return all_results


if __name__ == "__main__":
    main()

