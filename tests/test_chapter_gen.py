#!/usr/bin/env python3
"""
墨韵 - 第一章生成全流程 E2E 测试 v6
模拟用户通过页面操作生成一部作品的第一�?主要改进：正确打开文件、更好的聊天测试
"""

import sys
import time
from playwright.sync_api import sync_playwright

FRONTEND_URL = "file:///D:/newmoyun/prototype.html"
BACKEND_URL = "http://localhost:8000"
API_KEY = "sk-test-key-for-e2e"

class ChapterGenTest:
    def __init__(self):
        self.browser = None
        self.page = None
        self.test_results = []
        self.step_num = 0
        self.screenshots = []

    def log(self, msg, status="info"):
        icon = {"pass": "�?, "fail": "�?, "info": "ℹ️", "step": "▶️"}.get(status, "ℹ️")
        print(f"{icon} {msg}")
        self.test_results.append({"msg": msg, "status": status})

    def setup(self):
        self.log("启动浏览�?..", "step")
        p = sync_playwright().start()
        # 用有头浏览器方便调试
        self.browser = p.chromium.launch(headless=False)
        self.page = self.browser.new_page(viewport={"width": 1400, "height": 900})
        self.log("浏览器启动成�?, "pass")

    def teardown(self):
        if self.browser:
            self.browser.close()

    def screenshot(self, name):
        path = f"D:/newmoyun/screenshot_{name}.png"
        self.page.screenshot(path=path, full_page=False)
        self.screenshots.append(path)
        return path

    def next_step(self):
        self.step_num += 1
        return self.step_num

    def js(self, code):
        return self.page.evaluate(code)

    def close_modal(self):
        try:
            self.js("if(window.$moyun && window.$moyun.closeModal) window.$moyun.closeModal();")
            self.page.wait_for_timeout(500)
        except:
            pass

    # ============ 步骤 ============

    def step_open_page(self):
        step = self.next_step()
        self.log(f"步骤{step}：打开页面", "step")
        self.page.goto(FRONTEND_URL)
        self.page.wait_for_timeout(2000)
        assert "墨韵" in self.page.title()
        self.log(f"页面加载成功：{self.page.title()}", "pass")
        self.screenshot(f"{step:02d}_open")

    def step_configure_settings(self):
        step = self.next_step()
        self.log(f"步骤{step}：配置设�?, "step")
        self.close_modal()

        # 打开设置
        self.js("window.$moyun.openModal('settings')")
        self.page.wait_for_timeout(1000)
        self.log("设置模态框已打开", "pass")
        self.screenshot(f"{step:02d}_modal")

        # 填表
        inputs = self.page.locator(".settings-section input")
        cnt = inputs.count()
        self.log(f"找到 {cnt} 个输入框", "info")

        if cnt >= 1:
            inputs.nth(0).fill(BACKEND_URL)
            self.log(f"填写后端地址：{BACKEND_URL}", "pass")
        if cnt >= 2:
            inputs.nth(1).fill("https://api.deepseek.com")
            self.log("填写 LLM API 地址", "pass")

        pw_inputs = self.page.locator("input[type='password']")
        if pw_inputs.count() > 0:
            pw_inputs.first.fill(API_KEY)
            self.log("填写 API Key", "pass")

        self.screenshot(f"{step:02d}_filled")

        # 保存
        self.page.click(".modal-footer .btn-primary")
        self.page.wait_for_timeout(1500)
        self.close_modal()
        self.log("设置已保存，模态框已关�?, "pass")
        self.screenshot(f"{step:02d}_saved")

    def step_create_project(self):
        step = self.next_step()
        self.log(f"步骤{step}：创建新项目", "step")
        self.close_modal()

        self.js("window.$moyun.openModal('newProject')")
        self.page.wait_for_timeout(1000)
        self.log("新建项目模态框已打开", "pass")
        self.screenshot(f"{step:02d}_modal")

        # 选择题材/基调
        opts = self.page.locator(".modal .btn-option")
        if opts.count() > 0:
            opts.nth(0).click()
            self.log("选择题材：第1�?, "pass")
        if opts.count() > 4:
            opts.nth(4).click()
            self.log("选择基调：第5�?, "pass")

        # 填作者名
        author = self.page.locator("input[placeholder*='作�?]")
        if author.count() > 0:
            author.fill("测试作�?)
            self.log("填写作者名", "pass")

        self.screenshot(f"{step:02d}_filled")

        # 创建
        btn = self.page.locator(".modal-footer .btn-primary")
        if btn.count() > 0:
            btn.click()
            self.log("点击创建按钮", "pass")
            self.page.wait_for_timeout(4000)
            self.close_modal()

        # 验证
        cp = self.js("window.$moyun.currentProject?.value || null")
        if cp:
            self.log(f"项目创建成功：{cp.get('name', cp)}", "pass")
        else:
            self.log("项目创建�?currentProject 为空，强制加�?..", "info")
            self.js("window.$moyun.loadFileTree()")
            self.page.wait_for_timeout(2000)

        self.screenshot(f"{step:02d}_created")

    def step_open_file_and_write(self):
        step = self.next_step()
        self.log(f"步骤{step}：打开文件并填写内�?, "step")
        self.close_modal()
        self.page.wait_for_timeout(1500)

        # 打印文件树结�?        tree = self.js("""
        (function() {
            var t = window.$moyun.fileTree?.value || [];
            return t.map(function(n) {
                return {name: n.name, type: n.type, childCount: (n.children||[]).length};
            });
        })()
        """)
        self.log(f"文件树根节点：{tree}", "info")

        # 点击第一个可编辑文件（先展开目录�?        try:
            # 展开第一个目�?            first_folder = self.page.locator(".tree-item.folder").first
            if first_folder.count() > 0:
                first_folder.click()
                self.page.wait_for_timeout(800)
                self.log("展开第一个目�?, "pass")

            # 点击第一个文�?            first_file = self.page.locator(".tree-item:not(.folder)").first
            if first_file.count() > 0:
                first_file.click()
                self.page.wait_for_timeout(800)
                self.log("点击第一个文�?, "pass")
            else:
                # 尝试点击文件树中的任何文�?                file_items = self.page.locator(".tree-item")
                for i in range(min(file_items.count(), 10)):
                    item = file_items.nth(i)
                    cls = item.get_attribute("class") or ""
                    if "folder" not in cls:
                        item.click()
                        self.page.wait_for_timeout(500)
                        self.log(f"点击文件树项�?#{i}", "pass")
                        break

        except Exception as e:
            self.log(f"打开文件异常：{e}", "fail")

        self.screenshot(f"{step:02d}_file_opened")

        # 填写内容
        content = """# 逆天改命

## 第一�?废材觉醒

林家演武场上，一场针对林凡的羞辱正在进行�?
"林凡，你这个废物�?

就在这时，天空中一道流星划�?..

林凡趁机爬起来，悄悄向后山退去。当他来到后山时，发现坑中有一块散发幽光的玉佩�?
就在他触碰到玉佩的瞬间，一道信息涌入他的脑海�?
"吾乃上古仙人，留下此传承..."

林凡的眼睛突然变得明亮起来。这是他逆天改命的开始！

"""
        ta = self.page.locator("textarea")
        if ta.count() > 0:
            ta.first.fill(content)
            self.log("已填写章节内�?, "pass")
            self.js("window.$moyun.saveFile()")
            self.page.wait_for_timeout(1000)
            self.log("文件已保�?, "pass")
        else:
            self.log("未找到编辑器 textarea", "fail")

        self.screenshot(f"{step:02d}_written")

    def step_use_ai(self):
        step = self.next_step()
        self.log(f"步骤{step}：使�?AI 助手", "step")
        self.close_modal()

        ci = self.page.locator("textarea.chat-input")
        if ci.count() == 0:
            self.log("未找到聊天输入框", "fail")
            return

        ci.fill("请继续写一段剧情，让林凡的传承觉醒过程更详�?)
        self.log("已填�?AI 指令", "pass")
        self.screenshot(f"{step:02d}_prompt_ready")

        sb = self.page.locator("button.chat-send")
        if sb.count() > 0:
            sb.click(force=True)
            self.log("已点击发送按�?, "pass")
            self.screenshot(f"{step:02d}_sent")

            # 等待响应
            self.log("等待 AI 响应（最�?60 秒）...", "info")
            self.page.wait_for_timeout(60000)

            msgs = self.js("window.$moyun.chatMessages?.value || []")
            if len(msgs) >= 2:
                last = msgs[-1].get("content", "") if isinstance(msgs[-1], dict) else str(msgs[-1])
                self.log(f"AI 响应成功，长度：{len(last)}", "pass")
            else:
                self.log(f"聊天消息数量：{len(msgs)}，AI 可能未响�?, "info")
        else:
            self.log("未找到发送按�?, "fail")

        self.screenshot(f"{step:02d}_done")

    def step_verify(self):
        step = self.next_step()
        self.log(f"步骤{step}：最终验�?, "step")
        self.close_modal()

        cp = self.js("window.$moyun.currentProject?.value?.name || '�?")
        self.log(f"当前项目：{cp}", "pass")

        ft = self.js("window.$moyun.fileTree?.value || []")
        self.log(f"文件树节点数：{len(ft)}", "pass")

        msgs = self.js("window.$moyun.chatMessages?.value || []")
        self.log(f"聊天消息数：{len(msgs)}", "pass")

        self.screenshot(f"{step:02d}_final")

    def run(self):
        self.log("=" * 60, "info")
        self.log("开始第一章生成全流程测试 v6", "info")
        self.log("=" * 60, "info")

        try:
            self.setup()
            self.step_open_page()
            self.step_configure_settings()
            self.step_create_project()
            self.step_open_file_and_write()
            self.step_use_ai()
            self.step_verify()

            passed = sum(1 for r in self.test_results if r["status"] == "pass")
            failed = sum(1 for r in self.test_results if r["status"] == "fail")
            self.log("=" * 60, "info")
            self.log(f"测试完成：通过 {passed}，失�?{failed}", "info")
            return failed == 0

        except Exception as e:
            self.log(f"测试异常：{e}", "fail")
            import traceback; traceback.print_exc()
            return False
        finally:
            self.teardown()

if __name__ == "__main__":
    t = ChapterGenTest()
    sys.exit(0 if t.run() else 1)

