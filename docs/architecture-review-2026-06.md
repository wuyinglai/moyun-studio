# Moyun Studio 架构审查报告

> 审查日期：2026-06-02
> 审查范围：后端分层、前端模块、API 路由、Store 职责、SSE 事件流、Candidate 流、Lite/Professional 双链路
> 审查原则：不修改代码，仅梳理现状、识别风险、输出可执行建议

---

## 1. 当前后端分层图

```
┌─────────────────────────────────────────────────────────┐
│                    API 路由层 (backend/api/)              │
│  26 个路由文件：lite.py(59.9KB!), files.py, generate.py, │
│  candidates.py, projects.py, pipeline.py, sse.py, ...   │
├─────────────────────────────────────────────────────────┤
│                   Service 层 (backend/core/)             │
│  LLMService          → LLM 调用（LiteLLM 封装）          │
│  GenerationService   → 生成编排（管线+回退模式）          │
│  CandidateService    → 候选稿 CRUD + 安全采用            │
│  FileService         → 文件 I/O（强制入口）               │
│  ProjectService      → 项目 CRUD + 统计                  │
│  QualityService      → 质量审查                          │
│  PipelineRunner      → YAML 管线引擎（44.7KB）            │
│  WorkflowEngine      → 工作流引擎（47.8KB）               │
│  EventBus            → 事件发布/订阅                     │
│  LLMCircuitBreaker   → LLM 熔断器                       │
├─────────────────────────────────────────────────────────┤
│               Application 层 (backend/application/)      │
│  SceneService        → 场景路径构建/解析                  │
│  MemoryService       → 故事记忆维护                      │
│  PipelineContext     → 管线执行上下文                     │
│  NodeExecutorRegistry→ 管线节点注册                      │
├─────────────────────────────────────────────────────────┤
│                  Policies 层 (backend/policies/)          │
│  candidate_policy.py → 是否生成候选稿的策略判断            │
│  generation_output_policy.py → 输出安全策略               │
├─────────────────────────────────────────────────────────┤
│                  Domain 层 (backend/domain/)              │
│  events.py           → SSE 事件工厂函数                   │
└─────────────────────────────────────────────────────────┘
```

### 后端关键文件体积

| 文件 | 大小 | 风险 |
|------|------|------|
| `api/lite.py` | 59.9KB | **P0** — 单文件过大，包含完整 Lite 业务逻辑 |
| `core/pipeline.py` | 44.7KB | P1 — 管线引擎偏大 |
| `core/workflow.py` | 47.8KB | P1 — 工作流引擎偏大 |
| `api/files.py` | 13.8KB | OK |
| `core/generation_service.py` | 20.1KB | P2 — 偏大但可接受 |
| `core/candidate_service.py` | 14.9KB | OK |

---

## 2. 当前前端模块图

