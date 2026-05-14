# API 契约文档 [已废弃]

> ⚠️ **已废弃**：FastAPI 自动生成 OpenAPI 文档（`/docs` 和 `/redoc`），这是唯一的 API 参考来源。
> 保留此文作为历史参考，不再单独维护。最后更新：2026-05-14
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
| 500 | Internal Server Error | 服务器错误 |
| 503 | Service Unavailable | LLM服务不可用 |
| 504 | Gateway Timeout | LLM调用超时 |

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
      "project_id": "20260510120000",
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
  "tone": "热血",
  "background": "异界大陆",
  "writing_style": "简洁",
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

#### GET `/api/projects/{project_id}`
**功能**：获取单个项目详情

#### POST `/api/projects/{project_id}/recalculate-stats`
**功能**：重新计算项目统计信息（字数、章节数等）

#### DELETE `/api/projects/{project_id}`
**功能**：删除项目

---

### 3.2 文件树

#### GET `/api/tree`
**功能**：获取当前项目的文件树

**Query参数**：
- `project_id` (string, required): 项目ID

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
        "path": "outline.md"
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
- `project_id` (string, required): 项目ID
- `path` (string, required): 文件相对路径（相对于项目根目录）

**示例**：`/api/file?project_id=20260510120000&path=outline.md`

**响应**：
```json
{
  "success": true,
  "data": {
    "path": "outline.md",
    "content": "# 大纲\n\n...",
    "frontmatter": {
      "title": "大纲",
      "version": "1.0"
    }
  }
}
```

**说明**：`path` 为相对于项目根目录的文件路径，不含项目 ID 前缀

#### POST `/api/file`
**功能**：保存文件内容（支持 frontmatter 写入）

**请求体**：
```json
{
  "path": "chapters/vol-01/ch-001/sec-001.md",
  "content": "# 大纲\n\n...",
  "frontmatter": {
    "title": "大纲",
    "version": "1.0"
  },
  "encoding": "utf-8"
}
```

**Query参数**：
- `project_id` (string, required): 项目ID

#### POST `/api/file/create`
**功能**：创建新文件

**请求体**：
```json
{
  "project_id": "20260510120000",
  "path": "chapters/vol-01/ch-001/sec-001.md",
  "content": ""
}
```

#### POST `/api/file/rename`
**功能**：重命名文件

**请求体**：
```json
{
  "project_id": "20260510120000",
  "old_path": "chapters/vol-01/ch-001/sec-001.md",
  "new_path": "chapters/vol-01/ch-001/sec-001-new.md"
}
```

#### POST `/api/directory/create`
**功能**：创建新目录

**请求体**：
```json
{
  "project_id": "20260510120000",
  "path": "chapters/vol-01"
}
```

---

### 3.4 LLM 配置与调用（依赖 LiteLLM + pydantic-settings）

#### GET `/api/llm/config`
**功能**：获取LLM配置

**响应**：
```json
{
  "success": true,
  "data": {
    "provider": "openai",
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
  "provider": "openai",
  "api_key": "sk-...",
  "api_base": "https://api.openai.com/v1",
  "model": "gpt-4",
  "thinking": false
}
```

**说明**：
- 后端通过 **LiteLLM** 统一调用，前端无需关心具体实现
- `provider` 支持：openai, deepseek, azure, anthropic, ollama（后端通过 LiteLLM 可扩展更多）
- Ollama 无需 api_key，api_base 默认为 `http://localhost:11434`
- 保存后触发 SSE 事件 `llm-status`

#### GET `/api/llm/status`
**功能**：获取 LLM 连接状态

#### POST `/api/llm/test`
**功能**：测试LLM连接（通过 LiteLLM 测试）

#### GET `/api/llm/models`
**功能**：获取可用模型列表（通过 LiteLLM 获取）

---

### 3.5 LLM 生成

#### POST `/api/generate`
**功能**：提交生成任务（流式 SSE）

**请求体**：
```json
{
  "project_id": "20260510120000",
  "prompt_type": "generate/continuation",
  "file_path": "chapters/vol-01/ch-001/sec-001.md",
  "mode": "append",
  "extra_vars": {
    "user_prompt": "写一段主角在森林中迷路的情节"
  }
}
```

