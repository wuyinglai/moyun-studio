from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime

RESULTS = {
    "test_time": datetime.now().isoformat(),
    "commit": "afcbd62e25db55058cf71f31eb2c5388a2c98a8f",
    "llm_provider": "Agnes AI",
    "llm_model": "agnes-2.0-flash",
    "frontend_port": 5174,
    "tests": {},
    "bugs": [],
    "suggestions": []
}

def screenshot(page, name):
    path = f"docs/testing/screenshots/t3b-{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  Screenshot: {path}")
    return path

def test_phase_t3b():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            print("=" * 60)
            print("Phase T3-B: Agnes LLM 真实生成测试")
            print("=" * 60)
            
            # Step 1: Open Lite page on correct port
            print("\n[1/8] 打开 Lite 页面...")
            page.goto('http://127.0.0.1:5174/lite')
            page.wait_for_timeout(8000)  # Wait for idea cards to load
            screenshot(page, "01-lite-page.png")
            print("  Lite page loaded")
            
            # Check LLM status
            llm_status = page.locator('[class*="llm-status"]')
            if llm_status.count() > 0:
                status_text = llm_status.first.inner_text()
                print(f"  LLM Status: '{status_text}'")
                if "已连接" in status_text:
                    RESULTS["tests"]["llm_connection"] = "connected"
                else:
                    RESULTS["tests"]["llm_connection"] = "disconnected"
            RESULTS["tests"]["lite_page_load"] = "passed"
            
            # Check for idea cards - wait for them to appear
            print("\n  Waiting for idea cards...")
            page.wait_for_selector('button.idea-card', timeout=30000)
            idea_cards = page.locator('button.idea-card').all()
            print(f"  Found {len(idea_cards)} idea cards")
            
            # Step 2: Click on an idea card to start project
            print("\n[2/8] 选择开局卡并创建项目...")
            if idea_cards:
                first_card = idea_cards[0]
                card_text = first_card.inner_text()
                print(f"  Selected card: {card_text[:80]}...")
                first_card.click()
                print("  Clicked first idea card")
                
                # Wait for project creation and UI to switch
                page.wait_for_timeout(10000)
                screenshot(page, "02-project-started.png")
                
                # Check if writing shell is visible (means project was created)
                writing_shell = page.locator('.writing-shell')
                if writing_shell.count() > 0:
                    print("  Writing shell visible - project created!")
                    RESULTS["tests"]["create_project"] = "passed"
                else:
                    print("  WARNING: Writing shell not visible yet")
                    page.wait_for_timeout(5000)
                    screenshot(page, "02b-after-wait.png")
                    if page.locator('.writing-shell').count() > 0:
                        RESULTS["tests"]["create_project"] = "passed"
                    else:
                        RESULTS["tests"]["create_project"] = "partial"
            else:
                print("  ERROR: No idea cards found")
                RESULTS["tests"]["create_project"] = "failed"
                RESULTS["bugs"].append({
                    "type": "no_idea_cards",
                    "message": "开局卡未能生成"
                })
            
            # Step 3: Generate next scene cards (refresh if needed)
            print("\n[3/8] 生成下一场景爽点卡...")
            page.wait_for_timeout(3000)  # Wait for UI to settle
            
            # Look for refresh button in the "下一场景爽点卡" section
            refresh_btns = page.locator('button:has-text("刷新")')
            if refresh_btns.count() > 0:
                refresh_btns.first.click()
                print("  Clicked refresh button for next scene cards")
                page.wait_for_timeout(15000)
                screenshot(page, "03-next-scene-cards.png")
            else:
                print("  No refresh button found, using existing cards")
            
            # Step 4: Write next scene (select a card from next scene options)
            print("\n[4/8] 写下一场景...")
            page.wait_for_timeout(2000)
            
            # Look for option cards in the assistant panel
            option_cards = page.locator('.lite-assistant button, section button').all()
            clickable_options = [c for c in option_cards if not c.is_disabled() and c.is_visible()]
            print(f"  Found {len(clickable_options)} clickable buttons")
            
            if clickable_options:
                # Find the first option card (not action buttons like refresh)
                for card in clickable_options[:5]:
                    try:
                        text = card.inner_text()
                        if len(text) > 50 and "选这个" in text:  # Option cards have longer text
                            print(f"  Clicking option: {text[:60]}...")
                            card.click()
                            print("  Waiting for scene generation...")
                            page.wait_for_timeout(25000)
                            screenshot(page, "04-first-scene-generated.png")
                            RESULTS["tests"]["first_scene"] = "generated"
                            break
                    except:
                        pass
            else:
                print("  WARNING: No clickable option cards found")
                RESULTS["tests"]["first_scene"] = "no_cards"
                screenshot(page, "04-no-options.png")
            
            # Step 5: Generate 2 more scenes (total 3)
            print("\n[5/8] 连续生成 3 场...")
            scenes_generated = []
            
            for i in range(2):
                print(f"\n  Generating scene {i+2}...")
                page.wait_for_timeout(3000)
                
                # Find next scene cards again
                option_cards = page.locator('.lite-assistant button, section button').all()
                clickable_options = [c for c in option_cards if not c.is_disabled() and c.is_visible()]
                
                clicked = False
                for card in clickable_options[:5]:
                    try:
                        text = card.inner_text()
                        if len(text) > 50 and "选这个" in text:
                            print(f"  Clicking scene option #{i+2}")
                            card.click()
                            clicked = True
                            break
                    except:
                        pass
                
                if clicked:
                    page.wait_for_timeout(25000)
                    screenshot(page, f"05-scene-{i+2}-generated.png")
                    scenes_generated.append(f"scene-{i+2}")
                else:
                    print(f"  Could not find scene cards for scene {i+2}")
                    screenshot(page, f"05-no-cards-{i+2}.png")
            
            RESULTS["tests"]["continuous_scenes"] = {
                "status": "completed" if len(scenes_generated) >= 2 else "partial",
                "scenes": scenes_generated
            }
            print(f"  Generated {len(scenes_generated)} additional scenes")
            
            # Step 6: Test Candidate revision
            print("\n[6/8] 测试 Candidate 改稿...")
            revision_tests = []
            
            page.wait_for_timeout(2000)
            
            # Test "重写当前场景"
            rewrite_btn = page.locator('button:has-text("重写当前场景")')
            if rewrite_btn.count() > 0 and not rewrite_btn.first.is_disabled():
                rewrite_btn.click()
                print("  Clicked '重写当前场景'")
                page.wait_for_timeout(20000)
                screenshot(page, "06-rewrite-candidate.png")
                revision_tests.append("rewrite")
                
                # Check for adopt button
                adopt_btns = page.locator('button:has-text("采用")')
                if adopt_btns.count() > 0:
                    print("  Adopt button visible")
                    adopt_btns.first.click()
                    page.wait_for_timeout(3000)
                    screenshot(page, "06-rewrite-adopted.png")
            
            # Test "让当前场景更爽"
            exciting_btn = page.locator('button:has-text("更爽")')
            if exciting_btn.count() > 0 and not exciting_btn.first.is_disabled():
                exciting_btn.click()
                print("  Clicked '让当前场景更爽'")
                page.wait_for_timeout(20000)
                screenshot(page, "07-exciting-candidate.png")
                revision_tests.append("more_exciting")
            
            # Test "让当前场景更合理"
            reasonable_btn = page.locator('button:has-text("更合理")')
            if reasonable_btn.count() > 0 and not reasonable_btn.first.is_disabled():
                reasonable_btn.click()
                print("  Clicked '让当前场景更合理'")
                page.wait_for_timeout(20000)
                screenshot(page, "08-reasonable-candidate.png")
                revision_tests.append("more_reasonable")
            
            RESULTS["tests"]["candidate"] = {
                "status": "tested" if revision_tests else "not_tested",
                "tested_types": revision_tests
            }
            
            # Step 7: Check FlowPanel
            print("\n[7/8] 观察 FlowPanel...")
            screenshot(page, "09-flow-panel.png")
            RESULTS["tests"]["flow_panel"] = "observed"
            
            # Step 8: Quality scoring (check content)
            print("\n[8/8] 质量评分（基于生成内容）...")
            
            # Check if there's generated content in the editor
            textarea = page.locator('textarea[data-testid="lite-output-panel"]')
            if textarea.count() > 0:
                content = textarea.first.input_value()
                char_count = len(content)
                print(f"  Editor content length: {char_count} characters")
                RESULTS["tests"]["quality_scoring"] = {
                    "status": "content_generated",
                    "char_count": char_count,
                    "note": "Manual quality review required from screenshots"
                }
            else:
                RESULTS["tests"]["quality_scoring"] = {
                    "status": "no_content_found"
                }
            
            # Final screenshot
            screenshot(page, "99-final-state.png")
            
            print("\n" + "=" * 60)
            print("测试完成!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            RESULTS["bugs"].append({
                "type": "test_error",
                "message": str(e)
            })
            screenshot(page, "99-error.png")
        
        finally:
            browser.close()
    
    # Save results
    with open("docs/testing/screenshots/t3b-results.json", "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to docs/testing/screenshots/t3b-results.json")
    return RESULTS

if __name__ == "__main__":
    test_phase_t3b()
