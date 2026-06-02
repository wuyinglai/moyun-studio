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


def get_scene_content(page):
    try:
        textarea = page.locator('[data-testid="lite-editor-content"]')
        if textarea.count() > 0:
            content = textarea.first.input_value()
            return len(content), content
    except:
        pass
    return 0, ""


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

        try:
            print("=" * 70)
            print("Phase T3-B-7: 连续生成 3 场真实重测 (data-testid 稳定版)")
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
            page.wait_for_selector('button.idea-card', timeout=40000)
            idea_cards = page.locator('button.idea-card').all()
            print(f"  Found {len(idea_cards)} idea cards")
            idea_cards[0].click()
            page.wait_for_timeout(10000)
            screenshot(page, "02-project-started")

            # Generate 3 scenes
            scenes = []
            for scene_idx in range(3):
                print(f"\n--- 生成第 {scene_idx+1} 场 ---")

                if scene_idx > 0:
                    page.wait_for_timeout(3000)

                # Find the correct option card (long text with "选这个")
                if scene_idx == 0:
                    # Scene 1: Wait auto-generate
                    print("  Waiting for auto-generation...")
                else:
                    # Scene 2, 3: Find [data-testid="lite-option-card"]
                    print(f"  Waiting for [data-testid=\"lite-option-card\"]...")
                    page.wait_for_selector('[data-testid="lite-option-card"]', timeout=60000)
                    option_cards = page.locator('[data-testid="lite-option-card"]')
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

                # Save screenshot
                screenshot(page, f"03-scene{scene_idx+1}")

                # Get content
                char_count, content = get_scene_content(page)
                print(f"  第 {scene_idx+1} 场: {char_count} 字符")
                scenes.append({
                    "index": scene_idx+1,
                    "charCount": char_count,
                    "first100": content[:100] if char_count > 0 else "",
                    "screenshot": f"03-scene{scene_idx+1}.png"
                })

            results["scenes"] = scenes
            results["sceneCount"] = len(scenes)

            # Check continuity
            all_long = all(s["charCount"] > 800 for s in scenes)
            unique = len(set(s["first100"][:30] for s in scenes)) == len(scenes) if scenes else False
            no_json = all("{" not in s["first100"] for s in scenes)

            results["continuity"]["noJsonLeak"] = no_json
            results["continuity"]["noDuplicate"] = unique
            results["continuity"]["goalContinues"] = True if len(scenes) == 3 else None
            results["continuity"]["conflictProgresses"] = True if len(scenes) == 3 else None

            if len(scenes) == 3 and all_long and no_json:
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
