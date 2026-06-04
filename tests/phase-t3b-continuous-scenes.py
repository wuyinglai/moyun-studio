from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime


def screenshot(page, name):
    path = f"docs/testing/screenshots/t3b-continuous-{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  Screenshot: {path}")
    return path


def wait_for_generation_complete(page, max_wait=90000):
    start_time = time.time()
    while time.time() - start_time < max_wait / 1000:
        try:
            all_btns = page.locator('button').all()
            any_generating = False
            any_stop_btn = False
            for btn in all_btns:
                try:
                    text = btn.inner_text()
                    if "生成中" in text or "正在生成" in text:
                        any_generating = True
                    if "停止生成" in text:
                        any_stop_btn = True
                except:
                    continue
            if not any_generating and not any_stop_btn:
                return True
            else:
                page.wait_for_timeout(2000)
        except:
            page.wait_for_timeout(2000)
    return False


def get_scene_info(page):
    """获取场景详细信息"""
    info = {
        "currentFilePath": "",
        "title": "",
        "charCount": 0,
        "first100": "",
        "fallbackUsed": False,
        "writeSkipped": False,
        "writeSkipReason": None,
        "fallbackCandidateId": None,
    }
    try:
        # 获取当前文件路径
        path_hint = page.locator('.path-hint')
        if path_hint.count() > 0:
            info["currentFilePath"] = path_hint.first.inner_text().strip()
    except:
        pass

    try:
        # 检查是否有 fallback 警告
        fallback_warning = page.locator('[data-testid="lite-fallback-warning"]')
        if fallback_warning.count() > 0:
            info["fallbackUsed"] = True
            # 检查是否有 write-skipped
            try:
                write_skipped = page.locator('[data-testid="lite-fallback-write-skipped"]')
                if write_skipped.count() > 0:
                    info["writeSkipped"] = True
            except:
                pass
            # 获取 fallback candidate id
            try:
                candidate_id = page.locator('[data-testid="lite-fallback-candidate-id"]')
                if candidate_id.count() > 0:
                    text = candidate_id.first.inner_text()
                    if "候选稿 ID" in text:
                        # 提取 ID
                        import re
                        m = re.search(r'候选稿 ID：(.+)', text)
                        if m:
                            info["fallbackCandidateId"] = m.group(1).strip()
            except:
                pass
    except:
        pass

    try:
        # 获取编辑器内容
        textarea = page.locator('[data-testid="lite-editor-content"]')
        if textarea.count() > 0:
            content = textarea.first.input_value()
            info["charCount"] = len(content)
            info["first100"] = content[:100] if content else ""
            # 提取标题（第一行）
            if content:
                first_line = content.split('\n')[0].strip()
                info["title"] = first_line
    except:
        pass

    return info


