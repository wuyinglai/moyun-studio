from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime


def screenshot(page, name):
    path = f"docs/testing/screenshots/t3b-next-options-{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  Screenshot: {path}")
    return path


def test_next_options_diagnosis():
    results = {
        "testTime": datetime.now().isoformat(),
        "model": "agnes-2.0-flash",
        "result": "unknown",
        "observations": [],
        "network": {
            "nextOptionsRequest": None,
            "otherRequests": []
        },
        "frontend": {
            "refreshOptionsCalled": False,
            "loadingOptionsShown": False,
            "optionErrorShown": False,
            "optionErrorText": "",
            "nextCardsCount": 0,
            "optionCardsVisible": False,
            "consoleErrors": []
        },
        "conclusion": "unknown"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Network interception
        next_options_request = None
        all_requests = []

        def log_request(route):
            request = route.request
            url = request.url
            if "/lite/next-options" in url:
                nonlocal next_options_request
                next_options_request = {
                    "url": url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "timestamp": datetime.now().isoformat()
                }
                # Capture request body if available
                try:
                    body = request.post_data_json()
                    if body:
                        # Sanitize - remove any sensitive fields
                        if "api_key" in body:
                            body["api_key"] = "[REDACTED]"
                        next_options_request["body"] = body
                except:
                    pass
            all_requests.append({
                "url": url,
                "method": request.method,
                "timestamp": datetime.now().isoformat()
            })
            route.continue_()

        def log_response(response):
            request = response.request
            url = request.url
            if "/lite/next-options" in url and next_options_request:
                next_options_request["status"] = response.status
                next_options_request["responseHeaders"] = dict(response.headers)
                try:
                    json_data = response.json()
                    # Sanitize response - don't include full content
                    next_options_request["response"] = {
                        "status": json_data.get("status"),
                        "message": json_data.get("message"),
                        "cardsCount": len(json_data.get("data", {}).get("cards", [])) if json_data.get("data") else 0
                    }
                    if "data" in json_data and "cards" in json_data["data"]:
                        cards = json_data["data"]["cards"]
                        next_options_request["response"]["cardsSample"] = [
                            {"id": c.get("id"), "title": c.get("title", "")[:30]} 
                            for c in cards[:3]
                        ]
                except Exception as e:
                    next_options_request["responseError"] = str(e)

        page.route("**/*", log_request)
        page.on("response", log_response)

        # Console capture (all types including debug logs)
        console_errors = []
        console_logs = []
        def on_console(message):
            log_entry = {
                "type": message.type,
                "text": message.text,
                "timestamp": datetime.now().isoformat()
            }
            console_logs.append(log_entry)
            if message.type == "error":
                console_errors.append(log_entry)
                print(f"  Console Error: {message.text}")
            else:
                print(f"  Console [{message.type}]: {message.text[:200]}")
        page.on("console", on_console)

        try:
            print("=" * 70)
            print("Phase T3-B-11: next-options 链路诊断")
            print("=" * 70)

            # Step 1: Open Lite
            print("\n1. 打开 Lite 页面...")
            page.goto("http://127.0.0.1:5174/lite")
            page.wait_for_timeout(8000)
            screenshot(page, "01-lite-page")
            results["observations"].append("Lite 页面已打开")

            # Check LLM status
            llm_status = page.locator('[class*="llm-status"]')
            if llm_status.count() > 0:
                status_text = llm_status.first.inner_text()
                print(f"  LLM Status: {status_text}")
                if "已连接" not in status_text:
                    results["observations"].append(f"LLM 未连接: {status_text}")

            # Step 2: Wait for idea cards
            print("\n2. 等待开局卡...")
            idea_cards = page.locator('button.idea-card')
            refresh_btn = page.locator('button:has-text("换一批")')
            
            start_time = time.time()
            while time.time() - start_time < 60:
                if idea_cards.count() > 0:
                    break
                if refresh_btn.count() > 0 and refresh_btn.first.is_visible():
                    print("  点击换一批加载开局卡...")
                    refresh_btn.first.click()
                    page.wait_for_timeout(10000)
                page.wait_for_timeout(2000)
            
            if idea_cards.count() == 0:
                print("  Error: 未找到开局卡")
                results["observations"].append("未找到开局卡")
                screenshot(page, "02-no-idea-cards")
                results["conclusion"] = "failed"
                return results
            
            print(f"  找到 {idea_cards.count()} 张开局卡")
            idea_cards.first.click()
            page.wait_for_timeout(10000)
            screenshot(page, "02-project-started")
            results["observations"].append("已选择开局卡，项目已创建")

            # Step 3: Wait for first scene generation
            print("\n3. 等待第 1 场生成完成...")
            page.wait_for_timeout(30000)
            
            # Check if generation is in progress
            generating = True
            start_time = time.time()
            while generating and time.time() - start_time < 90:
                generating = False
                btns = page.locator('button').all()
                for btn in btns:
                    try:
                        text = btn.inner_text()
                        if "生成中" in text or "正在生成" in text or "停止生成" in text:
                            generating = True
                            break
                    except:
                        continue
                if generating:
                    page.wait_for_timeout(3000)
            
            screenshot(page, "03-scene1-generated")
            
            # Get scene 1 content
            textarea = page.locator('[data-testid="lite-editor-content"]')
            if textarea.count() > 0:
                content = textarea.first.input_value()
                char_count = len(content)
                print(f"  第 1 场生成完成: {char_count} 字符")
                results["observations"].append(f"第 1 场生成完成: {char_count} 字符")
            else:
                results["observations"].append("第 1 场未找到编辑器内容")

            # Step 4: Find and click "生成下一场景爽点卡" button or check current state
            print("\n4. 查找并点击'生成下一场景爽点卡'按钮...")
            generate_btn = page.locator('[data-testid="lite-generate-next-options"]')
            
            # Check if option cards already exist (auto-generated after scene 1)
            option_cards = page.locator('[data-testid="lite-option-card"]')
            if option_cards.count() > 0:
                print(f"  发现已有 {option_cards.count()} 张爽点卡，系统可能已自动生成")
                screenshot(page, "04-cards-already-exist")
                results["observations"].append(f"发现已有 {option_cards.count()} 张爽点卡")
            elif generate_btn.count() > 0 and generate_btn.first.is_visible():
                print("  找到按钮，准备点击...")
                screenshot(page, "04-before-click")
                
                # Click and monitor
                generate_btn.first.click()
                results["observations"].append("已点击'生成下一场景爽点卡'按钮")
                print("  按钮已点击")
                
                # Wait for network and UI changes (increased to 30s for slower responses)
                page.wait_for_timeout(30000)
                screenshot(page, "05-after-click")
            else:
                print("  未找到'生成下一场景爽点卡'按钮，检查是否有错误或加载状态...")
                screenshot(page, "04-no-button")
                
                # Check for loading state
                loading_selector = page.locator('.option-loading')
                if loading_selector.count() > 0:
                    loading_text = loading_selector.first.inner_text()
                    print(f"  Loading text: {loading_text}")
                    results["observations"].append(f"显示加载状态: {loading_text}")
                
                # Check for error
                error_selector = page.locator('.option-loading')
                if error_selector.count() > 0:
                    error_text = error_selector.first.inner_text()
                    if "失败" in error_text or "没有生成出" in error_text:
                        print(f"  Error text: {error_text}")
                        results["observations"].append(f"显示错误: {error_text}")
                
                # Continue analysis without clicking button
                results["observations"].append("未找到'生成下一场景爽点卡'按钮，但继续分析")

            # Step 5: Analyze network requests
            print("\n5. 分析网络请求...")
            if next_options_request:
                print(f"  Found next-options request:")
                print(f"    URL: {next_options_request.get('url')}")
                print(f"    Method: {next_options_request.get('method')}")
                print(f"    Status: {next_options_request.get('status')}")
                
                response = next_options_request.get("response", {})
                cards_count = response.get("cardsCount", 0)
                print(f"    Cards returned: {cards_count}")
                
                results["network"]["nextOptionsRequest"] = next_options_request
                results["observations"].append(f"next-options 请求已发送，状态: {next_options_request.get('status')}")
                results["observations"].append(f"API 返回 {cards_count} 张卡片")
            else:
                print("  Warning: No next-options request found!")
                results["observations"].append("未检测到 next-options 请求")

            # Step 6: Check frontend state
            print("\n6. 检查前端状态...")
            
            # Check generating state
            generating_mask = page.locator('[data-testid="lite-generating-status"]')
            if generating_mask.count() > 0 and generating_mask.first.is_visible():
                print("  generating 状态: true (有遮罩)")
                results["observations"].append("generating 状态为 true")
            else:
                print("  generating 状态: false (无遮罩)")
            
            # Check loading state
            loading_selector = page.locator('.option-loading')
            if loading_selector.count() > 0:
                loading_text = loading_selector.first.inner_text()
                print(f"  Loading text: {loading_text}")
                if "正在根据前文生成爽点卡" in loading_text:
                    results["frontend"]["loadingOptionsShown"] = True
                    results["observations"].append("显示'正在根据前文生成爽点卡'")
            
            # Check option error
            error_selector = page.locator('.option-loading')
            if error_selector.count() > 0:
                error_text = error_selector.first.inner_text()
                if "失败" in error_text or "没有生成出" in error_text:
                    results["frontend"]["optionErrorShown"] = True
                    results["frontend"]["optionErrorText"] = error_text
                    results["observations"].append(f"显示错误: {error_text}")
            
            # Check option cards (use class selector since data-testid pattern changed)
            option_cards = page.locator('button.option-card')
            card_count = option_cards.count()
            print(f"  Option cards found: {card_count}")
            results["frontend"]["nextCardsCount"] = card_count
            
            # Debug: check DOM structure
            panel = page.locator('[data-testid="lite-next-options-panel"]')
            if panel.count() > 0:
                panel_html = panel.first.inner_html()
                print(f"  Panel HTML length: {len(panel_html)}")
                results["observations"].append(f"Panel HTML 长度: {len(panel_html)}")
                # Print first 500 chars of panel HTML for debugging
                print(f"  Panel HTML preview: {panel_html[:500]}")
            
            # Debug: check Vue state via page state
            try:
                vue_state = page.evaluate('''() => {
                    // Try to find the Vue app instance
                    const app = document.querySelector('#app').__vue_app__
                    if (app) {
                        // Get the root component
                        const instance = app._instance
                        if (instance && instance.setupState) {
                            return {
                                nextCards: instance.setupState.nextCards?.value?.length || 0,
                                generating: instance.setupState.generating?.value || false,
                                loadingOptions: instance.setupState.loadingOptions?.value || false
                            }
                        }
                    }
                    return null
                }''')
                if vue_state:
                    print(f"  Vue state: {vue_state}")
                    results["observations"].append(f"Vue state: {vue_state}")
            except Exception as e:
                print(f"  Could not read Vue state: {e}")
                results["observations"].append(f"Vue state 读取失败: {e}")
            
            if card_count > 0:
                results["frontend"]["optionCardsVisible"] = True
                results["observations"].append(f"找到 {card_count} 张爽点卡")
            else:
                results["observations"].append("未找到爽点卡")

            # Step 7: Console errors
            results["frontend"]["consoleErrors"] = console_errors
            if console_errors:
                results["observations"].append(f"发现 {len(console_errors)} 个控制台错误")
                for err in console_errors:
                    print(f"  Console Error: {err.get('text')}")

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            results["observations"].append(f"Exception: {str(e)}")
            screenshot(page, "99-error")
        finally:
            browser.close()

        # Final analysis
        print("\n7. 分析结论...")
        network_ok = next_options_request and next_options_request.get("status") == 200
        cards_returned = next_options_request.get("response", {}).get("cardsCount", 0) > 0 if next_options_request else False
        cards_rendered = results["frontend"]["optionCardsVisible"]
        
        if not next_options_request:
            results["conclusion"] = "B"  # fetchLiteNextOptions 没有发请求
            print("  结论: B - fetchLiteNextOptions 没有发请求")
        elif next_options_request.get("status") != 200:
            results["conclusion"] = "C"  # next-options API 请求失败
            print(f"  结论: C - next-options API 请求失败 (status: {next_options_request.get('status')})")
        elif not cards_returned:
            results["conclusion"] = "D"  # API 成功但 cards 为空
            print("  结论: D - API 成功但 cards 为空")
        elif not cards_rendered:
            results["conclusion"] = "E"  # API 成功返回 cards，但前端没有渲染
            print("  结论: E - API 成功返回 cards，但前端没有渲染")
        else:
            results["conclusion"] = "success"
            print("  结论: 链路正常")

        # Save results
        with open("docs/testing/screenshots/t3b-next-options-diagnosis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n诊断结果已保存到 docs/testing/screenshots/t3b-next-options-diagnosis.json")
        print(f"最终结论: {results['conclusion']}")

    return results


if __name__ == "__main__":
    test_next_options_diagnosis()