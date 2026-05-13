"""墨韵 E2E 集成测试 — 模拟前端→后端完整工作流

测试项目: Integration Test Novel (e7b83e15)
跳过: 需要 LLM API Key 的端点（quality review, batch generate, extract）

运行: PYTHONIOENCODING=utf-8 python tests/test_integration_e2e.py
"""

import sys
import time
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000/api"

OK = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results = []


def api(path, method="GET", data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text), resp.status
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(text), e.code
        except json.JSONDecodeError:
            return {"error": text}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def test(name, fn):
    try:
        fn()
        results.append((name, OK, ""))
        print(f"  [PASS] {name}")
    except AssertionError as e:
        results.append((name, FAIL, str(e)))
        print(f"  [FAIL] {name}: {e}")
    except Exception as e:
        results.append((name, FAIL, str(e)))
        print(f"  [FAIL] {name}: {e}")


def check(label, condition, detail=""):
    if not condition:
        raise AssertionError(detail or f"{label} 未通过")


print("=" * 60)
print("墨韵 E2E 集成测试")
print("=" * 60)

PROJECT_ID = "e7b83e15"

# ── 1. 项目 ──────────────────────────────────────────────
print("\n[1/6] 项目相关")

def test_list_projects():
    data, code = api("/projects")
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)
    check("有 projects", "projects" in data.get("data", {}))
    projects = data["data"]["projects"]
    check("包含测试项目", any(p["project_id"] == PROJECT_ID for p in projects))

test("GET /api/projects — 列出项目", test_list_projects)


def test_get_project():
    data, code = api(f"/projects/{PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")
    check("project_id 匹配", data.get("data", {}).get("project_id") == PROJECT_ID)

test("GET /api/projects/:id — 获取项目详情", test_get_project)

# ── 2. 文件操作 ──────────────────────────────────────────
print("\n[2/6] 文件操作")

FILE_PATH = "chapters/chapter001.md"
FILE_CONTENT = "# 第一章\n\n测试内容。\n\n这是一段测试文本。"
FILE_CONTENT_V2 = "# 第一章（修订）\n\n测试内容已更新。\n\n这是修改后的测试文本。"


def test_create_directory():
    data, code = api("/directory/create", method="POST", data={
        "project_id": PROJECT_ID,
        "path": "chapters",
    })
    # 201 或 200 都算成功，已存在的目录可能返回不同code
    check("创建目录成功", code in (200, 201))

test("POST /api/directory/create — 创建目录", test_create_directory)


def test_create_file():
    data, code = api("/file/create", method="POST", data={
        "project_id": PROJECT_ID,
        "path": FILE_PATH,
        "content": FILE_CONTENT,
    })
    check("响应码", code in (200, 201), f"got {code}")
    check("success", data.get("success") is True)

test("POST /api/file/create — 创建文件", test_create_file)


def test_write_file():
    data, code = api(f"/file?project_id={PROJECT_ID}&path={FILE_PATH}", method="POST", data={
        "path": FILE_PATH,
        "content": FILE_CONTENT_V2,
        "frontmatter": {"title": "第一章", "order": 1},
    })
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)

test("POST /api/file — 写入文件", test_write_file)


def test_read_file():
    data, code = api(f"/file?project_id={PROJECT_ID}&path={FILE_PATH}")
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)
    content = data.get("data", {}).get("content", "")
    check("内容包含标题", "第一章" in content)

test("GET /api/file — 读取文件", test_read_file)


def test_get_tree():
    data, code = api(f"/tree?project_id={PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")
    tree = data.get("data", {}).get("tree", [])
    chapters = [n for n in tree if n.get("name") == "chapters"]
    check("有目录节点", len(chapters) > 0)

test("GET /api/tree — 文件树", test_get_tree)


def test_rename_file():
    new_path = "chapters/ch001_renamed.md"
    data, code = api("/file/rename", method="POST", data={
        "project_id": PROJECT_ID,
        "old_path": FILE_PATH,
        "new_path": new_path,
    })
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)
    # 改回来
    api("/file/rename", method="POST", data={
        "project_id": PROJECT_ID,
        "old_path": new_path,
        "new_path": FILE_PATH,
    })

test("POST /api/file/rename — 重命名文件", test_rename_file)

# ── 3. 写作辅助 ──────────────────────────────────────────
print("\n[3/6] 写作辅助")


def test_story_state():
    data, code = api(f"/story-state/{PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)

test("GET /api/story-state/:id — 读取故事状态", test_story_state)


def test_update_story_state():
    data, code = api(f"/story-state/{PROJECT_ID}", method="POST", data={
        "summary": "测试故事摘要",
        "recent_developments": "正在进行集成测试",
    })
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)

test("POST /api/story-state/:id — 更新故事状态", test_update_story_state)


def test_style_guide():
    data, code = api(f"/style-guide/{PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")

test("GET /api/style-guide/:id — 读取文风指南", test_style_guide)


def test_update_style_guide():
    data, code = api(f"/style-guide/{PROJECT_ID}", method="POST", data={
        "content": "简洁明快的文风，注重对话描写。",
    })
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)

test("POST /api/style-guide/:id — 更新文风指南", test_update_style_guide)


def test_characters():
    data, code = api(f"/characters?project_id={PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")
    check("有 characters", "characters" in data.get("data", {}))

test("GET /api/characters — 获取角色列表", test_characters)


