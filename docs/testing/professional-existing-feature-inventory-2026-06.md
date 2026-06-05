# Phase T4.0 — 原专业版现有功能总盘点与验收计划

## 1. 背景

T4 不应绕开原专业版模块重新设计。**正确的 T4 顺序是先验收原专业版现有功能，再扩展新专业能力。**

T3-D7 已完成 Python + LLM 写作质量与一致性引擎 MVP 链路：
```
Diff Engine → Review Engine → Validator → State Snapshot → Plot Debt → Rewrite Engine → Pipeline dry-run
```

现在进入 T4，但 T4 的第一步不是设计 Scene Plan 或 Prompt 编辑器，而是先盘点、验收原专业版现有功能。

## 2. 核心结论

**T4 = 先验旧专业版，再扩展新专业版。**

* 不应绕开原专业版模块重新设计
* 应先盘点、验收、复用，再扩展
* 原专业版功能稳定后，再接入 D7 Pipeline
* Scene Plan 和 Professional Prompt 扩展是后续阶段

## 3. 原专业版功能总览

| 功能模块 | 是否找到 | 后端位置 | 前端位置 | 当前作用 | 初步状态 | 风险 | 后续验收阶段 |
| ---- | ---- | ---- | ---- | ---- | ---- | -- | ------ |
| 用户对话框 / Chat Panel | ✅ | `api/candidates.py` | `stores/chat.ts` | 用户交互、生成、确认 | 已有 | 待验证 | T4.1 |
| 文件系统 / FileService | ✅ | `core/file_ops.py` | `composables/useEditorFileActions.ts` | 文件读写、项目管理 | 已有 | 待验证 | T4.5 |
| Lite 入口 | ✅ | `api/lite.py` | `composables/useLiteGeneration.ts` | 快速生成入口 | 已有 | 待验证 | T4.2 |
| Professional 入口 | ✅ | - | `router/index.ts` | 专业版入口 | 已有 | 待验证 | T4.2 |
| Workflow | ✅ | `core/workflow.py`, `api/workflows.py` | `composables/useWorkflow.ts` | 工作流定义和执行 | 已有 | 待验证 | T4.4 |
| Pipeline | ✅ | `core/pipeline.py`, `api/pipeline.py` | `stores/pipeline.ts` | 生成管线配置 | 已有 | 待验证 | T4.4 |
| Prompt Engine | ✅ | `core/prompt_engine.py` | `composables/usePromptSync.ts` | Prompt 渲染和版本管理 | 已有 | 待验证 | T4.4 |
| Prompt Editor / Template / Variant | ✅ | `api/prompts.py` | - | Prompt 编辑和变体 | 已有 | 待验证 | T4.4 |
| Candidate | ✅ | `core/candidate_service.py` | `modules/candidate/` | 候选稿机制 | 已有 | 待验证 | T4.3 |
| Generation / write-next / continuation | ✅ | `core/generation_service.py`, `api/generate.py` | `composables/useGenerationOrchestrator.ts` | 正文生成 | 已有 | 待验证 | T4.1 |
| Rewrite | ✅ | `core/quality_service.py` | `stores/review.ts` | 重写建议 | 已有 | 待验证 | T4.3 |
| Polish | ✅ | `core/quality_service.py` | `stores/review.ts` | 润色建议 | 已有 | 待验证 | T4.3 |
| De-AI | ✅ | `core/quality_service.py` | `stores/review.ts` | 去 AI 味 | 已有 | 待验证 | T4.3 |
| Story State Update | ✅ | `api/story_state.py` | `stores/storyState.ts` | 状态沉淀 | 已有 | 待验证 | T4.5 |
| Materials | ✅ | `api/materials.py` | - | 素材管理 | 已有 | 待验证 | T4.5 |
| Batch Generate | ⚠️ | 未明确 | 未明确 | 批量生成 | 未确认 | 待搜索 | T4.6 |
| Stream / SSE | ✅ | `api/sse.py` | `composables/useSSE.ts` | 流式响应 | 已有 | 待验证 | T4.6 |
| task_id / run_id | ✅ | `core/task_queue.py` | `modules/sse/types.ts` | 任务追踪 | 已有 | 待验证 | T4.6 |
| file.updated | ✅ | `api/sse.py` | `modules/sse/types.ts` | 文件更新事件 | 已有 | 待验证 | T4.6 |
| selected-card | ✅ | `api/lite.py` | `stores/generation.ts` | 选中的卡片 | 已有 | 待验证 | T4.1 |
| recent-context | ✅ | `api/recent_context.py` | `stores/recentContext.ts` | 最近上下文 | 已有 | 待验证 | T4.5 |
| story-engine | ⚠️ | - | 未明确 | 故事引擎 | 未确认 | 待搜索 | T4.5 |
| style-guide | ✅ | `api/style_guide.py` | `stores/styleGuide.ts` | 风格指南 | 已有 | 待验证 | T4.5 |

