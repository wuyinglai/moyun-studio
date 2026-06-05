# Phase T4.6 — Batch / Stream / SSE / Task 验收

## 1. 背景

上一阶段 T4.5 已完成 Story State / Materials / File System 静态验收。本阶段验收 Batch / Stream / SSE / Task 能力。只做静态验收和文档，不新增功能。

---

## 2. Batch Generate Findings

⚠️ **Batch Generate 模块尚未完整实现**

### 后端
- ❌ 未找到 `backend/*batch*.py` 独立批量生成模块
- ✅ `TaskQueue` (backend/core/task_queue.py) 支持单个任务入队和执行，可作为批量任务基础
- ✅ `api/tasks.py` 提供任务提交、列表、详情、取消接口

### 前端
- ❌ 未找到 `*Batch*.vue` 组件
- ✅ `useTaskStore` (stores/task.ts) 提供任务状态管理
- ✅ 支持 pending/running/done/failed/cancelled 状态

### 结论
Batch Generate 功能尚未完整实现，但底层 TaskQueue 已就绪。

---

## 3. Stream Generation Findings

⚠️ **Stream Generation 部分实现**

### 后端
- ✅ `TaskExecutor._generate_content` (task_queue.py) 支持流式 LLM 调用：
  ```python
  async for chunk in self.llm.complete(messages, model=model, stream=True):
      chunks.append(chunk)
  ```
- ✅ 流式内容收集后一次性返回，尚未实现流式 SSE 推送给前端

### 前端
- ✅ `useFileGeneration` 有 `generationEmitter` 处理生成事件
- ✅ `useSSE` 有 `_streamHandler` 引用，但具体实现未看到完整流式渲染

### 结论
Stream Generation 底层已支持，但完整前端流式输出尚未实现。

---

## 4. SSE Findings

✅ **SSE 模块完整且合规**

### 后端
- ✅ `backend/api/sse.py` 提供 SSE 端点
- ✅ `SSEManager` 管理连接、广播事件、心跳
- ✅ `EventBus` (core/event_bus.py) 发布事件
- ✅ `domain/events.py` 统一事件模型，所有事件带 `project_id`，可选 `task_id`
- ✅ `file.updated` 事件不带 `content`（符合契约要求）

### 事件类型完整
- ✅ `file.created` / `file.updated` / `file.deleted`
- ✅ `candidate.created` / `candidate.adopted`
- ✅ `pipeline.started` / `pipeline.step.started` / `pipeline.step.completed` / `pipeline.step.failed`
- ✅ `task.waiting_for_user` / `task.completed`
- ✅ `memory.updated`

### 前端
- ✅ `composables/useSSE.ts`
  - ✅ EventSource 连接管理
  - ✅ 心跳检测（45 秒超时自动重连）
  - ✅ 退避重连策略（最大 10 次）
  - ✅ 按 `project_id` 过滤事件（隐式：store 处理）
  - ✅ 集成 `useTaskStore` / `useFileStore` / 等

### 结论
SSE 模块完整，事件契约合规。

---

## 5. Task Queue Findings

✅ **Task Queue 模块完整**

### 后端
- ✅ `backend/core/task_queue.py`
  - ✅ 任务入队、执行、取消
  - ✅ 磁盘持久化：`<project>/.task-queue/<task_id>.json`
  - ✅ 启动时 `restore()` 恢复中断任务
  - ✅ `TaskExecutor` 执行具体任务

### 模型
- ✅ `backend/models/task.py`
  - ✅ `TaskStatus` enum (pending/running/completed/failed/cancelled)
  - ✅ `TaskModel` 完整字段

### API
- ✅ `backend/api/tasks.py`
  - ✅ `POST /api/tasks` 提交任务
  - ✅ `GET /api/tasks` 获取列表
  - ✅ `GET /api/tasks/{task_id}` 获取详情
  - ✅ `POST /api/tasks/{task_id}/cancel` 取消任务

### 结论
Task Queue 完整，支持持久化和恢复。

---

## 6. candidate_created / file.updated Findings

✅ **事件发布完整**

### candidate.created
- ✅ `candidate_service.create_candidate` 发布 `candidate.created` 事件（来自 domain/events.py `make_candidate_created_event`）
- ✅ 事件带 `project_id` / `candidate_id` / `source_path` / `action`

### candidate.adopted
- ✅ `candidate_service.adopt_candidate` 发布 `candidate.adopted` 事件
- ✅ 事件带 `project_id` / `candidate_id` / `source_path`

### file.updated
- ✅ `domain/events.make_file_updated_event` 明确标注不发送 `content`（`# AI_GUARDRAIL_ALLOW`）
- ✅ 事件带 `path` / `size` / `mtime`

### 结论
事件发布完整，符合安全契约。

---

## 7. Failure Handling Findings

✅ **失败处理机制完整**

### Task Queue
- ✅ `TaskExecutor.execute_task` 捕获异常，发布 `task.failed` 事件
- ✅ `TaskStatus.FAILED` 状态
- ✅ `error` 字段保存错误信息

### Pipeline
- ✅ `pipeline.py` 有 fallback 机制，失败时回退到上一步
- ✅ 发布 `pipeline.step.failed` 事件

### 结论
失败处理完整，状态可恢复。

---

## 8. Candidate / Official Write Boundary

✅ **边界清晰且安全**

### 原则
- ✅ `polish` / `rewrite` 默认 `output_mode='candidate'`（useFileGeneration.ts）
- ✅ 正式文件写入必须 `expected_mtime` / `expected_hash` 校验（FileService）
- ✅ `candidate.adopt` 前检查冲突，后写入 revision_log

### 结论
不会自动覆盖正式文件，边界安全。

---

## 9. Lite Impact

✅ **Lite 完全独立，不受影响**

- ✅ Lite 使用独立 API 路由（api/lite.py）
- ✅ Lite 有独立 stream 实现（api/lite.py 流式输出）
- ✅ Lite 不依赖 Professional TaskQueue / SSE

### 结论
T4.6 验收不修改 Lite，安全无影响。

---

## 10. Missing or Uncertain Areas

- ❌ Batch Generate 完整 UI/API 未实现
- ❌ Stream Generation 前端流式渲染未完整实现
- ⚠️ `run_id` 在 `AppEvent` 中有定义，但尚未大量使用

---

## 11. 验收结论

⚠️ **静态验收通过，核心能力完整，部分功能未实现**

✅ 通过项：
- ✅ SSE 模块完整，事件契约合规
- ✅ Task Queue 完整，支持持久化和恢复
- ✅ candidate.created / candidate.adopted / file.updated 事件发布完整
- ✅ 失败处理完整
- ✅ Candidate / Official Write Boundary 清晰安全
- ✅ Lite 不受影响

❌ 未实现：
- ❌ Batch Generate 完整功能
- ❌ Stream Generation 前端流式输出

**文档完成日期：2026-06-05**
