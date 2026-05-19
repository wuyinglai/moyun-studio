"""
墨韵AI小说创作助手 - 大纲生成修复验证测试
使用Playwright验证大纲生成功能修复
"""
import asyncio
import os
import time
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOT_DIR = "d:\\newmoyun\\screenshots\\fix_test\\"
FRONTEND_URL = "http://localhost:5173/"

async def ensure_screenshot_dir():
    Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

def screenshot_path(name):
    return os.path.join(SCREENSHOT_DIR, f"{name}.png")

async def test_outline_fix():
    report = {
        "outline_generated": False,
        "chapter_count": 0,
        "has_detailed_content": False,
        "errors": []
    }

    print("=" * 80)
    print("墨韵AI - 大纲生成修复验证测试")
    print("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        try:
            await ensure_screenshot_dir()

            # 1. 导航到主�?            print("\n[1/11] 导航到主�?..")
            await page.goto(FRONTEND_URL)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            await page.screenshot(path=screenshot_path("01_homepage"))
            print("�?主页加载成功")

            # 2. 等待页面加载并检�?            print("\n[2/11] 检查页面加载状�?..")
            page_title = await page.title()
            print(f"�?页面标题: {page_title}")

            # 3. 点击"新建项目"
            print("\n[3/11] 点击'新建项目'...")
            new_project_btn = page.locator("button", has_text="新建项目").first
            await new_project_btn.click()
            await asyncio.sleep(2)
            await page.screenshot(path=screenshot_path("02_new_project_dialog"))
            print("�?打开新建项目对话�?)

            # 4. 填写项目参数 (通过点击按钮�?
            print("\n[4/11] 填写项目参数...")

            # 题材: 玄幻 - 点击"玄幻"按钮
            print("  选择题材: 玄幻")
            genre_btn = page.locator("button.btn-option", has_text="玄幻").first
            await genre_btn.click()
            await asyncio.sleep(0.3)
            print("  �?已选择玄幻")

            # 基调: 热血
            print("  选择基调: 热血")
            tone_btn = page.locator("button.btn-option", has_text="热血").first
            await tone_btn.click()
            await asyncio.sleep(0.3)
            print("  �?已选择热血")

            # 写作风格: 快节�?            print("  选择写作风格: 快节�?)
            style_btn = page.locator("button.btn-option", has_text="快节�?).first
            await style_btn.click()
            await asyncio.sleep(0.3)
            print("  �?已选择快节�?)

            # 作品规模: 10万字
            print("  选择作品规模: 10万字")
            scale_btn = page.locator("button.btn-option", has_text="10万字").first
            await scale_btn.click()
            await asyncio.sleep(0.3)
            print("  �?已选择10万字")

            await page.screenshot(path=screenshot_path("03_filled_params"))
            print("�?参数填写完成")

            # 5. 点击"生成书名与创�?
            print("\n[5/11] 点击'生成书名与创�?...")
            generate_btn = page.locator("button.btn-primary", has_text="生成书名与创�?).first
            await generate_btn.click()
            print("�?点击生成书名与创�?)

            # 等待生成完成 (最�?5�?
            print("  等待生成结果 (最�?5�?...")
            start = time.time()
            book_name_found = False
            while time.time() - start < 45:
                await asyncio.sleep(2)
                # 检查是否出现书名输入框或创意内�?                name_input = page.locator("input[value]").first
                has_name = await name_input.count() > 0
                if has_name:
                    name_val = await name_input.get_attribute("value")
                    if name_val:
                        book_name_found = True
                        print(f"  检测到书名: {name_val}")
                        break
                # 检查是否有创意描述文本�?                textarea = page.locator("textarea.form-textarea").first
                if await textarea.count() > 0:
                    val = await textarea.input_value()
                    if val:
                        book_name_found = True
                        break
                # 检查标题是否变�?                title_el = page.locator(".modal-title").first
                if await title_el.count() > 0:
                    title_text = await title_el.inner_text()
                    if "书名" in title_text or "创意" in title_text:
                        await asyncio.sleep(1)
                        book_name_found = True
                        break
            
            await page.screenshot(path=screenshot_path("04_book_generated"))
            if book_name_found:
                print("�?书名生成完成")
            else:
                report["errors"].append("书名生成可能未完�?)
                print("�?书名生成状态不确定")

            # 6. 验证书名
            print("\n[6/11] 验证书名...")
            try:
                title_el = page.locator(".modal-title").first
                title_text = await title_el.inner_text()
                print(f"�?当前步骤标题: {title_text}")
            except Exception as e:
                print(f"�?未能获取标题: {e}")

            # 7. 点击"下一步：生成大纲"
            print("\n[7/11] 点击'下一步：生成大纲'...")
            next_btn = page.locator("button.btn-primary", has_text="下一�?).first
            await next_btn.click()
            await asyncio.sleep(2)
            print("�?点击下一�?)
            await page.screenshot(path=screenshot_path("05_proceeding_outline"))

            # 8. 等待大纲生成 (最�?20�?
            print("\n[8/11] 等待大纲生成 (最�?20�?...")
            
            start = time.time()
            outline_done = False
            while time.time() - start < 120:
                await asyncio.sleep(3)
                content = await page.content()
                text_content = await page.inner_text("body")
                
                # 检查是否进入确认大纲步�?(2.5)
                title_el = page.locator(".modal-title").first
                if await title_el.count() > 0:
                    title_text = await title_el.inner_text()
                    if "确认" in title_text:
                        outline_done = True
                        print(f"  �?大纲生成完成，进入确认步�?({time.time()-start:.1f}s)")
                        break
                
                # 检查是否显示成�?                if "创建成功" in text_content or "项目创建成功" in text_content:
                    outline_done = True
                    break
                    
                # �?5秒截图一次进�?                elapsed = time.time() - start
                if int(elapsed) % 15 < 3:
                    print(f"  仍在生成�?.. ({elapsed:.0f}s)")
                    await page.screenshot(path=screenshot_path(f"progress_{int(elapsed)}s"))
            
            elapsed = time.time() - start
            print(f"  等待总耗时: {elapsed:.1f} �?)

            # 截图大纲结果
            await page.screenshot(path=screenshot_path("06_outline_result"))
            print("�?截图已保�?)

            # 9. 验证大纲内容
            print("\n[9/11] 验证大纲内容...")
            text_content = await page.inner_text("body")
            
            if "待生成详细大�? in text_content:
                print("�?大纲仍显�?待生成详细大�?")
                report["errors"].append("大纲未实际生成，仍显示占位文�?)
            else:
                print("�?大纲包含实际内容（无占位文本�?)
                report["has_detailed_content"] = True

            # 10. 检查章�?            print("\n[10/11] 检查章节数�?..")
            
            import re
            chapter_matches = re.findall(r"第[一二三四五六七八九十百\d]+[章节卷篇]", text_content)
            report["chapter_count"] = len(chapter_matches)
            
            if len(chapter_matches) > 0:
                print(f"�?检测到 {len(chapter_matches)} 个章�?)
                report["outline_generated"] = True
            else:
                # 检查大纲文本框
                outline_ta = page.locator("textarea.form-textarea").first
                if await outline_ta.count() > 0:
                    outline_val = await outline_ta.input_value()
                    if outline_val:
                        cm2 = re.findall(r"第[一二三四五六七八九十百\d]+[章节卷篇]", outline_val)
                        report["chapter_count"] = len(cm2)
                        if len(cm2) > 0:
                            print(f"�?从大纲文本中检测到 {len(cm2)} 个章�?)
                            report["outline_generated"] = True
                            report["has_detailed_content"] = True
                if not report["outline_generated"]:
                    print("�?未检测到标准章节标题")
                    report["errors"].append("未检测到章节标题")

            # 11. 最终状�?            print("\n[11/11] 最终检�?..")
            await page.screenshot(path=screenshot_path("07_final_state"))
            
            # 尝试获取最终标�?            try:
                final_title = await page.locator(".modal-title").first.inner_text()
                print(f"�?最终步�? {final_title}")
            except:
                pass

        except Exception as e:
            error_msg = str(e)
            report["errors"].append(error_msg)
            print(f"\n�?测试错误: {error_msg}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path=screenshot_path("error"))
            except:
                pass
        finally:
            await browser.close()

    # 输出报告
    print("\n" + "=" * 80)
    print("测试报告")
    print("=" * 80)
    print(f"大纲生成成功: {'�? if report['outline_generated'] else '�?}")
    print(f"生成章节�? {report['chapter_count']}")
    print(f"包含详细内容: {'�? if report['has_detailed_content'] else '�?}")
    if report["errors"]:
        print(f"错误信息:")
        for err in report["errors"]:
            print(f"  - {err}")
    else:
        print("错误信息: �?)

    print(f"\n截图保存�? {SCREENSHOT_DIR}")
    screenshots = list(Path(SCREENSHOT_DIR).glob("*.png"))
    print(f"共生�?{len(screenshots)} 张截�?")
    for ss in sorted(screenshots):
        print(f"  - {ss.name}")

    print("\n" + "=" * 80)
    return report

if __name__ == "__main__":
    asyncio.run(test_outline_fix())