## 4. 用户主流程初步盘点

当前用户从打开项目到生成 candidate 的流程可能经过：

**后端 API 链路：**
```
projects.py → files.py → prompts.py → lite.py/generate.py 
→ candidate_service.py → workflow.py → generation_service.py 
→ llm.py → sse.py → candidates.py
```

**前端链路：**
```
router/index.ts → useApp.ts → useWorkflow.ts 
→ useGenerationOrchestrator.ts → useLiteGeneration.ts 
→ useSSE.ts → stores/candidate.ts → Chat/Dialog
```

## 5. Lite / Professional 共存风险

**共享代码可能影响 Lite 的模块：**
* `core/prompt_engine.py` - Prompt 渲染引擎
* `core/candidate_service.py` - 候选稿服务
* `core/generation_service.py` - 生成服务
* `api/sse.py` - SSE 事件推送

**后续必须做 Lite regression guard：**
* 扩展 Professional 功能时，不能破坏 Lite 的快速生成路径
* Prompt 变体和场景计划不能影响 Lite 的 selected-card 模式

## 6. Workflow / Pipeline / Prompt 初步发现

**后端 Workflow 模块：**
* `backend/core/workflow.py` - 核心工作流定义
* `backend/api/workflows.py` - 工作流 API
* `backend/schemas/workflow.py` - 工作流 Schema

**后端 Pipeline 模块：**
* `backend/core/pipeline.py` - 核心管线
* `backend/api/pipeline.py` - 管线 API
* `backend/application/pipeline/` - 管线执行器
* `backend/schemas/pipeline_config.py` - 管线配置

**后端 Prompt 模块：**
* `backend/core/prompt_engine.py` - Prompt 引擎
* `backend/core/prompt_versioning.py` - Prompt 版本管理
* `backend/api/prompts.py` - Prompt API

**前端相关：**
* `frontend/src/stores/pipeline.ts` - 管线状态
* `frontend/src/composables/usePromptSync.ts` - Prompt 同步
* `frontend/src/modules/pipeline/` - 管线模块

## 7. Candidate / Generation 初步发现

**后端 Candidate 模块：**
* `backend/core/candidate_service.py` - 候选稿服务
* `backend/api/candidates.py` - Candidate API
* `backend/schemas/candidate.py` - Candidate Schema
* `backend/domain/events.py` - Candidate 相关事件

**后端 Generation 模块：**
* `backend/core/generation_service.py` - 生成服务
* `backend/api/generate.py` - 生成 API
* `backend/application/lite_candidate_policy.py` - Lite Candidate 策略

**前端相关：**
* `frontend/src/modules/candidate/` - Candidate 模块
* `frontend/src/stores/generation.ts` - 生成状态
* `frontend/src/composables/useGenerationOrchestrator.ts` - 生成编排

## 8. Editing 能力初步发现

**后端编辑相关：**
* `backend/core/quality_service.py` - 质量服务（Rewrite/Polish/DeAI）
* `backend/api/quality.py` - 质量 API

