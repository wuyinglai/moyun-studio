# T6.7.3 Pipeline stream 格式标准化评估

> **阶段性质**：文档评估阶段。**不改协议，不破坏现有 E2E**。

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-10 | 初始评估 |

---

## 一、当前状态

- Pipeline dry-run 已通过（T6.6.3 / T6.7.1 均验证）
- 当前 stream 可观测：前端 `fetch` + `response.body.getReader()` 能逐行读取
- 当前 **不是标准 SSE `event:` / `data:` 双字段格式**
- 当前测试依赖 JSON payload 中的 `event: "done"` 和 `dry_run: true` 字段
- candidate-adopted SSE 映射 bug 已修复（T6.7.2）

---

## 二、当前链路图

```
┌──────────────────────────────────┐
│ ExecutionPanel.handleDryRunPipeline │
└─────────┬────────────────────────┘
          │ POST /api/pipeline/run
          │ Content-Type: application/json
          │ body: { pipeline, project_id, target_file, dry_run }
          ▼
┌──────────────────────────────────┐
│ backend/api/pipeline.py          │
│ run_pipeline()                   │
│ return EventSourceResponse(stream)│
└─────────┬────────────────────────┘
          │ async for event in runner.run():
          │   yield {"event": "...", "data": json.dumps({...})}
          ▼
┌──────────────────────────────────┐
│ sse_starlette EventSourceResponse│
│ 自动包装为 SSE 传输格式           │
│ data: {"event":"...","data":"..."}│
│ \n\n                              │
└─────────┬────────────────────────┘
          │ HTTP chunked transfer
          ▼
┌──────────────────────────────────┐
│ 前端 ExecutionPanel.vue          │
│ fetch() + response.body.getReader()│
│ 逐行读取 buffer                   │
│ 识别 line.startsWith('data: ')    │
│ JSON.parse(line.slice(6))        │
│ data.event === 'done' → 完成判断   │
│ data.dry_run === true → dry_run  │
└──────────────────────────────────┘
```

---

## 三、当前 stream 格式明细

### 后端 yield 格式（来自 `backend/core/pipeline.py`）

```python
yield {"event": "task_start", "data": json.dumps({...})}
yield {"event": "thinking",  "data": json.dumps({...})}
yield {"event": "prompt",    "data": json.dumps({...})}
yield {"event": "step_done", "data": json.dumps({...})}
yield {"event": "generation", "data": json.dumps({"dry_run": True, ...})}
yield {"event": "done",      "data": json.dumps({"dry_run": True, ...})}
yield {"event": "error",     "data": json.dumps({"message": "..."})}
```

### HTTP 传输格式（经 EventSourceResponse 包装后）

```
data: {"event":"task_start","data":"{...}"}

data: {"event":"thinking","data":"{...}"}

data: {"event":"done","data":"{...}","dry_run":true,"message":"..."}

```

注意：
1. 每一行以 `data: ` 开头，行尾 `\n\n` 表示消息分隔
2. payload 是**一整个 JSON 对象**，包含 `event` 字段
3. **没有**标准 SSE 的 `event: done\ndata: {...}` 双行格式

### 前端解析逻辑

```typescript
const line = 'data: {"event":"done","data":"{...}","dry_run":true,"message":"..."}'
if (line.startsWith('data: ')) {
  const data = JSON.parse(line.slice(6))   // 解析整个 JSON
  const event = data.event || data.type    // 从 JSON 中取 event 字段
  if (event === 'done') {
    receivedDone = true
    isDryRun = data.dry_run === true
  }
}
```

---

## 四、与标准 SSE 的差异

| 维度 | 当前 JSON stream | 标准 SSE |
|------|-----------------|----------|
| Content-Type | `text/event-stream` (由 EventSourceResponse 设置) | `text/event-stream` |
| 行格式 | `data: {event, data, ...}` | `event: pipeline-done\ndata: {...}\n\n` |
| event 名称位置 | JSON payload 内的 `event` 字段 | 独立的 `event:` 行 |
| 前端处理方式 | `fetch()` + `getReader()` 手动解析 | `new EventSource(url)` + `addEventListener('pipeline-done', ...)` |
| 与 `/api/sse` 体系一致性 | 不一致（两套解析逻辑） | 一致（统一 event/data 体系） |
| EventSource 浏览器原生支持 | 不直接（需要手动解析） | 直接（原生支持 `event:` / `data:`） |

---

## 五、两套机制对比

### 当前 Pipeline stream

- **路径**：`POST /api/pipeline/run`
- **实现**：`EventSourceResponse` 传输，但 event 名称在 JSON payload 内
- **前端**：`fetch` + `getReader` + 手动解析 `data: ` 行 + JSON.parse
- **EventBus 集成**：部分事件发布到 EventBus（`thinking`, `done`, `error`, `step_done`, `prompt`）
- **文件更新事件**：通过 EventBus → `/api/sse` 转发（与 Pipeline stream 是两条不同的流）

