# API 契约文档

> 定义墨韵前后端通信规范，所有接口必须严格遵守本文档。
> 
> **依赖对应说明**：
> - FastAPI：所有API端点定义
> - LiteLLM：LLM调用统一接口（/api/llm/*）
> - aiofiles：所有文件读写（/api/file）
> - tiktoken：Token计数接口（/api/tokens/*）
> - pydantic-settings：配置管理（/api/llm/config）
> - watchdog：文件监听（SSE事件 file-*）
> - python-frontmatter：Markdown元数据解析（/api/file）
> - Jinja2：Prompt模板渲染（/api/prompts/*）

---

## 一、设计原则

### 1.1 RESTful 风格
- **GET**：读取资源（不修改数据）
- **POST**：创建资源 / 执行操作
- **PUT**：完整更新资源
- **PATCH**：部分更新资源
- **DELETE**：删除资源

### 1.2 响应格式统一
所有接口返回统一结构：

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "error": null
}
```

**失败响应**：
```json
{
  "success": false,
  "data": null,
  "message": "文件不存在",
  "error": {
    "code": "FILE_NOT_FOUND",
    "details": "projects/demo/sec-001.md"
  }
}
```

### 1.3 状态码规范
| HTTP状态码 | 说明 | 使用场景 |
|-----------|------|----------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 参数错误 |
| 401 | Unauthorized | 未授权（未来扩展） |
| 403 | Forbidden | 权限不足（未来扩展） |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突（如重名） |
| 422 | Unprocessable Entity | 业务逻辑错误 |
| 429 | Too Many Requests | 限流 |
| 500 | Internal Server Error | 服务器错误 |
| 503 | Service Unavailable | LLM服务不可用 |

---

## 二、错误码定义

| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| `SUCCESS` | 成功 | 200 |
| `BAD_REQUEST` | 请求参数错误 | 400 |
| `UNAUTHORIZED` | 未授权 | 401 |
| `FORBIDDEN` | 禁止访问 | 403 |
| `NOT_FOUND` | 资源不存在 | 404 |
| `CONFLICT` | 资源冲突 | 409 |
| `VALIDATION_ERROR` | 数据验证失败 | 422 |
| `RATE_LIMIT` | 请求频率过高 | 429 |
| `INTERNAL_ERROR` | 内部错误 | 500 |
| `SERVICE_UNAVAILABLE` | 服务不可用 | 503 |
| `PROJECT_NOT_FOUND` | 项目不存在 | 404 |
| `FILE_NOT_FOUND` | 文件不存在 | 404 |
| `FILE_ALREADY_EXISTS` | 文件已存在 | 409 |
| `INVALID_TEMPLATE` | 模板格式错误 | 422 |
| `LLM_ERROR` | LLM调用失败 | 503 |
| `LLM_TIMEOUT` | LLM调用超时 | 504 |
| `TEMPLATE_NOT_FOUND` | 模板不存在 | 404 |
| `INVALID_VARIABLE` | 模板变量缺失 | 422 |

---

## 三、API 端点列表

### 3.1 项目管理

#### GET `/api/projects`
**功能**：获取所有项目列表

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "name": "我的小说",
      "path": "projects/20260510120000",
      "created_at": "2026-05-08T10:00:00",
      "updated_at": "2026-05-10T01:30:00",
      "progress": 35.5
    }
  ]
}
```

#### POST `/api/projects`
**功能**：新建项目

**请求体**：
```json
{
    "name": "我的小说",
      "genre": "玄幻",
      "theme": "友情与成长",
      "scale": 100000
    }
    ```

    **响应**：
    ```json
    {
      "success": true,
      "data": {
        "project_id": "20260510120000",
        "path": "projects/20260510120000"
      }
    }
```

#### POST `/api/projects/open`
**功能**：打开项目

**请求体**：
```json
{
  "project_id": "20260510120000"
}
```

#### DELETE `/api/projects/{project_id}`
**功能**：删除项目

---

### 3.2 文件树

#### GET `/api/tree`
**功能**：获取当前项目的文件树

**响应示例**：
```json
{
  "success": true,
  "data": {
    "name": "我的小说",
        "type": "directory",
        "children": [
          {
            "name": "chapters",
            "type": "directory",
            "children": [...]
          },
          {
            "name": "outline.md",
            "type": "file",
            "path": "projects/20260510120000/outline.md"
          }
        ]
      }
    }
    ```

---

### 3.3 文件内容（依赖 aiofiles + python-frontmatter）

#### GET `/api/file`
**功能**：获取文件内容（支持 frontmatter 解析）

**Query参数**：
- `path` (string, required): 文件相对路径

**示例**：`/api/file?path=projects/20260510120000/outline.md`

**响应**：
```json
{
  "success": true,
  "data": {
    "path": "projects/20260510120000/outline.md",
    "content": "# 大纲\n\n...",
    "frontmatter": {  // 由 python-frontmatter 解析
      "title": "大纲",
      "version": "1.0"
    },
    "encoding": "utf-8",
    "last_modified": "2026-05-10T01:30:00"
  }
}
```

#### POST `/api/file`
**功能**：保存文件内容（支持 frontmatter 写入）

**请求体**：
```json
{
  "path": "projects/temp_placeholder_no_match_expected/outline.md",
  "content": "# 大纲\n\n...",
  "frontmatter": {  // 可选，由 python-frontmatter 自动写入头部
    "title": "大纲",
    "version": "1.0"
  },
  "encoding": "utf-8"
}
```

**说明**：
- 如果传入 `frontmatter` 对象，后端使用 **python-frontmatter** 自动合并到文件头部
- 如果文件已包含 frontmatter，会自动更新而非覆盖

#### PUT `/api/file`
**功能**：创建新文件

---

### 3.4 LLM 配置与调用（依赖 LiteLLM + pydantic-settings）

#### GET `/api/llm/config`
**功能**：获取LLM配置

**响应**：
```json
{
  "success": true,
  "data": {
    "provider": "openai",  // 由 LiteLLM 支持：openai / ollama / anthropic / gemini / ...
    "api_base": "https://api.openai.com/v1",
    "model": "gpt-4",
    "thinking": false
  }
}
```

#### POST `/api/llm/config`
**功能**：保存LLM配置（依赖 **LiteLLM**，支持多provider）

**请求体**：
```json
{
  "provider": "openai",  // openai / ollama / anthropic / gemini / bedrock / azure 等100+种
  "api_key": "sk-...",
  "api_base": "https://api.openai.com/v1",  // Ollama可留空
  "model": "gpt-4",
  "thinking": false
}
```

**说明**：
- 后端通过 **LiteLLM** 统一调用，前端无需关心具体实现
- `provider` 支持：openai, ollama, anthropic, gemini, bedrock, azure 等
- Ollama 无需 api_key，api_base 默认为 `http://localhost:11434`
- 保存后触发 SSE 事件 `llm-status`

#### POST `/api/llm/test`
**功能**：测试LLM连接（通过 LiteLLM 测试）

#### GET `/api/llm/models`
**功能**：获取可用模型列表（通过 LiteLLM 获取）

---

### 3.5 LLM 生成

#### POST `/api/generate`
**功能**：提交生成任务

**请求体**：
```json
{
  "project_id": "20260510120000",
  "template": "generate/chapter",
  "variables": {
    "genre": "玄幻",
    "theme": "友情与成长",
    "protagonist": "张三"
  },
  "target_file": "chapters/vol-01/ch-001/sec-001.md"
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "task_id": "task_123456",
    "status": "queued"
  }
}
```

**说明**：
- 所有LLM调用通过 **tenacity** 包装，有自动重试机制
- 重试策略：指数退避，最多3次尝试
- 前端无需关心重试逻辑，后端自动处理
- 任务完成后通过SSE推送 `done` 事件

#### POST `/api/stop`
**功能**：停止当前LLM任务

#### GET `/api/tasks`
**功能**：获取所有任务状态

**响应**：
```json
{
  "success": true,
  "data": {
    "running": [...],
    "queued": [...],
    "completed": [...]
  }
}
```

---

### 3.6 Prompt 模板管理（依赖 Jinja2）

#### GET `/api/prompts`
**功能**：获取所有Prompt模板列表

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "category": "generate",
      "type": "chapter",
      "path": "prompts/generate/chapter",
      "name": "章节生成",
      "variables": ["genre", "theme", "protagonist"]
    }
  ]
}
```

#### GET `/api/prompts/{category}/{type}`
**功能**：获取指定模板内容（Jinja2 语法）

**响应**：
```json
{
  "success": true,
  "data": {
    "meta": {
      "name": "章节生成",
      "variables": {...}
    },
    "content": "请根据以下信息撰写章节：\n\n类型：{{ genre }}\n..."
  }
}
```

#### POST `/api/prompts/{category}/{type}`
**功能**：保存模板（更新main.md和meta.json）

#### POST `/api/prompts/render`
**功能**：渲染模板（测试用，依赖 **Jinja2**）

**请求体**：
```json
{
  "template": "generate/chapter",
  "variables": {
    "genre": "玄幻",
    "theme": "友情与成长"
  }
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "rendered": "请根据以下信息撰写小说章节：\n\n类型：玄幻\n..."
  }
}
```

---

### 3.7 备份与快照

#### GET `/api/backup`
**功能**：获取备份列表

#### POST `/api/backup`
**功能**：创建备份快照

**请求体**：
```json
{
  "project_id": "20260510120000",
  "description": "完成第一章后备份"
}
```

#### POST `/api/backup/restore`
**功能**：恢复备份

---

### 3.8 角色管理

#### GET `/api/characters`
**功能**：获取角色列表

#### GET `/api/characters/{character_id}`
**功能**：获取角色详情

#### POST `/api/characters`
**功能**：创建/更新角色

#### DELETE `/api/characters/{character_id}`
**功能**：将角色标记为 inactive（不提供物理删除）

**说明**：
- 文件不支持物理删除，只能标记为 inactive
- 通过 PATCH 请求更新 status 字段

---

### 3.9 提取结果

#### GET `/api/materials/{type}`
**功能**：获取提取结果列表（如 plots, scenes, summaries）

**示例**：`/api/materials/plots`

#### GET `/api/materials/{type}/{id}`
**功能**：获取提取结果详情

#### POST `/api/extract`
**功能**：提交提取任务

**请求体**：
```json
{
  "project_id": "20260510120000",
  "type": "plot",
  "source_file": "chapters/vol-01/ch-001/sec-001.md"
}
```

---

### 3.10 文风指南管理

#### GET `/api/style-guide`
**功能**：获取文风指南内容

**响应**：
```json
{
  "success": true,
  "data": {
    "content": "# 文风指南\n\n## 整体风格\n- 语言风格：古典雅致\n- 叙述视角：第三人称全知视角\n...",
    "last_modified": "2026-05-10T01:30:00"
  }
}
```

#### POST `/api/style-guide`
**功能**：保存文风指南

**请求体**：
```json
{
  "project_id": "20260510120000",
  "content": "# 文风指南\n\n## 整体风格\n..."
}
```

---

### 3.11 故事状态管理

#### GET `/api/story-state`
**功能**：获取故事状态

**响应**：
```json
{
  "success": true,
  "data": {
    "protagonist_status": {
      "name": "张三",
      "level": 10,
      "hp": 85,
      "skills": ["剑术", "内功"]
    },
    "factions": {
      "正派": ["武当", "少林"],
      "邪派": ["魔教"]
    },
    "foreshadowing": ["神秘玉佩", "黑衣人"],
    "main_plot_progress": 45,
    "side_plots": [
      {"id": "p001", "name": "寻找身世", "progress": 60}
    ],
    "last_modified": "2026-05-10T01:30:00"
  }
}
```

#### POST `/api/story-state`
**功能**：更新故事状态

**请求体**：
```json
{
  "project_id": "20260510120000",
  "protagonist_status": {...},
  "factions": {...},
  "foreshadowing": [...],
  "main_plot_progress": 50,
  "side_plots": [...]
}
```

---

### 3.12 近期上下文管理

#### GET `/api/recent-context`
**功能**：获取近期上下文（最近5章摘要）

**响应**：
```json
{
  "success": true,
  "data": {
    "chapters": [
      {
        "path": "chapters/vol-01/ch-005/sec-001.md",
        "title": "第五章：奇遇",
        "summary": "张三在山洞中发现了一本秘籍...",
        "word_count": 2000
      },
      ...
    ],
    "total_words": 8500
  }
}
```

#### POST `/api/recent-context/append`
**功能**：追加新章节摘要到近期上下文

**请求体**：
```json
{
  "project_id": "20260510120000",
  "chapter_path": "chapters/vol-01/ch-006/sec-001.md",
  "title": "第六章：修炼",
  "summary": "张三开始修炼秘籍...",
  "word_count": 2200
}
```

---

### 3.13 用户反馈管理

#### GET `/api/feedback/{chapter_path}`
**功能**：获取章节的用户反馈列表

**示例**：`/api/feedback/chapters/vol-01/ch-001`

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "id": "fb001",
      "type": "suggestion",  // suggestion, error, improvement
      "content": "这段对话可以更生动一些",
      "location": "第3段",
      "created_at": "2026-05-10T01:30:00",
      "resolved": false
    }
  ]
}
```

#### POST `/api/feedback`
**功能**：提交用户反馈

**请求体**：
```json
{
  "project_id": "20260510120000",
  "chapter_path": "chapters/vol-01/ch-001",
  "type": "suggestion",
  "content": "这段对话可以更生动一些",
  "location": "第3段"
}
```

#### PATCH `/api/feedback/{feedback_id}`
**功能**：更新反馈状态（标记为已解决）

**请求体**：
```json
{
  "resolved": true
}
```

---

### 3.14 修改日志管理

#### GET `/api/revision-log/{chapter_path}`
**功能**：获取章节的修改日志

**示例**：`/api/revision-log/chapters/vol-01/ch-001`

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "id": "rev001",
      "timestamp": "2026-05-10T01:30:00",
      "type": "ai_rewrite",  // ai_rewrite, user_edit, auto_save
      "description": "AI重写第2段",
      "diff": "@@ -10,5 +10,5 @@...",
      "word_count_before": 1500,
      "word_count_after": 1800
    }
  ]
}
```

#### POST `/api/revision-log`
**功能**：记录修改日志

**请求体**：
```json
{
  "project_id": "20260510120000",
  "chapter_path": "chapters/vol-01/ch-001",
  "type": "ai_rewrite",
  "description": "AI重写第2段",
  "diff": "@@ -10,5 +10,5 @@...",
  "word_count_before": 1500,
  "word_count_after": 1800
}
```

---

### 3.15 Token 计数（依赖 tiktoken）

#### POST `/api/tokens/count`
**功能**：计算文本的token数

**请求体**：
```json
{
  "text": "请根据以下信息撰写章节...",
  "model": "gpt-4"  // 可选，默认 gpt-4
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "tokens": 1234,
    "model": "gpt-4",
    "max_context": 128000,
    "remaining": 126766
  }
}
```

**说明**：
- 使用 `tiktoken` 库计算token数
- 返回模型的最大上下文长度
- 返回剩余可用token数
- 前端可用于检查是否超过限制

#### POST `/api/tokens/estimate`
**功能**：估算项目/模板的token数

**请求体**：
```json
{
  "project_id": "20260510120000",
  "target": "prompt",  // prompt, chapter, outline
  "template": "generate/chapter",  // 当target=prompt时必填
  "variables": {"genre": "玄幻"}  // 当target=prompt时可填
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "estimated_tokens": 5000,
    "target": "prompt"
  }
}
```

---

### 3.11 版本对比（依赖 difflib）

#### POST `/api/compare`
**功能**：对比两个文本的差异（依赖 **difflib**）

**请求体**：
```json
{
  "old_text": "旧版本内容...",
  "new_text": "新版本内容...",
  "fromfile": "版本1",
  "tofile": "版本2"
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "diff": "@@ -1,3 +1,3 @@\n-旧版本\n+新版本\n...",
    "has_diff": true
  }
}
```

**说明**：
- 使用 `difflib` 生成统一差异格式（unified diff）
- 可用于章节版本对比、Prompt模板对比等

---

### 3.12 文件监听（依赖 watchdog）

#### GET `/api/watch/status`
**功能**：获取文件监听状态

**响应**：
```json
{
  "success": true,
  "data": {
    "watching": true,
    "watched_paths": ["projects/20260510120000"],
    "events_count": 42
  }
}
```

**说明**：
- 后端使用 `watchdog` 监听workspace/目录
- 文件变动时通过SSE推送事件
- 前端无需主动轮询

---

## 五、SSE 事件规范（依赖 watchdog）

### 5.1 事件流端点
**GET `/api/events`**

前端通过EventSource连接，接收实时事件。

**说明**：
- 后端使用 **watchdog** 监听workspace/目录变动
- 文件事件由watchdog检测到后，通过SSE推送给前端
- 前端无需主动轮询文件变化

### 5.2 事件类型

| 事件类型 | 数据格式 | 说明 |
|---------|---------|------|
| `generation` | `{"task_id":"...", "content":"...", "done":false}` | AI生成内容流 |
| `file-created` | `{"path":"...", "type":"file"}` | 新文件创建（watchdog监听） |
| `file-updated` | `{"path":"...", "type":"file", "frontmatter":{...}}` | 文件更新（watchdog监听，python-frontmatter解析） |
| `file-renamed` | `{"src_path":"...", "dest_path":"..."}` | 文件被重命名（watchdog监听） |
| `directory-created` | `{"path":"...", "type":"directory"}` | 目录被创建（watchdog监听） |
| `task` | `{"task_id":"...", "status":"running", "progress":50}` | 任务状态变化 |
| `queue` | `{"running":[...], "queued":[...]}` | 队列变化 |
| `llm-status` | `{"status":"connected", "model":"gpt-4", "provider":"openai"}` | LLM状态变化（LiteLLM） |
| `thinking` | `{"task_id":"...", "content":"..."}` | AI思考中 |
| `error` | `{"code":"LLM_ERROR", "message":"..."}` | 错误 |
| `done` | `{"task_id":"...", "result":{...}}` | 任务完成 |

### 5.3 SSE 数据格式示例

```
event: generation
data: {"task_id":"task_123","content":"第一章：","done":false}

event: file-created
data: {"path":"projects/20260510120000/chapters/vol-01/ch-001/sec-001.md","type":"file"}

event: file-updated
data: {"path":"projects/20260510120000/outline.md","type":"file","frontmatter":{"title":"大纲"}}

event: file-renamed
data: {"src_path":"projects/20260510120000/old.md","dest_path":"projects/20260510120000/new.md"}

event: task
data: {"task_id":"task_123","status":"running","progress":30}

event: done
data: {"task_id":"task_123","result":{"file":"chapters/vol-01/ch-001/sec-001.md"}}
```

**说明**：
- 所有文件事件由 `watchdog` 监听到后推送
- `file-updated` 事件会同时返回文件的 frontmatter（用 **python-frontmatter** 解析）
- 前端收到事件后，按需刷新文件树或编辑器内容

---

## 六、请求/响应示例

### 6.1 新建项目完整流程

**Step 1: 前端提交创建请求**
```javascript
POST /api/projects
Content-Type: application/json

{
  "name": "我的玄幻小说",
  "genre": "玄幻",
  "theme": "友情与成长",
  "scale": 100000
}
```

**Step 2: 后端响应**
```json
{
  "success": true,
  "data": {
    "project_id": "20260510120001",
    "path": "projects/20260510120001",
    "created_at": "2026-05-10T02:00:00"
  },
  "message": "项目创建成功，正在生成大纲..."
}
```

**Step 3: 后端异步生成（SSE推送）**
```
event: generation
data: {"task_id":"task_001","content":"# 大纲\n\n## 故事背景...","done":false}

event: file-created
data: {"path":"projects/20260510120001/outline.md","type":"file"}

event: done
data: {"task_id":"task_001","result":{"file":"outline.md"}}
```

---

### 6.2 渲染Prompt模板（依赖 Jinja2）

**请求**：
```javascript
POST /api/prompts/render
Content-Type: application/json

{
  "template": "generate/chapter",
  "variables": {
    "genre": "玄幻",
    "theme": "友情与成长",
    "protagonist": "李四"
  }
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "rendered": "请根据以下信息撰写小说章节：\n\n类型：玄幻\n主题：友情与成长\n主角：李四\n\n请生成包含以下部分的内容：\n1. ..."
  }
}
```

---

### 6.3 计算Token数（依赖 tiktoken）

**请求**：
```javascript
POST /api/tokens/count
Content-Type: application/json

{
  "text": "请根据以下信息撰写章节：\n类型：玄幻\n...",
  "model": "gpt-4"
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "tokens": 1234,
    "model": "gpt-4",
    "max_context": 128000,
    "remaining": 126766
  }
}
```

---

## 七、分页与过滤

### 6.1 分页参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | number | 1 | 页码 |
| `page_size` | number | 20 | 每页数量 |
| `order_by` | string | `created_at` | 排序字段 |
| `order` | string | `desc` | 排序方向（asc/desc） |

### 6.2 过滤参数
| 参数 | 说明 |
|------|------|
| `name` | 按名称搜索 |
| `type` | 按类型过滤 |
| `status` | 按状态过滤 |
| `created_after` | 创建时间之后 |
| `created_before` | 创建时间之前 |

---

## 八、速率限制

- **普通请求**：60次/分钟
- **LLM生成请求**：10次/分钟
- **超出限制**：返回429状态码 + Retry-After头

**响应头**：
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1620000000
```

**说明**：
- 限流采用令牌桶算法，支持突发流量
- LLM生成任务有独立的限流计数器
- 超出限制后等待 Retry-After 秒后重试

---

## 九、版本控制

### 8.1 API版本
当前版本：`v1`

未来版本通过URL路径区分：`/api/v2/...`

### 8.2 向后兼容
- 新增字段：不影响旧版客户端
- 删除字段：先标记`deprecated`，下个大版本移除
- 修改字段：通过新版本API实现

---

## 十、安全规范

### 10.1 输入验证
- 所有用户输入必须验证
- 文件路径：禁止目录遍历（如 `../../../etc/passwd`）
- JSON：限制嵌套深度（≤10层）

### 10.2 输出编码
- JSON：自动转义特殊字符
- HTML：前端使用DOMPurify清洗

### 10.3 CORS（开发环境）
```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## 十一、前端调用示例

### 11.1 获取文件树
```javascript
async function loadFileTree() {
  const response = await fetch('/api/tree');
  const result = await response.json();
  
  if (result.success) {
    renderFileTree(result.data);
  } else {
    showError(result.message);
  }
}
```

### 11.2 SSE 连接（接收 watchdog 事件）
```javascript
function connectSSE() {
  const eventSource = new EventSource('/api/events');
  
  eventSource.addEventListener('generation', (event) => {
    const data = JSON.parse(event.data);
    appendToEditor(data.content);
    
    if (data.done) {
      eventSource.close();
    }
  });
  
  eventSource.addEventListener('file-updated', (event) => {
    const data = JSON.parse(event.data);
    // 用 python-frontmatter 解析的 frontmatter 更新UI
    updateFileMetadata(data.path, data.frontmatter);
  });
  
  eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    showError(data.message);
  });
}
```

### 11.3 保存文件（支持 frontmatter）
```javascript
async function saveFile(path, content, frontmatter) {
  const response = await fetch('/api/file', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      path: path,
      content: content,
      frontmatter: frontmatter,  // 可选，由 python-frontmatter 处理
      encoding: 'utf-8'
    })
  });
  
  const result = await response.json();
  return result.success;
}
```

### 11.4 计算Token数（使用 tiktoken）
```javascript
async function checkTokenLimit(text) {
  const response = await fetch('/api/tokens/count', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: text,
      model: 'gpt-4'
    })
  });
  
  const result = await response.json();
  if (result.success) {
    console.log(`Token数：${result.data.tokens}`);
    console.log(`剩余可用：${result.data.remaining}`);
    
    if (result.data.remaining < 1000) {
      alert('警告：Token剩余不足！');
    }
  }
}
```

---

## 附录：完整端点清单

| 方法 | 路径 | 功能 | 依赖 |
|------|------|------|------|
| GET | `/api/projects` | 获取项目列表 | FastAPI |
| POST | `/api/projects` | 新建项目 | FastAPI |
| POST | `/api/projects/open` | 打开项目 | FastAPI |
| DELETE | `/api/projects/{project_id}` | 删除项目 | FastAPI |
| GET | `/api/tree` | 获取文件树 | FastAPI, aiofiles |
| GET | `/api/file?path=` | 获取文件内容（含frontmatter） | FastAPI, aiofiles, python-frontmatter |
| POST | `/api/file` | 保存文件（支持frontmatter） | FastAPI, aiofiles, python-frontmatter |
| PUT | `/api/file` | 创建文件 | FastAPI, aiofiles |
| GET | `/api/llm/config` | 获取LLM配置 | FastAPI, pydantic-settings |
| POST | `/api/llm/config` | 保存LLM配置 | FastAPI, pydantic-settings, LiteLLM |
| POST | `/api/llm/test` | 测试LLM连接 | FastAPI, LiteLLM |
| GET | `/api/llm/models` | 获取模型列表 | FastAPI, LiteLLM |
| POST | `/api/generate` | 提交生成任务 | FastAPI, LiteLLM, Jinja2 |
| POST | `/api/stop` | 停止任务 | FastAPI |
| GET | `/api/tasks` | 获取任务列表 | FastAPI |
| GET | `/api/prompts` | 获取模板列表 | FastAPI, Jinja2 |
| GET | `/api/prompts/{cat}/{type}` | 获取模板内容 | FastAPI, Jinja2 |
| POST | `/api/prompts/{cat}/{type}` | 保存模板 | FastAPI, Jinja2 |
| POST | `/api/prompts/render` | 渲染模板 | FastAPI, Jinja2 |
| GET | `/api/backup` | 获取备份列表 | FastAPI, aiofiles |
| POST | `/api/backup` | 创建备份 | FastAPI, aiofiles |
| POST | `/api/backup/restore` | 恢复备份 | FastAPI, aiofiles |
| GET | `/api/characters` | 获取角色列表 | FastAPI, aiofiles, python-frontmatter |
| GET | `/api/characters/{id}` | 获取角色详情 | FastAPI, aiofiles, python-frontmatter |
| POST | `/api/characters` | 创建/更新角色 | FastAPI, aiofiles, python-frontmatter |
| DELETE | `/api/characters/{id}` | 将角色标记为inactive | FastAPI, aiofiles |
| GET | `/api/materials/{type}` | 获取提取结果 | FastAPI, aiofiles |
| POST | `/api/extract` | 提交提取任务 | FastAPI, LiteLLM |
| GET | `/api/style-guide` | 获取文风指南 | FastAPI, aiofiles |
| POST | `/api/style-guide` | 保存文风指南 | FastAPI, aiofiles |
| GET | `/api/story-state` | 获取故事状态 | FastAPI, aiofiles |
| POST | `/api/story-state` | 更新故事状态 | FastAPI, aiofiles |
| GET | `/api/recent-context` | 获取近期上下文 | FastAPI, aiofiles |
| POST | `/api/recent-context/append` | 追加章节摘要 | FastAPI, aiofiles |
| GET | `/api/feedback/{chapter_path}` | 获取章节反馈 | FastAPI, aiofiles |
| POST | `/api/feedback` | 提交用户反馈 | FastAPI, aiofiles |
| PATCH | `/api/feedback/{feedback_id}` | 更新反馈状态 | FastAPI, aiofiles |
| GET | `/api/revision-log/{chapter_path}` | 获取修改日志 | FastAPI, aiofiles |
| POST | `/api/revision-log` | 记录修改日志 | FastAPI, aiofiles, difflib |
| POST | `/api/tokens/count` | 计算Token数 | FastAPI, tiktoken |
| POST | `/api/tokens/estimate` | 估算Token数 | FastAPI, tiktoken, Jinja2 |
| POST | `/api/compare` | 版本对比 | FastAPI, difflib |
| GET | `/api/watch/status` | 获取监听状态 | FastAPI, watchdog |
| GET | `/api/events` | SSE事件流 | FastAPI, watchdog |
---

**文档版本**：v1.5  
**最后更新**：2026-05-11  
**维护者**：墨韵开发团队  
**修改记录**：
- v1.0 (2026-05-10): 初始版本
- v1.1 (2026-05-10): 补充依赖对应关系（tiktoken、watchdog、python-frontmatter、LiteLLM、Jinja2）
- v1.2 (2026-05-10): 补充版本对比API（difflib）、tenacity说明、章节编号调整
- v1.3 (2026-05-10): 移除文件删除相关API和事件（文件不支持物理删除）
- v1.4 (2026-05-10): 清理残留的 DELETE /api/file 端点和 file-deleted SSE 事件
- v1.5 (2026-05-11): 新增文风指南、故事状态、近期上下文、用户反馈、修改日志管理API端点