**支持 prompt_type 取值**：
- `generate/continuation` — 续写（走 pipeline）
- `generate/rewrite` — 重写（走 pipeline）
- 其他取值走回退模式（旧 PromptEngine 逻辑）

**响应**：`EventSourceResponse`（SSE 流式），事件类型见第五章

**说明**：
- 当 prompt_type 为 generate/continuation 时走 generate 管线（追加模式）
- 当 prompt_type 为 generate/rewrite 时走 rewrite 管线（覆盖模式）
- 其余情况走 PromptEngine + 直接 LLM 调用的回退模式
- 任意管线均可通过 `POST /api/pipeline/run` 直接执行，不经过此路由
- 所有LLM调用通过 **tenacity** 包装，有自动重试机制
- 重试策略：指数退避，最多3次尝试

#### POST `/api/generate/batch`
**功能**：批量生成章节内容

**请求体**：
```json
{
  "project_id": "20260510120000",
  "prompt_type": "generate/chapter",
  "volume_number": 1,
  "chapter_number": 1,
  "section_numbers": [1, 2, 3, 4],
  "temperature": 0.8
}
```

**响应**：
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "target_file": "chapters/vol-01/ch-001/sec-001.md",
        "status": "success",
        "word_count": 1850
      }
    ],
    "total": 4,
    "succeeded": 4,
    "failed": 0
  }
}
```

#### POST `/api/chat`
**功能**：聊天对话（流式 SSE），使用 `chat` 管线

**请求体**：
```json
{
  "project_id": "20260510120000",
  "message": "帮我分析一下当前章节的情节节奏",
  "context_file": "chapters/vol-01/ch-001/sec-001.md"
}
```

**响应**：`EventSourceResponse`（SSE 流式）

#### POST `/api/stop`
**功能**：停止当前LLM任务

**Query参数**：
- `task_id` (string, optional): 要停止的任务ID，不传则停止所有任务

**示例**：`POST /api/stop?task_id=gen-123456`

#### GET `/api/generate-tasks`
**功能**：获取当前运行的生成任务列表

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

#### GET `/api/prompts/{category}/{name}`
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

#### POST `/api/prompts/{category}/{name}`
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

### 3.7 管线管理 (Pipeline)

#### POST `/api/pipeline/run`
**功能**：运行自定义管线

#### GET `/api/pipeline/list`
**功能**：获取所有可用管线列表

#### GET `/api/pipeline/{name}`
**功能**：获取指定管线详情（含每步 prompt 内容）

#### PUT `/api/pipeline/{name}`
**功能**：保存管线定义

#### POST `/api/pipeline/custom`
**功能**：创建自定义管线

---

### 3.8 备份与快照

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

#### POST `/api/backup/{backup_id}`
**功能**：恢复备份

#### DELETE `/api/backup/{backup_id}`
**功能**：删除备份

#### GET `/api/snapshots/{project_id}`
**功能**：获取文件版本快照列表

**Query参数**：
- `file_path` (string, optional): 按文件路径筛选

#### POST `/api/snapshots/{project_id}`
**功能**：创建文件版本快照

**请求体**：
```json
{
  "file_path": "chapters/vol-01/ch-001/sec-001.md",
  "label": "自动保存"
}
```

#### POST `/api/snapshots/{project_id}/restore`
**功能**：恢复文件到指定快照

---

### 3.9 角色管理

#### GET `/api/characters`
**功能**：获取角色列表

#### GET `/api/characters/{character_id}`
**功能**：获取角色详情

#### POST `/api/characters`
**功能**：创建/更新角色

#### PUT `/api/characters/{character_id}`
**功能**：更新角色信息

#### DELETE `/api/characters/{character_id}`
**功能**：将角色标记为 inactive（不提供物理删除）

---

### 3.10 提取结果

#### GET `/api/materials/{material_type}`
**功能**：获取提取结果列表（如 plots, scenes, summaries）

**示例**：`/api/materials/plots`

#### GET `/api/materials/{material_type}/{item_id}`
**功能**：获取提取结果详情

#### POST `/api/materials/{material_type}`
**功能**：创建提取结果

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

#### DELETE `/api/materials/{material_type}/{item_id}`
**功能**：删除提取结果

---

### 3.11 文风指南管理

#### GET `/api/style-guide/{project_id}`
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

#### POST `/api/style-guide/{project_id}`
**功能**：保存文风指南

**请求体**：
```json
{
  "content": "# 文风指南\n\n## 整体风格\n..."
}
```

---

### 3.12 故事状态管理

#### GET `/api/story-state/{project_id}`
**功能**：获取故事状态

**响应**：
```json
{
  "success": true,
  "data": {
    "content": "# 故事全局状态\n\n## 主角状态\n...",
    "last_modified": "2026-05-10T01:30:00"
  }
}
```

#### POST `/api/story-state/{project_id}`
**功能**：更新故事状态

---

### 3.13 近期上下文管理

#### GET `/api/recent-context/{project_id}`
**功能**：获取近期上下文内容

#### POST `/api/recent-context/{project_id}/append`
**功能**：追加新内容到近期上下文

**请求体**：
```json
{
  "content": "\n## 2026-05-10 12:00 - sec-001.md\n新增章节内容摘要..."
}
```

#### DELETE `/api/recent-context/{project_id}`
**功能**：清空/重置近期上下文

---

### 3.14 用户反馈管理

#### GET `/api/feedback/{project_id}`
**功能**：获取项目的用户反馈列表

**Query参数**：
- `chapter_path` (string, optional): 按章节路径筛选

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "id": "fb-001",
      "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
      "type": "suggestion",
      "content": "这段对话可以更生动一些",
      "location": "第3段",
      "satisfaction_level": 3,
      "resolved": false,
      "created_at": "2026-05-10T01:30:00",
      "resolved_at": null
    }
  ]
}
```

