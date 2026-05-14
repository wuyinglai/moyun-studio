# 墨韵项目代码改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实施 `代码分析与改进建议.md` 中的所有改进项，按 P0→P1→P2→P3 优先级执行

**Architecture:** 分为前端改进和后端改进两条线，前端重点解决 SSE 通路统一和编辑器竞态问题，后端重点解决测试覆盖和异常体系重构

**Tech Stack:** Python (FastAPI, pytest, pytest-asyncio), TypeScript (Vue 3, Pinia), SSE, CodeMirror 6

---

## 文件结构总览

```
backend/
├── core/
│   ├── exceptions.py          # 修改: FileNotFoundError 重命名
│   ├── pipeline.py            # 修改: 缩小 except Exception 范围
│   └── llm.py                 # 修改: 统一并发控制
├── api/
│   └── config.py              # 修改: API Key 安全改进
tests/
├── test_pipeline.py           # 创建: PipelineRunner 单元测试
├── test_file_service.py       # 创建: FileService 单元测试
└── test_event_bus.py          # 创建: EventBus 单元测试
frontend/src/
├── composables/
│   ├── useSSE.ts              # 修改: 统一 SSE 通路
│   ├── useFileGeneration.ts   # 修改: 移除重复的 SSE 解析逻辑
│   └── useMarkdownPreview.ts  # 创建: Markdown 预览功能
├── components/
│   └── editor/
│       ├── MarkdownEditor.vue # 修改: 移除 setTimeout 重读竞态
│       └── EditorToolbar.vue  # 修改: 管线名称常量提取
├── stores/
│   ├── chat.ts                # 修改: 职责分离
│   └── editor.ts              # 修改: 移除 filePrompts 持久化
├── services/
│   └── api.ts                 # 修改: 添加重试机制
└── utils/
    └── constants.ts            # 创建: 管线名称常量
```

---

## P0 关键改进

### Task 1: 统一 SSE 事件通路

**Files:**
- Modify: `frontend/src/composables/useSSE.ts:1-382`
- Modify: `frontend/src/composables/useFileGeneration.ts:1-181`

- [ ] **Step 1: 分析现状并设计统一方案**

当前两套通路:
1. `useSSE.ts` - EventSource 订阅 `/api/sse`
2. `useFileGeneration.ts` + `chat.ts` - fetch + ReadableStream 直接调用管线 API

方案: **统一为 fetch + ReadableStream 一条通路**，理由:
- 支持 AbortController 取消请求
- 事件解析逻辑集中在一处
- 与现有 `useFileGeneration.ts` 的 `parseSSEStream` 复用

- [ ] **Step 2: 修改 useFileGeneration.ts - 扩展为全局事件分发中心**

```typescript
// useFileGeneration.ts 新增
class GenerationEmitter extends EventTarget {
  emit(type: string, data: any) {
    this.dispatchEvent(new CustomEvent(type, { detail: data }))
  }
}

export const generationEmitter = new GenerationEmitter()
```

- [ ] **Step 3: 修改 useSSE.ts - 改为接收 generationEmitter 事件**

将 SSE 事件处理中的 `generation` 事件改为监听 `generationEmitter`

- [ ] **Step 4: 修改 EditorToolbar.vue - 移除 setTimeout(500) 重读逻辑**

在 `createAndGenerateFile` 完成后，通过 `generationEmitter` 推送内容，移除 `setTimeout`

- [ ] **Step 5: 测试 SSE 通路**

启动后端和前端，执行润色/生成操作，验证内容正确写入编辑器且无重复

---

### Task 2: 修复编辑器内容同步竞态条件

**Files:**
- Modify: `frontend/src/components/editor/MarkdownEditor.vue:172-186`
- Modify: `frontend/src/stores/editor.ts`

- [ ] **Step 1: 分析竞态根源**

当前问题:
1. `_externalUpdate` 防环标记在 `nextTick` 后重置，但管线流式写入可能在此期间发生
2. `setTimeout(500)` 从磁盘重读会覆盖用户本地编辑

- [ ] **Step 2: 实现内容来源标记**

```typescript
// editor.ts 新增
type ContentSource = 'local' | 'external'

// 编辑器状态
const contentSource = ref<ContentSource>('local')

// 流式写入时标记来源
function appendContentExternal(path: string, content: string) {
  contentSource.value = 'external'
  appendContentToFile(path, content)
  nextTick(() => { contentSource.value = 'local' })
}
```

- [ ] **Step 3: 修改 MarkdownEditor.vue 监听逻辑**

