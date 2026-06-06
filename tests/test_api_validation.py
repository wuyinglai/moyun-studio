"""
T4.7.1a API 验证脚本
==================

验证文件 API 和 candidate API 是否正常工作。
"""

import asyncio
import aiohttp
import uuid
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
PROJECT_ID = "demo-novel"
TEST_FILE_PATH = "scenes/__e2e_candidate_test_scene.md"

CONTENT_INITIAL = """T4.7.1a initial source content

这是测试文件的初始内容。

雨没有停的意思。林澈站在旧港站入口的铁栅前，雨水顺着伞骨汇成一条线，砸在脚边的水洼里。
"""

CONTENT_CONFLICT = """T4.7.1a conflict source content

这是测试文件的冲突内容（用于制造冲突）。

铁栅没有上锁，铰链发出一声尖锐的呻吟，在雨幕中显得格外刺耳。
"""

CONTENT_CANDIDATE = """T4.7.1a E2E candidate replacement content

这是候选稿的替换内容。

站台的灯早已不亮。黑暗中，只有应急指示牌的绿色微光若隐若现。
"""


async def test_file_api():
    """测试文件 API"""
    print("\n" + "="*80)
    print("Step 1: 测试文件 API")
    print("="*80)

    async with aiohttp.ClientSession() as session:
        # 1. 创建文件
        print("\n1. 创建文件...")
        async with session.post(
            f"{BACKEND_URL}/api/file/create",
            json={
                "project_id": PROJECT_ID,
                "path": TEST_FILE_PATH,
                "content": CONTENT_INITIAL
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            print(f"   响应状态: {resp.status}")
            if resp.status in [200, 201]:
                data = await resp.json()
                print(f"   ✅ 文件创建成功")
                print(f"   响应: {str(data)[:200]}")
            else:
                text = await resp.text()
                print(f"   ⚠️ 文件创建响应: {text[:200]}")

        # 2. 读取文件
        print("\n2. 读取文件...")
        async with session.get(
            f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
        ) as resp:
            print(f"   响应状态: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"   ✅ 文件读取成功")
                print(f"   字段: {list(data.keys())}")
                print(f"   content 长度: {len(data.get('content', ''))}")
                print(f"   hash: {data.get('hash', 'N/A')}")
                print(f"   mtime: {data.get('mtime', 'N/A')}")
                print(f"   content 前 50 字: {data.get('content', '')[:50]}")
            else:
                text = await resp.text()
                print(f"   ❌ 文件读取失败: {text[:200]}")

        # 3. 修改文件
        print("\n3. 修改文件...")
        async with session.get(
            f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                current_hash = data.get("hash", "")
                current_mtime = data.get("mtime", 0)

                async with session.post(
                    f"{BACKEND_URL}/api/file",
                    json={
                        "project_id": PROJECT_ID,
                        "path": TEST_FILE_PATH,
                        "content": CONTENT_CONFLICT,
                        "expected_hash": current_hash,
                        "expected_mtime": current_mtime
                    },
                    headers={"Content-Type": "application/json"}
                ) as resp2:
                    print(f"   响应状态: {resp2.status}")
                    if resp2.status in [200, 201]:
                        print(f"   ✅ 文件修改成功")
                    else:
                        text = await resp2.text()
                        print(f"   ⚠️ 文件修改响应: {text[:200]}")

        # 4. 再次读取（验证修改）
        print("\n4. 再次读取文件（验证修改）...")
        async with session.get(
            f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"   ✅ 文件读取成功")
                print(f"   content 前 50 字: {data.get('content', '')[:50]}")
                print(f"   hash: {data.get('hash', 'N/A')}")

        # 5. 恢复到初始内容
        print("\n5. 恢复到初始内容...")
        async with session.get(
            f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                current_hash = data.get("hash", "")
                current_mtime = data.get("mtime", 0)

                async with session.post(
                    f"{BACKEND_URL}/api/file",
                    json={
                        "project_id": PROJECT_ID,
                        "path": TEST_FILE_PATH,
                        "content": CONTENT_INITIAL,
                        "expected_hash": current_hash,
                        "expected_mtime": current_mtime
                    },
                    headers={"Content-Type": "application/json"}
                ) as resp2:
                    if resp2.status in [200, 201]:
                        print(f"   ✅ 文件已恢复")
                    else:
                        text = await resp2.text()
                        print(f"   ⚠️ 恢复响应: {text[:200]}")


async def test_candidate_api():
    """测试 Candidate API"""
    print("\n" + "="*80)
    print("Step 2: 测试 Candidate API")
    print("="*80)

    candidate_id = f"cand_{uuid.uuid4().hex[:8]}"

    async with aiohttp.ClientSession() as session:
        # 1. 创建 candidate
        print("\n1. 创建 candidate...")
        async with session.post(
            f"{BACKEND_URL}/api/candidates/{PROJECT_ID}",
            json={
                "project_id": PROJECT_ID,
                "source_path": TEST_FILE_PATH,
                "action": "polish",
                "content": CONTENT_CANDIDATE,
                "workflow_run_id": f"test-run-{candidate_id}",
                "model": "test-model",
                "pipeline_id": "test-pipeline",
                "source_mode": "test"
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            print(f"   响应状态: {resp.status}")
            if resp.status in [200, 201]:
                data = await resp.json()
                print(f"   ✅ Candidate 创建成功")
                print(f"   id: {data.get('id')}")
                print(f"   source_path: {data.get('source_path')}")
                print(f"   action: {data.get('action')}")
                print(f"   status: {data.get('status')}")
                print(f"   base_hash: {data.get('base_hash', '')[:16] if data.get('base_hash') else 'N/A'}...")
                print(f"   base_mtime: {data.get('base_mtime')}")
                created_candidate_id = data.get("id")
            else:
                text = await resp.text()
                print(f"   ❌ Candidate 创建失败: {text[:300]}")
                return None

        # 2. 列出 candidates
        print("\n2. 列出 candidates...")
        async with session.get(
            f"{BACKEND_URL}/api/candidates/{PROJECT_ID}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                candidates = data.get("candidates", [])
                print(f"   ✅ 找到 {len(candidates)} 个候选稿")
                for c in candidates:
                    if c.get("source_path") == TEST_FILE_PATH:
                        print(f"   - id: {c.get('id')}, action: {c.get('action')}, status: {c.get('status')}")

        # 3. 获取 candidate 详情
        print("\n3. 获取 candidate 详情...")
        async with session.get(
            f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{created_candidate_id}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                candidate = data.get("candidate", {})
                print(f"   ✅ Candidate 详情")
                print(f"   id: {candidate.get('id')}")
                print(f"   source_path: {candidate.get('source_path')}")
                print(f"   base_hash: {candidate.get('base_hash', '')[:16] if candidate.get('base_hash') else 'N/A'}...")
                print(f"   base_mtime: {candidate.get('base_mtime')}")
                print(f"   content 长度: {len(data.get('content', ''))}")
                print(f"   content 前 50 字: {data.get('content', '')[:50]}")
            else:
                text = await resp.text()
                print(f"   ❌ 获取详情失败: {text[:200]}")

        # 4. 测试 adopt（非冲突场景）
        print("\n4. 测试 adopt（非冲突场景）...")
        async with session.post(
            f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{created_candidate_id}/adopt",
            headers={"Content-Type": "application/json"}
        ) as resp:
            print(f"   响应状态: {resp.status}")
            if resp.status in [200, 201]:
                data = await resp.json()
                print(f"   ✅ adopt 成功")
                print(f"   success: {data.get('success')}")
                print(f"   conflict: {data.get('conflict')}")
                print(f"   message: {data.get('message')}")
            else:
                text = await resp.text()
                print(f"   ⚠️ adopt 响应: {text[:200]}")

        # 5. 验证文件已被修改
        print("\n5. 验证文件已被修改...")
        async with session.get(
            f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                content = data.get("content", "")
                if CONTENT_CANDIDATE[:50] in content:
                    print(f"   ✅ 文件内容已被 candidate 替换")
                else:
                    print(f"   ⚠️ 文件内容未被替换")

        # 6. 清理：删除测试文件
        print("\n6. 清理：删除测试文件...")
        # 先恢复到初始内容，然后删除
        async with session.get(
            f"{BACKEND_URL}/api/file?project_id={PROJECT_ID}&path={TEST_FILE_PATH}"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                current_hash = data.get("hash", "")

                # 使用 file delete API 或恢复到初始内容
                # 这里我们恢复到初始内容而不是删除
                async with session.post(
                    f"{BACKEND_URL}/api/file",
                    json={
                        "project_id": PROJECT_ID,
                        "path": TEST_FILE_PATH,
                        "content": CONTENT_INITIAL,
                        "expected_hash": current_hash
                    },
                    headers={"Content-Type": "application/json"}
                ) as resp2:
                    if resp2.status in [200, 201]:
                        print(f"   ✅ 文件已恢复到初始内容")


async def main():
    print("="*80)
    print("T4.7.1a API 验证")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Test File: {TEST_FILE_PATH}")

    await test_file_api()
    await test_candidate_api()

    print("\n" + "="*80)
    print("API 验证完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
