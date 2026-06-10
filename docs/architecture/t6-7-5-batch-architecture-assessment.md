# T6.7.5 Batch 架构关系评估

> **任务性质**：架构评估文档，**不做实现**。不调用真实 LLM，不改 Batch 执行逻辑，不改文件写入策略，不改 candidate 策略。

> **前置基线**：T6.6.4（Batch dry-run 补齐）、T6.7.1（dev/test UI 整理）、T6.7.4（Task 状态 UI 统一）已完成。

---

## 一、当前 Batch 架构现状

### 1.1 执行链路

```
前端 generation.ts / 或测试触发
  ↓
POST /api/generate/batch
  (backend/api/generate.py)
  ↓
GenerationService.batch_generate(project_id, prompt_type, volume_number, chapter_number, section_numbers, temperature, dry_run)
  (backend/core/generation_service.py)
  ↓
for 每个 target section:
  渲染 prompt 文本
  ↓
  if dry_run:
    item.status = "dry_run", item.dry_run = True
    模拟文本，不调 LLM，不写文件，不生成 candidate
  else:
    svc.complete_sync(...)  ← 真实 LLM 调用（同步阻塞）
    ↓
    if 目标文件为空:
      file_service.write_file(full_path, generated.strip())  ← 直接写正文
    else:
      candidate_service.create_candidate(project_id, source_path, CONTINUE, generated.strip())
      item.status = "candidate"
  ↓
  tasks.append(item)
  ↓
return BatchGenerateResponse(tasks, total, succeeded, failed)
  ↓
ApiResponse.ok(result, message="批量 dry-run 完成" 或 "批量生成完成")
  ↓
前端：直接在调用侧处理，不进入 TaskQueue / 不发布 SSE
```

### 1.2 关键代码位置

| 模块 | 文件 | 关键函数 / 类型 |
|------|------|-----------------|
| API | `backend/api/generate.py` | `async def batch_generate(req)` |
| 服务 | `backend/core/generation_service.py` | `async def batch_generate(...)` |
| 响应类型 | `backend/schemas/llm.py` | `BatchGenerateRequest` / `BatchGenerateResponse` / `BatchGenerateItem` |
| LLM | `backend/core/llm.py` | `complete_sync()` |
| 候选稿 | `backend/core/candidate_service.py` | `create_candidate()` |
| Candidate 策略 | `backend/policies/candidate_policy.py` | `should_create_candidate()` |
| 前端调用 | `frontend/src/stores/generation.ts` | `async batchGenerate(req)` → `api.post(API_ROUTES.generateBatch, req)` |
| 前端状态面板 | `frontend/src/components/right-panel/ExecutionPanel.vue` | `dry-run-status-panel`（T6.7.4 统一状态面板） |

### 1.3 现状要点

- **同步执行**：一个 HTTP 请求内完成所有 section 的批量处理，无后台任务，无队列
- **不经过 TaskQueue**：`POST /api/tasks` 和 `POST /api/generate/batch` 是两条独立路径
- **不发布 EventBus / SSE 事件**：batch_generate 中无 `event_bus.publish()`
- **不返回 SSE stream**：与 Pipeline 的流式 JSON 不同，Batch 返回单个 JSON
- **dry-run 已有安全分支**：dry_run=True 时，不调 LLM，不写文件，不生成 candidate
- **真实 batch 仍是高风险路径**：真实 LLM 批量调用 + 批量写文件 + 批量 candidate，不可在未设计时大改

---

## 二、与 TaskQueue 对比

| 维度 | Batch (现在) | TaskQueue (现在) |
|------|--------------|------------------|
| 执行方式 | 同步 HTTP 内阻塞 | 异步队列（`asyncio.Queue` + worker） |
| 任务 ID | 无（每个 item 有自己的 target_file，非全局 task_id） | `uuid` 全局唯一 `task_id` |
| 状态返回 | 响应体中 `tasks / total / succeeded / failed` | `GET /api/tasks` 轮询 + `task:started/completed/failed` 事件 |
| 取消 | 无（HTTP 请求内无法取消已发起的 LLM 调用） | `POST /api/tasks/{task_id}/cancel` → 状态 `cancelled` |
| SSE | 无（T6.7.4 通过前端统一状态面板展示 dry-run 摘要） | `event_bus` 发布 `task:*` 事件，可经 SSE 推送 |
| dry-run | `dry_run=True` 请求参数，服务层分支处理 | `POST /api/tasks` 支持 `dry_run: true` |
| 文件写入 | 空文件→直接写正文；有内容→生成 candidate | TaskExecutor 简单写入，不区分文件是否存在 |
| candidate 策略 | 复用 `should_create_candidate()`，基于文件内容判断 | 任务执行器不强制使用 candidate |
| 持久化 | 无（结果在响应中，不落到磁盘） | `task_queue.json` 等持久化在项目目录 |
| 风险 | 批量 LLM/批量写；长请求易超时 | 单任务可控；超时风险分散 |

