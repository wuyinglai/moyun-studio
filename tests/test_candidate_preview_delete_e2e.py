"""
T4.7.1a-2: Preview 与 Delete 行为验证（简化版 - 无清理）
==================================================

目标：验证 preview 和 delete/reject 两个 UI 行为。
关键：不清理旧数据，直接用全新的唯一文件路径。
"""

import asyncio
import aiohttp
import uuid
import os
from datetime import datetime
from playwright.async_api import async_playwright

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
PROJECT_ID = "demo-novel"

# 生成唯一的测试文件路径（避免与旧数据冲突）
RUN_ID = uuid.uuid4().hex[:8]
PREVIEW_FILE_PATH = f"scenes/__e2e_preview_{RUN_ID}.md"
DELETE_FILE_PATH = f"scenes/__e2e_delete_{RUN_ID}.md"

# 初始正文
PREVIEW_INITIAL = "T4.7.1a preview initial source content"
DELETE_INITIAL = "T4.7.1a delete initial source content"

# Candidate 内容（包含唯一标记）
PREVIEW_CANDIDATE_CONTENT = f"T4.7.1a E2E candidate preview content UNIQUE_PREVIEW_{RUN_ID}"
DELETE_CANDIDATE_CONTENT = f"T4.7.1a E2E candidate delete content UNIQUE_DELETE_{RUN_ID}"