```
┌──────────────────────────────────────────────────────────────┐
│                     Views (页面)                              │
│  LiteWritingView.vue        → Lite 快写模式（独立入口）       │
│  ProjectView.vue            → Professional 全功能工作台       │
├──────────────────────────────────────────────────────────────┤
│                     Stores (Pinia)                            │
│  fileStore     → 文件树 + 文件 CRUD + 快照 + FILE_CONFLICT   │
│  editorStore   → 编辑器内容缓冲 + 脏标记 + contentSource      │
│  projectStore  → 项目列表 + 当前项目 + CRUD                  │
│  generationStore → 续写/重写任务管理（不含流式处理）           │
│  chatStore     → 聊天消息 + 流式传输                         │
│  pipelineStore → Pipeline 配置                               │
│  taskStore     → 任务生命周期 + 轮询                         │
│  llmStore      → LLM 配置状态                                │
│  uiStore       → UI 布局状态                                 │
│  rightPanelStore → 右侧面板 tab 切换                         │
│  reviewStore   → 质量审查                                    │
│  fileMetaStore → 文件元数据（持久化）                         │
│  historyStore  → 历史记录                                    │
│  notificationStore → 通知                                    │
│  recentContextStore → 近期上下文                             │
│  storyStateStore → 故事状态                                  │
│  styleGuideStore → 文风指南                                  │
│  customParamsStore → 自定义参数                              │
├──────────────────────────────────────────────────────────────┤
│                   Composables (组合逻辑)                      │
│  useSSE.ts (18.5KB)         → SSE 连接 + 事件分发中心        │
│  useFileGeneration.ts (10.1KB) → 流式生成 + generationEmitter│
│  useLiteGeneration.ts (22.0KB) → Lite 生成完整逻辑           │
│  useSceneGenerationActions.ts (22.1KB) → Professional 生成链 │
│  useWorkflow.ts (21.7KB)    → Workflow 编排                  │
│  useWorkflowGuide.ts (13.3KB) → 引导式工作流                 │
│  useAutoSave.ts             → 自动保存                       │
│  useTaskQueue.ts            → 任务队列                       │
│  useGenerationOrchestrator.ts → 生成编排器                   │
│  useLiteCandidateActions.ts → Lite 候选稿操作                │
│  useLitePrefetch.ts         → Lite 预取                      │
├──────────────────────────────────────────────────────────────┤
│                    Modules (领域模块)                         │
│  modules/scene/scenePath.ts → 场景路径构建/解析               │
│  modules/candidate/api.ts   → 候选稿 API 调用                │
│  modules/project/api.ts     → 项目 API 调用                  │
│  modules/sse/types.ts       → SSE 类型定义                   │
│  modules/pipeline/types.ts  → Pipeline 类型定义              │
├──────────────────────────────────────────────────────────────┤
│                    Services (通信层)                          │
│  services/api.ts            → Axios 实例 + 拦截器            │
│  services/liteService.ts    → Lite 模式专用 API              │
│  services/configService.ts  → 配置 API                       │
├──────────────────────────────────────────────────────────────┤
│                   Shared (共享定义)                           │
│  shared/api/routes.ts       → API 路由集中定义               │
│  shared/api/types.ts        → API 类型定义                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Professional 写下一场景调用链

```
用户点击「续写」按钮
  │
  ▼
EditorToolbar.vue / useSceneGenerationActions.ts
  │  调用 generationStore.continueWriting() 或 fileGen.generateToFile()
  │
  ├─ 路径A: 管线映射文件 → fileGen.runPipeline()
  │    POST /api/pipeline/run  →  PipelineRunner.run()
  │    → SSE 流式输出 → generationEmitter → useSSE 监听 → editorStore.appendContentToFile()
  │
  └─ 路径B: 普通场景文件 → generationStore.continueWriting()
       │  使用 fetch() 调用 POST /api/generate
       ▼
     backend/api/generate.py: generate()
       │  创建 GenerationService(settings)
       ▼
     GenerationService.generate_stream()
       │  加载 LLM 配置 → load_llm_config_from_workspace()
       │  创建 LLMService → PipelineRunner
       │
       ├─ 管线模式 (prompt_type 在 GENERATE_PIPELINE_MAP)
       │    → PipelineRunner.run(pipeline_name, output_mode)
       │    → SSE 事件 yield → event_bus.publish()
       │
       └─ 回退模式
            → render_prompt() → LLM complete()
            → 检查 should_create_candidate()
            → 写文件或创建候选稿
  │
  ▼
前端 SSE 处理:
  useFileGeneration.parseSSEStream()
    → generationEmitter.emit('generation', {delta, _targetFilePath})
    → useSSE 监听 generationEmitter
    → editorStore.appendContentToFile(path, delta)
    → fileStore.markDirty(path)
```

### 关键文件
- 前端: `useSceneGenerationActions.ts`, `generationStore.ts`, `useFileGeneration.ts`
- 后端: `api/generate.py`, `core/generation_service.py`, `core/pipeline.py`
- 策略: `policies/candidate_policy.py`

---

## 4. Lite 写下一场景调用链

```
用户选择爽点卡 → 点击「写下一场景」
  │
  ▼
LiteWritingView.vue
  │  调用 useLiteGeneration.runGeneration()
  │
  ▼
useLiteGeneration.ts: runGeneration(card, action, targetFile, outputFile)
  │
  ├─ 路径A: 流式模式 → streamLiteNext()
  │    POST /api/lite/write-next-stream
  │    → SSE 流: meta → delta → replace → status → done
  │    → streamingBuffers[path] += delta
  │    → 更新 textareaRef.value
  │
  └─ 路径B: 非流式模式 → writeLiteNext()
       POST /api/lite/write-next (timeout: 300s)
       → 等待完整响应
  │
  ▼
