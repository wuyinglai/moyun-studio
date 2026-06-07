"""
T4.7.1a-2 retry-2: Preview 与 Delete 行为验证（修复版）
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

# Preview 文件名（不含路径）
PREVIEW_FILENAME = f"__e2e_preview_{RUN_ID}.md"
DELETE_FILENAME = f"__e2e_delete_{RUN_ID}.md"


async def create_candidate(session, project_id, source_path, initial_content, candidate_content):
    """创建候选稿"""
    # 1. 先创建源文件
    write_url = f"{BACKEND_URL}/api/file"
    write_data = {
        "project_id": project_id,
        "path": source_path,
        "content": initial_content,
        "frontmatter": {},
    }
    async with session.post(write_url, json=write_data) as resp:
        print(f"      源文件创建: {resp.status}")
        write_result = await resp.json()
        if not write_result.get('success'):
            print(f"      源文件创建失败: {write_result.get('message')}")

    # 2. 创建候选稿
    candidate_url = f"{BACKEND_URL}/api/candidates/{project_id}"
    candidate_data = {
        "project_id": project_id,
        "source_path": source_path,
        "content": candidate_content,
        "action": "polish",
        "workflow_run_id": f"test-{RUN_ID}",
        "model": "test-model",
        "pipeline_id": "test-pipeline",
        "source_mode": "test"
    }
    async with session.post(candidate_url, json=candidate_data) as resp:
        print(f"      POST 响应状态: {resp.status}")
        result = await resp.json()
        print(f"      Response: {str(result)[:200]}")
        
        # API 直接返回 candidate 对象，不是 {success: true, data: {...}}
        if isinstance(result, dict) and 'id' in result:
            print(f"      ✅ Candidate ID: {result.get('id')}")
            print(f"         status: {result.get('status')}")
            print(f"         source_path: {result.get('source_path')}")
            return result.get('id')
        elif result.get('success') and isinstance(result.get('data'), dict):
            candidate = result.get('data', {})
            print(f"      ✅ Candidate ID: {candidate.get('id')}")
            print(f"         status: {candidate.get('status')}")
            print(f"         source_path: {candidate.get('source_path')}")
            return candidate.get('id')
        else:
            print(f"      ❌ 创建失败: {result.get('message') or result}")
            return None


async def main():
    print("\n" + "="*80)
    print("T4.7.1a-2 retry-2: Preview 与 Delete 行为验证（修复版）")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Run ID: {RUN_ID}")
    print(f"Preview file: {PREVIEW_FILE_PATH}")
    print(f"Delete file: {DELETE_FILE_PATH}")
    print("="*80)

    results = {
        'preview': {'result': 'FAIL', 'reason': ''},
        'delete': {'result': 'FAIL', 'reason': ''}
    }

    async with aiohttp.ClientSession() as session:
        # ========================================
        # 创建 Preview Candidate
        # ========================================
        print("\n" + "="*40)
        print("创建 Preview Candidate")
        print("="*40)
        preview_candidate_id = await create_candidate(
            session, PROJECT_ID, PREVIEW_FILE_PATH, 
            PREVIEW_INITIAL, PREVIEW_CANDIDATE_CONTENT
        )

        # ========================================
        # 创建 Delete Candidate
        # ========================================
        print("\n" + "="*40)
        print("创建 Delete Candidate")
        print("="*40)
        delete_candidate_id = await create_candidate(
            session, PROJECT_ID, DELETE_FILE_PATH,
            DELETE_INITIAL, DELETE_CANDIDATE_CONTENT
        )

        if not preview_candidate_id or not delete_candidate_id:
            print("\n❌ Candidate 创建失败，无法继续测试")
            print(f"\n【Preview Test】result: ❌ FAIL (创建失败)")
            print(f"\n【Delete Test】result: ❌ FAIL (创建失败)")
            print("\n最终判定: ❌ FAIL")
            return

        # ========================================
        # Test 1: Preview 行为验证
        # ========================================
        print("\n" + "="*40)
        print("Test 1: Preview 行为验证")
        print("="*40)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # 1.1 打开项目页面
                print("\n[1.1] 打开项目页面...")
                await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}")
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                await asyncio.sleep(5)
                print(f"      ✅ 页面加载成功")

                # 1.2 打开候选稿面板
                print("\n[1.2] 打开候选稿面板...")
                candidate_tab = page.locator('[role="tab"]:has-text("候选")')
                if await candidate_tab.count() > 0:
                    await candidate_tab.first.click()
                    await asyncio.sleep(2)
                    print(f"      ✅ 候选稿面板已打开")
                else:
                    print(f"      ❌ 未找到候选稿 tab")

                # 1.3 刷新候选稿列表
                print("\n[1.3] 刷新候选稿列表...")
                refresh_btn = page.locator('.btn-refresh')
                if await refresh_btn.count() > 0:
                    await refresh_btn.first.click()
                    await asyncio.sleep(2)
                    print(f"      ✅ 刷新完成")
                else:
                    print(f"      ⚠️ 未找到刷新按钮（可能不需要）")

                # 1.4 定位 Preview Candidate
                print("\n[1.4] 定位 Preview Candidate...")
                # 使用文件名（不含路径）查找
                preview_card = page.locator(f'.candidate-card:has-text("{PREVIEW_FILENAME}")')
                card_count = await preview_card.count()
                print(f"      找到 {card_count} 个匹配 '{PREVIEW_FILENAME}' 的 card")

                if card_count == 0:
                    results['preview']['reason'] = '未找到preview card'
                    print(f"      ❌ 未找到 preview candidate card")

                    # 列出所有 card 的文件名
                    all_cards = page.locator('.candidate-filename')
                    all_count = await all_cards.count()
                    print(f"      所有候选稿文件名:")
                    for i in range(min(all_count, 20)):
                        text = await all_cards.nth(i).inner_text()
                        print(f"        [{i}] {text}")
                else:
                    print(f"      ✅ 找到 preview candidate card")

                    # 1.5 点击 Preview 按钮
                    print("\n[1.5] 点击 Preview 按钮...")
                    preview_btn = preview_card.first.locator('[title="预览"]')
                    if await preview_btn.count() > 0:
                        await preview_btn.first.click()
                        await asyncio.sleep(2)
                        print(f"      ✅ 点击了 Preview 按钮")

                        # 1.6 检查预览弹窗
                        print("\n[1.6] 检查预览弹窗...")
                        preview_modal = page.locator('.preview-modal')
                        if await preview_modal.count() > 0:
                            print(f"      ✅ 预览弹窗已打开")

                            # 检查弹窗内容
                            preview_textarea = page.locator('.preview-textarea')
                            if await preview_textarea.count() > 0:
                                preview_text = await preview_textarea.first.evaluate('el => el.value')
                                print(f"      预览内容长度: {len(preview_text or '')} chars")
                                print(f"      预览内容: {preview_text[:200] if preview_text else '(empty)'}")

                                # 检查是否包含 UNIQUE_PREVIEW
                                has_preview_marker = f'UNIQUE_PREVIEW_{RUN_ID}' in (preview_text or '')
                                has_delete_marker = f'UNIQUE_DELETE_{RUN_ID}' in (preview_text or '')

                                print(f"      包含 UNIQUE_PREVIEW_{RUN_ID}: {has_preview_marker}")
                                print(f"      包含 UNIQUE_DELETE_{RUN_ID}: {has_delete_marker}")

                                if has_preview_marker and not has_delete_marker:
                                    results['preview']['result'] = 'PASS'
                                    print(f"      ✅ Preview 内容正确！")
                                else:
                                    results['preview']['reason'] = 'preview内容不匹配'
                                    print(f"      ❌ Preview 内容不正确")
                            else:
                                results['preview']['reason'] = 'preview弹窗内容缺失'
                                print(f"      ❌ 预览弹窗内容为空")
                        else:
                            results['preview']['reason'] = 'preview弹窗未打开'
                            print(f"      ❌ 预览弹窗未打开")

                        # 关闭预览
                        close_btn = page.locator('.btn-cancel')
                        if await close_btn.count() > 0:
                            await close_btn.first.click()
                            await asyncio.sleep(1)
                    else:
                        results['preview']['reason'] = 'preview按钮缺失'
                        print(f"      ❌ 未找到 Preview 按钮")

            except Exception as e:
                print(f"\n      ❌ Preview 测试异常: {str(e)[:200]}")
                results['preview']['reason'] = f'异常: {str(e)[:100]}'
            finally:
                await browser.close()

        # ========================================
        # Test 2: Delete 行为验证
        # ========================================
        print("\n" + "="*40)
        print("Test 2: Delete 行为验证")
        print("="*40)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # 设置 dialog 处理器：自动 accept 所有对话框
            async def handle_dialog(dialog):
                print(f"      [Dialog] {dialog.type}: {dialog.message}")
                await dialog.accept()
            
            page.on('dialog', handle_dialog)

            try:
                # 2.1 打开项目页面
                print("\n[2.1] 打开项目页面...")
                await page.goto(f"{FRONTEND_URL}/project/{PROJECT_ID}")
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                await asyncio.sleep(5)
                print(f"      ✅ 页面加载成功")

                # 2.2 打开候选稿面板
                print("\n[2.2] 打开候选稿面板...")
                candidate_tab = page.locator('[role="tab"]:has-text("候选")')
                if await candidate_tab.count() > 0:
                    await candidate_tab.first.click()
                    await asyncio.sleep(2)
                    print(f"      ✅ 候选稿面板已打开")

                # 2.3 刷新候选稿列表
                print("\n[2.3] 刷新候选稿列表...")
                refresh_btn = page.locator('.btn-refresh')
                if await refresh_btn.count() > 0:
                    await refresh_btn.first.click()
                    await asyncio.sleep(2)
                    print(f"      ✅ 刷新完成")

                # 2.4 定位 Delete Candidate
                print("\n[2.4] 定位 Delete Candidate...")
                delete_card = page.locator(f'.candidate-card:has-text("{DELETE_FILENAME}")')
                card_count = await delete_card.count()
                print(f"      找到 {card_count} 个匹配 '{DELETE_FILENAME}' 的 card")

                if card_count == 0:
                    results['delete']['reason'] = '未找到delete card'
                    print(f"      ❌ 未找到 delete candidate card")
                else:
                    print(f"      ✅ 找到 delete candidate card")

                    # 2.5 点击 Delete 按钮
                    print("\n[2.5] 点击 Delete 按钮...")
                    delete_btn = delete_card.first.locator('[title="删除"]')
                    if await delete_btn.count() > 0:
                        await delete_btn.first.click()
                        await asyncio.sleep(2)
                        print(f"      ✅ 点击了 Delete 按钮")

                        # 2.6 确认删除（如有确认弹窗）
                        print("\n[2.6] 确认删除...")
                        confirm_btn = page.locator('button:has-text("确定")')
                        if await confirm_btn.count() > 0:
                            await confirm_btn.first.click()
                            await asyncio.sleep(2)
                            print(f"      ✅ 已确认删除")
                        else:
                            print(f"      ⚠️ 无需确认")

                        # 2.7 刷新页面检查
                        print("\n[2.7] 刷新并检查结果...")
                        await page.reload()
                        await page.wait_for_load_state('domcontentloaded', timeout=10000)
                        await asyncio.sleep(5)

                        # 打开候选稿面板
                        candidate_tab = page.locator('[role="tab"]:has-text("候选")')
                        if await candidate_tab.count() > 0:
                            await candidate_tab.first.click()
                            await asyncio.sleep(2)

                        # 刷新列表
                        refresh_btn = page.locator('.btn-refresh')
                        if await refresh_btn.count() > 0:
                            await refresh_btn.first.click()
                            await asyncio.sleep(2)

                        # 检查 delete candidate 是否消失
                        delete_card_after = page.locator(f'.candidate-card:has-text("{DELETE_FILENAME}")')
                        card_count_after = await delete_card_after.count()
                        print(f"      删除后找到 {card_count_after} 个 card")

                        if card_count_after == 0:
                            results['delete']['result'] = 'PASS'
                            print(f"      ✅ Delete candidate 已消失！")
                        else:
                            # 检查状态是否变化
                            status_elem = delete_card_after.first.locator('.candidate-status')
                            status_text = await status_elem.first.inner_text()
                            print(f"      Delete candidate 状态: {status_text}")
                            if '已放弃' in status_text or 'discarded' in status_text.lower():
                                results['delete']['result'] = 'PASS'
                                print(f"      ✅ Delete candidate 状态已变为 discarded！")
                            else:
                                results['delete']['reason'] = 'UI未消失且状态未变化'
                                print(f"      ❌ Delete candidate 未消失且状态未变化")
                    else:
                        results['delete']['reason'] = 'delete按钮缺失'
                        print(f"      ❌ 未找到 Delete 按钮")

            except Exception as e:
                print(f"\n      ❌ Delete 测试异常: {str(e)[:200]}")
                results['delete']['reason'] = f'异常: {str(e)[:100]}'
            finally:
                await browser.close()

        # ========================================
        # 最终清理测试数据
        # ========================================
        print("\n" + "="*40)
        print("最终清理测试数据")
        print("="*40)

        # 删除 source 文件
        for file_path in [PREVIEW_FILE_PATH, DELETE_FILE_PATH]:
            delete_url = f"{BACKEND_URL}/api/file"
            params = {"project_id": PROJECT_ID, "path": file_path}
            async with session.delete(delete_url, params=params) as resp:
                print(f"      源文件 {file_path} 删除: {resp.status}")

        print(f"\n【Preview Test】")
        print(f"  candidate_id: {preview_candidate_id}")
        print(f"  source_path: {PREVIEW_FILE_PATH}")
        print(f"  unique_marker: UNIQUE_PREVIEW_{RUN_ID}")
        print(f"  result: {'✅' if results['preview']['result'] == 'PASS' else '❌'} {results['preview']['result']}")
        if results['preview']['reason']:
            print(f"  fail_reason: {results['preview']['reason']}")

        print(f"\n【Delete Test】")
        print(f"  candidate_id: {delete_candidate_id}")
        print(f"  source_path: {DELETE_FILE_PATH}")
        print(f"  unique_marker: UNIQUE_DELETE_{RUN_ID}")
        print(f"  result: {'✅' if results['delete']['result'] == 'PASS' else '❌'} {results['delete']['result']}")
        if results['delete']['reason']:
            print(f"  fail_reason: {results['delete']['reason']}")

        # 判定
        all_pass = results['preview']['result'] == 'PASS' and results['delete']['result'] == 'PASS'
        print(f"\n最终判定: {'✅ PASS' if all_pass else '❌ FAIL'}")


if __name__ == "__main__":
    asyncio.run(main())
