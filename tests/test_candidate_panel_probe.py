"""
T4.7.1a-2a: CandidatePanel 打开机制排查
==========================================

目标：诊断为什么点击"候选稿"tab 后 .candidate-panel 没有出现。
"""

import asyncio
import aiohttp
import uuid
from datetime import datetime
from playwright.async_api import async_playwright

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5174"
PROJECT_ID = "demo-novel"
# 需要先打开一个文件才能设置 currentProject 并显示 RightPanel
TEST_FILE_PATH = "scenes/__e2e_test_scene.md"


class CandidatePanelProbe:
    """CandidatePanel 打开机制探针"""

    def __init__(self):
        self.results = {}
        self.screenshot_dir = "d:/newmoyun/docs/testing/screenshots"
        import os
        os.makedirs(self.screenshot_dir, exist_ok=True)

    async def run(self):
        """运行探针"""
        print("\n" + "="*80)
        print("T4.7.1a-2a: CandidatePanel 打开机制排查")
        print("="*80)
        print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 监听 console 和 page errors
            console_errors = []
            page_errors = []

            def handle_console(msg):
                if msg.type == 'error':
                    console_errors.append(msg.text)

            def handle_pageerror(err):
                page_errors.append(str(err))

            page.on('console', handle_console)
            page.on('pageerror', handle_pageerror)

            try:
                # 1. 打开项目页面（需要带文件路径才能触发 Professional 视图）
                print("\n[1] 打开项目页面...")
                await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}/file/{TEST_FILE_PATH}")
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3)
                print(f"      URL: {page.url}")
                title = await page.title()
                print(f"      Title: {title}")

                # 2. 保存初始截图
                await page.screenshot(path=f"{self.screenshot_dir}/t471a2a_probe_initial.png", full_page=True)
                print(f"      ✅ 初始截图已保存")

                # 3. 探针：打印 DOM 状态
                print("\n[2] DOM 探针...")
                await self.probe_dom(page)

                # 4. 尝试正常 click
                print("\n[3] 尝试正常 click...")
                try:
                    tab = page.locator('[role="tab"]:has-text("候选稿")')
                    if await tab.count() > 0:
                        print(f"      找到 {await tab.count()} 个候选稿 tab")
                        await tab.first.click(timeout=5000)
                        await asyncio.sleep(2)
                        await page.screenshot(path=f"{self.screenshot_dir}/t471a2a_after_normal_click.png", full_page=True)
                        print(f"      ✅ 正常 click 后截图已保存")
                        await self.probe_after_click(page, "正常 click")
                    else:
                        print(f"      ❌ 未找到候选稿 tab")
                except Exception as e:
                    print(f"      ❌ 正常 click 失败: {str(e)[:100]}")

                # 5. 尝试 force click
                print("\n[4] 尝试 force click...")
                try:
                    tab = page.locator('[role="tab"]:has-text("候选稿")')
                    if await tab.count() > 0:
                        await tab.first.click(force=True, timeout=5000)
                        await asyncio.sleep(2)
                        await page.screenshot(path=f"{self.screenshot_dir}/t471a2a_after_force_click.png", full_page=True)
                        print(f"      ✅ force click 后截图已保存")
                        await self.probe_after_click(page, "force click")
                except Exception as e:
                    print(f"      ❌ force click 失败: {str(e)[:100]}")

                # 6. 尝试 JavaScript click
                print("\n[5] 尝试 JavaScript click...")
                try:
                    await page.evaluate(
                        """() => {
                            const tabs = document.querySelectorAll('[role="tab"]');
                            for (const tab of tabs) {
                                if (tab.textContent.includes('候选稿')) {
                                    console.log('JS click on:', tab.textContent);
                                    tab.click();
                                    break;
                                }
                            }
                        }"""
                    )
                    await asyncio.sleep(2)
                    await page.screenshot(path=f"{self.screenshot_dir}/t471a2a_after_js_click.png", full_page=True)
                    print(f"      ✅ JS click 后截图已保存")
                    await self.probe_after_click(page, "JS click")
                except Exception as e:
                    print(f"      ❌ JS click 失败: {str(e)[:100]}")

                # 7. 尝试直接访问候选稿 tab 所在页面
                print("\n[6] 尝试直接导航到候选稿模式...")
                try:
                    await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}/file/{TEST_FILE_PATH}?tab=candidate")
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(3)
                    await page.screenshot(path=f"{self.screenshot_dir}/t471a2a_after_nav_candidate.png", full_page=True)
                    print(f"      ✅ 直接导航后截图已保存")
                    await self.probe_after_click(page, "直接导航 ?tab=candidate")
                except Exception as e:
                    print(f"      ❌ 直接导航失败: {str(e)[:100]}")

                # 8. 打印 console errors 和 page errors
                print("\n[7] Console/Page Errors...")
                if console_errors:
                    print(f"      Console Errors ({len(console_errors)}):")
                    for err in console_errors[:5]:
                        print(f"        - {err[:200]}")
                else:
                    print(f"      ✅ 无 Console Errors")

                if page_errors:
                    print(f"      Page Errors ({len(page_errors)}):")
                    for err in page_errors[:5]:
                        print(f"        - {err[:200]}")
                else:
                    print(f"      ✅ 无 Page Errors")

                # 9. 检查网络请求
                print("\n[8] 检查 /api/candidates 请求...")
                candidate_requests = []
                candidate_responses = []

                def handle_response(response):
                    if '/api/candidates' in response.url:
                        candidate_requests.append({
                            'url': response.url,
                            'status': response.status
                        })

                page.on('response', handle_response)

                # 刷新页面触发请求
                await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}/file/{TEST_FILE_PATH}")
                await asyncio.sleep(3)

                if candidate_requests:
                    print(f"      捕获到 {len(candidate_requests)} 个 /api/candidates 请求:")
                    for req in candidate_requests:
                        print(f"        - {req['url']}: {req['status']}")
                else:
                    print(f"      ❌ 未捕获到 /api/candidates 请求")

                # 最终诊断
                print("\n" + "="*80)
                print("诊断结论")
                print("="*80)

                # 检查关键元素
                panel_count = await page.locator('.candidate-panel').count()
                card_count = await page.locator('.candidate-card').count()
                tab_count = await page.locator('[role="tab"]:has-text("候选稿")').count()

                print(f"  .candidate-panel 数量: {panel_count}")
                print(f"  .candidate-card 数量: {card_count}")
                print(f"  候选稿 tab 数量: {tab_count}")

                if tab_count == 0:
                    print(f"  归因: locator 错 - UI 中没有 [role='tab']:has-text('候选稿')")
                    self.results["diagnosis"] = "locator 错 - tab 不存在"
                elif panel_count == 0:
                    print(f"  归因: 点击无效 - tab 存在但 panel 未挂载")
                    self.results["diagnosis"] = "点击无效 - panel 未挂载"
                elif card_count == 0:
                    print(f"  归因: API 成功但 UI 不显示 - panel 存在但无数据")
                    self.results["diagnosis"] = "API 成功但 UI 不显示"
                else:
                    print(f"  归因: 其他原因")
                    self.results["diagnosis"] = "需进一步排查"

                self.results["panel_count"] = panel_count
                self.results["card_count"] = card_count
                self.results["tab_count"] = tab_count
                self.results["console_errors"] = console_errors
                self.results["page_errors"] = page_errors
                self.results["candidate_requests"] = candidate_requests

            except Exception as e:
                print(f"      ❌ 探针异常: {e}")
                self.results["error"] = str(e)

            finally:
                await browser.close()

        self.save_report()

    async def probe_dom(self, page):
        """探测 DOM 状态"""
        print(f"\n      --- DOM 探针 ---")

        # 打印 body 前 500 字符
        body_text = await page.locator('body').inner_text()
        print(f"      Body 文本前 500 字: {body_text[:500]}")

        # 打印所有 role=tab
        tabs = page.locator('[role="tab"]')
        tab_count = await tabs.count()
        print(f"      [role='tab'] 数量: {tab_count}")
        for i in range(min(tab_count, 15)):
            tab = tabs.nth(i)
            text = await tab.inner_text()
            cls = await tab.get_attribute('class')
            aria_selected = await tab.get_attribute('aria-selected')
            print(f"        [{i}] text='{text}' class='{cls}' aria-selected={aria_selected}")

        # 打印所有候选相关元素
        candidate_elements = page.locator(':has-text("候选")')
        try:
            cand_count = await candidate_elements.count()
            print(f"      包含'候选'的元素数量: {cand_count}")
            for i in range(min(cand_count, 5)):
                el = candidate_elements.nth(i)
                try:
                    outer = await el.evaluate('el => el.outerHTML.substring(0, 200)')
                    print(f"        [{i}]: {outer}")
                except:
                    pass
        except Exception as e:
            print(f"      包含'候选'的元素探测失败: {e}")

        # 检查 .candidate-panel
        panel_count = await page.locator('.candidate-panel').count()
        print(f"      .candidate-panel 数量: {panel_count}")

        # 检查 .btn-refresh
        refresh_count = await page.locator('.btn-refresh').count()
        print(f"      .btn-refresh 数量: {refresh_count}")

        # 检查 .candidate-card
        card_count = await page.locator('.candidate-card').count()
        print(f"      .candidate-card 数量: {card_count}")

        # 检查 right-panel
        right_panel = page.locator('.right-panel')
        rp_count = await right_panel.count()
        print(f"      .right-panel 数量: {rp_count}")
        if rp_count > 0:
            rp_html = await right_panel.first.evaluate('el => el.outerHTML.substring(0, 500)')
            print(f"      right-panel HTML: {rp_html}")

    async def probe_after_click(self, page, click_type):
        """点击后探测"""
        print(f"\n      --- {click_type} 后探测 ---")

        panel_count = await page.locator('.candidate-panel').count()
        card_count = await page.locator('.candidate-card').count()
        tab_count = await page.locator('[role="tab"]:has-text("候选稿")').count()

        print(f"      .candidate-panel: {panel_count}")
        print(f"      .candidate-card: {card_count}")
        print(f"      候选稿 tab: {tab_count}")

        # 检查 active tab
        active_tabs = page.locator('[role="tab"][aria-selected="true"]')
        active_count = await active_tabs.count()
        if active_count > 0:
            for i in range(active_count):
                text = await active_tabs.nth(i).inner_text()
                print(f"      Active tab [{i}]: {text}")

        # 检查是否有"刷新"文本
        refresh_elements = page.locator(':has-text("刷新")')
        try:
            print(f"      包含'刷新'的元素数量: {await refresh_elements.count()}")
        except:
            pass

        # 检查是否有"预览"文本
        preview_elements = page.locator(':has-text("预览")')
        try:
            print(f"      包含'预览'的元素数量: {await preview_elements.count()}")
        except:
            pass

    def save_report(self):
        """保存报告"""
        output_file = "d:/newmoyun/docs/testing/professional-candidate-flow-e2e-result-2026-06.md"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# T4.7.1a E2E 测试结果\n\n")
            f.write(f"**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            f.write("## T4.7.1a-2a：CandidatePanel 打开机制排查\n\n")
            f.write(f"**脚本**: `tests/test_candidate_panel_probe.py`\n\n")

            f.write("### 诊断结果\n\n")
            f.write(f"- **诊断结论**: {self.results.get('diagnosis', 'N/A')}\n")
            f.write(f"- **.candidate-panel 数量**: {self.results.get('panel_count', 'N/A')}\n")
            f.write(f"- **.candidate-card 数量**: {self.results.get('card_count', 'N/A')}\n")
            f.write(f"- **候选稿 tab 数量**: {self.results.get('tab_count', 'N/A')}\n\n")

            f.write("### Console/Page Errors\n\n")
            errors = self.results.get('console_errors', [])
            if errors:
                f.write(f"**Console Errors ({len(errors)}):**\n")
                for err in errors[:5]:
                    f.write(f"- `{err[:200]}`\n")
            else:
                f.write("✅ 无 Console Errors\n")

            page_errors = self.results.get('page_errors', [])
            if page_errors:
                f.write(f"**Page Errors ({len(page_errors)}):**\n")
                for err in page_errors[:5]:
                    f.write(f"- `{err[:200]}`\n")
            else:
                f.write("✅ 无 Page Errors\n\n")

            f.write("### /api/candidates 请求\n\n")
            reqs = self.results.get('candidate_requests', [])
            if reqs:
                for req in reqs:
                    f.write(f"- {req['url']}: {req['status']}\n")
            else:
                f.write("❌ 未捕获到 /api/candidates 请求\n\n")

            f.write("### 截图路径\n\n")
            f.write("- `docs/testing/screenshots/t471a2a_probe_initial.png`\n")
            f.write("- `docs/testing/screenshots/t471a2a_after_normal_click.png`\n")
            f.write("- `docs/testing/screenshots/t471a2a_after_force_click.png`\n")
            f.write("- `docs/testing/screenshots/t471a2a_after_js_click.png`\n")
            f.write("- `docs/testing/screenshots/t471a2a_after_nav_candidate.png`\n\n")

            f.write("### 归因分析\n\n")
            f.write(f"{self.results.get('diagnosis', 'N/A')}\n\n")

            f.write("### 结论\n\n")
            f.write(f"**T4.7.1a-2 状态**: ❌ FAIL（等待 CandidatePanel 打开问题解决后重测 preview/delete）\n")
            f.write(f"**T4.7.1a 整体状态**: ❌ FAIL（等待 adopt/conflict/SSE 验证）\n")

        print(f"\n✅ 报告已保存到: {output_file}")


if __name__ == "__main__":
    probe = CandidatePanelProbe()
    asyncio.run(probe.run())