**前端编辑相关：**
* `frontend/src/stores/review.ts` - 审查状态
* `frontend/src/composables/useLiteCandidateActions.ts` - Candidate 操作

## 9. File System / Materials / State 初步发现

**后端文件系统：**
* `backend/core/file_ops.py` - 文件操作
* `backend/api/files.py` - 文件 API
* `backend/application/scene_service.py` - 场景服务

**后端状态管理：**
* `backend/api/story_state.py` - 故事状态 API
* `backend/api/recent_context.py` - 最近上下文 API
* `backend/api/style_guide.py` - 风格指南 API
* `backend/api/materials.py` - 素材 API
* `backend/application/memory_service.py` - 记忆服务

**前端相关：**
* `frontend/src/stores/storyState.ts` - 故事状态
* `frontend/src/stores/recentContext.ts` - 最近上下文
* `frontend/src/stores/styleGuide.ts` - 风格指南
* `frontend/src/composables/useEditorFileActions.ts` - 文件操作

## 10. Batch / Stream / SSE 初步发现

**后端 SSE：**
* `backend/api/sse.py` - SSE API
* `backend/core/event_bus.py` - 事件总线
* `backend/models/task.py` - 任务模型

**后端任务队列：**
* `backend/core/task_queue.py` - 任务队列
* `backend/api/tasks.py` - 任务 API

**前端 SSE：**
* `frontend/src/composables/useSSE.ts` - SSE 组合式函数
* `frontend/src/modules/sse/` - SSE 模块
* `frontend/src/types/sse.ts` - SSE 类型定义

## 11. 不确定或缺失项

| 模块 | 状态 | 说明 |
| ---- | ---- | ---- |
| Batch Generate | ⚠️ 未确认 | 需要进一步搜索确认是否存在 |
| story-engine | ⚠️ 未确认 | 需要进一步搜索确认是否存在 |
| Chat Panel UI | ⚠️ 部分找到 | `stores/chat.ts` 存在，但 UI 组件需进一步确认 |
| selected-card | ✅ 找到 | Lite 相关代码中有定义 |

## 12. 修正后的 T4 路线图

| 阶段 | 任务 | 说明 |
| ---- | ---- | ---- |
| **T4.0** | 原专业版现有功能总盘点 | ✅ 本文档 |
| **T4.1** | 原专业版用户主流程端到端验收 | 验证从打开项目到生成 candidate 的完整流程 |
| **T4.2** | Lite / Professional 共存与切换基线验收 | 验证 Lite 和 Professional 入口切换 |
| **T4.3** | 原专业版编辑能力验收 | 验证 Rewrite/Polish/DeAI 功能 |
| **T4.4** | Workflow / Pipeline / Prompt 模块验收 | 验证工作流、管线、Prompt 引擎 |
| **T4.5** | Story State / Materials / 文件系统验收 | 验证状态管理、素材、文件操作 |
| **T4.6** | Batch / Stream / SSE / Task 验收 | 验证流式响应、任务追踪 |
| **T4.7** | 原专业版问题修复收口 | 修复发现的问题 |
| **T4.8** | Scene Plan schema + validator dry-run | 设计场景计划验收 |
| **T4.9** | Selected-card → Scene Brief / Scene Plan | 扩展到场景计划模式 |
| **T4.10** | Professional Draft Prompt 模板 | 设计专业版 Prompt |
| **T4.11** | Professional 接入 D7 Pipeline | 集成质量引擎 |
| **T4.12** | 用户确认清单 MVP | 用户确认流程 |

## 13. 不做的事

* 不新增功能
* 不调用 LLM
* 不修改生产 Prompt
* 不改生成主流程
* 不自动写正文
* 不自动入库
* 不跳过原专业版验收直接设计新功能

## 14. 当前结论

**T4 下一步应进入 T4.1：原专业版用户主流程端到端验收。**

必须先验证原专业版现有功能是否可用、稳定，再进行 Scene Plan 或 Prompt 编辑器扩展。

---

**文档完成日期**：2026-06-05
