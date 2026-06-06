"""
T4.7.1a-2b：E2E 环境健康检查脚本
"""
import asyncio
import aiohttp
import sys
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
PROJECT_ID = "demo-novel"
TEST_FILE = "scenes/chapters/vol-01/ch-001/sec-001.md"


async def check_api(session, name, url):
    print(f"\n--- {name} ---")
    print(f"URL: {url}")
    try:
        async with session.get(url, timeout=30) as resp:
            print(f"Status: {resp.status}")
            content = await resp.text()
            print(f"Response Length: {len(content)} chars")
            if resp.status == 200:
                try:
                    data = await resp.json()
                    print(f"Response Keys: {list(data.keys()) if isinstance(data, dict) else 'LIST/OTHER'}")
                except:
                    pass
            else:
                print(f"Response: {content[:200]}")
            return resp.status
    except Exception as e:
        print(f"Error: {type(e)} - {str(e)}")
        return -1


async def main():
    print("\n" + "="*80)
    print("T4.7.1a-2b：E2E 环境健康检查")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    async with aiohttp.ClientSession() as session:
        # 1. 检查后端根路径
        print("\n--- Backend Root ---")
        print(f"URL: {BACKEND_URL}/")
        try:
            async with session.get(f"{BACKEND_URL}/", timeout=30) as resp:
                print(f"Status: {resp.status}")
        except Exception as e:
            print(f"Error: {type(e)} - {str(e)}")

        # 2. 检查项目列表
        await check_api(session, "Project List", f"{BACKEND_URL}/api/projects")
        
        # 3. 检查 demo-novel 项目详情
        await check_api(session, "Project Detail", f"{BACKEND_URL}/api/projects/{PROJECT_ID}")
        
        # 4. 检查文件读取
        await check_api(session, "File Read", f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE}")
        
        # 5. 检查 candidate 列表
        await check_api(session, "Candidate List", f"{BACKEND_URL}/api/candidates/{PROJECT_ID}")

    print("\n" + "="*80)
    print("检查完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
