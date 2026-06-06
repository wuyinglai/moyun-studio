"""
T4.7.1a-2: Preview 与 Delete 行为验证（修复版）
================================================

目标：验证 preview 和 delete/reject 两个 UI 行为。
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
CONTENT_PREVIEW_CANDIDATE = "T4.7.1a E2E candidate preview content for this test"
CONTENT_DELETE_CANDIDATE = "T4.7.1a E2E candidate delete content for this test"
TITLE_PREVIEW = "T4.7.1a E2E Candidate Preview Test"
TITLE_DELETE = "T4.7.1a E2E Candidate Delete Test"


class PreviewDeleteTest:
    """Preview 与 Delete 行为测试"""

    def __init__(self):
        self.results = {
            "preview_test": {},
            "delete_test": {},
            "final_verdict": "PENDING"
        }
        self.preview_candidate_id = None
        self.delete_candidate_id = None
        self.file_hash = None
        self.file_mtime = None

    def parse_api_response(self, response_data):
        if isinstance(response_data, dict):
            if "data" in response_data:
                return response_data["data"]
        return response_data

    async def cleanup_old_candidates(self):
        """清理旧的 test candidates"""
        print("\n清理旧 candidates...")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}"
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    data = self.parse_api_response(response)
                    candidates = data.get("candidates", [])
                    print(f"      找到 {len(candidates)} 个候选稿")

                    for c in candidates:
                        # 删除所有与测试文件相关的 candidates
                        if c.get("source_path") == TEST_FILE_PATH or "test" in c.get("workflow_run_id", "") or c.get("action") == "polish":
                            await session.delete(
                                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{c.get('id')}"
                            )
                            print(f"      删除: {c.get('id')}")

    async def setup(self):
        """设置测试环境"""
        print("\n" + "="*80)
        print("设置测试环境")
        print("="*80)

        # 先清理旧 candidates
        await self.cleanup_old_candidates()

        async with aiohttp.ClientSession() as session:
            # 创建/恢复文件
            await session.post(
                f"{BACKEND_URL}/api/file/create",
                json={"project_id": PROJECT_ID, "path": TEST_FILE_PATH, "content": CONTENT_INITIAL},
                headers={"Content-Type": "application/json"}
            )

            # 读取文件
            async with session.get(
                f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    data = self.parse_api_response(response)
                    self.file_hash = data.get("hash", "")
                    self.file_mtime = data.get("mtime", 0)
                    print(f"      ✅ hash: {self.file_hash[:16]}...")

    async def create_preview_candidate(self):
        """创建 preview 测试 candidate"""
        print("\n创建 Preview 测试 Candidate...")

        self.preview_candidate_id = f"cand_{uuid.uuid4().hex[:8]}"

        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}",
                json={
                    "project_id": PROJECT_ID,
                    "source_path": TEST_FILE_PATH,
                    "action": "polish",
                    "content": CONTENT_PREVIEW_CANDIDATE,
                    "workflow_run_id": f"test-run-{self.preview_candidate_id}",
                    "model": "test-model",
                    "pipeline_id": "test-pipeline",
                    "source_mode": "test"
                },
                headers={"Content-Type": "application/json"}
            )

            async with session.get(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.preview_candidate_id}"
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    data = self.parse_api_response(response)
                    candidate = data.get("candidate", {})
                    print(f"      ✅ Preview Candidate: {self.preview_candidate_id}")
                    print(f"         status: {candidate.get('status')}")
                    self.results["preview_test"]["candidate_id"] = self.preview_candidate_id

    async def create_delete_candidate(self):
        """创建 delete 测试 candidate"""
        print("\n创建 Delete 测试 Candidate...")

        self.delete_candidate_id = f"cand_{uuid.uuid4().hex[:8]}"

        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}",
                json={
                    "project_id": PROJECT_ID,
                    "source_path": TEST_FILE_PATH,
                    "action": "polish",
                    "content": CONTENT_DELETE_CANDIDATE,
                    "workflow_run_id": f"test-run-{self.delete_candidate_id}",
                    "model": "test-model",
                    "pipeline_id": "test-pipeline",
                    "source_mode": "test"
                },
                headers={"Content-Type": "application/json"}
            )

            async with session.get(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.delete_candidate_id}"
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    data = self.parse_api_response(response)
                    candidate = data.get("candidate", {})
                    print(f"      ✅ Delete Candidate: {self.delete_candidate_id}")
                    print(f"         status: {candidate.get('status')}")
                    self.results["delete_test"]["candidate_id"] = self.delete_candidate_id

    async def test_preview_behavior(self):
        """测试 Preview 行为"""
        print("\n" + "="*80)
        print("Test 1: Preview 行为验证")
        print("="*80)

        screenshot_dir = "d:/newmoyun/docs/testing/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # 1. 打开项目页面
                print("\n[1.1] 打开项目页面...")
                await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}")
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3)
                print(f"      ✅ 页面加载成功")

                # 2. 打开候选稿面板
                print("\n[1.2] 打开候选稿面板...")
                candidate_tab = page.locator('[role="tab"]:has-text("候选稿")')
                await candidate_tab.first.click()
                await asyncio.sleep(2)
                print(f"      ✅ 候选稿面板打开")

                # 3. 刷新列表
                print("\n[1.3] 刷新候选稿列表...")
                refresh_btn = page.locator('.btn-refresh')
                await refresh_btn.click()
                await asyncio.sleep(1)
                print(f"      ✅ 刷新完成")

                # 4. 定位到测试文件对应的 candidate card
                print("\n[1.4] 定位 Preview Candidate...")
                # 由于 preview 和 delete candidate 都用同一文件，只能按创建顺序：
                # preview 先创建，所以找第一个匹配文件的 card
                preview_card = page.locator('.candidate-card', has=page.locator('text=__e2e_candidate_test_scene.md'))
                preview_count = await preview_card.count()
                print(f"      找到 {preview_count} 个匹配测试文件的 card")

                if preview_count > 0:
                    # 5. 点击该 card 内的 preview 按钮（用 first 获取最先创建的）
                    print("\n[1.5] 点击 Preview 按钮...")
                    preview_btn = preview_card.first.locator('.action-btn[title="预览"]')
                    await preview_btn.click()
                    await asyncio.sleep(1)
                    print(f"      ✅ Preview 按钮点击成功")

                    # 6. 检查预览弹窗
                    print("\n[1.6] 检查预览弹窗...")
                    preview_modal = page.locator('.preview-modal')
                    modal_count = await preview_modal.count()

                    if modal_count > 0:
                        print(f"      ✅ 预览弹窗打开")

                        screenshot1 = f"{screenshot_dir}/t471a2_preview_modal.png"
                        await page.screenshot(path=screenshot1, full_page=True)
                        print(f"      ✅ 截图已保存")

                        preview_textarea = page.locator('.preview-textarea')
                        if await preview_textarea.count() > 0:
                            content = await preview_textarea.input_value()
                            print(f"      预览内容长度: {len(content)}")
                            print(f"      内容前 50 字: {content[:50]}")

                            # 检查是否包含 preview candidate 内容
                            if "preview content for this test" in content:
                                print(f"      ✅ 预览内容正确")
                                self.results["preview_test"]["content_visible"] = True
                                self.results["preview_test"]["content_match"] = "✅ 正确"
                            else:
                                print(f"      ⚠️ 预览内容不是预期的 preview candidate")
                                self.results["preview_test"]["content_match"] = "⚠️ 不匹配"

                        self.results["preview_test"]["modal_opened"] = True

                        # 7. 关闭预览
                        print("\n[1.7] 关闭预览...")
                        close_btn = page.locator('.preview-modal .btn-close')
                        await close_btn.click()
                        await asyncio.sleep(1)
                        print(f"      ✅ 预览已关闭")
                        self.results["preview_test"]["modal_closed"] = True
                    else:
                        print(f"      ❌ 预览弹窗未打开")
                        self.results["preview_test"]["modal_opened"] = False
                else:
                    print(f"      ❌ 没有 preview 按钮")

                # 8. 验证正文未被覆盖
                print("\n[1.8] 验证正文未被覆盖...")

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
                    ) as resp:
                        if resp.status == 200:
                            response = await resp.json()
                            data = self.parse_api_response(response)
                            file_content = data.get("content", "")

                            if CONTENT_INITIAL in file_content:
                                print(f"      ✅ 正文未被覆盖")
                                self.results["preview_test"]["content_unchanged"] = True
                            else:
                                print(f"      ❌ 正文被意外覆盖！")
                                self.results["preview_test"]["content_unchanged"] = False

            except Exception as e:
                print(f"      ❌ 错误: {e}")
                self.results["preview_test"]["error"] = str(e)

            finally:
                await browser.close()

        if self.results["preview_test"].get("modal_opened") and \
           self.results["preview_test"].get("content_unchanged"):
            self.results["preview_test"]["result"] = "✅ PASS"
        else:
            self.results["preview_test"]["result"] = "❌ FAIL"

    async def test_delete_behavior(self):
        """测试 Delete 行为"""
        print("\n" + "="*80)
        print("Test 2: Delete 行为验证")
        print("="*80)

        screenshot_dir = "d:/newmoyun/docs/testing/screenshots"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # 1. 打开项目页面
                print("\n[2.1] 打开项目页面...")
                await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}")
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3)
                print(f"      ✅ 页面加载成功")

                # 2. 打开候选稿面板
                print("\n[2.2] 打开候选稿面板...")
                candidate_tab = page.locator('[role="tab"]:has-text("候选稿")')
                await candidate_tab.first.click()
                await asyncio.sleep(2)

                # 3. 刷新列表
                print("\n[2.3] 刷新候选稿列表...")
                refresh_btn = page.locator('.btn-refresh')
                await refresh_btn.click()
                await asyncio.sleep(1)

                # 4. 定位到测试文件对应的 candidate card（找最后一个，因为 delete 后创建）
                print("\n[2.4] 定位 Delete Candidate...")
                delete_card = page.locator('.candidate-card', has=page.locator('text=__e2e_candidate_test_scene.md'))
                delete_card_count = await delete_card.count()
                print(f"      找到 {delete_card_count} 个匹配测试文件的 card")

                if delete_card_count > 0:
                    # 5. 记录删除前数量
                    before_cards = page.locator('.candidate-card')
                    before_count = await before_cards.count()
                    print(f"      删除前候选稿数量: {before_count}")

                    # 6. 点击该 card 的 delete 按钮（用 last 获取最后创建的）
                    print("\n[2.5] 点击 Delete 按钮...")
                    delete_btn = delete_card.last.locator('[data-testid="candidate-reject-button"]')
                    await delete_btn.click()
                    await asyncio.sleep(1)
                    print(f"      ✅ Delete 按钮点击成功")

                    # 7. 刷新列表检查
                    print("\n[2.6] 检查 delete 结果...")
                    await refresh_btn.click()
                    await asyncio.sleep(1)

                    after_cards = page.locator('.candidate-card')
                    after_count = await after_cards.count()
                    print(f"      删除后候选稿数量: {after_count}")

                    screenshot2 = f"{screenshot_dir}/t471a2_delete_after.png"
                    await page.screenshot(path=screenshot2, full_page=True)
                    print(f"      ✅ 截图已保存")

                    self.results["delete_test"]["ui_count_before"] = before_count
                    self.results["delete_test"]["ui_count_after"] = after_count

                    # 8. API 复核
                    print("\n[2.7] 后端 API 复核...")

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.delete_candidate_id}"
                        ) as resp:
                            if resp.status == 404:
                                print(f"      ✅ API 返回 404（candidate 已删除）")
                                self.results["delete_test"]["api_deleted"] = True
                            else:
                                print(f"      ❌ API 返回: {resp.status}")
                                self.results["delete_test"]["api_deleted"] = False

                    # 9. 验证源文件未被影响
                    print("\n[2.8] 验证源文件未被影响...")

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
                        ) as resp:
                            if resp.status == 200:
                                response = await resp.json()
                                data = self.parse_api_response(response)
                                file_content = data.get("content", "")

                                if CONTENT_INITIAL in file_content:
                                    print(f"      ✅ 源文件未被影响")
                                    self.results["delete_test"]["file_unchanged"] = True
                                else:
                                    print(f"      ❌ 源文件被意外修改！")
                                    self.results["delete_test"]["file_unchanged"] = False
                else:
                    print(f"      ❌ 未找到 delete candidate card")

            except Exception as e:
                print(f"      ❌ 错误: {e}")
                self.results["delete_test"]["error"] = str(e)

            finally:
                await browser.close()

        if self.results["delete_test"].get("api_deleted") and \
           self.results["delete_test"].get("file_unchanged"):
            self.results["delete_test"]["result"] = "✅ PASS"
        else:
            self.results["delete_test"]["result"] = "❌ FAIL"

    async def cleanup(self):
        """清理测试数据"""
        print("\n" + "="*80)
        print("清理测试数据")
        print("="*80)

        if self.preview_candidate_id:
            async with aiohttp.ClientSession() as session:
                await session.delete(
                    f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.preview_candidate_id}"
                )
                print(f"      ✅ Preview candidate 已删除")

        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{BACKEND_URL}/api/file",
                json={"project_id": PROJECT_ID, "path": TEST_FILE_PATH, "content": CONTENT_INITIAL},
                headers={"Content-Type": "application/json"}
            )
            print(f"      ✅ 文件已恢复")

        self.results["cleanup"] = "✅ 完成"

    async def run(self):
        """运行测试"""
        print("\n" + "="*80)
        print("T4.7.1a-2: Preview 与 Delete 行为验证")
        print("="*80)

        await self.setup()
        await self.create_preview_candidate()
        await self.create_delete_candidate()
        await self.test_preview_behavior()
        await self.test_delete_behavior()
        await self.cleanup()

        print("\n" + "="*80)
        print("测试结果")
        print("="*80)

        print(f"\nPreview Test: {self.results['preview_test']}")
        print(f"Delete Test: {self.results['delete_test']}")

        preview_pass = self.results["preview_test"].get("result", "").startswith("✅")
        delete_pass = self.results["delete_test"].get("result", "").startswith("✅")

        if preview_pass and delete_pass:
            self.results["final_verdict"] = "✅ PASS"
        else:
            self.results["final_verdict"] = "❌ FAIL"

        print(f"\n最终判定: {self.results['final_verdict']}")

        self.save_report()

    def save_report(self):
        """保存测试报告"""
        output_file = "d:/newmoyun/docs/testing/professional-candidate-flow-e2e-result-2026-06.md"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# T4.7.1a E2E 测试结果\n\n")
            f.write(f"**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**最终判定**: {self.results['final_verdict']}\n\n")
            f.write("---\n\n")

            f.write("## T4.7.1a-2: Preview 与 Delete 行为验证\n\n")

            f.write("### Preview 测试\n\n")
            for key, value in self.results["preview_test"].items():
                f.write(f"- **{key}**: {value}\n")

            f.write("\n### Delete 测试\n\n")
            for key, value in self.results["delete_test"].items():
                f.write(f"- **{key}**: {value}\n")

            f.write("\n### 截图\n\n")
            f.write("- `docs/testing/screenshots/t471a2_preview_modal.png`\n")
            f.write("- `docs/testing/screenshots/t471a2_delete_after.png`\n")

            f.write("\n## 约束检查\n\n")
            f.write("- **是否调用 LLM**: 否\n")
            f.write("- **是否修改生产 Prompt**: 否\n")
            f.write("- **是否修改业务逻辑**: 否\n")
            f.write("- **是否测试 adopt**: 否\n")
            f.write("- **是否测试 conflict**: 否\n")
            f.write("- **是否测试 SSE**: 否\n")

            f.write("\n## 结论\n\n")
            f.write(f"**T4.7.1a-2 判定**: {self.results['final_verdict']}\n\n")
            f.write(f"**T4.7.1a 整体状态**: ❌ FAIL（等待 adopt/conflict/SSE 验证）\n")

        print(f"\n✅ 报告已保存到: {output_file}")


if __name__ == "__main__":
    test = PreviewDeleteTest()
    asyncio.run(test.run())