class PreviewDeleteTestSimple:
    """Preview 与 Delete 行为测试（简化版）"""

    def __init__(self):
        self.results = {
            "preview_test": {},
            "delete_test": {},
            "final_verdict": "PENDING"
        }
        self.preview_candidate_id = None
        self.delete_candidate_id = None

    def parse_api_response(self, response_data):
        if isinstance(response_data, dict):
            if "data" in response_data:
                return response_data["data"]
        return response_data

    async def create_preview_candidate(self):
        """创建 preview 测试 candidate"""
        print("\n" + "="*80)
        print("创建 Preview Candidate")
        print("="*80)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}",
                json={
                    "project_id": PROJECT_ID,
                    "source_path": PREVIEW_FILE_PATH,
                    "action": "polish",
                    "content": PREVIEW_CANDIDATE_CONTENT,
                    "workflow_run_id": f"T471A2-preview-{RUN_ID}",
                    "model": "test-model",
                    "pipeline_id": "test-pipeline",
                    "source_mode": "test"
                },
                headers={"Content-Type": "application/json"}
            ) as resp:
                print(f"      POST 响应状态: {resp.status}")
                if resp.status == 200:
                    response = await resp.json()
                    candidate = self.parse_api_response(response)
                    if isinstance(candidate, dict) and "id" in candidate:
                        self.preview_candidate_id = candidate["id"]
                        print(f"      ✅ Preview Candidate ID: {self.preview_candidate_id}")
                        print(f"         status: {candidate.get('status')}")
                        print(f"         source_path: {candidate.get('source_path')}")
                        self.results["preview_test"]["candidate_id"] = self.preview_candidate_id
                        self.results["preview_test"]["source_path"] = PREVIEW_FILE_PATH
                        self.results["preview_test"]["unique_marker"] = f"UNIQUE_PREVIEW_{RUN_ID}"
                        return True

        print(f"      ❌ POST 失败")
        return False

    async def create_delete_candidate(self):
        """创建 delete 测试 candidate"""
        print("\n" + "="*80)
        print("创建 Delete Candidate")
        print("="*80)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/candidates/{PROJECT_ID}",
                json={
                    "project_id": PROJECT_ID,
                    "source_path": DELETE_FILE_PATH,
                    "action": "polish",
                    "content": DELETE_CANDIDATE_CONTENT,
                    "workflow_run_id": f"T471A2-delete-{RUN_ID}",
                    "model": "test-model",
                    "pipeline_id": "test-pipeline",
                    "source_mode": "test"
                },
                headers={"Content-Type": "application/json"}
            ) as resp:
                print(f"      POST 响应状态: {resp.status}")
                if resp.status == 200:
                    response = await resp.json()
                    candidate = self.parse_api_response(response)
                    if isinstance(candidate, dict) and "id" in candidate:
                        self.delete_candidate_id = candidate["id"]
                        print(f"      ✅ Delete Candidate ID: {self.delete_candidate_id}")
                        print(f"         status: {candidate.get('status')}")
                        print(f"         source_path: {candidate.get('source_path')}")
                        self.results["delete_test"]["candidate_id"] = self.delete_candidate_id
                        self.results["delete_test"]["source_path"] = DELETE_FILE_PATH
                        self.results["delete_test"]["unique_marker"] = f"UNIQUE_DELETE_{RUN_ID}"
                        return True

        print(f"      ❌ POST 失败")
        return False

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
                try:
                    await candidate_tab.first.click(timeout=15000)
                except Exception:
                    print("      尝试 JavaScript 点击...")
                    await page.evaluate(
                        "() => { const tabs = document.querySelectorAll('[role=\"tab\"]'); "
                        "for (const tab of tabs) { if (tab.textContent.includes('候选稿')) { tab.click(); break; } } }"
                    )
                # 等待 panel 出现
                await asyncio.sleep(5)
                # 检查 panel 是否可见
                panel = page.locator('.candidate-panel')
                if await panel.count() > 0:
                    print(f"      ✅ 候选稿面板已打开")
                else:
                    print(f"      ⚠️ Panel 未找到但继续...")

                # 3. 刷新列表
                print("\n[1.3] 刷新候选稿列表...")
                # 尝试多种刷新按钮选择器
                refresh_btn = page.locator('.btn-refresh')
                if await refresh_btn.count() == 0:
                    refresh_btn = page.locator('button:has-text("刷新")')
                if await refresh_btn.count() == 0:
                    refresh_btn = page.locator('[aria-label="刷新"]')
                await refresh_btn.first.click(timeout=15000)
                await asyncio.sleep(2)
                print(f"      ✅ 刷新完成")

                # 4. 定位到 preview 文件对应的 candidate card
                print("\n[1.4] 定位 Preview Candidate...")
                preview_card = page.locator(
                    '.candidate-card',
                    has=page.locator(f'text={PREVIEW_FILE_PATH}')
                )
                preview_card_count = await preview_card.count()
                print(f"      找到 {preview_card_count} 个匹配 '{PREVIEW_FILE_PATH}' 的 card")

                if preview_card_count == 0:
                    print(f"      ❌ 未找到 preview candidate card")
                    self.results["preview_test"]["card_found"] = False
                    self.results["preview_test"]["result"] = "❌ FAIL"
                    return

                self.results["preview_test"]["card_found"] = True

                # 4b. 截图 preview card
                card_screenshot = f"{screenshot_dir}/t471a2_preview_specific_card.png"
                await preview_card.first.screenshot(path=card_screenshot)
                print(f"      ✅ Preview card 截图已保存")

                # 5. 点击该 card 的 preview 按钮
                print("\n[1.5] 点击 Preview 按钮...")
                preview_btn = preview_card.first.locator('.action-btn[title="预览"]')
                await preview_btn.click(timeout=15000)
                await asyncio.sleep(1)
                print(f"      ✅ Preview 按钮点击成功")

                # 6. 检查预览弹窗
                print("\n[1.6] 检查预览弹窗...")
                preview_modal = page.locator('.preview-modal')
                modal_count = await preview_modal.count()

                if modal_count == 0:
                    print(f"      ❌ 预览弹窗未打开")
                    self.results["preview_test"]["modal_opened"] = False
                    self.results["preview_test"]["result"] = "❌ FAIL"
                    return

                print(f"      ✅ 预览弹窗打开")

                # 6b. 截图预览弹窗内容
                modal_screenshot = f"{screenshot_dir}/t471a2_preview_modal_unique.png"
                await preview_modal.screenshot(path=modal_screenshot)
                print(f"      ✅ 预览弹窗截图已保存")

                # 7. 检查预览内容是否包含唯一标记
                print("\n[1.7] 验证预览内容...")
                preview_textarea = page.locator('.preview-textarea')
                if await preview_textarea.count() > 0:
                    content = await preview_textarea.input_value()
                    print(f"      预览内容长度: {len(content)}")
                    print(f"      内容前 80 字: {content[:80]}")

                    marker = f"UNIQUE_PREVIEW_{RUN_ID}"
                    has_preview_marker = marker in content
                    delete_marker = f"UNIQUE_DELETE_{RUN_ID}"
                    has_delete_marker = delete_marker in content

                    if has_preview_marker:
                        print(f"      ✅ 包含 preview 唯一标记: {marker}")
                        self.results["preview_test"]["has_preview_marker"] = True
                    else:
                        print(f"      ❌ 不包含 preview 唯一标记")
                        self.results["preview_test"]["has_preview_marker"] = False

                    if has_delete_marker:
                        print(f"      ❌ 错误：包含 delete 标记（应只显示 preview 内容）")
                        self.results["preview_test"]["has_delete_marker"] = True
                    else:
                        print(f"      ✅ 不包含 delete 标记")
                        self.results["preview_test"]["has_delete_marker"] = False

                    self.results["preview_test"]["modal_content"] = content[:100]
                else:
                    print(f"      ❌ 无法读取预览内容")
                    self.results["preview_test"]["has_preview_marker"] = False

                self.results["preview_test"]["modal_opened"] = True

                # 8. 关闭预览
                print("\n[1.8] 关闭预览...")
                close_btn = page.locator('.preview-modal .btn-close')
                await close_btn.click(timeout=15000)
                await asyncio.sleep(1)
                print(f"      ✅ 预览已关闭")

                # 9. 验证源文件未被覆盖
                print("\n[1.9] 验证源文件未被覆盖...")

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={PREVIEW_FILE_PATH}"
                    ) as resp:
                        if resp.status == 200:
                            response = await resp.json()
                            data = self.parse_api_response(response)
                            file_content = data.get("content", "")

                            if PREVIEW_INITIAL in file_content:
                                print(f"      ✅ 正文未被覆盖，仍为初始内容")
                                self.results["preview_test"]["content_unchanged"] = True
                            else:
                                print(f"      ❌ 正文被意外覆盖！")
                                print(f"      当前内容: {file_content[:50]}")
                                self.results["preview_test"]["content_unchanged"] = False
                        else:
                            print(f"      ❌ 无法读取文件: {resp.status}")

            except Exception as e:
                print(f"      ❌ 错误: {e}")
                self.results["preview_test"]["error"] = str(e)
                self.results["preview_test"]["result"] = "❌ FAIL"

            finally:
                await browser.close()

        # 综合判定
        modal_ok = self.results["preview_test"].get("modal_opened") == True
        preview_marker_ok = self.results["preview_test"].get("has_preview_marker") == True
        no_delete_marker = self.results["preview_test"].get("has_delete_marker") == False
        content_ok = self.results["preview_test"].get("content_unchanged") == True
        card_found = self.results["preview_test"].get("card_found") == True

        if modal_ok and preview_marker_ok and no_delete_marker and content_ok and card_found:
            self.results["preview_test"]["result"] = "✅ PASS"
        else:
            self.results["preview_test"]["result"] = "❌ FAIL"
            reason = []
            if not modal_ok: reason.append("modal未打开")
            if not preview_marker_ok: reason.append("不包含preview标记")
            if not no_delete_marker: reason.append("包含delete标记")
            if not content_ok: reason.append("正文被覆盖")
            if not card_found: reason.append("未找到card")
            self.results["preview_test"]["fail_reason"] = "; ".join(reason)

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
                try:
                    await candidate_tab.first.click(timeout=15000)
                except Exception:
                    print("      尝试 JavaScript 点击...")
                    await page.evaluate(
                        "() => { const tabs = document.querySelectorAll('[role=\"tab\"]'); "
                        "for (const tab of tabs) { if (tab.textContent.includes('候选稿')) { tab.click(); break; } } }"
                    )
                # 等待 panel 出现
                await asyncio.sleep(5)
                panel = page.locator('.candidate-panel')
                if await panel.count() > 0:
                    print(f"      ✅ 候选稿面板已打开")
                else:
                    print(f"      ⚠️ Panel 未找到但继续...")

                # 3. 刷新列表
                print("\n[2.3] 刷新候选稿列表...")
                refresh_btn = page.locator('.btn-refresh')
                if await refresh_btn.count() == 0:
                    refresh_btn = page.locator('button:has-text("刷新")')
                if await refresh_btn.count() == 0:
                    refresh_btn = page.locator('[aria-label="刷新"]')
                await refresh_btn.first.click(timeout=15000)
                await asyncio.sleep(2)
                print(f"      ✅ 刷新完成")

                # 4. 定位到 delete 文件对应的 candidate card
                print("\n[2.4] 定位 Delete Candidate...")
                delete_card = page.locator(
                    '.candidate-card',
                    has=page.locator(f'text={DELETE_FILE_PATH}')
                )
                delete_card_count = await delete_card.count()
                print(f"      找到 {delete_card_count} 个匹配 '{DELETE_FILE_PATH}' 的 card")

                if delete_card_count == 0:
                    print(f"      ❌ 未找到 delete candidate card")
                    self.results["delete_test"]["card_found"] = False
                    self.results["delete_test"]["result"] = "❌ FAIL"
                    return

                self.results["delete_test"]["card_found"] = True

                # 4b. 截图 delete card（删除前）
                before_screenshot = f"{screenshot_dir}/t471a2_delete_before_specific_card.png"
                await delete_card.first.screenshot(path=before_screenshot)
                print(f"      ✅ Delete card 截图（删除前）已保存")

                # 5. 记录删除前数量
                before_cards = page.locator('.candidate-card')
                before_count = await before_cards.count()
                print(f"      删除前候选稿总数量: {before_count}")
                self.results["delete_test"]["ui_count_before"] = before_count

                # 6. 点击该 card 的 delete 按钮
                print("\n[2.5] 点击 Delete 按钮...")
                delete_btn = delete_card.first.locator('[data-testid="candidate-reject-button"]')
                await delete_btn.click(timeout=15000)
                await asyncio.sleep(1)
                print(f"      ✅ Delete 按钮点击成功")

                # 7. 等待确认弹窗（如果有）
                confirm_dialog = page.locator('.ant-modal-confirm')
                if await confirm_dialog.count() > 0:
                    print(f"      发现确认弹窗，点击确定...")
                    confirm_btn = page.locator('.ant-modal-confirm .ant-btn-primary')
                    await confirm_btn.click(timeout=15000)
                    await asyncio.sleep(2)

                # 8. 刷新列表（触发 UI 更新）
                print("\n[2.6] 刷新候选稿列表...")
                await refresh_btn.click(timeout=15000)
                await asyncio.sleep(2)

                # 9. 再次刷新确保更新
                await page.reload()
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3)

                # 重新打开候选稿面板
                await candidate_tab.first.click(timeout=15000)
                await asyncio.sleep(2)
                await refresh_btn.click(timeout=15000)
                await asyncio.sleep(2)

                # 10. 截图删除后 UI
                after_screenshot = f"{screenshot_dir}/t471a2_delete_after_ui.png"
                await page.screenshot(path=after_screenshot, full_page=True)
                print(f"      ✅ Delete 后 UI 截图已保存")

                # 11. 检查 UI 变化
                print("\n[2.7] 检查 UI 变化...")
                after_cards = page.locator('.candidate-card')
                after_count = await after_cards.count()
                print(f"      删除后候选稿总数量: {after_count}")
                self.results["delete_test"]["ui_count_after"] = after_count

                # 检查 delete card 是否消失
                remaining_delete_cards = page.locator(
                    '.candidate-card',
                    has=page.locator(f'text={DELETE_FILE_PATH}')
                )
                remaining_count = await remaining_delete_cards.count()
                print(f"      Delete 文件对应的 card 数量: {remaining_count}")

                if remaining_count == 0:
                    print(f"      ✅ Delete candidate card 已从 UI 消失")
                    self.results["delete_test"]["ui_card_gone"] = True
                else:
                    print(f"      ❌ Delete candidate card 仍在 UI 中（前端刷新 bug）")
                    self.results["delete_test"]["ui_card_gone"] = False

                # 12. API 复核
                print("\n[2.8] 后端 API 复核...")

                async with aiohttp.ClientSession() as session:
                    # detail API
                    async with session.get(
                        f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.delete_candidate_id}"
                    ) as resp:
                        if resp.status == 404:
                            print(f"      ✅ API detail 返回 404（candidate 已删除）")
                            self.results["delete_test"]["api_404"] = True
                        else:
                            print(f"      ❌ API detail 返回: {resp.status}")
                            self.results["delete_test"]["api_404"] = False

                    # list API 检查状态
                    async with session.get(
                        f"{BACKEND_URL}/api/candidates/{PROJECT_ID}"
                    ) as resp_list:
                        if resp_list.status == 200:
                            response = await resp_list.json()
                            data = self.parse_api_response(response)
                            candidates = data.get("candidates", [])
                            delete_in_list = [
                                c for c in candidates
                                if c.get("id") == self.delete_candidate_id
                            ]
                            if not delete_in_list:
                                print(f"      ✅ list API 中不存在该 candidate")
                                self.results["delete_test"]["api_list_gone"] = True
                            else:
                                status = delete_in_list[0].get("status")
                                print(f"      ❌ list API 中仍存在，status: {status}")
                                self.results["delete_test"]["api_list_gone"] = False

                # 13. 验证源文件未被影响
                print("\n[2.9] 验证源文件未被影响...")

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={DELETE_FILE_PATH}"
                    ) as resp:
                        if resp.status == 200:
                            response = await resp.json()
                            data = self.parse_api_response(response)
                            file_content = data.get("content", "")

                            if DELETE_INITIAL in file_content:
                                print(f"      ✅ 源文件未被影响")
                                self.results["delete_test"]["file_unchanged"] = True
                            else:
                                print(f"      ❌ 源文件被意外修改！")
                                self.results["delete_test"]["file_unchanged"] = False

            except Exception as e:
                print(f"      ❌ 错误: {e}")
                self.results["delete_test"]["error"] = str(e)
                self.results["delete_test"]["result"] = "❌ FAIL"

            finally:
                await browser.close()

        # 综合判定
        card_found = self.results["delete_test"].get("card_found") == True
        api_404 = self.results["delete_test"].get("api_404") == True
        file_ok = self.results["delete_test"].get("file_unchanged") == True

        # UI 消失或 API list 中消失才算成功
        ui_gone = self.results["delete_test"].get("ui_card_gone") == True
        list_gone = self.results["delete_test"].get("api_list_gone") == True

        if card_found and api_404 and file_ok and (ui_gone or list_gone):
            self.results["delete_test"]["result"] = "✅ PASS"
        else:
            self.results["delete_test"]["result"] = "❌ FAIL"
            reason = []
            if not card_found: reason.append("未找到card")
            if not api_404: reason.append("API非404")
            if not file_ok: reason.append("文件被影响")
            if not ui_gone and not list_gone: reason.append("UI未消失")
            self.results["delete_test"]["fail_reason"] = "; ".join(reason)

    async def cleanup(self):
        """清理测试数据"""
        print("\n" + "="*80)
        print("最终清理测试数据")
        print("="*80)

        # 删除 preview candidate
        if self.preview_candidate_id:
            async with aiohttp.ClientSession() as session:
                await session.delete(
                    f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.preview_candidate_id}"
                )
                print(f"      ✅ Preview candidate 已删除")

        # 删除 delete candidate（如果还在的话）
        if self.delete_candidate_id:
            async with aiohttp.ClientSession() as session:
                await session.delete(
                    f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{self.delete_candidate_id}"
                )
                print(f"      ✅ Delete candidate 已删除")

        self.results["cleanup"] = "✅ 完成"

    async def run(self):
        """运行测试"""
        print("\n" + "="*80)
        print("T4.7.1a-2: Preview 与 Delete 行为验证 (简化版)")
        print("="*80)
        print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Run ID: {RUN_ID}")
        print(f"Preview file: {PREVIEW_FILE_PATH}")
        print(f"Delete file: {DELETE_FILE_PATH}")

        # 创建 candidates
        preview_ok = await self.create_preview_candidate()
        delete_ok = await self.create_delete_candidate()

        if not preview_ok or not delete_ok:
            print("\n❌ Candidate 创建失败，测试中止")
            self.results["final_verdict"] = "❌ FAIL"
            self.save_report()
            return

        # 运行测试
        await self.test_preview_behavior()
        await self.test_delete_behavior()
        await self.cleanup()

        print("\n" + "="*80)
        print("测试结果汇总")
        print("="*80)

        print(f"\n【Preview Test】")
        for key, value in self.results["preview_test"].items():
            print(f"  {key}: {value}")

        print(f"\n【Delete Test】")
        for key, value in self.results["delete_test"].items():
            print(f"  {key}: {value}")

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

        preview_res = self.results["preview_test"]
        delete_res = self.results["delete_test"]

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# T4.7.1a E2E 测试结果\n\n")
            f.write(f"**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**最终判定**: {self.results['final_verdict']}\n\n")
            f.write(f"**Run ID**: {RUN_ID}\n\n")
            f.write("---\n\n")

            f.write("## T4.7.1a-2: Preview 与 Delete 行为验证\n\n")
            f.write(f"**脚本**: `tests/test_candidate_preview_delete_e2e.py`\n\n")
            f.write(f"**注意**: 使用简化版（无预清理），每次运行使用唯一文件路径\n\n")

            f.write("### Preview 测试\n\n")
            f.write(f"- **Candidate ID**: {preview_res.get('candidate_id', 'N/A')}\n")
            f.write(f"- **source_path**: {preview_res.get('source_path', 'N/A')}\n")
            f.write(f"- **唯一标记**: {preview_res.get('unique_marker', 'N/A')}\n")
            f.write(f"- **Card 找到**: {preview_res.get('card_found', 'N/A')}\n")
            f.write(f"- **Modal 打开**: {preview_res.get('modal_opened', 'N/A')}\n")
            f.write(f"- **包含 preview 标记**: {preview_res.get('has_preview_marker', 'N/A')}\n")
            f.write(f"- **不包含 delete 标记**: {preview_res.get('has_delete_marker', 'N/A')}\n")
            f.write(f"- **正文未覆盖**: {preview_res.get('content_unchanged', 'N/A')}\n")
            f.write(f"- **判定**: {preview_res.get('result', 'N/A')}\n")
            if preview_res.get('fail_reason'):
                f.write(f"- **失败原因**: {preview_res.get('fail_reason')}\n")
            f.write(f"- **Modal 内容**: {preview_res.get('modal_content', 'N/A')}\n\n")

            f.write("### Delete 测试\n\n")
            f.write(f"- **Candidate ID**: {delete_res.get('candidate_id', 'N/A')}\n")
            f.write(f"- **source_path**: {delete_res.get('source_path', 'N/A')}\n")
            f.write(f"- **唯一标记**: {delete_res.get('unique_marker', 'N/A')}\n")
            f.write(f"- **Card 找到**: {delete_res.get('card_found', 'N/A')}\n")
            f.write(f"- **UI 数量变化**: {delete_res.get('ui_count_before', 'N/A')} -> {delete_res.get('ui_count_after', 'N/A')}\n")
            f.write(f"- **UI Card 消失**: {delete_res.get('ui_card_gone', 'N/A')}\n")
            f.write(f"- **API 404**: {delete_res.get('api_404', 'N/A')}\n")
            f.write(f"- **API List 消失**: {delete_res.get('api_list_gone', 'N/A')}\n")
            f.write(f"- **文件未影响**: {delete_res.get('file_unchanged', 'N/A')}\n")
            f.write(f"- **判定**: {delete_res.get('result', 'N/A')}\n")
            if delete_res.get('fail_reason'):
                f.write(f"- **失败原因**: {delete_res.get('fail_reason')}\n\n")

            f.write("### 截图路径\n\n")
            f.write("- `docs/testing/screenshots/t471a2_preview_specific_card.png`\n")
            f.write("- `docs/testing/screenshots/t471a2_preview_modal_unique.png`\n")
            f.write("- `docs/testing/screenshots/t471a2_delete_before_specific_card.png`\n")
            f.write("- `docs/testing/screenshots/t471a2_delete_after_ui.png`\n\n")

            f.write("### 约束检查\n\n")
            f.write("- **是否调用 LLM**: 否\n")
            f.write("- **是否修改生产 Prompt**: 否\n")
            f.write("- **是否修改业务逻辑**: 否\n")
            f.write("- **是否测试 adopt**: 否\n")
            f.write("- **是否测试 conflict**: 否\n")
            f.write("- **是否测试 SSE**: 否\n\n")

            f.write("### 结论\n\n")
            f.write(f"**T4.7.1a-2 判定**: {self.results['final_verdict']}\n\n")
            f.write(f"**T4.7.1a 整体状态**: ❌ FAIL（等待 adopt/conflict/SSE 验证）\n")

        print(f"\n✅ 报告已保存到: {output_file}")


if __name__ == "__main__":
    test = PreviewDeleteTestSimple()
    asyncio.run(test.run())