backend/api/lite.py: write_lite_next() / write_lite_next_stream()
  │  【巨量业务逻辑直接在 API 路由中】
  │
  ├─ 路径验证: _validate_project_id(), _validate_rel_path()
  ├─ 目标文件决策: _resolve_lite_output_file()
  │    → should_create_candidate() → 决定是否生成候选稿
  ├─ 确保章节存在: _ensure_chapter()
  ├─ 读取上下文: story-engine, story-state, style-guide, recent-context, ch-meta
  ├─ 构建 Prompt: PromptEngine.render("generate/continuation", {...})
  ├─ LLM 调用: LLMService.complete_sync()
  │    → 失败时使用 _fallback_section_content() 硬编码兜底
  ├─ 写入文件: file_service.write_file()
  ├─ 质量审查: QualityService.perform_review() (非候选稿时)
  │    → 质量过低时自动修复: 重新 LLM 调用
  ├─ 更新故事引擎: story-engine.md, recent-context.md
  ├─ 更新章节记忆: ch-meta.json
  └─ 章完成时: _generate_chapter_plan() (sec=4时)
  │
  ▼
前端处理:
  streamingBuffers[path] → content.value (textarea 绑定)
  → dirty = true → 用户手动保存或自动保存
  → fileStore.saveFile() → POST /api/file
```

### 关键文件
- 前端: `useLiteGeneration.ts` (22KB), `useLiteCandidateActions.ts`, `liteService.ts`
- 后端: `api/lite.py` (59.9KB!), `core/prompt_engine.py`
- 策略: `policies/candidate_policy.py`

---

## 5. Candidate 创建与采用调用链

### 创建候选稿

```
触发条件: should_create_candidate(action, target_path, file_exists, file_has_content)
  │
  ├─ 来源1: PipelineRunner 执行 rewrite/polish 管线
  │    → output_mode="candidate"
  │    → CandidateService.create_candidate()
  │
  ├─ 来源2: GenerationService.generate_stream() 回退模式
  │    → should_create_candidate() = True
  │    → CandidateService.create_candidate()
  │
  ├─ 来源3: API 直接调用 POST /api/candidates/{project_id}
  │    → backend/api/candidates.py: create_candidate()
  │
  └─ 来源4: Lite 模式
       → _resolve_lite_output_file() 决定输出到 .lite-candidates/
       → file_service.write_file() (不经过 CandidateService!)
  │
  ▼
CandidateService.create_candidate()
  │  读取源文件 → 记录 base_hash + base_mtime
  │  保存候选正文到 .candidates/{id}.{action}.md
  │  更新 metadata.json
  │  → SSE: candidate.created
```

### 采用候选稿

```
用户点击「采用」
  │
  ▼
CandidatePanel.vue → candidate API → POST /api/candidates/{project_id}/{id}/adopt
  │
  ▼
backend/api/candidates.py: adopt_candidate()
  │  创建 FileService + CandidateService
  ▼
CandidateService.adopt_candidate()
  │  1. 读取候选稿内容
  │  2. 读取当前源文件 → 计算 current_hash
  │  3. 对比 base_hash vs current_hash
  │     → 不一致: 返回 CONFLICT → 前端弹出冲突提示
  │  4. 对比 base_mtime vs current_mtime
  │     → 不一致: 返回 CONFLICT
  │  5. 写 revision-log (diff 摘要)
  │  6. 覆盖正式文件: file_service.write_file()
  │  7. 更新 status = adopted
  │  → SSE: candidate.adopted
```

### 关键文件
- 前端: `modules/candidate/api.ts`, `CandidatePanel.vue`, `useLiteCandidateActions.ts`
- 后端: `api/candidates.py`, `core/candidate_service.py`
- 策略: `policies/candidate_policy.py`

---

## 6. Project 创建与加载调用链

### 创建项目

```
Professional 模式:
  projectStore.createProject() → POST /api/projects
    → backend/api/projects.py: create_project()
      → ProjectService.create_project_meta()
      → 写 meta.json, context.json
      → 创建子目录: chapters, characters, materials, backup, revision-log, feedback
      → 初始化文件: style-guide.md, story-state.md, story-engine.md, recent-context.md, outline.md

