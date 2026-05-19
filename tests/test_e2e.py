"""端到端测试脚�?""
import requests
import json

BASE_URL = "http://127.0.0.1:8002"

def test_llm_config():
    """测试1: LLM配置"""
    print("=== 测试1: LLM配置 ===")
    resp = requests.get(f"{BASE_URL}/api/llm/config")
    print(f"GET /api/llm/config: {resp.json()}")

    # 保存配置
    config = {
        "api_type": "deepseek",
        "api_url": "https://api.deepseek.com",
        "api_key": "sk-test-placeholder",
        "model": "deepseek/deepseek-v4-flash",
        "thinking": False
    }
    resp = requests.post(f"{BASE_URL}/api/llm/config", json=config)
    print(f"POST /api/llm/config: {resp.json()}")

    # 测试连接
    resp = requests.post(f"{BASE_URL}/api/llm/test")
    result = resp.json()
    print(f"POST /api/llm/test: {result}")
    print(f"LLM连接状�? {'�?成功' if result['data']['connected'] else '�?失败'}")
    return result['data']['connected']

def test_projects():
    """测试2: 项目管理"""
    print("\n=== 测试2: 项目管理 ===")

    # 创建项目
    project_data = {
        "name": "E2E测试玄幻小说",
        "author": "阿来",
        "genre": "玄幻",
        "tone": "热血",
        "background": "异世�?,
        "theme": "冒险",
        "writing_style": "网络文学",
        "target_word_count": 100000
    }
    resp = requests.post(f"{BASE_URL}/api/projects", json=project_data)
    print(f"POST /api/projects: {resp.status_code}")
    if resp.status_code == 201:
        project = resp.json()['data']
        print(f"�?项目创建成功: {project['project_id']} - {project['name']}")
        project_id = project['project_id']
    else:
        print(f"�?创建失败: {resp.text}")
        return None

    # 获取项目列表
    resp = requests.get(f"{BASE_URL}/api/projects")
    data = resp.json()
    print(f"GET /api/projects: 共有 {data['data']['total']} 个项�?)

    # 获取文件�?    resp = requests.get(f"{BASE_URL}/api/tree?project_id={project_id}")
    tree = resp.json()['data']
    print(f"GET /api/tree: 项目包含 {len(tree.get('tree', []))} 个根项目/目录")

    return project_id

def test_file_operations(project_id):
    """测试3: 文件操作"""
    print(f"\n=== 测试3: 文件操作 (项目: {project_id}) ===")

    # 读取大纲文件
    resp = requests.get(f"{BASE_URL}/api/file?project_id={project_id}&path=outline.md")
    if resp.status_code == 200:
        content = resp.json()['data']
        print(f"GET /api/file outline.md: �?读取成功 ({len(content)} 字符)")
    else:
        print(f"GET /api/file outline.md: �?失败")

def test_llm_generation():
    """测试4: LLM生成"""
    print("\n=== 测试4: LLM生成测试 ===")

    # 简单聊天测�?    resp = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "project_id": "test",
            "message": "用一句话描述秋天的黄�?
        },
        stream=True,
        timeout=30
    )
    print(f"POST /api/chat: {resp.status_code}")
    if resp.status_code == 200:
        # 收集流式响应
        content = ""
        for line in resp.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    data = json.loads(line[5:])
                    if 'delta' in data:
                        content += data['delta']
        print(f"�?AI回复: {content[:100]}...")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 墨韵 - 端到端集成测�?)
    print("=" * 60)

    connected = test_llm_config()
    if not connected:
        print("\n⚠️  LLM未连接，跳过部分测试")

    project_id = test_projects()
    if project_id:
        test_file_operations(project_id)

    test_llm_generation()

    print("\n" + "=" * 60)
    print("�?端到端测试完�?)
    print("=" * 60)