### `/api/sse` 标准 SSE

- **路径**：`GET /api/sse`（持久连接）
- **实现**：`SSEManager` + `_bridge_events_to_sse`
- **格式**：`event: file-updated\ndata: {...}\n\n`（标准格式）
- **前端**：`useSSE.ts` → `new EventSource()` → `addEventListener('file-updated', ...)`
- **事件**：`file-updated`, `candidate-adopted`, `file-created`, `file-deleted`, `pipeline-started` 等

---

## 六、风险分析

### 直接改 `pipeline/run` 为标准 SSE 的风险

1. **破坏现有 E2E**：T6.6.3 / T6.7.1 的 Playwright 依赖当前格式
2. **前端解析逻辑改动**：`ExecutionPanel.vue` 的 stream 解析需完全重写
3. **真实 LLM 流式 token 输出**：当前 JSON payload 结构承载 token 流，改标准 SSE 需重新设计 token 流
4. **与 EventBus/SSEManager 合并**：需要设计 event 类型映射，可能引入新 bug
5. **兼容性降级**：如果同时支持 JSON stream 和 SSE，复杂度加倍

### 保留当前格式的风险

1. **两套 stream 体系**：Pipeline 与 `/api/sse` 不一致，前端两套解析逻辑
2. **event 名称依赖 JSON payload**：需要手动找 `data.event` 而非原生 `addEventListener`
3. **不可直接用 EventSource API**：需要手动解析 `data: ` 行
4. **新增 stream 事件时需同步改两处**（前端解析 + 后端 yield 格式）

---

## 七、推荐方案：分阶段演进

### Phase A：文档化 + contract 锁定（本阶段已完成的部分）

- [x] 文档化当前 JSON stream 格式（本文档）
- [x] 新增 contract 测试锁定当前消息格式（见 `test_t6_7_3_pipeline_stream_contract.py`）
- [ ] （可选）文档化真实 LLM 流式 token 输出格式（T6.6.5 后）

### Phase B：可选标准 SSE 模式（不改默认）

新增可选 query/header 参数：
- `POST /api/pipeline/run?stream_format=sse` 或
- `Accept: text/event-stream` + `X-Stream-Format: standard-sse`

后端响应：
```
event: pipeline-step-done
data: {"step_id": "validate", "step_label": "Scene Plan 验证"}

event: pipeline-done
data: {"dry_run": true, "message": "管线执行完成...", "total_steps": 3}

```

前端接入：
- 新的执行器通过 `EventSource` 监听标准事件
- 逐步替换旧的 `fetch + getReader` 实现

**风险低**：默认不改，新增路径可选

### Phase C：前端统一接入

- ExecutionPanel 新增 SSE 模式执行器
- dev/test 工具区增加 "Standard SSE" 按钮
- Playwright 测试双模式覆盖

### Phase D：兼容期后默认切换（可选）

- 充分验证后，可在某个大版本中把默认切换为 SSE
- 保留旧的 stream 格式一段时间作为兼容模式

---

## 八、本阶段不建议做的事

| 不做事项 | 原因 |
|---------|------|
| 直接改 `/api/pipeline/run` 默认返回格式 | 破坏现有 28 测试，风险高 |
| 删除 JSON stream | 无回退方案 |
| 改真实 LLM 流式生成 | 超出 dry-run 验证范围 |
| 改 Batch / TaskQueue stream | 架构割裂评估需在 T6.7.5 |
| 合并 Pipeline stream 和 `/api/sse` | 两套机制设计目的不同 |
| 调用真实 LLM | 超出 dry-run 阶段 |

---

## 九、最小推荐方案（即 T6.7.3 交付）

1. ✅ 本评估文档
2. ✅ 新增 `test_t6_7_3_pipeline_stream_contract.py` 锁定当前格式
3. 暂不改变 `pipeline/run` 默认行为
4. 暂不改变前端解析逻辑

---

## 十、下一步建议

| 选项 | 说明 | 推荐度 |
|------|------|--------|
| **T6.7.4 Task 状态 UI 统一** | 整理 TaskQueue / Pipeline / Batch 的 task 状态显示，不涉及协议 | 高 |
| **T6.7.5 Batch 架构关系评估** | 设计评估 Batch 是否接入 TaskQueue | 中 |
| **T6.7.3a Phase B 标准 SSE 模式** | 实现可选标准 SSE 模式，不改默认 | 中低 |
| **T6.6.5 真实 LLM 冒烟** | 需要显式开关，风险中等 | 视需求 |

---

*文档结束*