Lite 模式:
  createLiteProject() → POST /api/lite/projects
    → backend/api/lite.py: create_lite_project()
      → ProjectService.create_project_meta() (复用)
      → 写 meta.json (含 lite_mode=True), context.json
      → 创建子目录 + story-engine.md (爽文模板)
      → _ensure_chapter() 创建第一章
```

### 加载项目

```
projectStore.openProject(id) → GET /api/projects/{id}
  → backend/api/projects.py: get_project()
    → ProjectService.get_project_info()
      → 读 meta.json + context.json + 计算统计

fileStore.loadTree(projectId) → GET /api/tree?project_id=...
  → backend/api/files.py: get_tree()
    → FileService.get_file_tree()

editorStore: 用户点击文件时
  → fileStore.readFile() → GET /api/file?project_id=...&path=...
    → FileService.read_file()
    → editorStore.loadContent(path, content)
```

### 关键文件
- 前端: `projectStore.ts`, `fileStore.ts`, `editorStore.ts`
- 后端: `api/projects.py`, `api/files.py`, `core/project_service.py`

---

## 7. File 保存与 FILE_CONFLICT 调用链

```
编辑器内容变化 → editorStore.updateContent() → fileStore.markDirty()
  │
  ▼
自动保存 (useAutoSave) 或手动保存 (Ctrl+S)
  │
  ▼
fileStore.saveFile(projectId, path, content)
  │  携带 expected_mtime + expected_hash
  │
  ▼
POST /api/file?project_id=...
  │  body: { path, content, expected_mtime, expected_hash }
  │
  ▼
backend/api/files.py: write_file()
  │  FileService.write_file(full_path, content, expected_mtime, expected_hash)
  │
  ├─ 成功: → SSE: file.updated (不含正文 content)
  │         → 返回 { path, content, mtime, hash }
  │
  └─ 冲突: expected_mtime/hash 不匹配
            → 抛出 FileConflictError (HTTP 409)
            → 前端 fileStore.showFileConflict()
               → Modal: "重新加载服务器版本" / "取消保存"
               → 重新加载: fileStore.readFile() → editorStore.loadContent()
```

### 关键文件
- 前端: `fileStore.ts` (saveFile, showFileConflict), `useAutoSave.ts`
- 后端: `api/files.py`, `core/file_ops.py`
- 事件: `domain/events.py` (make_file_updated_event)

---

## 8. SSE 事件流调用链

```
┌─────────────────────────────────────────────────────────┐
│                    后端事件源                            │
│                                                         │
│  1. EventBus (core/event_bus.py)                        │
│     → publish(event_type, data)                         │
│     → 推送到所有 subscriber queue                       │
│                                                         │
│  2. SSEManager (api/sse.py)                             │
│     → broadcast(event_type, data)                       │
│     → 推送到所有 SSE 连接 queue                         │
│     → 事件名映射: file.created → file-created           │
│                                                         │
│  3. main.py: _bridge_events_to_sse()                    │
│     → EventBus → SSEManager 桥接                        │
│                                                         │
│  4. 流式响应 (generate/pipeline/lite)                    │
│     → 直接 yield SSE 事件，不经过 EventBus               │
│     → generation/done/error 事件在响应流中直接返回       │
└─────────────────────────────────────────────────────────┘
        │
        ▼ EventSource / fetch SSE
