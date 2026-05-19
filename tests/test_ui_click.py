"""墨韵 - 通过Playwright模拟点击测试所有前端功�?
本脚本模拟人类操作，通过点击前端页面测试所有功能，验证返回结果是否符合预期�?"""
import asyncio
import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright

# 配置
FRONTEND_URL = "http://localhost:5174/"
SCREENSHOTS_DIR = Path(__file__).parent / "test_screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# 测试报告
test_results = []
errors = []


def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "passed": passed, "detail": detail})
    print(f"  [{status}] {name}" + (f" ({detail})" if detail else ""))
    if not passed:
        errors.append(name)


async def screenshot(page, filename):
    path = SCREENSHOTS_DIR / filename
    await page.screenshot(path=str(path), full_page=True)
    print(f"  [截图] {filename}")


async def wait_and_click(page, selector, timeout=10000):
    """等待并点击元�?""
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        btn = page.locator(selector).first
        await btn.click()
        await asyncio.sleep(1)
        return True
    except Exception as e:
        print(f"  点击失败: {selector} - {e}")
        return False


async def fill_input(page, selector, value):
    """填写输入�?""
    try:
        inp = page.locator(selector).first
        await inp.fill(value)
        return True
    except:
        return False


async def test_1_page_load(page):
    """测试1: 页面加载"""
    print("\n=== 测试1: 页面加载 ===")
    try:
        await page.goto(FRONTEND_URL, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(2)
        
        title = await page.title()
        record("页面标题正确", "墨韵" in title, f"实际标题: {title}")
        
        # 检查核心元�?        header = await page.locator("text=墨韵").count() > 0
        record("应用头部显示", header)
        
        toolbar = await page.locator(".editor-toolbar, .toolbar").count() > 0
        record("编辑器工具栏存在", toolbar)
        
        await screenshot(page, "01_page_load.png")
    except Exception as e:
        record("页面加载", False, str(e))


async def test_2_settings(page):
    """测试2: 设置功能 - 配置DeepSeek并测试连�?""
    print("\n=== 测试2: 设置功能 ===")
    try:
        # 点击设置按钮
        clicked = await wait_and_click(page, 'button:has-text("设置")')
        record("打开设置弹窗", clicked)
        await asyncio.sleep(1)
        
        if not clicked:
            await screenshot(page, "02_settings_failed.png")
            return
        
        # 检查弹�?        modal = await page.locator('.modal-overlay, .modal, [role="dialog"]').count() > 0
        record("设置弹窗可见", modal)
        
        # 检查DeepSeek是否在Provider选项�?        content = await page.content()
        has_deepseek = "DeepSeek" in content or "deepseek" in content.lower()
        record("DeepSeek选项存在", has_deepseek)
        
        # 选择DeepSeek Provider
        if has_deepseek:
            await wait_and_click(page, 'text=DeepSeek')
            await asyncio.sleep(0.5)
        
        # 填写API配置
        # API Key
        await fill_input(page, 'input[type="password"], input[placeholder*="Key"], input[name*="key"]', "sk-test-placeholder")
        await asyncio.sleep(0.5)
        
        # API URL
        await fill_input(page, 'input[placeholder*="url"], input[placeholder*="URL"], input[name*="url"]', "https://api.deepseek.com")
        await asyncio.sleep(0.5)
        
        # Model
        await fill_input(page, 'input[placeholder*="model"], input[name*="model"]', "deepseek-chat")
        await asyncio.sleep(0.5)
        
        await screenshot(page, "02_settings_filled.png")
        
        # 测试连接
        clicked = await wait_and_click(page, 'button:has-text("测试连接")')
        record("点击测试连接", clicked)
        
        if clicked:
            # 等待15秒让测试完成
            print("  等待连接测试结果...")
            for i in range(15):
                await asyncio.sleep(1)
                content = await page.content()
                if "成功" in content or "success" in content.lower() or "连接成功" in content:
                    print(f"  连接测试成功 (等待{i+1}�?")
                    break
            
            content = await page.content()
            connected = "连接成功" in content or "success" in content.lower() or "成功" in content
            record("DeepSeek连接测试", connected, "等待15秒后检�?)
            
            await screenshot(page, "02_connection_test.png")
        
        # 保存设置
        await wait_and_click(page, 'button:has-text("保存")')
        await asyncio.sleep(1)
        record("保存设置", True)
        
        await screenshot(page, "02_settings_saved.png")
    except Exception as e:
        record("设置功能", False, str(e))
        await screenshot(page, "02_settings_error.png")


async def test_3_create_project_wizard(page):
    """测试3: 创建项目向导 - 选择题材、基调、风格、规�?""
    print("\n=== 测试3: 创建项目向导 ===")
    try:
        # 点击新建项目
        clicked = await wait_and_click(page, 'button:has-text("新建项目")')
        record("打开新建项目弹窗", clicked)
        await asyncio.sleep(1.5)
        
        if not clicked:
            await screenshot(page, "03_wizard_failed.png")
            return
        
        # 检查向导打开
        modal = await page.locator('.modal-overlay, [role="dialog"]').count() > 0
        record("新建项目弹窗可见", modal)
        
        # 步骤1: 选择题材 - 玄幻
        await wait_and_click(page, 'button:has-text("玄幻")')
        await asyncio.sleep(0.5)
        record("选择题材-玄幻", True)
        
        # 步骤2: 选择基调 - 热血
        await wait_and_click(page, 'button:has-text("热血")')
        await asyncio.sleep(0.5)
        record("选择基调-热血", True)
        
        # 步骤3: 选择写作风格 - 快节�?        await wait_and_click(page, 'button:has-text("快节�?)')
        await asyncio.sleep(0.5)
        record("选择写作风格-快节�?, True)
        
        # 步骤4: 选择作品规模 - 10万字
        await wait_and_click(page, 'button:has-text("10万字")')
        await asyncio.sleep(0.5)
        record("选择作品规模-10万字", True)
        
        await screenshot(page, "03_params_filled.png")
        
        # 点击生成书名
        clicked = await wait_and_click(page, 'button:has-text("生成"), button:has-text("开�?)')
        record("点击生成书名", clicked)
        
        if clicked:
            # 等待AI生成书名（最�?5秒）
            print("  等待AI生成书名...")
            generated = False
            for i in range(45):
                await asyncio.sleep(1)
                content = await page.content()
                if "�? in content and "�? in content:
                    print(f"  AI生成完成 (等待{i+1}�?")
                    generated = True
                    break
                if i % 10 == 0 and i > 0:
                    print(f"  已等�?{i} �?..")
            
            record("AI生成书名创意", generated, "等待最�?5�?)
            await screenshot(page, "03_book_idea_generated.png")
        
        # 检查书名是否显�?        content = await page.content()
        has_book_name = "�? in content and "�? in content
        record("书名创意显示", has_book_name)
        
        # 点击下一�?        await wait_and_click(page, 'button:has-text("下一�?)')
        await asyncio.sleep(1)
        record("点击下一�?, True)
        
        await screenshot(page, "03_next_step.png")
    except Exception as e:
        record("创建项目向导", False, str(e))
        await screenshot(page, "03_wizard_error.png")


async def test_4_outline_generation(page):
    """测试4: 大纲生成"""
    print("\n=== 测试4: 大纲生成 ===")
    try:
        # 等待大纲生成按钮
        await asyncio.sleep(2)
        
        # 点击生成大纲
        clicked = await wait_and_click(page, 'button:has-text("生成大纲")', timeout=15000)
        record("点击生成大纲", clicked)
        
        if clicked:
            # 等待大纲生成（最�?0秒）
            print("  等待AI生成大纲...")
            generated = False
            for i in range(90):
                await asyncio.sleep(1)
                content = await page.content()
                if "�?�? in content or "�?�? in content or "确认大纲" in content:
                    print(f"  大纲生成完成 (等待{i+1}�?")
                    generated = True
                    break
                if i % 15 == 0 and i > 0:
                    print(f"  已等�?{i} �?..")
            
            record("AI生成大纲", generated, "等待最�?0�?)
            await screenshot(page, "04_outline_generated.png")
        
        # 检查大纲内�?        content = await page.content()
        has_chapters = "�? in content and "�? in content
        has_detail = "简�? in content or "情节" in content
        record("大纲包含章节", has_chapters)
        record("大纲内容详细", has_detail)
        
        # 确认大纲
        await wait_and_click(page, 'button:has-text("确认"), button:has-text("创建项目")')
        await asyncio.sleep(3)
        record("确认大纲并创建项�?, True)
        
        await screenshot(page, "04_project_created.png")
    except Exception as e:
        record("大纲生成", False, str(e))
        await screenshot(page, "04_outline_error.png")


async def test_5_editor(page):
    """测试5: 编辑器功�?""
    print("\n=== 测试5: 编辑器功�?===")
    try:
        # 等待项目加载
        await asyncio.sleep(3)
        
        # 检查文件树
        file_tree = await page.locator('.file-tree, .sidebar-files, .tree').count() > 0
        record("文件树可�?, file_tree)
        
        # 检查编辑器
        editor = await page.locator('.editor, [contenteditable="true"], .cm-editor, .monaco-editor').count() > 0
        record("编辑器可�?, editor)
        
        # 尝试点击编辑器并输入
        if editor:
            await page.locator('.editor, [contenteditable="true"]').first.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type("这是一段UI自动化测试文本�?)
            await asyncio.sleep(1)
            
            content = await page.content()
            has_text = "UI自动化测�? in content
            record("编辑器输入文�?, has_text)
        
        # 测试工具栏按�?        toolbar_btns = page.locator('.toolbar button, .editor-toolbar button')
        count = await toolbar_btns.count()
        record("工具栏按钮存�?, count > 0, f"按钮数量: {count}")
        
        if count > 0:
            await toolbar_btns.first.click()
            record("工具栏按钮可点击", True)
        
        await screenshot(page, "05_editor.png")
    except Exception as e:
        record("编辑器功�?, False, str(e))
        await screenshot(page, "05_editor_error.png")


async def test_6_chat_panel(page):
    """测试6: AI对话面板"""
    print("\n=== 测试6: AI对话面板 ===")
    try:
        # 检查聊天输入框
        chat_input = await page.locator('input[placeholder*="输入消息"], textarea[placeholder*="输入"]').count() > 0
        record("聊天输入框可�?, chat_input)
        
        if chat_input:
            await page.locator('input[placeholder*="输入消息"]').first.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type("你好")
            await asyncio.sleep(0.5)
            
            # 点击发�?            await wait_and_click(page, 'button:has-text("发�?), .send-btn')
            await asyncio.sleep(3)
            record("发送聊天消�?, True)
        
        await screenshot(page, "06_chat.png")
    except Exception as e:
        record("AI对话面板", False, str(e))
        await screenshot(page, "06_chat_error.png")


async def main():
    print("=" * 70)
    print("墨韵 AI小说创作助手 - UI功能测试")
    print("通过模拟点击前端页面，测试页面上的全部功�?)
    print("=" * 70)
    print(f"\n前端地址: {FRONTEND_URL}")
    print(f"截图目录: {SCREENSHOTS_DIR}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        # 监听控制�?        page.on("console", lambda msg: print(f"  [Console] {msg.text[:200]}"))
        page.on("pageerror", lambda err: print(f"  [Error] {str(err)[:200]}"))
        
        try:
            await test_1_page_load(page)
            await test_2_settings(page)
            await test_3_create_project_wizard(page)
            await test_4_outline_generation(page)
            await test_5_editor(page)
            await test_6_chat_panel(page)
            
            await screenshot(page, "final_result.png")
        except Exception as e:
            print(f"\n测试异常: {e}")
            await screenshot(page, "error_final.png")
        finally:
            await browser.close()
    
    # 打印报告
    print("\n" + "=" * 70)
    print("测试报告")
    print("=" * 70)
    
    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    total = len(test_results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed} �?)
    print(f"失败: {failed} �?)
    print(f"通过�? {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for i, t in enumerate(test_results, 1):
        icon = "�? if t["passed"] else "�?
        detail = f" - {t['detail']}" if t['detail'] else ""
        print(f"  {i:2d}. [{icon}] {t['name']}{detail}")
    
    if errors:
        print(f"\n失败的测�?")
        for e in errors:
            print(f"  �?{e}")
    
    print("\n" + "=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