```typescript
watch(
  () => fileStore.currentFile ? editorStore.contents[fileStore.currentFile.path] : undefined,
  (content) => {
    if (content === undefined || !editorView) return
    const current = editorView.state.doc.toString()
    if (current !== content && contentSource.value === 'external') {
      editorView.dispatch({
        changes: { from: 0, to: current.length, insert: content },
      })
    }
  }
)
```

- [ ] **Step 4: 移除 EditorToolbar.vue 中的 setTimeout 重读**

- [ ] **Step 5: 验证修复**

执行生成操作，同时在编辑器中输入文字，检查是否有覆盖现象

---

### Task 3: 后端测试覆盖率

**Files:**
- Create: `tests/test_pipeline.py`
- Create: `tests/test_file_service.py`
- Create: `tests/test_event_bus.py`
- Modify: `backend/core/pipeline.py` (如需要 mock)

- [ ] **Step 1: 创建 PipelineRunner 单元测试**

```python
# tests/test_pipeline.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.core.pipeline import PipelineRunner

@pytest.fixture
def mock_llm_service():
    service = MagicMock()
    service.complete = AsyncMock(return_value=iter(["测试", "输出"]))
    return service

@pytest.fixture
def mock_file_service():
    service = MagicMock()
    service.read_file = AsyncMock(return_value=("文件内容", None))
    service.write_file = AsyncMock()
    return service

@pytest.fixture
def pipeline_runner(mock_llm_service, mock_file_service, tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    return PipelineRunner(prompts_dir, mock_llm_service, mock_file_service)

async def test_pipeline_runs_steps(pipeline_runner, tmp_path):
    # 创建测试用 pipeline YAML
    pipeline_dir = tmp_path / "prompts" / "pipeline"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "test.yaml").write_text("""
name: test
label: 测试管线
steps:
  - id: step1
    label: 第一步
    prompt: pipeline/test/step1
""")
    (pipeline_dir / "test").mkdir()
    (pipeline_dir / "test" / "step1.md").write_text("{{ file_content }}")

    events = []
    async for event in pipeline_runner.run("test", "project-1", "test.md"):
        events.append(event)

    assert any(e["event"] == "task_start" for e in events)
    assert any(e["event"] == "done" for e in events)
```

- [ ] **Step 2: 创建 FileService 单元测试**

```python
# tests/test_file_service.py
import pytest
import json
from backend.core.file_ops import FileService

@pytest.fixture
def file_service(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return FileService(workspace)

async def test_read_file_with_frontmatter(file_service, tmp_path):
    project_dir = tmp_path / "workspace" / "test-project"
    project_dir.mkdir(parents=True)
    file_path = project_dir / "test.md"
    file_path.write_text("---\ntitle: Test\n---\n\n正文内容")

    content, fm = await file_service.read_file("test-project/test.md")
    assert content == "\n正文内容"
    assert fm["title"] == "Test"
```

- [ ] **Step 3: 创建 EventBus 单元测试**

```python
# tests/test_event_bus.py
import pytest
from backend.core.event_bus import EventBus

@pytest.fixture
def event_bus():
    return EventBus()

def test_subscribe_and_publish(event_bus):
    received = []
    unsub = event_bus.subscribe("test_event", lambda d: received.append(d))
    event_bus.publish("test_event", {"value": 1})
    assert len(received) == 1
    assert received[0]["value"] == 1
    unsub()
    event_bus.publish("test_event", {"value": 2})
    assert len(received) == 1  # 未订阅后不再接收
```

- [ ] **Step 4: 运行所有测试验证**

```bash
cd D:\newmoyun
pytest tests/ -v --tb=short
```

---

## P1 重要改进

### Task 4: Chat Store 职责分离

**Files:**
- Modify: `frontend/src/stores/chat.ts:1-352`

- [ ] **Step 1: 分析 Chat Store 当前职责**

当前问题:
- `chat.ts` 既管消息列表，又管编辑器写入
- `continueWriting` 和 `rewriteContent` 中调用 `reloadFileIntoEditor`

- [ ] **Step 2: 移除 Chat Store 中的编辑器写入逻辑**

```typescript
// 移除 continueWriting 和 rewriteContent 中的:
// await reloadFileIntoEditor(projectId, filePath)

// 移除 reloadFileIntoEditor 函数
// 保留 sendMessage (聊天消息) 和 cancelStream
```

- [ ] **Step 3: 将 reloadFileIntoEditor 移到 useFileGeneration.ts**

```typescript
// useFileGeneration.ts 新增
export async function reloadFileIntoEditor(projectId: string, filePath: string) {
  const fileStore = useFileStore()
  const editorStore = useEditorStore()
  const result = await fileStore.readFile(projectId, filePath)
  if (result?.content) {
    editorStore.loadContent(filePath, result.content)
  }
}
```