┌─────────────────────────────────────────────────────────┐
│                    前端事件处理                          │
│                                                         │
│  1. useSSE.ts (SSEService)                              │
│     → EventSource 连接 /api/sse                         │
│     → 监听: file-created, file-updated, file-deleted,  │
│             task, pipeline-*, candidate-*, memory-*     │
│     → 分发到各 store 的 handler                         │
│                                                         │
│  2. useFileGeneration.ts (generationEmitter)            │
│     → fetch + ReadableStream 解析 SSE                   │
│     → generationEmitter.emit('generation', ...)         │
│     → useSSE 订阅 generationEmitter                     │
│     → editorStore.appendContentToFile()                 │
│                                                         │
│  3. chatStore.ts                                        │
│     → fetch + parseSSEStreamForChat()                   │
│     → 直接处理 delta，不经过 generationEmitter           │
│                                                         │
│  4. liteService.ts (streamLiteNext)                     │
│     → fetch + 手动 SSE 解析                             │
│     → callbacks.onDelta/onReplace/onDone                │
│     → 不经过 generationEmitter 或 useSSE                │
└─────────────────────────────────────────────────────────┘
```

### 事件类型双层命名

| 旧格式 (冒号分隔) | 新格式 (点分隔) | 前端映射 |
|-------------------|-----------------|----------|
| `file:created` | `file.created` | `file-created` |
| `file:modified` | `file.updated` | `file-updated` |
| `task:started` | - | `task` |
| - | `candidate.created` | `candidate-created` |
| - | `candidate.adopted` | `candidate-adopted` |
| - | `pipeline.started` | `pipeline-started` |
| - | `memory.updated` | `memory-updated` |

---

## 9. 当前混乱点列表

### P0 — 高风险（可能导致数据不一致或维护困难）

#### P0-1: `api/lite.py` 是一个 60KB 的巨型路由文件

**文件**: `backend/api/lite.py` (59.9KB, ~1200行)

**问题**:
- 包含完整的 Lite 业务逻辑：项目创建、章节规划、故事引擎更新、质量审查、LLM 调用、候选稿策略
- 大量硬编码的业务逻辑（故事引擎模板、兜底内容、章节结构常量）
- 直接操作 FileService，绕过 GenerationService 和 PipelineRunner
- 包含自己的路径验证函数（`_validate_project_id`, `_validate_rel_path`, `_safe_project_path`），与 FileService 内置验证重复
- 包含自己的章节/场景路径函数（`_path_parts`, `_section_path`, `_next_section_path`），与 `SceneService` 重复

**风险**:
- Lite 和 Professional 两条链路使用完全不同的生成逻辑，无法共享修复和改进
- 任何对生成流程的修改需要在两处同步
- 单文件过大，阅读和维护困难

#### P0-2: Lite 模式绕过 Pipeline 和 GenerationService

**文件**: `backend/api/lite.py:979-1167` (write_lite_next)

**问题**:
- Lite 的 `write_lite_next` 直接调用 `PromptEngine.render()` + `LLMService.complete_sync()`
- 不使用 `PipelineRunner` 或 `GenerationService`
- 候选稿写入使用 `.lite-candidates/` 目录而非标准 `.candidates/` 目录
- Lite 的候选稿不经过 `CandidateService`，没有 base_hash/base_mtime 冲突检测

**风险**:
- Lite 候选稿无法被 Professional 模式的 CandidatePanel 识别和管理
- 缺乏冲突检测可能导致数据丢失
- 两套候选稿系统增加用户心智负担

#### P0-3: 前端正文存在多个真相源

**文件**: `editorStore.ts`, `fileStore.ts`, `useLiteGeneration.ts`

**问题**:
- `editorStore.contents[path]` — 编辑器当前内容
- `fileStore.fileContents[path].content` — 文件读取/保存的内容
- `useLiteGeneration.streamingBuffers[path]` — Lite 模式流式缓冲
- `useFileGeneration._currentPrompt` — 当前生成提示

**数据流冲突**:
```
editorStore.contents[path] ←→ fileStore.fileContents[path].content
  ↑                              ↑
  │ 用户编辑                     │ 保存/读取
  │                              │
  └── appendContentToFile() ─────┘  AI 生成
  └── streamingBuffers[path] ──────┘  Lite 流式