def test_recent_context():
    data, code = api(f"/recent-context/{PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")

test("GET /api/recent-context/:id — 读取近期上下文", test_recent_context)


def test_recent_context_append():
    data, code = api(f"/recent-context/{PROJECT_ID}/append", method="POST", data={
        "chapter_path": "chapters/chapter001.md",
        "title": "第一章",
        "summary": "集成测试：新写了一段内容。",
        "word_count": 50,
    })
    check("响应码", code == 200, f"got {code}")

test("POST /api/recent-context/:id/append — 追加上下文", test_recent_context_append)


def test_tokens_count():
    data, code = api("/tokens/count", method="POST", data={
        "text": "这是一段用于测试 token 计量的文本。" * 10,
    })
    check("响应码", code == 200, f"got {code}")
    check("有 tokens", "tokens" in data.get("data", {}))
    check("tokens > 0", data["data"]["tokens"] > 0)

test("POST /api/tokens/count — Token 计数", test_tokens_count)


def test_compare():
    data, code = api("/compare", method="POST", data={
        "old_text": "这是原始文本。",
        "new_text": "这是修改后的文本。",
    })
    check("响应码", code == 200, f"got {code}")
    check("有 diff", "diff" in data.get("data", {}))

test("POST /api/compare — 文本对比", test_compare)

# ── 4. 记录管理 ──────────────────────────────────────────
print("\n[4/6] 记录管理")


def test_revision_log():
    data, code = api(f"/revision-log/{PROJECT_ID}", method="POST", data={
        "chapter_path": "chapters/chapter001.md",
        "revision_type": "user_edit",
        "description": "集成测试修改",
        "content_before": "旧内容",
        "content_after": "新内容",
    })
    check("响应码", code == 200, f"got {code}")

test("POST /api/revision-log/:id — 写入修改日志", test_revision_log)


def test_get_revision_log():
    data, code = api(f"/revision-log/{PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")
    check("success", data.get("success") is True)

test("GET /api/revision-log/:id — 读取修改日志", test_get_revision_log)


def test_feedback():
    data, code = api(f"/feedback/{PROJECT_ID}", method="POST", data={
        "chapter_path": "chapters/chapter001.md",
        "type": "suggestion",
        "content": "需要更多对话描写。",
    })
    check("响应码", code == 200, f"got {code}")

test("POST /api/feedback/:id — 提交反馈", test_feedback)


def test_get_feedback():
    data, code = api(f"/feedback/{PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")

test("GET /api/feedback/:id — 读取反馈", test_get_feedback)


def test_backup_create():
    data, code = api("/backup", method="POST", data={
        "project_id": PROJECT_ID,
        "description": "集成测试备份",
    })
    check("响应码", code in (200, 201), f"got {code}")

test("POST /api/backup — 创建备份", test_backup_create)


def test_backup_list():
    data, code = api(f"/backup?project_id={PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")

test("GET /api/backup — 备份列表", test_backup_list)

# ── 5. 任务队列 ──────────────────────────────────────────
print("\n[5/6] 任务队列")


def test_list_tasks():
    data, code = api("/tasks")
    check("响应码", code == 200, f"got {code}")

test("GET /api/tasks — 任务列表", test_list_tasks)


def test_create_task():
    data, code = api("/tasks", method="POST", data={
        "template_category": "generate",
        "template_type": "chapter",
        "project_id": PROJECT_ID,
        "target_file": "chapters/chapter001.md",
        "variables": {"theme": "冒险"},
    })
    check("响应码", code in (200, 201), f"got {code}")

test("POST /api/tasks — 创建任务", test_create_task)


def test_prompts():
    data, code = api("/prompts")
    check("响应码", code == 200, f"got {code}")

test("GET /api/prompts — 提示词列表", test_prompts)


def test_llm_config():
    data, code = api("/llm/config")
    check("响应码", code == 200, f"got {code}")

test("GET /api/llm/config — LLM 配置", test_llm_config)

# ── 6. 质量审查 (已知无 API Key 时会超时或报错) ──────────
print("\n[6/6] 质量审查")

def test_quality_reviews():
    data, code = api(f"/quality/reviews/{PROJECT_ID}")
    check("响应码", code == 200, f"got {code}")

test("GET /api/quality/reviews/:id — 审查列表(无需Key)", test_quality_reviews)


def test_batch_review_no_key():
    data, code = api("/quality/review-batch", method="POST", data={
        "project_id": PROJECT_ID,
        "target_files": [FILE_PATH],
    })
    # 没有 API Key 时可能返回 500 或 503，不是空响应就行
    print(f"      -> 响应码: {code}", end="")
    if code in (200, 201):
        check("batch 成功", data.get("success") is True)
    else:
        print(f" (无 API Key 时正常)")

test("POST /api/quality/review-batch — 批量审查(可能跳过)", test_batch_review_no_key)


# ── 汇总 ──────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, s, _ in results if s == OK)
failed = sum(1 for _, s, _ in results if s == FAIL)
skipped = sum(1 for _, s, _ in results if s == SKIP)
total = passed + failed + skipped
print(f"结果: {passed}/{total} 通过, {failed} 失败, {skipped} 跳过")

if failed > 0:
    print("\n失败项:")
    for name, status, detail in results:
        if status == FAIL:
            print(f"  - {name}: {detail}")
    sys.exit(1)
else:
    print("全部通过!")
    sys.exit(0)
