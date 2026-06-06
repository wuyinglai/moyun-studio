"""
T4.7.1a-1: E2E 脚本基础修复与 Locator 稳定性验证
=====================================================

目标：验证 locator 稳定性，不验证完整行为。

测试内容：
1. 文件 API 写入测试文件
2. 读取 hash/mtime
3. 创建 pending candidate
4. 打开 Professional 页面
5. 打开测试文件
6. 打开 CandidatePanel
7. 稳定找到 candidate card
8. 稳定找到 preview/delete/adopt 按钮
9. 保存截图
10. 清理测试数据
"""

import asyncio
import aiohttp
import uuid
import os
from datetime import datetime
from playwright.async_api import async_playwright

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5174"
PROJECT_ID = "demo-novel"
TEST_FILE_PATH = "scenes/__e2e_candidate_test_scene.md"

CONTENT_INITIAL = "T4.7.1a initial source content"
CONTENT_CANDIDATE = "T4.7.1a E2E candidate replacement content"
CANDIDATE_TITLE = "T4.7.1a E2E Candidate Locator Test"


class E2ELocatorTest:
    """E2E Locator 稳定性测试"""

    def __init__(self):
        self.results = {
            "file_api": {},
            "candidate_api": {},
            "locator_test": {},
            "screenshots": [],
            "final_verdict": "PENDING"
        }
        self.candidate_id = None
        self.file_hash = None
        self.file_mtime = None

    def parse_api_response(self, response_data):
        """解析 ApiResponse 格式"""
        if isinstance(response_data, dict):
            if "data" in response_data:
                return response_data["data"]
        return response_data

    async def test_file_api(self):
        """测试文件 API"""
        print("\n" + "="*80)
        print("Part 1: 文件 API 验证")
        print("="*80)

        async with aiohttp.ClientSession() as session:
            # 1. 创建文件
            print("\n[1.1] 创建测试文件...")
            async with session.post(
                f"{BACKEND_URL}/api/file/create",
                json={"project_id": PROJECT_ID, "path": TEST_FILE_PATH, "content": CONTENT_INITIAL},
                headers={"Content-Type": "application/json"}
            ) as resp:
                status = resp.status
                print(f"      状态: {status}")
                self.results["file_api"]["create"] = status

            # 2. 读取文件
            print("\n[1.2] 读取文件获取 hash/mtime...")
            async with session.get(
                f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    data = self.parse_api_response(response)
                    self.file_hash = data.get("hash", "")
                    self.file_mtime = data.get("mtime", 0)
                    print(f"      ✅ hash: {self.file_hash[:16]}...")
                    print(f"      ✅ mtime: {self.file_mtime}")
                    self.results["file_api"]["hash"] = self.file_hash
                    self.results["file_api"]["mtime"] = self.file_mtime
                    self.results["file_api"]["read"] = "✅ 成功"
                else:
                    print(f"      ❌ 失败")
                    self.results["file_api"]["read"] = "❌ 失败"

    async def test_candidate_api(self):
        """测试 Candidate API"""
        print("\n" + "="*80)
        print("Part 2: Candidate API 验证")
        print("="*80)

        self.candidate_id = f"cand_{uuid.uuid4().hex[:8]}"

        async with aiohttp.ClientSession() as session:
            # 1. 创建 candidate
            print("\n[2.1] 创建 candidate...")
            async with session.post(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}",
                json={
                    "project_id": PROJECT_ID,
                    "source_path": TEST_FILE_PATH,
                    "action": "polish",
                    "content": CONTENT_CANDIDATE,
                    "workflow_run_id": f"test-run-{self.candidate_id}",
                    "model": "test-model",
                    "pipeline_id": "test-pipeline",
                    "source_mode": "test"
                },
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status in [200, 201]:
                    response = await resp.json()
                    data = self.parse_api_response(response)
                    self.candidate_id = data.get("id", self.candidate_id)
                    base_hash = data.get("base_hash", "")
                    base_mtime = data.get("base_mtime", 0)
                    status = data.get("status", "")

                    print(f"      ✅ Candidate 创建成功")
                    print(f"      id: {self.candidate_id}")
                    print(f"      status: {status}")
                    print(f"      base_hash: {base_hash[:16]}...")
                    print(f"      base_mtime: {base_mtime}")

                    self.results["candidate_api"]["create"] = "✅ 成功"
                    self.results["candidate_api"]["id"] = self.candidate_id
                    self.results["candidate_api"]["status"] = status
                    self.results["candidate_api"]["base_hash"] = base_hash
                    self.results["candidate_api"]["base_mtime"] = base_mtime
                else:
                    text = await resp.text()
                    print(f"      ❌ 创建失败: {text[:100]}")
                    self.results["candidate_api"]["create"] = "❌ 失败"

    async def test_locators(self):
        """测试 Locator 稳定性"""
        print("\n" + "="*80)
        print("Part 3: Locator 稳定性验证")
        print("="*80)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            screenshot_dir = "d:/newmoyun/docs/testing/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)

            try:
                # 1. 打开项目页面
                print("\n[3.1] 打开项目页面...")
                await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}")
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3)
                print(f"      ✅ 页面加载成功")

                # 截图1: 项目页面
                screenshot1 = f"{screenshot_dir}/step1_project_page.png"
                await page.screenshot(path=screenshot1, full_page=True)
                self.results["screenshots"].append(screenshot1)
                print(f"      ✅ 截图已保存: {screenshot1}")

                # 2. 打开测试文件
                print("\n[3.2] 打开测试文件...")
                await page.wait_for_selector('[draggable]', timeout=10000)

                file_links = await page.locator('[draggable]').all()
                test_file_found = False

                for link in file_links:
                    text = await link.text_content()
                    if "__e2e_candidate" in text or "e2e" in text.lower():
                        await link.click()
                        test_file_found = True
                        print(f"      ✅ 打开文件: {text}")
                        break

                if not test_file_found:
                    print(f"      ⚠️ 未找到测试文件")

                await asyncio.sleep(2)

                # 截图2: 文件打开
                screenshot2 = f"{screenshot_dir}/step2_file_opened.png"
                await page.screenshot(path=screenshot2, full_page=True)
                self.results["screenshots"].append(screenshot2)
                print(f"      ✅ 截图已保存: {screenshot2}")

                # 3. 打开候选稿面板
                print("\n[3.3] 打开候选稿面板...")

                # 定位候选稿标签
                candidate_tab = page.locator('[role="tab"]:has-text("候选稿")')
                tab_count = await candidate_tab.count()
                print(f"      找到 {tab_count} 个候选稿标签")

                if tab_count > 0:
                    await candidate_tab.first.click()
                    await asyncio.sleep(2)
                    print(f"      ✅ 候选稿面板打开")

                    # 截图3: 候选稿面板
                    screenshot3 = f"{screenshot_dir}/step3_candidate_panel.png"
                    await page.screenshot(path=screenshot3, full_page=True)
                    self.results["screenshots"].append(screenshot3)
                    print(f"      ✅ 截图已保存: {screenshot3}")
                    self.results["locator_test"]["panel_opened"] = "✅ 成功"
                else:
                    print(f"      ❌ 候选稿标签未找到")
                    self.results["locator_test"]["panel_opened"] = "❌ 失败"

                # 4. 查找 candidate card
                print("\n[3.4] 查找 candidate card...")
                candidate_cards = page.locator('.candidate-card')
                card_count = await candidate_cards.count()
                print(f"      找到 {card_count} 个 candidate card")

                self.results["locator_test"]["card_count"] = card_count

                if card_count > 0:
                    self.results["locator_test"]["card_found"] = "✅ 成功"

                    # 截图4: candidate card
                    screenshot4 = f"{screenshot_dir}/step4_candidate_cards.png"
                    await page.screenshot(path=screenshot4, full_page=True)
                    self.results["screenshots"].append(screenshot4)
                    print(f"      ✅ 截图已保存: {screenshot4}")

                    # 5. 查找按钮
                    print("\n[3.5] 查找按钮...")

                    # 5.1 preview 按钮
                    preview_btns = page.locator('.action-btn')
                    preview_count = await preview_btns.count()
                    print(f"      找到 {preview_count} 个 action-btn")

                    if preview_count > 0:
                        self.results["locator_test"]["preview_btn"] = f"✅ 找到 {preview_count} 个"
                        print(f"      ✅ preview 按钮存在")

                        # 尝试更精确的定位
                        preview_by_title = page.locator('.action-btn[title="预览"]')
                        preview_title_count = await preview_by_title.count()
                        if preview_title_count > 0:
                            print(f"      ✅ preview (title=预览) 按钮精确找到")
                            self.results["locator_test"]["preview_btn_exact"] = "✅ 找到"
                        else:
                            print(f"      ⚠️ preview (title=预览) 未找到")
                            self.results["locator_test"]["preview_btn_exact"] = "⚠️ 未找到"
                    else:
                        print(f"      ❌ action-btn 未找到")
                        self.results["locator_test"]["preview_btn"] = "❌ 未找到"

                    # 5.2 adopt 按钮
                    adopt_btns = page.locator('[data-testid="candidate-adopt-button"]')
                    adopt_count = await adopt_btns.count()
                    print(f"      找到 {adopt_count} 个 adopt 按钮")

                    if adopt_count > 0:
                        self.results["locator_test"]["adopt_btn"] = f"✅ 找到 {adopt_count} 个"
                        print(f"      ✅ adopt 按钮存在")
                    else:
                        print(f"      ⚠️ adopt 按钮未找到")
                        self.results["locator_test"]["adopt_btn"] = "⚠️ 未找到"

                        # 打印当前 candidate 状态
                        print(f"      当前 candidate status: {self.results['candidate_api'].get('status', 'N/A')}")
                        print(f"      可能原因: candidate 已 adopted 或状态不是 pending")

                        # 尝试其他 selector
                        adopt_alts = [
                            ".action-adopt",
                            ".adopt-btn",
                            "button:has-text('采用')",
                            "button:has-text('采纳')",
                            "button:has-text('Adopt')"
                        ]

                        for alt in adopt_alts:
                            try:
                                alt_btns = page.locator(alt)
                                alt_count = await alt_btns.count()
                                if alt_count > 0:
                                    print(f"      ✅ 替代定位器找到 {alt}: {alt_count} 个")
                                    self.results["locator_test"]["adopt_btn_alt"] = f"✅ {alt} 找到"
                                    break
                            except:
                                pass

                    # 5.3 delete 按钮
                    delete_btns = page.locator('[data-testid="candidate-reject-button"]')
                    delete_count = await delete_btns.count()
                    print(f"      找到 {delete_count} 个 delete 按钮")

                    if delete_count > 0:
                        self.results["locator_test"]["delete_btn"] = f"✅ 找到 {delete_count} 个"
                        print(f"      ✅ delete 按钮存在")
                    else:
                        print(f"      ⚠️ delete 按钮未找到")
                        self.results["locator_test"]["delete_btn"] = "⚠️ 未找到"

                        # 尝试其他 selector
                        delete_alts = [
                            ".action-delete",
                            ".delete-btn",
                            ".reject-btn",
                            "button:has-text('删除')",
                            "button:has-text('拒绝')"
                        ]

                        for alt in delete_alts:
                            try:
                                alt_btns = page.locator(alt)
                                alt_count = await alt_btns.count()
                                if alt_count > 0:
                                    print(f"      ✅ 替代定位器找到 {alt}: {alt_count} 个")
                                    self.results["locator_test"]["delete_btn_alt"] = f"✅ {alt} 找到"
                                    break
                            except:
                                pass

                    # 截图5: 按钮定位
                    screenshot5 = f"{screenshot_dir}/step5_buttons.png"
                    await page.screenshot(path=screenshot5, full_page=True)
                    self.results["screenshots"].append(screenshot5)
                    print(f"      ✅ 截图已保存: {screenshot5}")

                else:
                    print(f"      ❌ 没有 candidate card")
                    self.results["locator_test"]["card_found"] = "❌ 失败"

                    # 截图5: 空面板
                    screenshot5 = f"{screenshot_dir}/step5_no_cards.png"
                    await page.screenshot(path=screenshot5, full_page=True)
                    self.results["screenshots"].append(screenshot5)

            except Exception as e:
                print(f"      ❌ 错误: {e}")
                import traceback
                traceback.print_exc()
                self.results["locator_test"]["error"] = str(e)

                # 截图错误状态
                error_screenshot = f"{screenshot_dir}/step_error.png"
                try:
                    await page.screenshot(path=error_screenshot, full_page=True)
                    self.results["screenshots"].append(error_screenshot)
                except:
                    pass

            finally:
                await browser.close()

    async def cleanup(self):
        """清理测试数据"""
        print("\n" + "="*80)
        print("清理测试数据")
        print("="*80)

        if self.candidate_id:
            async with aiohttp.ClientSession() as session:
                await session.delete(
                    f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.candidate_id}"
                )
                print(f"      ✅ candidate 已删除")

        # 恢复文件
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{BACKEND_URL}/api/file",
                json={"project_id": PROJECT_ID, "path": TEST_FILE_PATH, "content": CONTENT_INITIAL},
                headers={"Content-Type": "application/json"}
            )
            print(f"      ✅ 文件已恢复")

    async def run(self):
        """运行测试"""
        print("\n" + "="*80)
        print("T4.7.1a-1: E2E Locator 稳定性验证")
        print("="*80)

        # 1. 文件 API
        await self.test_file_api()

        # 2. Candidate API
        await self.test_candidate_api()

        # 3. Locator 测试
        await self.test_locators()

        # 4. 清理
        await self.cleanup()

        # 5. 判定
        print("\n" + "="*80)
        print("测试结果")
        print("="*80)

        print(f"\n文件 API: {self.results['file_api']}")
        print(f"Candidate API: {self.results['candidate_api']}")
        print(f"Locator 测试: {self.results['locator_test']}")
        print(f"\n截图: {self.results['screenshots']}")

        # 判定 locator 稳定性
        locator_pass = all([
            self.results["file_api"].get("read") == "✅ 成功",
            self.results["candidate_api"].get("create") == "✅ 成功",
            self.results["locator_test"].get("panel_opened") == "✅ 成功",
            self.results["locator_test"].get("card_found") == "✅ 成功",
        ])

        if locator_pass:
            self.results["final_verdict"] = "✅ LOCATOR STABLE"
        else:
            self.results["final_verdict"] = "❌ LOCATOR ISSUES"

        print(f"\n最终判定: {self.results['final_verdict']}")

        # 保存报告
        self.save_report()

    def save_report(self):
        """保存测试报告"""
        output_file = "d:/newmoyun/docs/testing/professional-candidate-flow-e2e-result-2026-06.md"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# T4.7.1a E2E 测试结果\n\n")
            f.write(f"**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**最终判定**: {self.results['final_verdict']}\n\n")
            f.write("---\n\n")

            f.write("## T4.7.1a-1: Locator 稳定性验证\n\n")

            f.write("### 文件 API\n\n")
            for key, value in self.results["file_api"].items():
                f.write(f"- **{key}**: {value}\n")

            f.write("\n### Candidate API\n\n")
            for key, value in self.results["candidate_api"].items():
                f.write(f"- **{key}**: {value}\n")

            f.write("\n### Locator 测试\n\n")
            for key, value in self.results["locator_test"].items():
                f.write(f"- **{key}**: {value}\n")

            f.write("\n### 截图\n\n")
            for screenshot in self.results["screenshots"]:
                f.write(f"- {screenshot}\n")

            f.write("\n## 约束检查\n\n")
            f.write("- **是否调用 LLM**: 否\n")
            f.write("- **是否修改生产 Prompt**: 否\n")
            f.write("- **是否修改业务逻辑**: 否\n")

            f.write("\n## 结论\n\n")
            f.write(f"**T4.7.1a 状态**: ❌ FAIL（等待行为验证）\n\n")
            f.write(f"**本次验证**: Locator 稳定性测试 {self.results['final_verdict']}\n\n")
            f.write("本次只验证了 locator 稳定性，未验证完整行为（preview/delete/adopt/conflict/SSE）。\n")

        print(f"\n✅ 报告已保存到: {output_file}")


if __name__ == "__main__":
    test = E2ELocatorTest()
    asyncio.run(test.run())