```

- `editorStore.loadContent()` 设置 `contentSource = 'external'`
- `editorStore.updateContent()` 调用 `fileStore.markDirty()`
- `editorStore.appendContentToFile()` 同时修改 contents 和 markDirty
- Lite 模式的 `streamingBuffers` 是独立的缓冲区，通过 textarea 绑定显示

**风险**:
- 用户正在编辑时 AI 生成可能覆盖未保存内容
- `contentSource` 标记不够精确，无法区分 AI 追加 vs AI 替换 vs 文件读取
- Lite 的 `streamingBuffers` 和 `editorStore.contents` 可能不同步

#### P0-4: 两套 SSE 处理机制并存

**文件**: `useSSE.ts`, `useFileGeneration.ts`, `chatStore.ts`, `liteService.ts`

**问题**:
- **EventSource** (`useSSE.ts`): 用于 `/api/sse` 持久连接，处理文件/任务/管线事件
- **fetch + ReadableStream** (`useFileGeneration.ts`): 用于 `/api/generate` 和 `/api/pipeline/run`
- **fetch + parseSSEStreamForChat** (`chatStore.ts`): 用于 `/api/chat`
- **fetch + 手动 SSE 解析** (`liteService.ts`): 用于 `/api/lite/write-next-stream`

**generationEmitter 桥接**:
- `useFileGeneration` 通过 `generationEmitter.emit()` 分发事件
- `useSSE` 订阅 `generationEmitter` 并调用 `editorStore.appendContentToFile()`
- 但 `chatStore` 和 `liteService` 不经过 `generationEmitter`

**风险**:
- 4 种不同的 SSE 解析方式，维护成本高
- `generationEmitter` 只桥接了 generate/pipeline，chat 和 lite 完全独立
- 事件处理逻辑分散在多个文件中

### P1 — 中风险（代码重复或职责不清晰）

#### P1-1: 场景路径逻辑重复

**文件**:
- `backend/api/lite.py`: `_path_parts()`, `_section_path()`, `_next_section_path()`
- `backend/application/scene_service.py`: `SceneService.parse_scene_path()`, `build_scene_path()`
- `frontend/src/modules/scene/scenePath.ts`: `parseScenePath()`, `buildScenePath()`, `getNextScenePath()`
- `frontend/src/composables/useLiteGeneration.ts`: `parseSectionPath()`, `formatChapterLabel()`

**问题**: 4 处场景路径解析逻辑，命名和实现细节不完全一致。

#### P1-2: 候选稿策略分散

**文件**:
- `backend/policies/candidate_policy.py`: `should_create_candidate()` — 核心策略
- `backend/api/lite.py`: `_resolve_lite_output_file()` — Lite 专用策略
- `backend/core/pipeline.py`: 管线内的 output_mode 决策
- `backend/core/generation_service.py`: 回退模式内的候选稿判断

**问题**: 候选稿决策逻辑分散在 4 个文件中，Lite 有自己独立的策略。

#### P1-3: 项目创建逻辑重复

**文件**:
- `backend/api/projects.py:41-92`: Professional 项目创建
- `backend/api/lite.py:843-898`: Lite 项目创建

**问题**:
- 两处都手动创建目录结构和初始文件
- Lite 版本使用 `SECTIONS_PER_CHAPTER = 4` 和 `CHAPTERS_PER_VOLUME = 10`，与 AGENTS.md 声明的默认值（5场景/12章）不一致
- 没有统一的项目初始化 Service

#### P1-4: generationStore 职责边界模糊

**文件**: `frontend/src/stores/generation.ts`

**问题**:
- `continueWriting()` 使用 `fetch()` 直接调用 `/api/generate`（违反 CLAUDE.md 中"禁止用 fetch() 调后端 API"的规则）
- `continueWriting()` 内部判断管线映射，部分走 `fileGen.runPipeline()`，部分走 `fetch()`
- `rewriteContent()` 完全走 `fileGen.runPipeline()`
- 与 `useFileGeneration.ts` 的 `generateToFile()` 功能重叠

#### P1-5: EventBus 事件名双重格式

**文件**: `backend/core/event_bus.py`, `backend/api/sse.py`

**问题**:
- 旧格式: `file:created`, `file:modified`, `task:started`
- 新格式: `file.created`, `file.updated`, `candidate.created`
- `SSEManager._EVENT_MAP` 同时映射两种格式
- `EventTypes` 类同时定义两种常量

**风险**: 新代码可能使用任一格式，导致事件监听遗漏。

### P2 — 低风险（可改进但不紧急）

#### P2-1: `GenerationService` 内联创建 `CandidateService`

**文件**: `backend/core/generation_service.py:205-225`

**问题**: `GenerationService.generate_stream()` 在回退模式中直接 import 并创建 `CandidateService`，没有通过依赖注入。

#### P2-2: `api/files.py` 中的遗留项目路径兼容

**文件**: `backend/api/files.py:78-95`

**问题**: `_project_collection_root()` 检查遗留路径 `workspace/{project_id}` vs 新路径 `workspace/projects/{project_id}`，增加了每个请求的复杂度。

#### P2-3: 前端 `generationStore.continueWriting()` 使用 `fetch()` 而非 `api` 服务

**文件**: `frontend/src/stores/generation.ts:64`

**问题**: 直接使用 `fetch(API_BASE + API_ROUTES.generate)` 而非 `api.post()`，绕过了 Axios 拦截器（错误处理、token 注入等）。

#### P2-4: `chatStore` 持久化所有聊天消息到 localStorage

**文件**: `frontend/src/stores/chat.ts:215`

**问题**: `persist: { pick: ['messages'] }` 将所有聊天消息持久化，长期使用可能导致 localStorage 过大。

#### P2-5: Lite 模式的 `SECTIONS_PER_CHAPTER = 4` 与全局默认值不一致

**文件**: `backend/api/lite.py:101`

**问题**: AGENTS.md 声明默认每章 5 个场景，但 Lite 硬编码为 4。

---

## 10. 每个混乱点的风险等级汇总

| 编号 | 描述 | 等级 | 影响范围 |
|------|------|------|----------|
| P0-1 | lite.py 60KB 巨型路由文件 | P0 | Lite 全链路 |
| P0-2 | Lite 绕过 Pipeline/GenerationService | P0 | 生成一致性 |
| P0-3 | 前端正文多个真相源 | P0 | 数据安全 |
| P0-4 | 4 套 SSE 处理机制并存 | P0 | 事件一致性 |
| P1-1 | 场景路径逻辑 4 处重复 | P1 | 维护成本 |
| P1-2 | 候选稿策略分散在 4 个文件 | P1 | 策略一致性 |
| P1-3 | 项目创建逻辑重复 | P1 | 初始化一致性 |
| P1-4 | generationStore 职责模糊 | P1 | 前端架构 |
| P1-5 | EventBus 事件名双重格式 | P1 | 事件可靠性 |
| P2-1 | GenerationService 内联创建 CandidateService | P2 | 可测试性 |
| P2-2 | 遗留项目路径兼容 | P2 | 性能微损 |
| P2-3 | continueWriting 使用 fetch 而非 api | P2 | 错误处理 |
| P2-4 | chatStore 持久化所有消息 | P2 | 存储膨胀 |
| P2-5 | Lite 场景数与全局默认不一致 | P2 | 产品一致性 |

---

## 11. 建议的最小重构步骤

### 阶段 1: 提取 Lite 业务逻辑（解决 P0-1, P0-2）

**目标**: 将 `api/lite.py` 的业务逻辑提取到 Service 层

1. 创建 `backend/core/lite_service.py`，包含:
   - `LiteProjectService`: 项目创建 + 章节初始化
   - `LiteStoryEngine`: 故事引擎读写 + 更新
   - `LiteGenerationService`: 生成编排（复用 `GenerationService`）
   - `LiteQualityService`: 质量审查 + 自动修复

2. 将 `_ensure_chapter()`, `_path_parts()`, `_next_section_path()` 等函数迁移到 `SceneService`

3. 让 Lite 生成复用 `GenerationService` 或 `PipelineRunner`，而非直接调用 LLM

4. 将 Lite 候选稿统一到标准 `.candidates/` 目录和 `CandidateService`

**预期效果**: `api/lite.py` 缩减到 <15KB，只做参数校验和调 Service。

### 阶段 2: 统一前端正文管理（解决 P0-3）

**目标**: 确保正文只有一个真相源

1. 明确 `editorStore.contents[path]` 为唯一正文真相源
2. 将 Lite 的 `streamingBuffers` 改为直接写入 `editorStore.contents`
3. 添加 `contentSource` 细粒度标记: `'user' | 'ai-append' | 'ai-replace' | 'file-read'`
4. 在 `editorStore` 中添加 `mergeContent(path, delta, source)` 方法，处理并发编辑

### 阶段 3: 统一 SSE 处理（解决 P0-4）

**目标**: 减少 SSE 解析方式数量

1. 将 `useFileGeneration.parseSSEStream()` 提取为通用的 `parseSSE(reader, callbacks)` 工具
2. `chatStore` 和 `liteService` 都使用这个通用工具
3. 所有生成类事件（generation/done/error）统一通过 `generationEmitter` 分发
4. `useSSE` 作为唯一的 SSE 事件入口，所有组件只订阅 `useSSE`

### 阶段 4: 统一场景路径和候选稿策略（解决 P1-1, P1-2）

1. 后端: 所有场景路径操作统一使用 `SceneService`
2. 前端: 所有场景路径操作统一使用 `modules/scene/scenePath.ts`
3. 创建 `backend/policies/output_policy.py` 统一所有输出决策逻辑
4. 移除 `api/lite.py` 中的重复路径函数

### 阶段 5: 清理事件命名（解决 P1-5）

1. 统一使用点分格式 (`file.created`, `candidate.adopted`)
2. 移除冒号格式的 `EventTypes` 常量
3. 更新 `SSEManager._EVENT_MAP` 只映射点分格式

---

## 12. Lite vs Professional 对比

| 维度 | Lite 模式 | Professional 模式 |
|------|-----------|-------------------|
| 项目创建 | `POST /api/lite/projects` | `POST /api/projects` |
| 生成入口 | `POST /api/lite/write-next` | `POST /api/generate` |
| 生成方式 | 直接 LLM 调用 | Pipeline + 回退模式 |
| 流式输出 | `write-next-stream` (自有 SSE) | `generate` (通过 generationEmitter) |
| 候选稿 | `.lite-candidates/` (绕过 CandidateService) | `.candidates/` (CandidateService) |
| 故事记忆 | 内联更新 story-engine.md | MemoryService |
| 质量审查 | 内联 QualityService + 自动修复 | QualityService (独立调用) |
| 场景路径 | 自有 `_path_parts()` 等函数 | SceneService |
| 章节规划 | 内联 `_generate_chapter_plan()` | 无对应功能 |
| 前端缓冲 | `streamingBuffers` (独立) | `editorStore.contents` (共享) |
| 每章场景数 | 4 (硬编码) | 5 (全局默认) |

---

## 附录 A: 后端 API 端点清单

### generate.py
- `POST /api/generate` — LLM 生成（流式 SSE）
- `POST /api/generate/batch` — 批量生成
- `POST /api/chat` — 聊天（流式 SSE）
- `POST /api/stop` — 停止任务
- `GET /api/generate-tasks` — 生成任务状态（旧端点，已弃用）

### files.py
- `GET /api/file` — 读取文件
- `POST /api/file` — 写入文件
- `POST /api/file/create` — 创建文件
- `POST /api/file/rename` — 重命名文件
- `POST /api/file/delete` — 删除文件
- `POST /api/directory/create` — 创建目录
- `POST /api/directory/delete` — 删除目录
- `GET /api/tree` — 文件树
- `POST /api/files/search` — 搜索文件

### candidates.py
- `GET /api/candidates/{project_id}` — 列出候选稿
- `GET /api/candidates/{project_id}/{id}` — 获取候选稿详情
- `POST /api/candidates/{project_id}` — 创建候选稿
- `POST /api/candidates/{project_id}/{id}/adopt` — 采用候选稿
- `DELETE /api/candidates/{project_id}/{id}` — 删除候选稿
- `GET /api/candidates/{project_id}/file/{path}` — 获取文件的候选稿

### projects.py
- `GET /api/projects` — 项目列表
- `POST /api/projects` — 创建项目
- `GET /api/projects/{id}` — 项目详情
- `PUT /api/projects/{id}` — 更新项目
- `POST /api/projects/{id}/recalculate-stats` — 重新计算统计
- `DELETE /api/projects/{id}` — 删除项目

### lite.py
- `POST /api/lite/ideas` — 生成开局卡
- `POST /api/lite/projects` — 创建 Lite 项目
- `POST /api/lite/next-options` — 获取下一选项卡
- `POST /api/lite/write-next` — 写下一场景（非流式）
- `POST /api/lite/write-next-stream` — 写下一场景（流式）

### pipeline.py
- `POST /api/pipeline/run` — 运行管线
- `GET /api/pipeline/{name}` — 获取管线定义
- `POST /api/pipeline/custom` — 自定义管线

### sse.py
- `GET /api/sse` — SSE 事件流

---

## 附录 B: 前端 Store 依赖关系

```
projectStore ←── fileStore (watch currentProject → refreshTree)
     ↑               ↑
     │               │
editorStore ────→ fileStore (markDirty, unsavedFiles)
     ↑
     │
generationStore ──→ editorStore (setFilePrompt)
     │          ──→ taskStore (addTask, startTask)
     │          ──→ fileGeneration (runPipeline)
     │
chatStore ──────→ llmStore (setGenerating)
     │          ──→ taskStore (cancelTask)
     │
uiStore ←── rightPanelStore (布局联动)
```
