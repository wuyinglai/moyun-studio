"""测试 LLM 连接"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_llm():
    from backend.services.llm_service import LLMService
    
    print("=== 墨韵 LLM 测试 ===")
    
    llm_service = LLMService()
    
    print(f"Provider: {llm_service.provider}")
    print(f"Model: {llm_service.model}")
    print(f"API Base: {llm_service.api_base}")
    
    # 测试连接
    print("\n正在测试连接...")
    result = await llm_service.test_connection()
    print(f"结果: {result}")
    
    if result.get("success"):
        print("\n✓ LLM 连接成功！")
        return True
    else:
        print("\n✗ LLM 连接失败")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_llm())
    sys.exit(0 if success else 1)
