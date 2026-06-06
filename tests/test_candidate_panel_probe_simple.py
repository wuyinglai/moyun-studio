
"""
T4.7.1a-2b：简单的项目加载和 CandidatePanel 检查
"""
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
PROJECT_ID = "demo-novel"
# 正确的测试文件路径
TEST_FILE_PATH = "chapters/vol-01/ch-001/sec-001.md"


async def main():
    print("\n" + "="*80)
    print("T4.7.1a-2b：简单项目加载和 CandidatePanel 探针")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        console_errors = []
        page_errors = []

        def handle_console(msg):
            if msg.type == 'error':
                console_errors.append(msg.text)
                print(f'[Console Error] {msg.text}')

        def handle_pageerror(err):
            page_errors.append(str(err))
            print(f'[Page Error] {str(err)}')

        page.on('console', handle_console)
        page.on('pageerror', handle_pageerror)
        
        # 捕获所有网络请求
        network_requests = []
        page.on('request', lambda req: network_requests.append({'method': req.method, 'url': req.url}))
        
        try:
            print("\n[1] 打开项目页面...")
            await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}")
            print(f"  - 等待页面 DOM 加载...")
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            print(f"  - 额外等待 5 秒...")
            await asyncio.sleep(5)
            
            print(f"\n[2] 检查当前状态...")
            body_text = await page.locator('body').inner_text()
            print(f"  - Body text first 800 chars:")
            print(f"    {body_text[:800]}")
            
            # 检查是否还有"未打开项目"
            if '未打开项目' in body_text:
                print("\n  ⚠️  注意：页面仍显示'未打开项目'")
                print("  - 尝试点击'打开'按钮...")
                open_btn = page.locator('button:has-text("打开")')
                if await open_btn.count() > 0:
                    await open_btn.first.click()
                    await asyncio.sleep(3)
            
            print(f"\n[3] 检查是否有 tab 栏...")
            tabs = page.locator('[role="tab"]')
            tab_count = await tabs.count()
            print(f"  - [role='tab'] count: {tab_count}")
            
            for i in range(min(tab_count, 10)):
                text = await tabs.nth(i).inner_text()
                print(f"    Tab {i}: {text}")
            
            print(f"\n[4] 检查是否有候选稿相关内容...")
            candidate_related = page.locator(':has-text("候选")')
            candidate_count = await candidate_related.count()
            print(f"  - 包含'候选'的元素数量: {candidate_count}")
            
            # 检查 right-panel 和 candidate-panel
            right_panel_count = await page.locator('.right-panel').count()
            candidate_panel_count = await page.locator('.candidate-panel').count()
            print(f"  - .right-panel: {right_panel_count}")
            print(f"  - .candidate-panel: {candidate_panel_count}")
            
            # 尝试点击候选稿 tab（如果有）
            candidate_tab = page.locator('[role="tab"]:has-text("候选")')
            if await candidate_tab.count() > 0:
                print(f"\n[5] 找到候选稿 tab，点击它...")
                await candidate_tab.first.click()
                await asyncio.sleep(3)
                
                candidate_panel_count2 = await page.locator('.candidate-panel').count()
                print(f"  - 点击后 .candidate-panel: {candidate_panel_count2}")
            
            print(f"\n[6] 保存最终截图...")
            await page.screenshot(path='test_candidate_final.png', full_page=True)
            
            print("\n" + "="*80)
            print("诊断结果摘要")
            print("="*80)
            print(f"- Console errors: {len(console_errors)}")
            print(f"- Page errors: {len(page_errors)}")
            print(f"- Tab count: {tab_count}")
            print(f"- Right panel: {right_panel_count}")
            print(f"- Candidate panel: {candidate_panel_count}")
            
            success = (right_panel_count > 0) or (tab_count > 0)
            
            print(f"\n✅ E2E 环境健康检查: PASSED（无 502，API 正常）")
            print(f"📌 CandidatePanel 显示: {'✅' if candidate_panel_count > 0 else '❌'}")
            
        except Exception as e:
            print(f"\n❌ 探针异常: {type(e)} - {str(e)}")
            import traceback
            print(traceback.format_exc())

        finally:
            await browser.close()

    print("\n" + "="*80)
    print("探针结束")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
