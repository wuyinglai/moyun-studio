"""
墨韵 - 完整测试脚本
测试所有核心功能，包括项目管理、文件操作、LLM 生成�?"""
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

# 配置
BASE_URL = "http://127.0.0.1:8000"
TEST_PROJECT_NAME = "墨韵测试项目 - 修仙之旅"
TEST_AUTHOR = "测试作�?

class MoyunTester:
    def __init__(self):
        self.project_id = None
        self.passed_tests = []
        self.failed_tests = []
        self.errors = []
        self.generated_files = []
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def run_all_tests(self):
        """运行所有测�?""
        print("=" * 80)
        print("🧪 墨韵 - 完整功能测试")
        print("=" * 80)
        print(f"开始时�? {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. 测试项目管理
        await self.test_project_management()
        
        if self.project_id:
            # 2. 测试文件操作
            await self.test_file_operations()
            
            # 3. 测试 LLM 生成
            await self.test_llm_generation()
            
            # 4. 测试质量保障功能
            await self.test_quality_assurance()
            
            # 5. �?LLM 验证生成的内�?            await self.verify_generated_content()
        
        # 输出报告
        await self.print_report()
    
    async def test_project_management(self):
        """测试项目管理功能"""
        print("\n" + "=" * 80)
        print("📌 �?部分: 项目管理测试")
        print("=" * 80)
        
        try:
            # 1. 获取项目列表
            print("\n[1/5] 获取项目列表...")
            resp = await self.client.get(f"{BASE_URL}/api/projects")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   �?成功，当前有 {data.get('data', {}).get('total', 0)} 个项�?)
                self.passed_tests.append("获取项目列表")
            else:
                print(f"   �?失败: {resp.text}")
                self.failed_tests.append("获取项目列表")
                return
            
            # 2. 创建新项�?            print("\n[2/5] 创建新项�?..")
            create_data = {
                "name": TEST_PROJECT_NAME,
                "author": TEST_AUTHOR,
                "genre": "玄幻",
                "tone": "热血",
                "background": "一个修仙者在异世界闯荡的故事，主角从底层一步步成长",
                "theme": "成长、冒险、友�?,
                "writing_style": "网络小说风格，节奏轻快，情节跌宕起伏",
                "target_word_count": 500000
            }
            resp = await self.client.post(f"{BASE_URL}/api/projects", json=create_data)
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                self.project_id = data.get('data', {}).get('project_id')
                print(f"   �?项目创建成功!")
                print(f"      项目 ID: {self.project_id}")
                print(f"      项目名称: {data.get('data', {}).get('name')}")
                self.passed_tests.append("创建项目")
            else:
                print(f"   �?创建失败: {resp.text}")
                self.failed_tests.append("创建项目")
                return
            
            # 3. 获取项目详情
            print(f"\n[3/5] 获取项目详情 (ID: {self.project_id})...")
            resp = await self.client.get(f"{BASE_URL}/api/projects/{self.project_id}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   �?成功")
                print(f"      项目名称: {data.get('data', {}).get('name')}")
                print(f"      完成�? {data.get('data', {}).get('completion_rate', 0) * 100:.1f}%")
                self.passed_tests.append("获取项目详情")
            else:
                print(f"   �?失败: {resp.text}")
                self.failed_tests.append("获取项目详情")
        
        except Exception as e:
            print(f"   �?项目管理测试出错: {e}")
            self.errors.append(f"项目管理测试: {e}")
    
    async def test_file_operations(self):
        """测试文件操作"""
        print("\n" + "=" * 80)
        print("📌 �?部分: 文件操作测试")
        print("=" * 80)
        
        if not self.project_id:
            print("   ⚠️  跳过（没有项�?ID�?)
            return
        
        try:
            # 1. 测试读取初始文件
            print("\n[1/4] 检查项目初始文�?..")
            project_dir = Path(f"workspace/projects/{self.project_id}")
            expected_files = [
                "meta.json", "context.json", "outline.md",
                "style-guide.md", "story-state.md", "recent-context.md"
            ]
            
            found_files = []
            for f in expected_files:
                fpath = project_dir / f
                if fpath.exists():
                    found_files.append(f)
                    print(f"   �?{f}")
                    self.generated_files.append(str(fpath))
                else:
                    print(f"   �?{f} (缺失)")
            
            if len(found_files) == len(expected_files):
                self.passed_tests.append("检查初始文�?)
            else:
                self.failed_tests.append("检查初始文�?)
            
            # 2. 读取并展示大纲文�?            print("\n[2/4] 读取大纲文件...")
            outline_path = project_dir / "outline.md"
            if outline_path.exists():
                content = outline_path.read_text(encoding="utf-8")
                print(f"   �?成功 (长度: {len(content)} 字符)")
                if len(content) > 100:
                    print(f"   预览: {content[:100]}...")
                self.passed_tests.append("读取大纲")
            else:
                print(f"   �?不存�?)
                self.failed_tests.append("读取大纲")
            
            # 3. 编辑并保存文�?            print("\n[3/4] 编辑大纲文件...")
            new_content = (outline_path.read_text(encoding="utf-8") if outline_path.exists() else "") + """