#### POST `/api/feedback/{project_id}`
**功能**：提交用户反馈

**请求体**：
```json
{
  "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
  "type": "suggestion",
  "content": "这段对话可以更生动一些",
  "location": "第3段",
  "satisfaction_level": 3
}
```

#### PATCH `/api/feedback/{project_id}/{feedback_id}`
**功能**：更新反馈状态（标记为已解决）

#### DELETE `/api/feedback/{project_id}/{feedback_id}`
**功能**：删除反馈记录

---

### 3.15 修改日志管理

#### GET `/api/revision-log/{project_id}`
**功能**：获取项目的修改日志

**Query参数**：
- `chapter_path` (string, optional): 按章节路径筛选

**响应**：
```json
{
  "success": true,
  "data": [
    {
      "id": "rev-001",
      "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
      "revision_type": "ai_rewrite",
      "description": "AI重写第2段",
      "diff": "@@ -10,5 +10,5 @@...",
      "word_count_before": 1500,
      "word_count_after": 1800,
      "created_at": "2026-05-10T01:30:00"
    }
  ]
}
```

#### POST `/api/revision-log/{project_id}`
**功能**：记录修改日志

**请求体**：
```json
{
  "chapter_path": "chapters/vol-01/ch-001/sec-001.md",
  "revision_type": "ai_rewrite",
  "description": "AI重写第2段",
  "diff": "@@ -10,5 +10,5 @@...",
  "word_count_before": 1500,
  "word_count_after": 1800
}
```

#### GET `/api/revision-log/{project_id}/{log_id}`
**功能**：获取单条修改日志详情

---

### 3.16 Token 计数（依赖 tiktoken）

#### POST `/api/tokens/count`
**功能**：计算文本的token数