- [ ] **Step 4: 验证聊天续写功能正常**

---

### Task 5: FileNotFoundError 重命名

**Files:**
- Modify: `backend/core/exceptions.py:67-79`

- [ ] **Step 1: 将 FileNotFoundError 重命名为 MoyunFileNotFoundError**

```python
# exceptions.py
class MoyunFileNotFoundError(MoyunFileError):
    """文件不存在（code: FILE_NOT_FOUND，对应 HTTP 404）"""

    def __init__(self, file_path: str):
        super().__init__(
            f"文件不存在: {file_path}",
            {"file_path": file_path},
        )
        self.code = "FILE_NOT_FOUND"
```

- [ ] **Step 2: 在所有使用处更新导入**

搜索所有 `from backend.core.exceptions import FileNotFoundError`，更新为 `MoyunFileNotFoundError`

- [ ] **Step 3: 验证后端启动正常**

```bash
cd D:\newmoyun\backend
uvicorn backend.main:app --reload
```

---

### Task 6: 统一 LLM 并发控制

**Files:**
- Modify: `backend/core/llm.py`
- Modify: `backend/api/main.py`

- [ ] **Step 1: 实现 Semaphore 并发控制**

```python
# backend/core/llm.py
import asyncio

class LLMService:
    def __init__(self, config: dict):
        # ...
        self._semaphore = asyncio.Semaphore(3)  # 最多 3 个并发

    async def complete(self, messages, **kwargs):
        async with self._semaphore:
            # 原有 LLM 调用逻辑
            pass
```

- [ ] **Step 2: 实现 RateLimitError 中间件**

```python
# backend/api/middleware.py
from backend.core.exceptions import RateLimitError

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 根据 IP 或用户限流
    response = await call_next(request)
    return response
```

- [ ] **Step 3: 测试并发控制**

启动多个并发请求，验证超出限制时返回 429 状态码

---

### Task 7: 减少前端 `any` 类型

**Files:**
- Modify: `frontend/src/composables/useSSE.ts`
- Modify: `frontend/src/stores/file.ts`
- Modify: `frontend/src/stores/editor.ts`

- [ ] **Step 1: 定义 SSE 事件联合类型**

```typescript
// types/sse.ts
export type SSEEvent =
  | { type: 'generation'; delta?: string; content?: string; taskId?: string }
  | { type: 'file-created'; path: string; name?: string }
  | { type: 'file-updated'; path: string; content?: string }
  | { type: 'task'; taskId: string; status: TaskStatus; name?: string }
  | { type: 'error'; message: string }
  | { type: 'done'; message?: string }
```

- [ ] **Step 2: 替换 useSSE.ts 中的 `data: any`**

```typescript
// useSSE.ts
private handleEvent(type: SSEEventType, data: SSEEventData) {
  // 使用具体类型而非 any
}
```

- [ ] **Step 3: 替换 stores/file.ts 中的 `api.get<any>`**

```typescript
// file.ts
const data = await api.get<FileContent>('/file', { params: { project_id, path } })
```

- [ ] **Step 4: 验证 TypeScript 编译无错误**

```bash
cd D:\newmoyun\frontend
npx vue-tsc --noEmit
```

---

### Task 8: 添加 Markdown 预览功能

**Files:**
- Create: `frontend/src/composables/useMarkdownPreview.ts`
- Modify: `frontend/src/components/editor/EditorToolbar.vue`

- [ ] **Step 1: 创建 useMarkdownPreview composable**

```typescript
// composables/useMarkdownPreview.ts
import { ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function useMarkdownPreview() {
  const isPreviewMode = ref(false)
  const previewHtml = ref('')

  function togglePreview(content: string) {
    isPreviewMode.value = !isPreviewMode.value
    if (isPreviewMode.value) {
      const rawHtml = marked.parse(content) as string
      previewHtml.value = DOMPurify.sanitize(rawHtml)
    }
  }

  return { isPreviewMode, previewHtml, togglePreview }
}
```

- [ ] **Step 2: 在 EditorToolbar 添加预览按钮**

- [ ] **Step 3: 在 MarkdownEditor 添加预览面板**

- [ ] **Step 4: 测试预览功能**

---

## P2 次要改进

### Task 9: 任务队列持久化

**Files:**
- Modify: `backend/core/task_queue.py`

- [ ] **Step 1: 设计任务队列持久化格式**

```python
# <project>/.task-queue/<task_id>.json
{
  "id": "task-xxx",
  "status": "pending",
  "name": "润色: 第一章.md",
  "created_at": "2026-05-14T10:00:00Z",
  "data": {}
}
```

- [ ] **Step 2: 实现队列恢复逻辑**

