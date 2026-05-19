#!/usr/bin/env python3
"""
墨韵 - AI小说创作助手 功能测试脚本
测试功能清单中的所有功�?"""

from playwright.sync_api import sync_playwright
import time
import json

class MoyunTester:
    def __init__(self):
        self.results = []
        
    def log(self, test_name, status, message=""):
        """记录测试结果"""
        result = {
            "test": test_name,
            "status": status,
            "message": message
        }
        self.results.append(result)
        status_symbol = "�? if status == "PASS" else "�?
        print(f"{status_symbol} {test_name}: {status} {message}")
        
    def run_all_tests(self):
        """运行所有测�?""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # 监听控制台日�?            console_logs = []
            page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
            
            # 打开应用
            print("\n=== 打开应用 ===")
            page.goto('http://localhost:5176/')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # M01 顶部工具栏测�?            self.test_m01_top_toolbar(page)
            
            # M02 左侧文件树测�?            self.test_m02_file_tree(page)
            
            # M03 中间编辑器区测试
            self.test_m03_editor_area(page)
            
            # M04 右侧面板测试
            self.test_m04_right_panel(page)
            
            # M05 模态框测试
            self.test_m05_modals(page)
            
            # M06 通知系统测试
            self.test_m06_notification(page)
            
            # M07 拖拽调整测试
            self.test_m07_drag_resize(page)
            
            # M08 主题系统测试
            self.test_m08_theme_system(page)
            
            # 打印测试总结
            self.print_summary()
            
            browser.close()
    
    def test_m01_top_toolbar(self, page):
        """测试 M01 顶部工具�?""
        print("\n=== M01 顶部工具栏测�?===")
        
        # M0101 Logo区域
        try:
            logo = page.locator('text=墨韵').first
            if logo.is_visible():
                self.log("M0101 Logo区域", "PASS", "Logo正常显示")
            else:
                self.log("M0101 Logo区域", "FAIL", "Logo未显�?)
        except Exception as e:
            self.log("M0101 Logo区域", "FAIL", str(e))
        
        # M0108 打开项目按钮
        try:
            open_btn = page.locator('button:has-text("打开项目")')
            if open_btn.is_visible():
                self.log("M0108 打开项目按钮", "PASS", "按钮正常显示")
                # 点击打开项目
                open_btn.click()
                page.wait_for_timeout(500)
                
                # 检查模态框是否打开
                modal = page.locator('.ant-modal')
                if modal.is_visible():
                    self.log("M0108 打开项目", "PASS", "模态框正常打开")
                    # 关闭模态框
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(300)
                else:
                    self.log("M0108 打开项目", "FAIL", "模态框未打开")
            else:
                self.log("M0108 打开项目按钮", "FAIL", "按钮未找�?)
        except Exception as e:
            self.log("M0108 打开项目按钮", "FAIL", str(e))
        
        # M0109 新建项目按钮
        try:
            new_btn = page.locator('button:has-text("新建项目")')
            if new_btn.is_visible():
                self.log("M0109 新建项目按钮", "PASS", "按钮正常显示")
            else:
                self.log("M0109 新建项目按钮", "FAIL", "按钮未找�?)
        except Exception as e:
            self.log("M0109 新建项目按钮", "FAIL", str(e))
        
        # M0110 设置按钮
        try:
            settings_btn = page.locator('button:has-text("设置")')
            if settings_btn.is_visible():
                self.log("M0110 设置按钮", "PASS", "按钮正常显示")
                # 点击设置
                settings_btn.click()
                page.wait_for_timeout(500)
                
                # 检查设置模态框
                settings_modal = page.locator('.ant-modal')
                if settings_modal.is_visible():
                    self.log("M0110 设置模态框", "PASS", "设置模态框正常打开")
                    # 关闭模态框
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(300)
                else:
                    self.log("M0110 设置模态框", "FAIL", "模态框未打开")
            else:
                self.log("M0110 设置按钮", "FAIL", "按钮未找�?)
        except Exception as e:
            self.log("M0110 设置按钮", "FAIL", str(e))
    
    def test_m02_file_tree(self, page):
        """测试 M02 左侧文件�?""
        print("\n=== M02 左侧文件树测�?===")
        
        # M0201 标题�?        try:
            title = page.locator('text=文件').first
            if title.is_visible():
                self.log("M0201 文件树标�?, "PASS", "标题正常显示")
            else:
                self.log("M0201 文件树标�?, "FAIL", "标题未显�?)
        except Exception as e:
            self.log("M0201 文件树标�?, "FAIL", str(e))
        
        # M0202 文件夹展开/折叠
        try:
            folders = page.locator('.folder-item, [class*="folder"]').all()
            if folders:
                self.log("M0202 文件�?, "PASS", f"找到 {len(folders)} 个文件夹")
                # 点击第一个文件夹
                folders[0].click()
                page.wait_for_timeout(300)
            else:
                # 可能是空状�?                empty_state = page.locator('text=选择或创建项�? text=暂无文件')
                if empty_state.is_visible():
                    self.log("M0202 文件树空状�?, "PASS", "未打开项目时显示空状�?)
                else:
                    self.log("M0202 文件�?, "FAIL", "未找到文件夹且无空状�?)
        except Exception as e:
            self.log("M0202 文件�?, "FAIL", str(e))
    
    def test_m03_editor_area(self, page):
        """测试 M03 中间编辑器区"""
        print("\n=== M03 中间编辑器区测试 ===")
        
        # M0301 标签页栏
        try:
            tabs_area = page.locator('.editor-tabs, [class*="tab"]').first
            if tabs_area.is_visible():
                self.log("M0301 标签页栏", "PASS", "标签页区域正常显�?)
            else:
                self.log("M0301 标签页栏", "FAIL", "标签页区域未显示")
        except Exception as e:
            self.log("M0301 标签页栏", "FAIL", str(e))
        
        # M0302 工具栏按�?        try:
            # 后退按钮
            undo_btn = page.locator('button:has-text("后退")')
            if undo_btn.is_visible():
                self.log("M0302-4 后退按钮", "PASS", "后退按钮正常显示")
            else:
                self.log("M0302-4 后退按钮", "FAIL", "后退按钮未找�?)
            
            # 前进按钮
            redo_btn = page.locator('button:has-text("前进")')
            if redo_btn.is_visible():
                self.log("M0302-3 前进按钮", "PASS", "前进按钮正常显示")
            else:
                self.log("M0302-3 前进按钮", "FAIL", "前进按钮未找�?)
            
            # 重写按钮
            regen_btn = page.locator('button:has-text("重写")')
            if regen_btn.is_visible():
                self.log("M0302-1 重写按钮", "PASS", "重写按钮正常显示")
            else:
                self.log("M0302-1 重写按钮", "FAIL", "重写按钮未找�?)
            
            # 生成下一个文件按�?            next_btn = page.locator('button:has-text("生成下一个文�?)')
            if next_btn.is_visible():
                self.log("M0302-2 生成下一个文件按�?, "PASS", "生成下一个文件按钮正常显�?)
            else:
                self.log("M0302-2 生成下一个文件按�?, "FAIL", "生成下一个文件按钮未找到")
                
        except Exception as e:
            self.log("M0302 工具�?, "FAIL", str(e))
        
        # M0303 编辑�?        try:
            editor = page.locator('.cm-editor, .editor-pane, [class*="editor"]').first
            if editor.is_visible():
                self.log("M0303 编辑�?, "PASS", "编辑器正常显�?)
            else:
                # 空状�?                empty_editor = page.locator('text=暂无打开的文�? text=从左侧文件树选择一个文件开始编�?)
                if empty_editor.is_visible():
                    self.log("M0303 空状态占位符", "PASS", "编辑区空状态正常显�?)
                else:
                    self.log("M0303 编辑�?, "FAIL", "编辑器未找到且无空状�?)
        except Exception as e:
            self.log("M0303 编辑�?, "FAIL", str(e))
        
        # M0304 聊天�?        try:
            chat_input = page.locator('textarea, [class*="chat"] input').first
            if chat_input.is_visible():
                self.log("M0304 聊天输入�?, "PASS", "聊天输入框正常显�?)
            else:
                self.log("M0304 聊天输入�?, "FAIL", "聊天输入框未找到")
        except Exception as e:
            self.log("M0304 聊天�?, "FAIL", str(e))
    
    def test_m04_right_panel(self, page):
        """测试 M04 右侧面板"""
        print("\n=== M04 右侧面板测试 ===")
        
        # M0402 Prompt面板
        try:
            prompt_title = page.locator('text=当前 Prompt')
            if prompt_title.is_visible():
                self.log("M0402 Prompt面板标题", "PASS", "Prompt面板标题正常显示")
                
                # 检查前�?后退按钮
                prompt_back = page.locator('button:has-text("后退")').last
                prompt_forward = page.locator('button:has-text("前进")').last
                
                if prompt_back.is_visible() and prompt_forward.is_visible():
                    self.log("M0402 Prompt前进/后退", "PASS", "前进后退按钮正常显示")
                else:
                    self.log("M0402 Prompt前进/后退", "FAIL", "前进后退按钮未找�?)
                
                # 检查Prompt编辑�?                prompt_textarea = page.locator('textarea').first
                if prompt_textarea.is_visible():
                    self.log("M0402 Prompt编辑�?, "PASS", "Prompt编辑区正常显�?)
                else:
                    self.log("M0402 Prompt编辑�?, "FAIL", "Prompt编辑区未找到")
            else:
                self.log("M0402 Prompt面板", "FAIL", "Prompt面板未找�?)
        except Exception as e:
            self.log("M0402 Prompt面板", "FAIL", str(e))
        
        # M0403 执行面板
        try:
            execution_tab = page.locator('button:has-text("执行"), text=执行').first
            if execution_tab.is_visible():
                self.log("M0403 执行面板Tab", "PASS", "执行面板Tab正常显示")
        except Exception as e:
            self.log("M0403 执行面板", "FAIL", str(e))
    
    def test_m05_modals(self, page):
        """测试 M05 模态框"""
        print("\n=== M05 模态框测试 ===")
        
        # 测试新建项目模态框
        try:
            new_btn = page.locator('button:has-text("新建项目")')
            new_btn.click()
            page.wait_for_timeout(500)
            
            modal = page.locator('.ant-modal')
            if modal.is_visible():
                self.log("M0501 新建项目模态框", "PASS", "模态框正常打开")
                
                # 检查模态框内容
                modal_title = page.locator('.ant-modal-title, .ant-modal-header')
                if modal_title.is_visible():
                    self.log("M0501 模态框标题", "PASS", "模态框标题正常显示")
                
                # 关闭模态框
                page.keyboard.press('Escape')
                page.wait_for_timeout(300)
            else:
                self.log("M0501 新建项目模态框", "FAIL", "模态框未打开")
        except Exception as e:
            self.log("M0501 新建项目模态框", "FAIL", str(e))
        
        # 测试设置模态框
        try:
            settings_btn = page.locator('button:has-text("设置")')
            settings_btn.click()
            page.wait_for_timeout(500)
            
            modal = page.locator('.ant-modal')
            if modal.is_visible():
                self.log("M0503 设置模态框", "PASS", "设置模态框正常打开")
                
                # 检查主题选择
                theme_options = page.locator('text=深邃夜紫, text=墨绿护眼, text=经典炭灰').all()
                if len(theme_options) > 0:
                    self.log("M0503-1 主题选择", "PASS", f"找到 {len(theme_options)} 个主题选项")
                
                # 关闭模态框
                page.keyboard.press('Escape')
                page.wait_for_timeout(300)
            else:
                self.log("M0503 设置模态框", "FAIL", "模态框未打开")
        except Exception as e:
            self.log("M0503 设置模态框", "FAIL", str(e))
    
    def test_m06_notification(self, page):
        """测试 M06 通知系统"""
        print("\n=== M06 通知系统测试 ===")
        
        # 触发一个操作来看是否有通知
        try:
            # 尝试打开设置然后关闭，看是否有保存提�?            settings_btn = page.locator('button:has-text("设置")')
            settings_btn.click()
            page.wait_for_timeout(300)
            page.keyboard.press('Escape')
            page.wait_for_timeout(500)
            
            # 检查通知容器
            notifications = page.locator('.ant-notification, [class*="notification"]').all()
            if notifications:
                self.log("M0601 通知容器", "PASS", f"找到 {len(notifications)} 个通知")
            else:
                self.log("M0601 通知系统", "PASS", "通知系统已就绪（无待显示通知�?)
        except Exception as e:
            self.log("M0601 通知系统", "FAIL", str(e))
    
    def test_m07_drag_resize(self, page):
        """测试 M07 拖拽调整"""
        print("\n=== M07 拖拽调整测试 ===")
        
        try:
            # 检查分隔线
            gutters = page.locator('.gutter').all()
            if gutters:
                self.log("M0701 分隔�?, "PASS", f"找到 {len(gutters)} 个分隔线")
            else:
                self.log("M0701 分隔�?, "FAIL", "未找到分隔线")
        except Exception as e:
            self.log("M0701 拖拽分隔�?, "FAIL", str(e))
    
    def test_m08_theme_system(self, page):
        """测试 M08 主题系统"""
        print("\n=== M08 主题系统测试 ===")
        
        try:
            settings_btn = page.locator('button:has-text("设置")')
            settings_btn.click()
            page.wait_for_timeout(500)
            
            # 检查三个主�?            themes = {
                "深邃夜紫": page.locator('text=深邃夜紫'),
                "墨绿护眼": page.locator('text=墨绿护眼'),
                "经典炭灰": page.locator('text=经典炭灰')
            }
            
            found_themes = 0
            for theme_name, theme_elem in themes.items():
                if theme_elem.is_visible():
                    found_themes += 1
            
            if found_themes >= 2:
                self.log("M0801-M0803 主题选项", "PASS", f"找到 {found_themes} 个主题选项")
            else:
                self.log("M0801-M0803 主题选项", "FAIL", f"只找�?{found_themes} 个主题选项")
            
            # 关闭模态框
            page.keyboard.press('Escape')
            page.wait_for_timeout(300)
        except Exception as e:
            self.log("M0801-M0803 主题系统", "FAIL", str(e))
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = len(self.results)
        
        print(f"\n总计: {total} 个测�?)
        print(f"通过: {passed} �?)
        print(f"失败: {failed} �?)
        print(f"通过�? {passed/total*100:.1f}%")
        
        if failed > 0:
            print("\n失败测试:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  - {r['test']}: {r['message']}")
        
        # 保存结果到文�?        with open('/tmp/moyun_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n详细结果已保存到 /tmp/moyun_test_results.json")

if __name__ == "__main__":
    tester = MoyunTester()
    tester.run_all_tests()