**请求体**：
```json
{
  "text": "请根据以下信息撰写章节...",
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

**说明**：
- 使用 `tiktoken` 库计算token数
- 返回模型的最大上下文长度和剩余可用token数

#### POST `/api/tokens/estimate`
**功能**：估算项目/模板的token数

**请求体**：
```json
{
  "project_id": "20260510120000",
  "target": "prompt",
  "template": "generate/chapter",
  "variables": {"genre": "玄幻"}
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

### 3.17 版本对比（依赖 difflib）

#### POST `/api/compare`
**功能**：对比两个文本的差异

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

**说明**：使用 `difflib` 生成统一差异格式（unified diff）

#### POST `/api/compare/side-by-side`
**功能**：获取并排对比格式

#### POST `/api/compare/chapters`
**功能**：对比两个章节文件的差异

---

### 3.18 新建项目引导（Wizard）

#### POST `/api/wizard/generate-idea`
**功能**：AI 生成书名+核心创意

**请求体**：
```json
{
  "genre": "玄幻",
  "tone": "热血",
  "background": "异界大陆",
  "theme": "友情与成长",
  "writing_style": "简洁",
  "author": "作者名",
  "target_word_count": 100000
}
```

#### POST `/api/wizard/{project_id}/generate-outline`
**功能**：AI 生成大纲（含卷/章/节结构）

**请求体**：
```json
{
  "genre": "玄幻",
  "tone": "热血",
  "background": "异界大陆",
  "theme": "友情与成长",
  "writing_style": "简洁",
  "author": "作者名",
  "target_word_count": 100000,
  "book_name": "书名",
  "book_description": "创意描述"
}
```

#### POST `/api/wizard/{project_id}/confirm-outline`
**功能**：确认大纲并生成目录结构

**请求体**：
```json
{
  "outline": "大纲内容（Markdown格式）"
}
```

---

### 3.19 质量审查

#### POST `/api/quality/review`
**功能**：对指定文件进行质量审查

#### POST `/api/quality/review-batch`
**功能**：批量质量审查

#### GET `/api/quality/reviews/{project_id}`
**功能**：获取项目的质量审查记录

---

### 3.20 全局配置

#### GET `/api/config/custom-params`
**功能**：获取自定义参数（题材/基调/写作风格/背景/主题 选项列表）

#### PUT `/api/config/custom-params`
**功能**：保存自定义参数

---

### 3.21 任务队列

#### POST `/api/tasks`
**功能**：创建后台任务

#### GET `/api/tasks`
**功能**：获取所有任务状态

#### GET `/api/tasks/{task_id}`
**功能**：获取单个任务详情

#### POST `/api/tasks/{task_id}/cancel`
**功能**：取消指定任务

---

### 3.22 工作流引擎 ✨NEW

> 工作流是多步骤编排层，详见 [工作流引擎设计.md](工作流引擎设计.md)

#### GET `/api/workflows`
**功能**：获取所有可用工作流

#### GET `/api/workflows/{name}`
**功能**：获取工作流详情（含完整步骤树）

#### POST `/api/workflows/save`
**功能**：保存（创建或更新）工作流

**请求体**：
```json
{
  "name": "write-chapters",
  "label": "批量写章节",
  "steps": [{ "id": "gen", "label": "生成", "type": "pipeline", "pipeline": "generate", "output": "..." }]
}
```

#### DELETE `/api/workflows/{name}`
**功能**：删除工作流

#### POST `/api/workflows/run`
**功能**：运行工作流（SSE 流式）

**请求体**：
```json
{
  "workflow": "write-chapters",
  "project_id": "my-novel",
  "variables": { "chapter_count": "5" }
}
```

**SSE 事件**：`workflow_start`, `step_start`, `step_done`, `step_skip`, `loop_iteration`, `workflow_done`, `workflow_error`, `workflow_stopped`

#### POST `/api/workflows/stop/{run_id}`
**功能**：停止正在运行的工作流

#### GET `/api/workflows/runs/{run_id}`
**功能**：查询工作流运行状态

---

## 四、SSE 事件规范（依赖 watchdog）

### 4.1 事件流端点
**GET `/api/sse`**

前端通过 EventSource 连接，接收实时事件。

### 4.2 事件类型

| 事件类型 | 数据格式 | 说明 |
|---------|---------|------|
| `generation` | `{"delta":"...", "task_id":"..."}` | AI生成内容流（流式 delta） |
| `prompt` | `{"prompt":"...", "task_id":"...", "step_id":"..."}` | 渲染后的 Prompt 内容 |
| `thinking` | `{"step_id":"...", "label":"...", "step":1, "total":3}` | AI 思考中 |
| `step_done` | `{"step_id":"...", "label":"...", "status":"done"}` | 管线步骤完成 |
| `task_start` | `{"task_id":"...", "pipeline":"...", "total_steps":3}` | 任务开始 |
| `file-created` | `{"path":"...", "type":"file"}` | 新文件创建（watchdog监听） |
| `file-modified` | `{"path":"...", "type":"file"}` | 文件修改（watchdog监听） |
| `file-renamed` | `{"src_path":"...", "dest_path":"..."}` | 文件重命名（watchdog监听） |
| `directory-created` | `{"path":"...", "type":"directory"}` | 目录创建（watchdog监听） |
| `task` | `{"task_id":"...", "status":"running", "progress":50}` | 任务状态变化 |
| `llm-status` | `{"status":"connected", "model":"gpt-4"}` | LLM状态变化 |
| `error` | `{"message":"...", "task_id":"...", "warning":true}` | 错误（warning 为 true 表示非致命警告） |
| `done` | `{"task_id":"...", "message":"..."}` | 任务完成 |
| `workflow_start` | `{"run_id":"...", "workflow":"...", "label":"...", "total_steps":N}` | 工作流开始 ✨NEW |
| `step_start` | `{"step_id":"...", "label":"...", "type":"pipeline", "path":"..."}` | 工作流步骤开始（含 loop/pipeline/file） |
| `step_skip` | `{"step_id":"...", "label":"...", "status":"skipped", "path":"..."}` | 工作流转步续跑跳过步骤 |
| `step_done` | `{"step_id":"...", "label":"...", "type":"...", "status":"done", "output":"..."}` | 工作流步骤完成 |
| `loop_iteration` | `{"step_id":"...", "label":"...", "var":"ch", "value":2, "current":2, "total":10}` | 工作流循环迭代 |
| `workflow_done` | `{"run_id":"...", "message":"..."}` | 工作流全部完成 |
| `workflow_error` | `{"run_id":"...", "message":"..."}` | 工作流执行失败 |
| `workflow_stopped` | `{"run_id":"...", "message":"..."}` | 工作流被用户停止 |

### 4.3 SSE 数据格式示例

```
event: generation
data: {"delta":"第一章：","task_id":"task_123"}

event: file-created
data: {"path":"projects/20260510120000/chapters/vol-01/ch-001/sec-001.md","type":"file"}

event: file-modified
data: {"path":"projects/20260510120000/outline.md","type":"file"}

event: task
data: {"task_id":"task_123","status":"running","progress":30}

event: done
data: {"task_id":"task_123","message":"管线执行完成"}
```

**说明**：
- 所有文件事件由 `watchdog` 监听到后推送
- 前端收到事件后，按需刷新文件树或编辑器内容

---

## 五、请求/响应示例

### 5.1 新建项目完整流程

**Step 1: 前端提交创建请求**
```javascript
POST /api/projects
Content-Type: application/json

{
  "name": "我的玄幻小说",
  "genre": "玄幻",
  "theme": "友情与成长",
  "tone": "热血",
  "background": "异界大陆",
  "writing_style": "简洁",
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

**Step 3: 引导流程** — 前端依次调用：
1. `POST /api/wizard/generate-idea` — 生成书名+创意
2. `POST /api/wizard/{project_id}/generate-outline` — 生成大纲结构
3. `POST /api/wizard/{project_id}/confirm-outline` — 确认并创建目录

---

### 5.2 渲染Prompt模板（依赖 Jinja2）

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

### 5.3 计算Token数（依赖 tiktoken）

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

## 六、版本控制

### 6.1 API版本
当前版本：`v1`

未来版本通过URL路径区分：`/api/v2/...`

### 6.2 向后兼容
- 新增字段：不影响旧版客户端
- 删除字段：先标记`deprecated`，下个大版本移除
- 修改字段：通过新版本API实现

---

## 七、安全规范

### 7.1 输入验证
- 所有用户输入必须验证
- 文件路径：禁止目录遍历（如 `../../../etc/passwd`）
- JSON：限制嵌套深度（≤10层）

### 7.2 输出编码
- JSON：自动转义特殊字符
- HTML：前端使用DOMPurify清洗

### 7.3 CORS（开发环境）
```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Origin: http://127.0.0.1:5173
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## 八、前端调用示例

### 8.1 获取文件树
```javascript
async function loadFileTree() {
  const response = await fetch('/api/tree?project_id=20260510120000');
  const result = await response.json();

  if (result.success) {
    renderFileTree(result.data);
  } else {
    showError(result.message);
  }
}
```

### 8.2 SSE 连接
```javascript
function connectSSE() {
  const eventSource = new EventSource('/api/sse');

  eventSource.addEventListener('generation', (event) => {
    const data = JSON.parse(event.data);
    appendToEditor(data.delta);
  });

  eventSource.addEventListener('file-created', (event) => {
    const data = JSON.parse(event.data);
    refreshFileTree();
  });

  eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    showError(data.message);
  });
}
```

### 8.3 保存文件（支持 frontmatter）
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
      frontmatter: frontmatter,
      encoding: 'utf-8'
    })
  });

  const result = await response.json();
  return result.success;
}
```

### 8.4 计算Token数（使用 tiktoken）
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
| GET | `/api/projects/{project_id}` | 获取项目详情 | FastAPI |
| POST | `/api/projects/{project_id}/recalculate-stats` | 重新计算统计 | FastAPI |
| DELETE | `/api/projects/{project_id}` | 删除项目 | FastAPI |
| GET | `/api/tree` | 获取文件树 | FastAPI, aiofiles |
| GET | `/api/file` | 获取文件内容（含frontmatter） | FastAPI, aiofiles, python-frontmatter |
| POST | `/api/file` | 保存文件（支持frontmatter） | FastAPI, aiofiles, python-frontmatter |
| POST | `/api/file/create` | 创建新文件 | FastAPI, aiofiles |
| POST | `/api/file/rename` | 重命名文件 | FastAPI, aiofiles |
| POST | `/api/directory/create` | 创建目录 | FastAPI, aiofiles |
| GET | `/api/llm/config` | 获取LLM配置 | FastAPI, pydantic-settings |
| POST | `/api/llm/config` | 保存LLM配置 | FastAPI, pydantic-settings, LiteLLM |
| GET | `/api/llm/status` | 获取LLM连接状态 | FastAPI, LiteLLM |
| POST | `/api/llm/test` | 测试LLM连接 | FastAPI, LiteLLM |
| GET | `/api/llm/models` | 获取模型列表 | FastAPI, LiteLLM |
| POST | `/api/generate` | 提交生成任务（流式SSE） | FastAPI, LiteLLM, Jinja2 |
| POST | `/api/generate/batch` | 批量生成章节 | FastAPI, LiteLLM |
| POST | `/api/chat` | 聊天对话（流式SSE） | FastAPI, LiteLLM |
| POST | `/api/stop` | 停止任务 | FastAPI |
| GET | `/api/generate-tasks` | 获取运行中任务 | FastAPI |
| POST | `/api/pipeline/run` | 运行自定义管线 | FastAPI, LiteLLM |
| GET | `/api/pipeline/list` | 获取管线列表 | FastAPI |
| GET | `/api/pipeline/{name}` | 获取管线详情 | FastAPI |
| PUT | `/api/pipeline/{name}` | 保存管线定义 | FastAPI |
| POST | `/api/pipeline/custom` | 创建自定义管线 | FastAPI |
| GET | `/api/prompts` | 获取模板列表 | FastAPI, Jinja2 |
| GET | `/api/prompts/{category}/{name}` | 获取模板内容 | FastAPI, Jinja2 |
| POST | `/api/prompts/{category}/{name}` | 保存模板 | FastAPI, Jinja2 |
| POST | `/api/prompts/render` | 渲染模板 | FastAPI, Jinja2 |
| GET | `/api/backup` | 获取备份列表 | FastAPI, aiofiles |
| POST | `/api/backup` | 创建备份 | FastAPI, aiofiles |
| POST | `/api/backup/{backup_id}` | 恢复备份 | FastAPI, aiofiles |
| DELETE | `/api/backup/{backup_id}` | 删除备份 | FastAPI, aiofiles |
| GET | `/api/snapshots/{project_id}` | 获取快照列表 | FastAPI, aiofiles |
| POST | `/api/snapshots/{project_id}` | 创建快照 | FastAPI, aiofiles |
| POST | `/api/snapshots/{project_id}/restore` | 恢复快照 | FastAPI, aiofiles |
| GET | `/api/characters` | 获取角色列表 | FastAPI, aiofiles |
| GET | `/api/characters/{id}` | 获取角色详情 | FastAPI, aiofiles |
| POST | `/api/characters` | 创建/更新角色 | FastAPI, aiofiles |
| PUT | `/api/characters/{id}` | 更新角色信息 | FastAPI, aiofiles |
| DELETE | `/api/characters/{id}` | 标记角色为inactive | FastAPI, aiofiles |
| GET | `/api/materials/{type}` | 获取提取结果 | FastAPI, aiofiles |
| GET | `/api/materials/{type}/{id}` | 获取提取结果详情 | FastAPI, aiofiles |
| POST | `/api/materials/{type}` | 创建提取结果 | FastAPI, aiofiles |
| POST | `/api/extract` | 提交提取任务 | FastAPI, LiteLLM |
| DELETE | `/api/materials/{type}/{id}` | 删除提取结果 | FastAPI, aiofiles |
| GET | `/api/style-guide/{project_id}` | 获取文风指南 | FastAPI, aiofiles |
| POST | `/api/style-guide/{project_id}` | 保存文风指南 | FastAPI, aiofiles |
| GET | `/api/story-state/{project_id}` | 获取故事状态 | FastAPI, aiofiles |
| POST | `/api/story-state/{project_id}` | 更新故事状态 | FastAPI, aiofiles |
| GET | `/api/recent-context/{project_id}` | 获取近期上下文 | FastAPI, aiofiles |
| POST | `/api/recent-context/{project_id}/append` | 追加章节摘要 | FastAPI, aiofiles |
| DELETE | `/api/recent-context/{project_id}` | 重置近期上下文 | FastAPI, aiofiles |
| GET | `/api/feedback/{project_id}` | 获取反馈列表 | FastAPI, aiofiles |
| POST | `/api/feedback/{project_id}` | 提交反馈 | FastAPI, aiofiles |
| PATCH | `/api/feedback/{project_id}/{id}` | 更新反馈状态 | FastAPI, aiofiles |
| DELETE | `/api/feedback/{project_id}/{id}` | 删除反馈 | FastAPI, aiofiles |
| GET | `/api/revision-log/{project_id}` | 获取修改日志 | FastAPI, aiofiles |
| POST | `/api/revision-log/{project_id}` | 记录修改日志 | FastAPI, aiofiles, difflib |
| GET | `/api/revision-log/{project_id}/{id}` | 获取单条日志 | FastAPI, aiofiles |
| POST | `/api/tokens/count` | 计算Token数 | FastAPI, tiktoken |
| POST | `/api/tokens/estimate` | 估算Token数 | FastAPI, tiktoken, Jinja2 |
| POST | `/api/compare` | 版本对比 | FastAPI, difflib |
| POST | `/api/compare/side-by-side` | 并排对比 | FastAPI, difflib |
| POST | `/api/compare/chapters` | 章节对比 | FastAPI, difflib |
| POST | `/api/wizard/generate-idea` | 生成书名创意 | FastAPI, LiteLLM |
| POST | `/api/wizard/{project_id}/generate-outline` | 生成大纲 | FastAPI, LiteLLM |
| POST | `/api/wizard/{project_id}/confirm-outline` | 确认大纲 | FastAPI |
| POST | `/api/quality/review` | 质量审查 | FastAPI, LiteLLM |
| POST | `/api/quality/review-batch` | 批量质量审查 | FastAPI, LiteLLM |
| GET | `/api/quality/reviews/{project_id}` | 获取审查记录 | FastAPI |
| GET | `/api/config/custom-params` | 获取自定义参数 | FastAPI |
| PUT | `/api/config/custom-params` | 保存自定义参数 | FastAPI |
| POST | `/api/tasks` | 创建后台任务 | FastAPI |
| GET | `/api/tasks` | 获取任务列表 | FastAPI |
| GET | `/api/tasks/{task_id}` | 获取任务详情 | FastAPI |
| POST | `/api/tasks/{task_id}/cancel` | 取消任务 | FastAPI |
| GET | `/api/sse` | SSE事件流 | FastAPI, watchdog |
| GET | `/api/workflows` | 获取工作流列表 | FastAPI ✨NEW |
| GET | `/api/workflows/{name}` | 获取工作流详情 | FastAPI ✨NEW |
| POST | `/api/workflows/save` | 保存工作流 | FastAPI ✨NEW |
| DELETE | `/api/workflows/{name}` | 删除工作流 | FastAPI ✨NEW |
| POST | `/api/workflows/run` | 运行工作流（SSE） | FastAPI, LiteLLM ✨NEW |
| POST | `/api/workflows/stop/{run_id}` | 停止工作流 | FastAPI ✨NEW |
| GET | `/api/workflows/runs/{run_id}` | 查询运行状态 | FastAPI ✨NEW |

---

**文档版本**：v2.3
**最后更新**：2026-05-14
**维护者**：墨韵开发团队