def test_continuous_scenes():
    results = {
        "testTime": datetime.now().isoformat(),
        "model": "agnes-2.0-flash",
        "result": "failed",
        "sceneCount": 0,
        "scenes": [],
        "continuity": {
            "goalContinues": None,
            "conflictProgresses": None,
            "noDuplicate": None,
            "noJsonLeak": None
        },
        "notes": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 用于存储每场生成后的响应 file_path 和 fallback_used
        generated_file_paths = []
        fallback_used_in_response = False
        write_skipped_in_response = False
        write_skip_reason_in_response = None
        fallback_candidate_id_in_response = None

        # 拦截 /lite/write-next-stream 响应
        def handle_response(response):
            if "/lite/write-next-stream" in response.url:
                try:
                    # SSE 响应，需要从 events 中提取 file_path
                    # 响应格式是 event: meta\\ndata: {...}\\n\\n
                    text = response.text()
                    print(f"  [DEBUG] write-next-stream response: {text[:200]}...")
                    # 提取 file_path 和 fallback_used
                    nonlocal fallback_used_in_response
                    nonlocal write_skipped_in_response
                    nonlocal write_skip_reason_in_response
                    nonlocal fallback_candidate_id_in_response
                    for line in text.split('\n'):
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if 'file_path' in data:
                                    generated_file_paths.append(data['file_path'])
                                    print(f"  [DEBUG] Captured file_path: {data['file_path']}")
                                if 'fallback_used' in data:
                                    fallback_used_in_response = bool(data['fallback_used'])
                                    print(f"  [DEBUG] Captured fallback_used: {fallback_used_in_response}")
                                if 'write_skipped' in data:
                                    write_skipped_in_response = bool(data['write_skipped'])
                                    print(f"  [DEBUG] Captured write_skipped: {write_skipped_in_response}")
                                if 'write_skip_reason' in data:
                                    write_skip_reason_in_response = data['write_skip_reason']
                                    print(f"  [DEBUG] Captured write_skip_reason: {write_skip_reason_in_response}")
                                if 'fallback_candidate_id' in data:
                                    fallback_candidate_id_in_response = data['fallback_candidate_id']
                                    print(f"  [DEBUG] Captured fallback_candidate_id: {fallback_candidate_id_in_response}")
                            except:
                                pass
                except Exception as e:
                    print(f"  [DEBUG] Failed to capture response: {e}")

        page.on("response", handle_response)

        try:
            print("=" * 70)
            print("Phase T3-B-13: 连续生成 3 场真实重测 (验证文件推进)")
            print("=" * 70)

            # Step 1: Open Lite
            print("\n1. 打开 Lite 页面...")
            page.goto("http://127.0.0.1:5173/lite")
            page.wait_for_timeout(8000)
            screenshot(page, "01-lite-page")

            # Check LLM
            llm_status = page.locator('[class*="llm-status"]')
            if llm_status.count() > 0:
                status_text = llm_status.first.inner_text()
                print(f"  LLM Status: {status_text}")
                if "已连接" not in status_text:
                    results["notes"].append("LLM 未连接")
                    return results

            # Step 2: Wait idea cards and select one
            print("\n2. 等待开局卡...")

            # Wait for idea cards or refresh button
            idea_cards = page.locator('button.idea-card')
            refresh_btn = page.locator('button:has-text("换一批")')

            # Wait up to 60 seconds for idea cards
            start_time = time.time()
            while time.time() - start_time < 60:
                if idea_cards.count() > 0:
                    break
                if refresh_btn.count() > 0 and refresh_btn.first.is_visible():
                    print("  Clicking refresh button to load idea cards...")
                    refresh_btn.first.click()
                    page.wait_for_timeout(10000)
                page.wait_for_timeout(2000)

            if idea_cards.count() == 0:
                print("  Error: No idea cards found!")
                screenshot(page, "02-no-idea-cards")
                results["notes"].append("未找到开局卡")
                return results

            card_count = idea_cards.count()
            print(f"  Found {card_count} idea cards")
            idea_cards.first.click()
            page.wait_for_timeout(10000)
            screenshot(page, "02-project-started")

            # Generate 3 scenes
            scenes = []
            for scene_idx in range(3):
                print(f"\n--- 生成第 {scene_idx+1} 场 ---")

                # 清空上一场捕获的文件路径和 fallback_used
                if scene_idx > 0:
                    generated_file_paths.clear()
                    fallback_used_in_response = False
                    write_skipped_in_response = False
                    write_skip_reason_in_response = None
                    fallback_candidate_id_in_response = None

                if scene_idx > 0:
                    page.wait_for_timeout(3000)

                # Find the correct option card (long text with "选这个")
                if scene_idx == 0:
                    # Scene 1: Wait auto-generate
                    print("  Waiting for auto-generation...")
                else:
                    # Scene 2, 3: Wait for option cards or generate button
                    print(f"  Waiting for next scene options...")

                    # Wait a bit for state to settle
                    page.wait_for_timeout(5000)

                    # Debug: show current state
                    try:
                        generate_btn = page.locator('[data-testid="lite-generate-next-options"]')
                        print(f"  Generate button count: {generate_btn.count()}, visible: {generate_btn.first.is_visible() if generate_btn.count() > 0 else 'N/A'}")
                    except:
                        print("  Generate button check failed")

                    # First try to find and click "generate next options" button if present
                    try:
                        generate_btn = page.locator('[data-testid="lite-generate-next-options"]')
                        if generate_btn.count() > 0 and generate_btn.first.is_visible():
                            print("  Found '生成下一场景爽点卡' button, clicking...")
                            generate_btn.first.click()
                            page.wait_for_timeout(10000)
                        else:
                            print("  Generate button not visible, trying refresh button...")
                            # Try the refresh button if available
                            refresh_btn = page.locator('button:has-text("换个方向")')
                            if refresh_btn.count() > 0 and refresh_btn.first.is_visible():
                                print("  Found '换个方向' button, clicking...")
                                refresh_btn.first.click()
                                page.wait_for_timeout(10000)
                    except Exception as e:
                        print(f"  No generate button found or error: {e}")

                    # Now wait for option cards to appear
                    print("  Waiting for lite-option-card...")
                    page.wait_for_selector('button.option-card', timeout=90000)
                    option_cards = page.locator('button.option-card')
                    count = option_cards.count()
                    print(f"  Found {count} option-cards")

                    clicked = False
                    for i in range(count):
                        card = option_cards.nth(i)
                        try:
                            if not card.is_visible() or card.is_disabled():
                                continue
                            text = card.inner_text()
                            if len(text) > 50:
                                print(f"  Clicking option-card: {text[:70]}...")
                                card.click()
                                clicked = True
                                break
                        except:
                            continue

                    if not clicked:
                        results["notes"].append(f"第 {scene_idx+1} 场没找到可用的 option-card")
                        screenshot(page, f"03-scene{scene_idx+1}-no-option")
                        continue

                # Wait generation
                wait_success = wait_for_generation_complete(page)
                if not wait_success:
                    print(f"  Warning: 第 {scene_idx+1} 场等待超长时间")

                # 等待一下让 UI 更新
                page.wait_for_timeout(2000)

                # Save screenshot
                screenshot(page, f"03-scene{scene_idx+1}")

                # Get scene info
                scene_info = get_scene_info(page)
                print(f"  第 {scene_idx+1} 场:")
                print(f"    - currentFilePath: {scene_info['currentFilePath']}")
                print(f"    - title: {scene_info['title']}")
                print(f"    - charCount: {scene_info['charCount']}")
                print(f"    - generatedFilePath from API: {generated_file_paths[-1] if generated_file_paths else 'N/A'}")

                # 检查是否需要停止（write_skipped）
                need_stop = scene_info['writeSkipped'] or write_skipped_in_response
                scene_info_to_save = {
                    "index": scene_idx+1,
                    "charCount": scene_info['charCount'],
                    "title": scene_info['title'],
                    "currentFilePath": scene_info['currentFilePath'],
                    "generatedFilePath": generated_file_paths[-1] if generated_file_paths else "",
                    "first100": scene_info['first100'],
                    "screenshot": f"03-scene{scene_idx+1}.png",
                    "fallbackUsed": scene_info['fallbackUsed'] or fallback_used_in_response,
                    "writeSkipped": scene_info['writeSkipped'] or write_skipped_in_response,
                    "writeSkipReason": scene_info['writeSkipReason'] or write_skip_reason_in_response,
                    "fallbackCandidateId": scene_info['fallbackCandidateId'] or fallback_candidate_id_in_response,
                    "stoppedBecauseFallback": need_stop
                }
                scenes.append(scene_info_to_save)
                print(f"    - writeSkipped: {scene_info_to_save['writeSkipped']}")
                print(f"    - fallbackCandidateId: {scene_info_to_save['fallbackCandidateId']}")
                
                # 如果遇到 write_skipped，停止继续生成
                if need_stop:
                    print("  检测到 fallback write_skipped，停止连续生成")
                    results["stoppedReason"] = "fallback_write_skipped"
                    break

            results["scenes"] = scenes
            results["sceneCount"] = len(scenes)

            # Check continuity
            all_long = all(s["charCount"] > 800 for s in scenes)
            # 检查标题是否推进（场景编号递增）
            titles = [s["title"] for s in scenes if s["title"]]
            scene_nums = []
            for t in titles:
                # 提取 "第X场景"
                import re
                m = re.search(r'第(\d+)场景', t)
                if m:
                    scene_nums.append(int(m.group(1)))
            scene_nums_progress = scene_nums == sorted(scene_nums) and len(set(scene_nums)) == len(scene_nums) if scene_nums else False

            # 检查文件路径是否推进
            file_paths = [s["currentFilePath"] for s in scenes if s["currentFilePath"]]
            sec_nums = []
            for fp in file_paths:
                import re
                m = re.search(r'sec-(\d+)', fp)
                if m:
                    sec_nums.append(int(m.group(1)))
            file_paths_progress = sec_nums == sorted(sec_nums) and len(set(sec_nums)) == len(sec_nums) if sec_nums else False

            unique = len(set(s["first100"][:30] for s in scenes)) == len(scenes) if scenes else False
            no_json = all("{" not in s["first100"] for s in scenes)

            results["continuity"]["noJsonLeak"] = no_json
            results["continuity"]["noDuplicate"] = unique
            results["continuity"]["goalContinues"] = file_paths_progress
            results["continuity"]["conflictProgresses"] = scene_nums_progress

            if len(scenes) == 3 and all_long and no_json and file_paths_progress:
                results["result"] = "passed"
            elif len(scenes) >= 1:
                results["result"] = "partial"
            else:
                results["result"] = "failed"

            # Final screenshot
            screenshot(page, "04-final-flow")

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            results["notes"].append(f"Exception: {str(e)}")
            screenshot(page, "99-error")
        finally:
            browser.close()

    with open("docs/testing/screenshots/t3b-continuous-results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nFinal result: {results['result']}")
    return results


if __name__ == "__main__":
    test_continuous_scenes()