## 第一卷：初入修仙�?
### 第一章：山村少年
在一个偏僻的小山村，主角林凡平静地生活着...

### 第二章：神秘玉佩
一次偶然的机会，林凡得到了一枚神秘的玉佩...

"""
            outline_path.write_text(new_content, encoding="utf-8")
            print(f"   �?成功写入 (新长�? {len(new_content)} 字符)")
            self.passed_tests.append("编辑文件")
            
            # 4. 检查文风指�?            print("\n[4/4] 检查文风指�?..")
            sg_path = project_dir / "style-guide.md"
            if sg_path.exists():
                sg_content = sg_path.read_text(encoding="utf-8")
                print(f"   �?成功 (长度: {len(sg_content)} 字符)")
                self.passed_tests.append("检查文风指�?)
            else:
                print(f"   ⚠️  文风指南不存�?)
        
        except Exception as e:
            print(f"   �?文件操作测试出错: {e}")
            self.errors.append(f"文件操作测试: {e}")
    
    async def test_llm_generation(self):
        """测试 LLM 生成功能"""
        print("\n" + "=" * 80)
        print("📌 �?部分: LLM 生成测试")
        print("=" * 80)
        
        if not self.project_id:
            print("   ⚠️  跳过（没有项�?ID�?)
            return
        
        try:
            # 1. 测试 LLM 配置
            print("\n[1/3] 检�?LLM 配置...")
            try:
                resp = await self.client.get(f"{BASE_URL}/api/llm/config")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"   �?配置获取成功")
                    self.passed_tests.append("获取 LLM 配置")
                else:
                    print(f"   ⚠️  配置端点可能不存�?)
            except Exception:
                print(f"   ⚠️  配置端点可能不存�?)
            
            # 2. 尝试生成章节内容
            print("\n[2/3] 测试 LLM 生成...")
            try:
                # 尝试使用 generate API
                test_messages = [
                    {"role": "system", "content": "你是一个优秀的小说作家，擅长写玄幻修仙小说�?},
                    {"role": "user", "content": "写一段约300字的开篇章节，描写主角在山村的生活和得到神秘玉佩的场景�?}
                ]
                
                # 直接通过我们�?LLM service 测试
                from backend.services.llm_service import LLMService
                llm_service = LLMService()
                
                print("   正在调用 LLM...")
                start_time = time.time()
                result = await llm_service.complete_sync(test_messages)
                elapsed = time.time() - start_time
                
                print(f"   �?LLM 调用成功 (耗时: {elapsed:.1f}�?")
                print(f"   生成内容长度: {len(result)} 字符")
                
                # 保存生成的内�?                chapter_file = Path(f"workspace/projects/{self.project_id}/chapters/test_chapter.md")
                chapter_file.parent.mkdir(exist_ok=True)
                chapter_file.write_text(result, encoding="utf-8")
                self.generated_files.append(str(chapter_file))
                
                print(f"   已保存到: {chapter_file}")
                print(f"   内容预览: {result[:150]}...")
                
                self.passed_tests.append("LLM 生成")
                
            except Exception as e:
                print(f"   �?LLM 生成失败: {e}")
                self.failed_tests.append("LLM 生成")
            
            # 3. 验证 Token 计数
            print("\n[3/3] 测试 Token 计数...")
            try:
                from backend.services.llm_service import LLMService
                llm_service = LLMService()
                test_text = "这是一段测试文本，用于测试 token 计数功能�?
                tokens = await llm_service.count_tokens(test_text)
                print(f"   �?Token 计数: {tokens}")
                self.passed_tests.append("Token 计数")
            except Exception as e:
                print(f"   ⚠️  Token 计数跳过: {e}")
        
        except Exception as e:
            print(f"   �?LLM 生成测试出错: {e}")
            self.errors.append(f"LLM 生成测试: {e}")
    
    async def test_quality_assurance(self):
        """测试质量保障功能"""
        print("\n" + "=" * 80)
        print("📌 �?部分: 质量保障功能测试")
        print("=" * 80)
        
        if not self.project_id:
            print("   ⚠️  跳过（没有项�?ID�?)
            return
        
        try:
            project_dir = Path(f"workspace/projects/{self.project_id}")
            
            # 检查各个质量保障文�?            quality_files = {
                "style-guide.md": "文风指南",
                "story-state.md": "故事状�?,
                "recent-context.md": "近期上下�?
            }
            
            for filename, desc in quality_files.items():
                filepath = project_dir / filename
                if filepath.exists():
                    content = filepath.read_text(encoding="utf-8")
                    print(f"\n�?{desc} ({filename})")
                    print(f"   长度: {len(content)} 字符")
                    if len(content) > 0:
                        print(f"   内容: {content[:80]}...")
                    self.passed_tests.append(f"检�?{desc}")
                else:
                    print(f"\n⚠️  {desc} ({filename}) 不存�?)
            
            # 测试修改日志目录
            revision_dir = project_dir / "revision-log"
            feedback_dir = project_dir / "feedback"
            for d in [revision_dir, feedback_dir]:
                if d.exists():
                    print(f"\n�?{d.name} 目录存在")
                    self.passed_tests.append(f"检�?{d.name} 目录")
                else:
                    print(f"\n⚠️  {d.name} 目录不存�?)
            
        except Exception as e:
            print(f"   �?质量保障测试出错: {e}")
            self.errors.append(f"质量保障测试: {e}")
    
    async def verify_generated_content(self):
        """�?LLM 验证生成的内�?""
        print("\n" + "=" * 80)
        print("📌 �?部分: LLM 内容验证")
        print("=" * 80)
        
        if not self.generated_files:
            print("   ⚠️  没有生成的文件可验证")
            return
        
        try:
            from backend.services.llm_service import LLMService
            llm_service = LLMService()
            
            verified_count = 0
            for filepath in self.generated_files:
                path = Path(filepath)
                if not path.exists():
                    continue
                
                print(f"\n验证: {path.name}...")
                content = path.read_text(encoding="utf-8")
                
                if len(content) < 20:
                    print(f"   ⚠️  内容太短，跳�?)
                    continue
                
                # 构建验证提示
                verify_prompt = f"""请评估以下小说创作相关的文件内容，这是文�? {path.name}

内容:
\"\"\"
{content[:1500]}
\"\"\"

请从以下几个方面评估（只需回答分数 0-10 和简短评价）�?1. 内容完整�?(是否结构完整)
2. 内容质量 (是否符合小说创作要求)
3. 格式规范�?(格式是否正确)

请以 JSON 格式回答，格式如�?
{{"overall_score": 分数, "comments": "简短评�?}}
"""
                
                messages = [{"role": "user", "content": verify_prompt}]
                
                try:
                    result = await llm_service.complete_sync(messages)
                    
                    # 尝试解析 JSON
                    try:
                        # 提取 JSON
                        json_start = result.find("{")
                        json_end = result.rfind("}") + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = result[json_start:json_end]
                            evaluation = json.loads(json_str)
                            score = evaluation.get("overall_score", 0)
                            comments = evaluation.get("comments", "")
                            
                            if score >= 6:
                                print(f"   �?验证通过，评�? {score}/10")
                                print(f"   评价: {comments}")
                                self.passed_tests.append(f"内容验证: {path.name}")
                                verified_count += 1
                            else:
                                print(f"   ⚠️  评分较低: {score}/10")
                                print(f"   评价: {comments}")
                        else:
                            print(f"   �?内容已生成，长度: {len(content)}")
                            print(f"   LLM 评价: {result[:100]}...")
                    except:
                        print(f"   �?内容已生�?(长度: {len(content)} 字符)")
                        
                except Exception as e:
                    print(f"   ⚠️  验证失败: {e}")
            
            print(f"\n验证完成，共验证 {verified_count} 个文�?)
        
        except Exception as e:
            print(f"   �?内容验证测试出错: {e}")
            self.errors.append(f"内容验证测试: {e}")
    
    async def print_report(self):
        """打印测试报告"""
        print("\n" + "=" * 80)
        print("📊 测试结果报告")
        print("=" * 80)
        print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n�?通过的测�?({len(self.passed_tests)}):")
        for i, test in enumerate(self.passed_tests, 1):
            print(f"   {i}. {test}")
        
        if self.failed_tests:
            print(f"\n�?失败的测�?({len(self.failed_tests)}):")
            for i, test in enumerate(self.failed_tests, 1):
                print(f"   {i}. {test}")
        
        if self.errors:
            print(f"\n⚠️  错误 ({len(self.errors)}):")
            for i, err in enumerate(self.errors, 1):
                print(f"   {i}. {err}")
        
        if self.generated_files:
            print(f"\n📝 生成/修改的文�?({len(self.generated_files)}):")
            for f in self.generated_files:
                print(f"   - {f}")
        
        print(f"\n{'=' * 80}")
        if not self.failed_tests and not self.errors:
            print("🎉 所有测试通过�?)
        else:
            print(f"⚠️  �?{len(self.failed_tests)} 个测试失败，{len(self.errors)} 个错�?)
        print(f"{'=' * 80}")


async def main():
    async with MoyunTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())


