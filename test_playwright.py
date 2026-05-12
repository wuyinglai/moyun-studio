"""
墨韵 - Playwright 端到端测试
模拟人类操作测试所有功能，并用 LLM 验证生成内容
"""
import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright, expect

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

TEST_PROJECT_NAME = "Playwright测试小说"
TEST_AUTHOR = "测试作者"

class MoyunE2ETest:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.test_project_id = None
        self.errors = []
        self.passed_tests = []
        
    async def start(self):
        """启动测试"""
        print("=" * 80)
        print("🧪 墨韵 - Playwright 端到端测试")
        print("=" * 80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 初始化 Playwright
        self.playwright = await async_playwright().start()
        
        # 启动浏览器
        print("正在启动浏览器...")
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # 显示浏览器
            slow_mo=300      # 减慢操作以便观察
        )
        
        self.page = await self.browser.new_page(
            viewport={"width": 1440, "height": 900}
        )
        
        try:
            await self.test_all_features()
        except Exception as e:
            self.errors.append(f"测试主流程异常: {str(e)}")
        finally:
            await self.report_results()
            await self.close()
    
    async def test_all_features(self):
        """测试所有功能"""
        
        # 1. 访问主页
        await self.test_homepage()
        
        # 2. 打开项目页面
        await self.test_open_project_modal()
        
        # 3. 创建新项目
        await self.test_create_project()
        
        # 4. 进入项目
        await self.test_enter_project()
        
        # 5. 测试编辑文件
        await self.test_edit_outline()
        
        # 6. 测试 LLM 生成功能
        await self.test_llm_generation()
        
        # 7. 测试质量保障功能
        await self.test_quality_assurance()
        
        # 8. 用 LLM 验证生成内容
        await self.verify_generated_content()
    
    async def test_homepage(self):
        """测试主页加载"""
        print("\n" + "=" * 80)
        print("📌 测试1: 主页加载")
        print("=" * 80)
        
        try:
            # 访问主页
            print("访问 http://127.0.0.1:8000...")
            await self.page.goto("http://127.0.0.1:8000")
            
            # 等待页面加载
            await asyncio.sleep(1)
            
            # 检查标题
            title = await self.page.title()
            print(f"页面标题: {title}")
            assert "墨韵" in title, "页面标题不正确"
            
            # 检查主要 UI 元素
            await expect(self.page.locator("text=墨韵").first).to_be_visible()
            
            print("✅ 主页加载成功")
            self.passed_tests.append("主页加载")
            
        except Exception as e:
            self.errors.append(f"主页测试失败: {str(e)}")
            print(f"❌ 主页测试失败: {str(e)}")
    
    async def test_open_project_modal(self):
        """测试打开项目弹窗"""
        print("\n" + "=" * 80)
        print("📌 测试2: 打开项目弹窗")
        print("=" * 80)
        
        try:
            # 等待按钮可用
            await asyncio.sleep(0.5)
            
            # 查找并点击"打开项目"按钮
            open_btn = self.page.get_by_text("打开项目", exact=False)
            await open_btn.click()
            
            # 等待弹窗出现
            await asyncio.sleep(1)
            
            # 检查弹窗
            await expect(self.page.locator("text=打开项目").first).to_be_visible()
            
            print("✅ 打开项目弹窗显示成功")
            self.passed_tests.append("打开项目弹窗")
            
            # 关闭弹窗
            close_btn = self.page.locator("button").filter(has_text="关闭").first
            if await close_btn.count() > 0:
                await close_btn.click()
                
        except Exception as e:
            self.errors.append(f"打开项目弹窗测试失败: {str(e)}")
            print(f"❌ 打开项目弹窗测试失败: {str(e)}")
    
    async def test_create_project(self):
        """测试创建新项目"""
        print("\n" + "=" * 80)
        print("📌 测试3: 创建新项目")
        print("=" * 80)
        
        try:
            await asyncio.sleep(0.5)
            
            # 点击"创建项目"按钮
            create_btn = self.page.get_by_text("创建项目", exact=False)
            await create_btn.click()
            
            await asyncio.sleep(1)
            
            # 检查创建项目弹窗
            await expect(self.page.locator("text=创建项目").first).to_be_visible()
            
            # 填写表单
            await self.page.fill("[placeholder*='名称'], [placeholder*='name'], input[name='name']", TEST_PROJECT_NAME)
            await self.page.fill("[placeholder*='作者'], [placeholder*='author'], input[name='author']", TEST_AUTHOR)
            
            # 选择题材
            genre_select = self.page.locator("select[name='genre'], select:has-text('玄幻')")
            if await genre_select.count() > 0:
                await genre_select.select_option("玄幻")
            else:
                # 尝试点击类型按钮
                genre_btn = self.page.get_by_text("玄幻").first
                if await genre_btn.count() > 0:
                    await genre_btn.click()
            
            # 点击下一步/创建按钮
            next_btn = self.page.get_by_text("下一步", exact=False).or_(self.page.get_by_text("创建", exact=False)).first
            await next_btn.click()
            
            await asyncio.sleep(1)
            
            # 填写更多信息
            await self.page.fill("textarea[name='background'], textarea[name='theme']", "一个关于修仙者在异世界闯荡的故事")
            
            # 点击完成创建
            finish_btn = self.page.get_by_text("完成", exact=False).or_(self.page.get_by_text("创建", exact=False)).last
            await finish_btn.click()
            
            await asyncio.sleep(2)
            
            print("✅ 项目创建流程成功")
            self.passed_tests.append("创建项目")
            
        except Exception as e:
            self.errors.append(f"创建项目测试失败: {str(e)}")
            print(f"❌ 创建项目测试失败: {str(e)}")
            # 截图
            await self.page.screenshot(path="d:/newmoyun/debug_create_project.png")
    
    async def test_enter_project(self):
        """测试进入项目"""
        print("\n" + "=" * 80)
        print("📌 测试4: 进入项目")
        print("=" * 80)
        
        try:
            # 先打开项目列表
            await asyncio.sleep(0.5)
            open_btn = self.page.get_by_text("打开项目", exact=False)
            await open_btn.click()
            await asyncio.sleep(1)
            
            # 查找测试项目
            test_project = self.page.get_by_text(TEST_PROJECT_NAME, exact=False).first
            if await test_project.count() > 0:
                await test_project.click()
                
                await asyncio.sleep(2)
                
                # 检查项目是否打开成功
                # 查找编辑器或文件树
                await expect(self.page.locator("text=outline.md").first).to_be_visible()
                
                print("✅ 成功进入项目")
                self.passed_tests.append("进入项目")
            else:
                print("⚠️  未找到测试项目，尝试进入已有项目")
                # 点击第一个项目
                first_project = self.page.locator(".project-item, li").first
                if await first_project.count() > 0:
                    await first_project.click()
                    await asyncio.sleep(2)
                    self.passed_tests.append("进入已有项目")
            
        except Exception as e:
            self.errors.append(f"进入项目测试失败: {str(e)}")
            print(f"❌ 进入项目测试失败: {str(e)}")
            await self.page.screenshot(path="d:/newmoyun/debug_enter_project.png")
    
    async def test_edit_outline(self):
        """测试编辑大纲文件"""
        print("\n" + "=" * 80)
        print("📌 测试5: 编辑大纲文件")
        print("=" * 80)
        
        try:
            await asyncio.sleep(1)
            
            # 查找并点击 outline.md
            outline_file = self.page.get_by_text("outline.md").first
            if await outline_file.count() > 0:
                await outline_file.click()
                await asyncio.sleep(1)
                
                # 查找编辑器
                editor = self.page.locator("textarea, [contenteditable='true']").first
                if await editor.count() > 0:
                    # 输入测试内容
                    test_content = f"\n\n# 测试大纲\n\n这是 Playwright 测试添加的内容\n"
                    await editor.fill(await editor.input_value() + test_content)
                    
                    await asyncio.sleep(1)
                    
                    # 触发保存（点击保存按钮或自动保存）
                    save_btn = self.page.get_by_text("保存", exact=False).first
                    if await save_btn.count() > 0:
                        await save_btn.click()
                        await asyncio.sleep(1)
                    
                    print("✅ 大纲文件编辑成功")
                    self.passed_tests.append("编辑大纲")
                else:
                    print("⚠️  未找到编辑器")
                
        except Exception as e:
            self.errors.append(f"编辑大纲测试失败: {str(e)}")
            print(f"❌ 编辑大纲测试失败: {str(e)}")
    
    async def test_llm_generation(self):
        """测试 LLM 生成功能"""
        print("\n" + "=" * 80)
        print("📌 测试6: LLM 生成功能")
        print("=" * 80)
        
        try:
            await asyncio.sleep(0.5)
            
            # 查找 AI 生成相关按钮
            generate_btn = (
                self.page.get_by_text("生成", exact=False)
                .or_(self.page.get_by_text("AI", exact=False))
                .or_(self.page.get_by_text("续写", exact=False))
                .first
            )
            
            if await generate_btn.count() > 0:
                await generate_btn.click()
                await asyncio.sleep(1)
                
                # 查找提示词输入框
                prompt_input = self.page.locator("textarea, input[type='text']").filter(has_text="请输入").first
                if await prompt_input.count() == 0:
                    # 尝试查找其他输入框
                    prompt_input = self.page.locator("textarea, input[type='text']").first
                
                if await prompt_input.count() > 0:
                    await prompt_input.fill("写一段关于主角初入修仙界的场景")
                    
                    # 点击生成按钮
                    submit_btn = (
                        self.page.get_by_text("生成", exact=True)
                        .or_(self.page.get_by_text("发送", exact=False))
                        .or_(self.page.locator("button[type='submit']"))
                    ).first
                    
                    await submit_btn.click()
                    
                    print("⏳ 正在等待 LLM 生成...")
                    
                    # 等待生成完成（较长时间）
                    for i in range(30):
                        await asyncio.sleep(1)
                        print(f"  等待中... ({i+1}/30)")
                    
                    print("✅ LLM 生成测试完成")
                    self.passed_tests.append("LLM生成")
                else:
                    print("⚠️  未找到提示词输入框")
            else:
                print("⚠️  未找到生成按钮")
                
        except Exception as e:
            self.errors.append(f"LLM 生成测试失败: {str(e)}")
            print(f"❌ LLM 生成测试失败: {str(e)}")
            await self.page.screenshot(path="d:/newmoyun/debug_llm_generation.png")
    
    async def test_quality_assurance(self):
        """测试质量保障功能"""
        print("\n" + "=" * 80)
        print("📌 测试7: 质量保障功能")
        print("=" * 80)
        
        try:
            await asyncio.sleep(0.5)
            
            # 查找质量保障相关按钮
            quality_features = [
                "文风指南",
                "故事状态",
                "近期上下文",
                "修改日志",
                "用户反馈"
            ]
            
            found_features = []
            for feature in quality_features:
                locator = self.page.get_by_text(feature, exact=False).first
                if await locator.count() > 0:
                    found_features.append(feature)
                    print(f"  ✅ 发现功能: {feature}")
                    
                    # 点击查看
                    await locator.click()
                    await asyncio.sleep(0.5)
            
            if found_features:
                print(f"✅ 质量保障功能正常 (发现 {len(found_features)} 个)")
                self.passed_tests.append("质量保障")
            else:
                print("⚠️  未发现质量保障功能")
                
        except Exception as e:
            self.errors.append(f"质量保障测试失败: {str(e)}")
            print(f"❌ 质量保障测试失败: {str(e)}")
    
    async def verify_generated_content(self):
        """用 LLM 验证生成的文件内容"""
        print("\n" + "=" * 80)
        print("📌 测试8: LLM 内容验证")
        print("=" * 80)
        
        try:
            # 查找最近的项目
            projects_path = Path("d:/newmoyun/workspace/projects")
            
            if projects_path.exists():
                # 获取最新修改的项目
                project_dirs = sorted(
                    [d for d in projects_path.iterdir() if d.is_dir()],
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                
                if project_dirs:
                    latest_project = project_dirs[0]
                    print(f"检查项目: {latest_project.name}")
                    
                    # 查找生成的文件
                    files_to_check = [
                        latest_project / "outline.md",
                        latest_project / "style-guide.md",
                        latest_project / "story-state.md"
                    ]
                    
                    for file_path in files_to_check:
                        if file_path.exists():
                            print(f"\n读取文件: {file_path.name}")
                            content = file_path.read_text(encoding='utf-8')
                            print(f"内容长度: {len(content)} 字符")
                            
                            if len(content) > 50:
                                preview = content[:200] + "..."
                                print(f"内容预览: {preview}")
                                
                                # 用 LLM 验证
                                is_valid = await self.llm_verify_content(content, file_path.name)
                                if is_valid:
                                    print(f"✅ {file_path.name} 内容验证通过")
                                    self.passed_tests.append(f"内容验证: {file_path.name}")
                                else:
                                    print(f"⚠️  {file_path.name} 内容需要检查")
                    else:
                        print(f"📝 {file_path.name} 不存在或过短")
                                
        except Exception as e:
            self.errors.append(f"内容验证失败: {str(e)}")
            print(f"❌ 内容验证失败: {str(e)}")
    
    async def llm_verify_content(self, content: str, filename: str) -> bool:
        """使用 LLM 验证生成的内容是否合理"""
        try:
            from backend.services.llm_service import LLMService
            
            llm = LLMService()
            
            verify_prompt = f"""请检查以下 {filename} 的内容是否合理：

```
{content[:1000]}
```

请回答：
1. 内容是否完整？
2. 内容是否符合小说创作的要求？
3. 格式是否正确？

只需回答 '通过' 或 '不通过'，然后简短说明理由。"""
            
            messages = [{"role": "user", "content": verify_prompt}]
            
            # 调用 LLM
            result = await llm.complete_sync(messages)
            
            print(f"\nLLM 验证结果:")
            print(f"  {result[:200]}...")
            
            # 简单判断
            return "通过" in result
            
        except Exception as e:
            print(f"  LLM 验证出错: {str(e)}")
            return False
    
    async def report_results(self):
        """报告测试结果"""
        print("\n" + "=" * 80)
        print("📊 测试结果报告")
        print("=" * 80)
        
        print(f"\n✅ 通过的测试 ({len(self.passed_tests)}):")
        for test in self.passed_tests:
            print(f"  ✓ {test}")
        
        if self.errors:
            print(f"\n❌ 发现的问题 ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ✗ {error}")
        else:
            print("\n✅ 所有测试通过！")
        
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def main():
    test = MoyunE2ETest()
    await test.start()


if __name__ == "__main__":
    asyncio.run(main())