---

## 三、与 Pipeline 对比

| 维度 | Batch (现在) | Pipeline (现在) |
|------|--------------|-----------------|
| 执行方式 | 同步批量（一次请求完成） | 流式 SSE（`event: thinking / generation / done`） |
| 响应格式 | 单个 JSON (`ApiResponse<BatchGenerateResponse>`) | SSE 分帧：`event: done` + `data: {dry_run: true}` |
| dry-run | 请求内分支 | 流内事件标记 dry_run |
| 前端观测 | `api.post()` → 直接拿 JSON → 调用方自行展示 | `EventSource` / `fetch` 分帧 → `useSSE` 消费 |
| 事件体系 | 无（不发布到 event_bus） | `runner.run()` 生成独立 SSE 事件流；部分发布到 event_bus |
| 适用场景 | 多 section 批量生成（如一卷/一章的多个场景） | 单文件/工作流（润色/重写/续写等） |
| Pipeline 定义 | 使用 prompt 模板文本，不经过 pipeline YAML | 每个 pipeline 有 YAML 定义 + step prompt 分档 |
| 进度反馈 | 前端无（直到响应返回） | 流式 `thinking / generation / step_done / done` |

---

## 四、风险分析

### 4.1 直接接入 TaskQueue 的风险

1. **API 响应语义变化**：现在 `POST /api/generate/batch` 同步返回完整结果。接入 TaskQueue 意味着从「同步响应」变为「提交 task_id + 异步拉取结果」，调用方需改动。
2. **批量任务的取消/失败/部分成功**：Batch 中部分 section 成功、部分失败，当前在响应中以 `succeeded / failed` 区分。接入队列后，失败项的重跑策略、结果聚合未设计。
3. **子任务模型**：如果把每个 section 拆成一个子任务，需要「父任务 + N 子任务」模型。现有 TaskQueue 是扁平的，不支持父子关系。
4. **SSE 事件量**：若发布 per-section 事件，100 个 section 可能产生 300+ 事件（start/generation/done）。前端消费和展示需设计。
5. **真实 LLM 成本**：Batch 调用 `svc.complete_sync()` 多次，无任务间节流。接入 TaskQueue 后应考虑节流，但当前无设计。
6. **不应在无设计时大改**：这是本任务的核心结论——Batch 与 TaskQueue 的合并需要先做设计，再分阶段实现，不在 T6.7 直接实现。

### 4.2 保留 Batch 独立架构的合理性

- **设计用途不同**：Batch 面向「批量预热/批量生成多场景」，TaskQueue 面向「单个长任务排队」
- **API 契约不同**：同步响应 vs 异步队列
- **失败语义不同**：Batch 的「部分成功」在 TaskQueue 中无直接对应

---

## 五、推荐方案：分阶段演进

### Phase A（本任务）：保持现状，文档化

- ✅ 已完成：本评估文档
- ✅ T6.7.4 已补充 dry-run 统一状态面板（前端观测）
- 不改动后端 Batch 执行逻辑
- 不改动文件写入策略
- 不改动 candidate 策略

### Phase B：为 Batch 增加更明确的结果结构字段（可选后续任务）

目标：不改执行模式，**只增强响应结构**。

- 在 `BatchGenerateItem` 中增加：
  - `would_write_file: bool`（dry-run 模式下，模拟判断是否会写正文）
  - `would_create_candidate: bool`（dry-run 模式下，模拟判断是否会生成 candidate）
  - `prompt_tokens: int`（估算 prompt token 数）
  - `section_path: str`（明确 section 的相对路径）