```python
async def restore_queue(self, project_id: str):
    queue_dir = Path(f"workspace/projects/{project_id}/.task-queue")
    if not queue_dir.exists():
        return
    for task_file in queue_dir.glob("*.json"):
        task_data = json.loads(task_file.read_text())
        if task_data["status"] in ("pending", "running"):
            task_data["status"] = "pending"
            self.enqueue(task_data)
```

- [ ] **Step 3: 测试队列持久化**

---

### Task 10: 缩小 except Exception 范围

**Files:**
- Modify: `backend/core/pipeline.py`

- [ ] **Step 1: 识别所有宽泛异常捕获**

```python
# 当前问题代码:
except Exception:
    pass
except Exception as e:
    logger.warning(...)
```

- [ ] **Step 2: 替换为具体异常类型**

```python
# _resolve_references
except FileNotFoundError:
    replacement = f"\n<!-- 文件 {file_path} 不存在 -->\n"

# _load_project_meta
except (json.JSONDecodeError, KeyError) as e:
    logger.warning("解析 meta.json 失败: %s", e)
```

- [ ] **Step 3: 验证修改后功能正常**

---

### Task 11: 前端请求重试机制

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 添加 axios 拦截器重试逻辑**

```typescript
// api.ts
import axios from 'axios'

const api = axios.create({ /* ... */ })

api.interceptors.response.use(
  response => response,
  async error => {
    const config = error.config
    if (!config || error.response?.status !== 429) {
      return Promise.reject(error)
    }
    // 重试最多 3 次
    config.__retryCount = config.__retryCount || 0
    if (config.__retryCount >= 3) {
      return Promise.reject(error)
    }
    config.__retryCount++
    const delay = Math.pow(2, config.__retryCount) * 1000
    await new Promise(r => setTimeout(r, delay))
    return api(config)
  }
)
```

- [ ] **Step 2: 测试重试机制**

---

### Task 12: 跨文件搜索和键盘快捷键

**Files:**
- Create: `frontend/src/composables/useSearch.ts`
- Modify: `frontend/src/components/editor/MarkdownEditor.vue`

- [ ] **Step 1: 实现全文搜索**

```typescript
// composables/useSearch.ts
export function useSearch() {
  async function searchInProject(projectId: string, query: string): Promise<SearchResult[]> {
    const results = await api.post('/search', { project_id: projectId, query })
    return results
  }
}
```

- [ ] **Step 2: 添加 Ctrl+P 文件切换**

```typescript
// MarkdownEditor.vue
function handleKeyDown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'p') {
    e.preventDefault()
    // 打开文件切换面板
  }
}
```

- [ ] **Step 3: 添加 Ctrl+F 搜索**

---

## P3 其他改进

### Task 13: 迁移到 watchfiles

**Files:**
- Modify: `backend/core/file_watcher.py`

- [ ] **Step 1: 替换 watchdog 为 watchfiles**

```python
# file_watcher.py
import watchfiles

async def watch_directory(path: str, callback):
    async for changes in watchfiles.watch(path):
        for change in changes:
            callback(change)
```

---

### Task 14: Prompts 版本管理

**Files:**
- Create: `backend/core/prompt_versioning.py`

- [ ] **Step 1: 实现 prompts 归档逻辑**

```python
# prompts/.archive/<timestamp>/...
```

---

### Task 15: 结构化日志

**Files:**
- Modify: `backend/core/pipeline.py`

- [ ] **Step 1: 按级别区分日志**

```python
logger.info("管线执行完成: %s", pipeline_name)  # 正常流程
logger.warning("文件不存在，使用默认值: %s", path)  # 可恢复
logger.error("LLM 调用失败: %s", e)  # 不可恢复
```

---

### Task 16: 管线名称常量化和组件加载态

**Files:**
- Create: `frontend/src/utils/constants.ts`
- Modify: `frontend/src/components/editor/EditorToolbar.vue`

- [ ] **Step 1: 创建常量文件**

```typescript
// utils/constants.ts
export const PIPELINE_NAMES = {
  POLISH: 'polish',
  GENERATE: 'generate',
  REWRITE: 'rewrite',
  EXTRACT: 'extract',
} as const
```

- [ ] **Step 2: 替换 EditorToolbar 中的硬编码字符串**

- [ ] **Step 3: 添加组件加载态**

---

## 执行顺序

1. **Task 1 (SSE 统一)** → Task 2 (编辑器竞态) → Task 3 (测试覆盖)
2. **Task 5 (FileNotFoundError 重命名)** → Task 4 (Chat Store 分离) → Task 6-8
3. **Task 9-12** → Task 13-16

每个 Task 内按 Step 顺序执行。