- 不改变真实执行路径
- 需要更新 contract 测试（新测试文件，不修改现有 T6.6.4 测试）

### Phase C：设计 BatchTask 概念（不立即实现）

- 为 Batch 设计「父任务 + 子 items」模型
- 设计状态：`pending / running / partially_completed / completed / failed`
- 设计取消语义：支持在 item 粒度取消，保留已完成项结果
- 设计结果持久化：`{project}/.batch-results/{run_id}.json`
- **设计阶段不写代码**，以 RFC 形式评审

### Phase D：可选接入 TaskQueue

- Phase C 设计完成后，再考虑把 Batch 作为一个新的任务类型接入 TaskQueue
- 采用 `parent task + child items` 模式，父任务代表整个 batch
- 改变 API 响应为：`{task_id: string, status: "running", child_count: N}`
- 需要兼容旧 API：要么新增 `POST /api/generate/batch-async`，要么通过 `mode=async` 参数切换

### Phase E：Batch SSE / progress events

- 若 Phase D 落地，考虑为 Batch 建立 `batch:item_started / batch:item_completed / batch:done` 事件
- 与现有 Pipeline stream 格式一致，不另造格式

### Phase F：真实 Batch LLM 冒烟

- 在 Phase B/C/D 至少 B 完成后，再在受控环境下执行真实 LLM Batch 冒烟
- 先小批量（2-3 个 section），验证 token 成本和失败恢复

---

## 六、最小后续任务建议

### 任务 1：T6.7.5a — Batch result schema contract 加固

**目标**：锁定 dry-run 和真实 batch 的响应结构，为后续 Phase B 打基础。

- 新增 `backend/tests/contracts/test_t6_7_5a_batch_result_schema.py`
- 测试点：
  1. `POST /api/generate/batch(dry_run=True)` 的响应字段完整（tasks / total / succeeded / failed）
  2. 每个 `BatchGenerateItem` 包含 `target_file / status / dry_run`
  3. status = "dry_run" 时，不包含真实 LLM 文本
  4. 不写文件，不生成 candidate
- 不调用真实 LLM
- 不改现有 API 行为
- 不改现有 T6.6.4 dry-run contract 测试（平行存在）

### 任务 2：T6.7.6 — 真实 LLM 冒烟测试准备检查

如果用户想进入真实 LLM 阶段，先检查：

- `MOYUN_ALLOW_REAL_LLM_SMOKE=1` 开关机制
- `__llm_smoke_*` 项目命名规范
- 真实调用的 max_tokens <= 300 限制
- API Key 不出现在日志

---

## 七、本轮明确不做的事

以下内容在本任务中**明确不做**，避免架构震荡：

| 事项 | 原因 |
|------|------|
| 把 Batch 接入 TaskQueue | 需要 Phase C 先做设计，本轮只评估 |
| 改 Batch 默认执行路径 | 保持现有同步 API 契约稳定 |
| 增加真实 LLM 调用 | 本任务不触发真实 LLM |
| 改 candidate 策略 | 现有 `should_create_candidate` 已工作 |
| 改文件写入策略 | 空文件直接写 / 有内容生成 candidate 保留 |
| 引入 batch SSE 事件 | Phase E 以后考虑 |
| 大重构 Batch 架构 | 高风险，T6.7 不做 |

---

## 八、结论汇总

### 8.1 现状总结

- ✅ Batch dry-run 已工作（T6.6.4 验证）
- ✅ 前端统一状态面板已展示 dry-run 摘要（T6.7.4）
- ⚠️ Batch 与 TaskQueue / Pipeline 架构不统一，三条链路各自独立
- ⚠️ Batch 真实 LLM 路径高风险，未在冒烟阶段执行

### 8.2 建议后续顺序

1. **T6.7.5a**（建议 P2）：Batch result schema contract 加固（只读测试，不写代码）
2. **T6.7.6**（P1，如有真实 LLM 需求）：真实 LLM 冒烟测试准备检查
3. （可选未来）**Phase C**：BatchTask 设计 RFC
4. （可选未来）**Phase D**：接入 TaskQueue

### 8.3 本任务交付物

- 本文档：`docs/architecture/t6-7-5-batch-architecture-assessment.md`
- 更新：`docs/roadmap/t6-7-productization-roadmap.md`（T6.7.5 标记为完成）

---

*文档结束*
