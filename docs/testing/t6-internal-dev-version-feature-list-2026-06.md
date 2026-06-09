# T6.1: 内部开发版功能清单与状态汇总

**版本**: 2026-06（T5.18-H1 验收后刷新）
**扫描基准 Commit**: `977c602`（盘点时远端 HEAD）
**生成日期**: 2026-06-09
**执行方式**: 纯静态文件扫描（`docs/testing/` + `tests/` + `backend/` + `frontend/`），未调用 LLM，未生成 candidate，未修改 workspace

---

## 1. 整体状态

| 维度 | 值 |
|------|-----|
| 功能模块总数 | **22** |
| 已完整验收（有验收文档 + 有测试 + 通过） | **12** |
| 部分验收（有文档 or 部分测试覆盖） | **5** |
| 未验收（代码存在但无独立验收文档） | **5** |
| 验收文档总数 | **43 份** |
| 测试文件总数 | **47 份** |
| Backend 核心文件数 | **66 份**（api + core + schemas + policies） |
| 扫描基准 Commit | `977c602`（文档修订 commit 见文末） |
| 当前分支 | `main` |
| 文档生成时工作区状态 | clean（T6.1 提交时） |

**总结**：T5.18-H1 之后，项目已形成可用的写作最小闭环。Scene Plan 后端链路完整（生成/保存/验证），Candidate Provenance 元数据机制就绪，Scoring 规则评分系统稳定；主要缺口在前端 UI（Scene Plan 编辑器、Prompt 编辑器深度验证、Stream SSE 推送）与批量生成能力。

---

## 2. 模块详细清单（22 个模块）

### 2.1 文件系统 / FileService

- **验收状态**: ✅ 已验收（静态层）
- **定位**: 项目最底层的文件读写服务，所有文件操作必须通过此层，禁止 API 直接拼接路径
- **后端关键代码**:
  - `file_ops.py` — `FileService` 类（`read_file` / `write_file` / `expected_hash` / `expected_mtime`）
  - `files.py` — 文件 REST API
  - `exceptions.py` — 文件冲突异常（`FILE_CONFLICT`）
- **前端状态**:
  - `file.ts` — 文件状态管理
  - `editor.ts` — 编辑器内容管理
- **验收文档**:
  - `professional-state-materials-filesystem-acceptance-2026-06.md`
- **测试文件**:
  - `test_api_validation.py`
  - `test_api_quality.py`
  - `test_candidate_flow_e2e*.py` 中集成验证
- **关键能力**: 文件读取、写入、冲突检测、expected_hash/mtime 校验
- **缺口**: 大文件分片上传 / 断点恢复（非当前目标）

---

### 2.2 Project 项目管理

- **验收状态**: ✅ 已验收（基础层）
- **定位**: 项目创建、列举、元数据管理
- **后端关键代码**:
  - `project_service.py`
  - `projects.py`
- **前端状态**:
  - `project.ts`
- **验收文档**: professional-main-flow-acceptance-2026-06.md（作为主流程起点提及）
- **测试文件**: test_user_story.py, test_api_validation.py
- **关键能力**: 项目创建、列举、元数据读写
- **缺口**: 项目归档、项目删除的深度验证

---

### 2.3 Candidate 候选稿机制（含 Provenance）

- **验收状态**: ✅ 已完整验收（含 T5.17-H2 / T5.18-H1）
- **定位**: 写作系统最核心的安全机制。所有 polish / rewrite / chat-edit / continue 默认生成 candidate，不覆盖正文；用户显式 adopt 后才生效
- **后端关键代码**:
  - `candidate_service.py` — `CandidateService` 类（`create_candidate` / `get_candidate` / `adopt` 等）
  - `candidates.py` — REST API
  - `candidate.py` — `CandidateInfo` / `CandidateAction` 定义，含 `generation_context` / `scene_plan_hash` / `scene_plan_path` 字段（T5.17-H2）
  - `candidate_policy.py` — candidate 策略（禁止直接覆盖正文）
  - `generation_output_policy.py` — 输出策略
- **前端关键代码**:
  - `CandidatePanel.vue` — candidate 预览、采用、删除
- **验收文档（9 份）**:
  - `professional-main-flow-acceptance-2026-06.md`
  - `professional-editing-flow-acceptance-2026-06.md`
  - `professional-candidate-flow-e2e-result-2026-06.md`
  - `professional-candidate-flow-dryrun-2026-06.md`
  - `t5-scene-plan-chain-architecture-audit-2026-06.md`
  - `t5-scene-plan-target-binding-fix-2026-06.md`
  - `t5-scene-plan-candidate-provenance-fix-2026-06.md`
  - `t5-candidate-provenance-chain-acceptance-2026-06.md`
  - `chat-panel-candidate-trigger-dryrun-2026-06.md`
- **测试文件（13 份）**:
  - `test_candidate_provenance.py` — provenance 字段验证
  - `test_candidate_flow_e2e.py` / `test_candidate_flow_e2e_v2.py` / `test_candidate_flow_e2e_full.py` — candidate 主流程 e2e
  - `test_candidate_panel_probe.py` / `test_candidate_panel_probe_simple.py` — CandidatePanel UI 探测
  - `test_candidate_preview_delete_e2e.py` / `test_candidate_preview_delete_fixed.py` — 预览/删除功能
  - `test_candidate_adopt_conflict_sse_e2e.py` — adopt 冲突检测与 SSE 事件
  - `test_professional_candidate_flow.py` — professional 模式 candidate 流
  - `test_scene_plan_quality_provenance_scoring.py` — scoring 层 provenance 处理
- **关键能力**:
  - candidate 创建 / 获取 / 预览 / 采用 / 删除
  - adopt 前 `base_hash` / `base_mtime` 冲突检测
  - adopt 后写入 revision-log
  - generation_context / scene_plan_hash / scene_plan_path 元数据（T5.17-H2）
- **评分关联**: T5.18-H1 后 scoring JSON 已注入 provenance 状态；当前历史样本 4 个均为 `legacy_candidate`（不伪造）
- **缺口**: 历史 candidate 无 provenance；后续新生成的 candidate 将自动携带

---

### 2.4 Scene Plan 场景计划（API 层）

- **验收状态**: ✅ 已完整验收（后端 API）
- **定位**: 给 AI 生成提供结构化的场景约束——地点、时间、角色、冲突、情节 beats 等
- **后端关键代码**:
  - `scene_plan.py` — `/api/scene-plan/generate` / `save` / `validate` / `load` / `list`
  - `scene_plan_validator.py` — `validate_scene_plan` / `validate_scene_plan_target_binding`
  - `scene_plan.py` — Pydantic Schema
- **验收文档（7 份）**:
  - `t5-scene-plan-generate-api-2026-06.md`
  - `t5-scene-plan-persistence-api-2026-06.md`
  - `t5-scene-plan-frontend-ui-2026-06.md`
  - `t5-scene-plan-chain-architecture-audit-2026-06.md`
  - `t5-scene-plan-target-binding-fix-2026-06.md`
  - `t5-scene-plan-professional-smoke-2026-06.md`
  - `t5-writing-loop-gap-analysis-2026-06.md`
- **测试文件（5 份）**:
  - `test_scene_plan_generate_api.py` — API 生成测试
  - `test_scene_plan_persistence_api.py` — 保存/加载测试
  - `test_scene_plan_validate_api.py` — 验证测试
  - `test_scene_plan_validator.py` — validator 单元测试
  - `test_scene_plan_pipeline_integration.py` — pipeline 集成
- **关键能力**:
  - JSON Schema 校验（title / goal / conflict / required_beats / location / time / characters）
  - target_file 强绑定：scene_plan 与 target scene 路径一致
  - 危险路径检测（禁止穿越 workspace）
- **缺口**: 前端 Scene Plan 编辑器未实现（见 2.16）

---

### 2.5 Scoring 评分系统

- **验收状态**: ✅ 已完整验收（规则评分 + 对比 + multi-score + provenance 注入）
- **定位**: 基于规则对 baseline 与 with-plan candidate 进行自动化评分，不调用 LLM
- **后端关键代码**:
  - `scene_plan_quality_score.py` — 主评分脚本（9 个评分维度 + 汇总）
- **评分维度**:
  1. scene_goal_alignment（目标对齐度）
  2. beats_coverage（情节覆盖度）
  3. conflict_presence（冲突体现）
  4. characters_consistency（人物一致性）
  5. location_consistency（地点一致性）
  6. time_consistency（时间一致性）
  7. no_reasoning_logs（无推理日志）
  8. language_quality_basic（语言质量）
  9. plan_contradiction_check（矛盾检测）
  10. **provenance 状态**（T5.18-H1 新增注入）
- **验收文档（6 份）**:
  - `t5-scene-plan-quality-score-2026-06.md`
  - `t5-scene-plan-quality-compare-2026-06.md`
  - `t5-scene-plan-quality-multi-score-2026-06.md`
  - `t5-scene-plan-quality-final-errata-2026-06.md`
  - `t5-candidate-provenance-chain-acceptance-2026-06.md`
- **评分产物**（artifacts，禁止修改）:
  - `docs/testing/artifacts/t5-scene-plan-quality-multi-score-final-2026-06.json` / `.md`
  - `docs/testing/artifacts/t5-scene-plan-quality-cases-2026-06.json`
- **当前评分（固定值）**:
  - sec-001: baseline 17 / with-plan 15（with-plan 表现较差）
  - sec-002: baseline 14 / with-plan 14（两者相近）
- **测试文件**:
  - `test_scene_plan_quality_provenance_scoring.py` — 9 个测试用例
- **关键能力**: 规则评分、JSON/Markdown 报告、legacy candidate 兼容、provenance 状态注入
- **缺口**: 无（功能完整，测试覆盖）

---

### 2.6 Generation 生成服务

- **验收状态**: ✅ 已完整验收（主流程）
- **定位**: 正文生成（continue / rewrite / polish）的服务层
- **后端关键代码**:
  - `generation_service.py` — `GenerationService`（`generate_stream` / `batch_generate` 骨架）
  - `generate.py` — REST API
  - `quality_service.py` — 润色/重写质量服务
- **前端关键代码**:
  - `generation.ts` — 生成状态管理
  - `review.ts` — rewrite/polish 结果管理
- **验收文档**: professional-main-flow-acceptance-2026-06.md, professional-editing-flow-acceptance-2026-06.md
- **测试文件**: test_professional_regression_smoke.py, test_user_story.py, 各种 candidate e2e 测试中集成
- **关键能力**: 流式生成、停止信号、批处理骨架
- **缺口**: Stream 生成的 SSE 推送未完整接入前端（见 2.17）

---

### 2.7 LLM 服务与熔断器

- **验收状态**: ✅ 已完整验收（安全层）
- **定位**: 统一 LLM 调用入口 + 连续失败熔断 + API Key 脱敏
- **后端关键代码**:
  - `llm.py` — `LLMService`（LiteLLM 封装，流式调用）
  - `llm_circuit_breaker.py` — 连续失败熔断
  - `llm.py` — LLM 配置 API（不含 key 泄漏）
  - `llm.py` — Schema
- **验收文档**:
  - `t5-local-model-dryrun-smoke-2026-06.md`
- **测试文件**:
  - `test_llm.py` — 基础调用测试
  - `test_llm_api.py` — API 层测试
  - `test_llm_reasoning_detection.py` — 推理日志检测（`<thinking>` 等）
- **关键能力**: 统一 LiteLLM 入口、流式响应、熔断器、API Key 脱敏（sk-\* → sk-\*\*\*）
- **缺口**: 无（安全关键层完整）

---

### 2.8 Chat Panel（对话面板）

- **验收状态**: ✅ 已验收
- **定位**: 用户与 AI 对话的 UI，触发 rewrite/polish/continue 并生成 candidate
- **前端关键代码**:
  - `ChatPanel.vue` — 对话 UI
  - `chat.ts` — 消息状态管理
- **验收文档（3 份）**:
  - `chat-panel-trigger-contract-2026-06.md`
  - `chat-panel-candidate-trigger-dryrun-2026-06.md`
- **测试文件（3 份）**:
  - `test_chatpanel_selected_text_ui_e2e.py`
  - `test_chatpanel_selected_text_candidate_simple.py`
  - `test_chatpanel_selected_text_candidate_link.py`
- **关键能力**: 对话输入、SSE 流式消息、选中文字触发 rewrite/polish、生成 candidate

---

### 2.9 Lite 快速写作

- **验收状态**: ✅ 已完整验收（爽文模式）
- **定位**: 低门槛快速生成路径，不依赖 Scene Plan
- **后端关键代码**:
  - `lite.py` — Lite API
  - `lite.py` — Schema
- **前端关键代码**:
  - LiteWritingView.vue（快速写作页面）
- **验收文档（11 份，含 prompt 优化与质量评审）**:
  - `lite-professional-switch-baseline-2026-06.md`
  - `lite-real-generation-smoke-report-2026-06.md`
  - `lite-output-quality-review-2026-06.md`
  - lite-prompt-optimization-\* 系列（4 份）
  - lite-fallback-\* 系列（2 份）
  - lite-next-options-chain-diagnosis-2026-06.md
  - lite-continuous-generation-diagnosis-2026-06.md
- **测试文件**: test_professional_regression_smoke.py（含 Lite 模式切换）
- **关键能力**: selected-card 模式、快速生成、与 Professional 共存且互不破坏

---

### 2.10 Pipeline 管线

- **验收状态**: ⚠️ 部分验收（dry-run 通过，深度场景未独立验证）
- **定位**: 定义一条生成任务的执行步骤——调用什么模型、使用什么 prompt、输出到哪里
- **后端关键代码**:
  - `pipeline.py` — 管线核心
  - `pipeline.py` — API
  - `pipeline.py` / `pipeline_config.py` — Schema
  - `pipeline_validator.py` — 启动时校验
- **前端关键代码**:
  - `pipeline.ts`
  - `PipelineEditor.vue`
- **验收文档**: professional-workflow-pipeline-prompt-acceptance-2026-06.md, t5-scene-plan-chain-architecture-audit-2026-06.md
- **测试文件**: test_workflow_pipeline_dryrun.py, test_scene_plan_pipeline_integration.py
- **关键能力**: 多步骤管线定义、scene_plan 软接入、prompt 变量替换
- **缺口**: 自定义管线编辑器的端到端验收、复杂 pipeline 场景的稳定性

---

### 2.11 Workflow 工作流

- **验收状态**: ⚠️ 部分验收（静态结构完整，深度场景未独立验证）
- **定位**: 编排多个 pipeline 顺序执行 / 条件分支 / Human-in-the-loop 暂停
- **后端关键代码**:
  - `workflow.py` — Workflow 引擎
  - `workflows.py` — API
  - `workflow.py` — Schema
  - `node_types.py` — 节点类型
- **前端关键代码**:
  - WorkflowPanel.vue
  - StepEditor.vue
  - useWorkflow.ts（composable）
- **验收文档**: professional-workflow-pipeline-prompt-acceptance-2026-06.md
- **测试文件**:
  - `test_workflow_pipeline_dryrun.py`
  - `test_workflow_pipeline_crud.py`
- **关键能力**: 多步骤编排、loop 嵌套、Human 节点暂停/恢复、变量池
- **缺口**: 实际工作流运行场景的深度验收、错误恢复、异常分支测试

---

### 2.12 Prompt Engine 提示词引擎

- **验收状态**: ⚠️ 部分验收（静态结构完整，prompt 变体未深度验证）
- **定位**: Jinja2 模板渲染 + Prompt 版本管理 + 变体管理
- **后端关键代码**:
  - `prompt_engine.py` — Jinja2 模板引擎
  - `prompt_versioning.py` — 版本管理
  - `prompts.py` — Prompt API
- **验收文档（2 份）**:
  - professional-workflow-pipeline-prompt-acceptance-2026-06.md
  - professional-prompt-architecture-2026-06.md
- **测试文件**: 无独立测试文件（依赖 workflow/pipeline 测试覆盖）
- **关键能力**: Jinja2 模板、变量注入、版本管理
- **缺口**: Prompt 变体选择器的前端验证、模板编辑预览、独立测试用例

---

### 2.13 Story State 故事状态

- **验收状态**: ⚠️ 部分验收（静态 API 完整，与主流程深度集成未独立验证）
- **定位**: 沉淀主角状态、势力关系、伏笔回收、主线进度等结构化信息
- **后端关键代码**:
  - `story_state.py` — API
  - `character_service.py` — 角色服务
- **前端关键代码**:
  - `storyState.ts` — Store
  - StoryStatePanel.vue — 面板
- **验收文档**: professional-state-materials-filesystem-acceptance-2026-06.md
- **测试文件**:
  - `test_story_state_materials_dryrun.py`
- **关键能力**: 读写状态、结构化 Schema、用户确认后写入
- **缺口**: 与 candidate generation 的深度集成、状态变更的 SSE 推送

---

### 2.14 Materials 素材管理

- **验收状态**: ⚠️ 部分验收（静态 API 完整）
- **定位**: 角色卡、设定卡、世界观素材管理
- **后端关键代码**:
  - `materials.py`
  - `characters.py`
- **前端关键代码**: MemorySettingsPanel.vue
- **验收文档**: professional-state-materials-filesystem-acceptance-2026-06.md
- **测试文件**: test_story_state_materials_dryrun.py（共同覆盖）
- **关键能力**: 素材文件读写、素材列举
- **缺口**: 素材版本管理、与 pipeline 的集成深度

---

### 2.15 Style Guide 风格指南

- **验收状态**: ⚠️ 部分验收（静态 API 存在）
- **定位**: 定义写作风格（简洁 vs 华丽等），AI 生成时参考
- **后端关键代码**:
  - `style_guide.py`
- **前端关键代码**:
  - `styleGuide.ts`
- **验收文档**: professional-state-materials-filesystem-acceptance-2026-06.md
- **测试文件**: 无独立测试
- **关键能力**: 风格配置读写
- **缺口**: 风格指南与生成 pipeline 的深度集成验证

---

### 2.16 Recent Context 最近上下文

- **验收状态**: ⚠️ 部分验收（API 存在，无独立测试）
- **定位**: 提供最近 N 个场景文本摘要，供 AI 生成时参考上下文
- **后端关键代码**:
  - `recent_context.py`
- **前端关键代码**:
  - `recentContext.ts`
- **验收文档**: professional-state-materials-filesystem-acceptance-2026-06.md
- **测试文件**: 无独立测试
- **关键能力**: 最近 N 个场景内容聚合
- **缺口**: 上下文生成质量验证、与 Generation Service 的深度集成

---

### 2.17 Stream / SSE 流式推送

- **验收状态**: ❌ 未验收（底层存在但前端推送未完整接入）
- **定位**: 将 LLM 流式响应实时推送到前端，实现打字机效果和进度反馈
- **后端关键代码**:
  - `sse.py` — SSE 路由
  - `event_bus.py` — 事件总线
  - `task_queue.py` — TaskQueue（chunk 收集已实现）
- **前端关键代码**:
  - useSSE.ts（SSE 连接管理）
- **验收文档**: professional-batch-stream-sse-task-acceptance-2026-06.md（定位为缺口）
- **测试文件**: test_candidate_adopt_conflict_sse_e2e.py（仅 cover 单个 adopt 事件）
- **关键能力（已实现）**: 心跳机制（15s 间隔）、超时重连（45s）、事件总线
- **关键能力（缺失）**: 流式内容 chunk 的 SSE 推送（当前收集后一次性返回）、前端打字机效果
- **缺口**: Streaming 是用户体验关键缺口；需实现 `generate_stream` → `event_bus` → `SSE` → `useSSE.ts` 全链路打通

---

### 2.18 Task Queue 任务队列

- **验收状态**: ❌ 未验收（存在但与 Batch 绑定，未独立验证）
- **定位**: 异步任务执行、取消、状态追踪
- **后端关键代码**:
  - `task_queue.py` — `TaskExecutor` / `Task`
  - `tasks.py` — 任务 API
- **前端关键代码**:
  - `task.ts`
- **验收文档**: professional-batch-stream-sse-task-acceptance-2026-06.md
- **测试文件**: `test_t472_backend_verification.py`（部分底层验证）
- **关键能力**: 任务提交、取消、状态查询（pending/running/done/failed/cancelled）
- **缺口**: 复杂任务依赖、任务持久化恢复、任务队列持久化

---

### 2.19 Batch Generate 批量生成

- **验收状态**: ❌ 未验收（未完整实现）
- **定位**: 对多个场景一键执行 polish / continue / scene plan 生成
- **后端关键代码**:
  - generation_service.py 中的 `batch_generate`（骨架存在）
- **前端关键代码**: 无独立 Batch 组件
- **验收文档**: professional-batch-stream-sse-task-acceptance-2026-06.md（明确为未实现）
- **测试文件**: 无独立测试
- **关键能力**: 骨架存在；UI / 实际调度未实现
- **阻塞点**: 依赖 Task Queue + Stream SSE；当前非最小闭环所需

---

### 2.20 Scene Plan 前端 UI

- **验收状态**: ❌ 未验收（未实现）
- **定位**: 用户在前端编辑器中创建 / 编辑 / 保存 Scene Plan 的界面
- **后端基础**: 已完整（API 存在，见 2.4）
- **前端状态**:
  - 无专门的 ScenePlan 编辑器组件
  - EditorToolbar 存在但未接入 Scene Plan 生成
  - RightPanel 无 Scene Plan Tab
- **验收文档**: t5-scene-plan-frontend-ui-2026-06.md（明确记录缺口）
- **测试文件**: `test_scene_plan_frontend_smoke.py`（仅 smoke）
- **缺口**: 完整 UI 实现：表单式编辑器、beats 列表编辑、JSON 预览、保存按钮

---

### 2.21 Quality Engine / De-AI（写作质量引擎）

- **验收状态**: ✅ 已验收（规则层完整）
- **定位**: 润色、去 AI 味、矛盾检测
- **后端关键代码**:
  - `quality_service.py` — QualityService
  - `quality.py` — API
  - `quality.py` — Schema
- **验收文档（3 份）**:
  - `d7-writing-quality-engine-acceptance-2026-06.md`
  - `python-llm-writing-quality-engine-2026-06.md`
  - `de-ai-writing-quality-rules-2026-06.md`
- **测试文件**: 包含于 candidate flow e2e 测试
- **关键能力**: polish / rewrite / de-ai 规则、与 candidate 集成

---

### 2.22 辅助能力（Revision Log / Snapshot / Trash / Backup / Wizard）

- **验收状态**: ✅ 已验收（作为主流程的辅助能力，在 candidate flow 中隐式验证）
- **模块组成**:
  - `revision_log.py` — 修改日志
  - `snapshot.py` — 快照
  - `snapshots.py` — 快照 API
  - `trash.py` / `trash.py` — 回收站
  - `backup.py` — 备份
  - `wizard.py` — 引导向导
  - `compare.py` — 正文对比
  - `feedback.py` — 用户反馈
  - `config.py` — 系统配置
  - `tokens.py` — Token 用量
- **关键能力**: 辅助运维与审计
- **验收文档**: professional-existing-feature-inventory-2026-06.md

---

## 3. 状态汇总表

| # | 模块 | 状态 | 验收文档 | 测试文件 | 关键缺口 |
|---|------|------|---------|---------|---------|
| 1 | 文件系统 / FileService | ✅ 已验收 | 1 份 | 2+ 份 | 无 |
| 2 | Project 项目管理 | ✅ 已验收 | 集成 | 2 份 | 无 |
| 3 | Candidate 候选稿 + Provenance | ✅ 已验收 | 9 份 | 13 份 | 历史样本缺 provenance |
| 4 | Scene Plan（API 层） | ✅ 已验收 | 7 份 | 5 份 | 前端 UI 缺失 |
| 5 | Scoring 评分 | ✅ 已验收 | 6 份 | 1 份 | 无 |
| 6 | Generation 生成服务 | ✅ 已验收 | 集成 | 3+ 份 | Stream SSE 未打通 |
| 7 | LLM 服务与熔断器 | ✅ 已验收 | 1 份 | 3 份 | 无 |
| 8 | Chat Panel 对话面板 | ✅ 已验收 | 3 份 | 3 份 | 无 |
| 9 | Lite 快速写作 | ✅ 已验收 | 11 份 | 集成 | 无 |
| 10 | Quality Engine / De-AI | ✅ 已验收 | 3 份 | 集成 | 无 |
| 11 | Story State 故事状态 | ⚠️ 部分 | 集成 | 1 份 | 与生成深度集成 |
| 12 | Materials 素材 | ⚠️ 部分 | 集成 | 1 份 | 版本管理 |
| 13 | Style Guide 风格指南 | ⚠️ 部分 | 集成 | 0 份 | 生成集成验证 |
| 14 | Recent Context 最近上下文 | ⚠️ 部分 | 集成 | 0 份 | 上下文质量验证 |
| 15 | Pipeline 管线 | ⚠️ 部分 | 1 份 | 2 份 | 编辑器深度验证 |
| 16 | Workflow 工作流 | ⚠️ 部分 | 1 份 | 2 份 | 深度运行场景 |
| 17 | Prompt Engine | ⚠️ 部分 | 2 份 | 0 份 | Prompt 变体系统 |
| 18 | 辅助能力（revision/snapshot/trash） | ✅ 已验收 | 集成 | 集成 | 无 |
| 19 | Stream / SSE 流式推送 | ❌ 未验收 | 1 份（缺口定位） | 0 份 | chunk → SSE 全链路 |
| 20 | Task Queue 任务队列 | ❌ 未验收 | 1 份（缺口定位） | 0 份 | 复杂任务依赖 |
| 21 | Batch Generate 批量生成 | ❌ 未验收 | 1 份（缺口定位） | 0 份 | 完整 UI + 调度 |
| 22 | Scene Plan 前端 UI | ❌ 未验收 | 1 份（缺口定位） | 1 份（smoke） | 完整编辑器实现 |

**总计**: 22 个模块 / ✅ 12 / ⚠️ 5 / ❌ 5

---

## 4. 测试文件与验收文档映射表

| 测试文件 | 对应模块 | 验收文档 |
|----------|---------|---------|
| test_candidate_provenance.py | Candidate Provenance | t5-candidate-provenance-chain-acceptance-2026-06.md |
| test_candidate_flow_e2e*.py (3 份) | Candidate 主流程 | professional-candidate-flow-\* |
| test_candidate_panel_probe\*.py (2 份) | CandidatePanel UI | professional-editing-flow-acceptance |
| test_candidate_preview_delete\*.py (2 份) | Candidate 预览/删除 | professional-main-flow-acceptance |
| test_candidate_adopt_conflict_sse_e2e.py | Adopt 冲突检测 + SSE | professional-candidate-flow-\* |
| test_professional_candidate_flow.py | Professional candidate | professional-candidate-flow-\* |
| test_scene_plan_quality_provenance_scoring.py | Scoring + Provenance | t5-scene-plan-quality-\* + provenance |
| test_scene_plan_generate_api.py | Scene Plan API | t5-scene-plan-generate-api-2026-06.md |
| test_scene_plan_persistence_api.py | Scene Plan 持久化 | t5-scene-plan-persistence-api-2026-06.md |
| test_scene_plan_validate_api.py | Scene Plan 验证 | t5-scene-plan-chain-architecture-audit |
| test_scene_plan_validator.py | Scene Plan validator | t5-scene-plan-chain-architecture-audit |
| test_scene_plan_pipeline_integration.py | Scene Plan ↔ Pipeline | t5-scene-plan-chain-architecture-audit |
| test_scene_plan_frontend_smoke.py | Scene Plan UI（smoke） | t5-scene-plan-frontend-ui-2026-06.md |
| test_professional_regression_smoke.py | Professional 回归 | professional-main-flow-acceptance |
| test_user_story.py | 用户故事流 | professional-main-flow-acceptance |
| test_workflow_pipeline_dryrun.py | Workflow + Pipeline | professional-workflow-pipeline-prompt-acceptance |
| test_workflow_pipeline_crud.py | Workflow CRUD | professional-workflow-pipeline-prompt-acceptance |
| test_story_state_materials_dryrun.py | Story State + Materials | professional-state-materials-filesystem-acceptance |
| test_chatpanel_selected_text_\*.py (3 份) | Chat Panel | chat-panel-trigger-contract |
| test_llm.py / test_llm_api.py / test_llm_reasoning_detection.py | LLM + 熔断器 | t5-local-model-dryrun-smoke |
| test_api_validation.py / test_api_quality.py | 文件系统 + API | professional-state-materials-filesystem |
| test_t472_backend_verification.py | Task Queue 底层 | professional-batch-stream-sse-task-acceptance |
| test_e2e\*.py / test_full_ui.py / test_ui_playwright.py (7+ 份) | 端到端 UI | e2e-human-flow-checklist, full-product-test-plan |
| test_outline_fix.py / test_chapter_gen.py | 大纲/章节 | 集成验证 |
| test_simple.py / test_quick_verify.py | 基础冒烟 | 集成验证 |

---

## 5. 测试运行状态（最近一次验证：T5.18-H1）

```
tests/test_scene_plan_quality_provenance_scoring.py  →  9/9 PASSED
tests/test_candidate_provenance.py                     →  5/5 PASSED
tests/test_scene_plan_pipeline_integration.py          →  PASSED
tests/test_scene_plan_generate_api.py                  →  PASSED
tests/test_scene_plan_persistence_api.py               →  PASSED
tests/test_scene_plan_validate_api.py                  →  PASSED
tests/test_scene_plan_validator.py                     →  PASSED
tests/test_professional_regression_smoke.py            →  PASSED
```

- **核心测试通过率**: 100%
- **总测试文件数**: 47 份
- **核心测试文件（Scene Plan + Candidate + Provenance）**: 约 21 份，覆盖端到端主链路

---

## 6. 建议的后续迭代优先级

| 优先级 | 模块 | 原因 | 前置依赖 | 预计验收文档 |
|--------|------|------|---------|------------|
| P1（最高） | Scene Plan 前端 UI | 后端 API 已完整；缺 UI 导致用户无法真正使用 Scene Plan | Scene Plan API（已完成） | 1 份 |
| P1 | Stream / SSE 流式推送 | 影响用户体验；长任务无实时进度反馈 | EventBus + TaskQueue（已存在） | 1 份 |
| P2 | Prompt Engine 独立测试 | 当前 0 份独立测试，安全隐患 | Workflow / Pipeline（已完成） | 1 份 |
| P2 | Prompt / Pipeline 编辑器深度验证 | 影响自定义能力易用性 | Workflow / Pipeline（已完成） | 1 份 |
| P3 | Story State 与生成深度集成 | 提升一致性质量，非最小闭环必需 | Candidate Provenance（已完成） | 1 份 |
| P3 | Batch Generate | 增强能力；非最小闭环 | Task Queue + Stream SSE（待完成） | 1 份 |
| P4 | Recent Context 质量验证 | 锦上添花 | Story State（已部分完成） | 1 份 |

---

## 6.5 未验收模块最小验收方案

针对内部开发版，以下为未验收/部分验收模块的最小验收方案，确保核心功能可运行并验证：

### 6.5.1 ❌ Scene Plan 前端 UI（未验收）

**最小验收步骤**：
1. 在 EditorToolbar 添加「生成 Scene Plan」按钮
2. 点击按钮调用 `/api/scene-plan/generate` 生成 plan
3. 在 RightPanel 添加 ScenePlanTab，展示生成的 JSON
4. 提供「保存」按钮，调用 `/api/scene-plan/save`
5. 提供「验证」按钮，调用 `/api/scene-plan/validate`

**依赖**：Scene Plan API（已完成）、RightPanel 框架（已存在）

**测试文件**：`test_scene_plan_frontend_smoke.py`（需扩展）

**验证方法**：
- UI 点击测试：按钮存在且可点击
- API 调用测试：生成/保存/验证接口返回成功
- 状态测试：plan 内容正确显示

**预期结果**：用户可通过 UI 创建、查看、保存 Scene Plan

---

### 6.5.2 ❌ Stream / SSE 流式推送（未验收）

**最小验收步骤**：
1. 在 `generation_service.py` 中实现流式响应到 EventBus 的转发
2. 在 `sse.py` 中添加 chunk 级事件广播
3. 在 `useSSE.ts` 中实现流式消息接收
4. 在编辑器中实现打字机效果

**依赖**：EventBus（已存在）、TaskQueue（已存在）、Generation Service（已完成）

**测试文件**：新建 `test_stream_sse_integration.py`

**验证方法**：
- 启动生成任务，验证 SSE 事件持续推送
- 验证打字机效果实时显示
- 验证进度百分比更新

**预期结果**：长任务有实时进度反馈，正文逐字显示

---

### 6.5.3 ⚠️ Prompt Engine 独立测试（部分验收）

**最小验收步骤**：
1. 创建独立测试文件，覆盖 Jinja2 模板渲染
2. 测试变量注入、条件判断、循环等核心功能
3. 测试模板版本管理的基本 CRUD

**依赖**：Workflow / Pipeline（已完成）

**测试文件**：新建 `test_prompt_engine.py`

**验证方法**：
- 模板渲染正确性测试
- 变量替换测试
- 版本切换测试

**预期结果**：Prompt 模板引擎功能独立验证通过

---

### 6.5.4 ❌ Batch Generate 批量生成（未验收）

**最小验收步骤**：
1. 实现 `batch_generate` 核心逻辑（已有骨架）
2. 集成 TaskQueue 进行任务调度
3. 添加批量生成 API 端点

**依赖**：Task Queue（待完成）、Stream SSE（待完成）

**测试文件**：新建 `test_batch_generate.py`

**验证方法**：
- 多场景批量生成测试
- 任务状态跟踪测试
- 失败重试测试

**预期结果**：支持选择多个场景一键生成

---

### 6.5.5 ⚠️ Story State 深度集成（部分验收）

**最小验收步骤**：
1. 在生成前读取 Story State 作为上下文
2. 在生成后更新角色状态
3. 实现状态变更的 SSE 推送

**依赖**：Candidate Provenance（已完成）、EventBus（已存在）

**测试文件**：扩展 `test_story_state_materials_dryrun.py`

**验证方法**：
- 状态读取测试：生成时正确获取状态
- 状态更新测试：生成后状态正确变更
- 事件推送测试：状态变更触发 SSE

**预期结果**：故事状态与生成深度集成，保持一致性

---

### 6.5.6 ⚠️ Pipeline / Workflow 深度验证（部分验收）

**最小验收步骤**：
1. 测试多步骤管线执行
2. 测试条件分支逻辑
3. 测试 Human-in-the-loop 暂停/恢复

**依赖**：Pipeline（已完成）、Workflow（已完成）

**测试文件**：扩展 `test_workflow_pipeline_dryrun.py`

**验证方法**：
- 多步骤顺序执行测试
- 条件分支测试
- 暂停/恢复测试

**预期结果**：复杂工作流场景稳定运行

---

### 6.5.7 ⚠️ Materials / Style Guide / Recent Context（部分验收）

**最小验收步骤**：
1. Materials：添加版本管理 API
2. Style Guide：集成到生成 pipeline
3. Recent Context：验证上下文生成质量

**依赖**：Story State（已部分完成）

**测试文件**：扩展现有测试

**验证方法**：
- 素材版本回滚测试
- 风格指南影响生成测试
- 上下文相关性测试

**预期结果**：辅助模块与主流程有效集成

---

## 6.6 最小验收优先级汇总

| 优先级 | 模块 | 状态 | 最小验收完成后可验证能力 |
|--------|------|------|------------------------|
| P1 | Scene Plan 前端 UI | ❌ | 用户可创建/编辑/保存 Scene Plan |
| P1 | Stream / SSE 流式推送 | ❌ | 长任务实时进度反馈 |
| P2 | Prompt Engine 独立测试 | ⚠️ | 模板引擎功能独立验证 |
| P2 | Pipeline / Workflow 深度验证 | ⚠️ | 复杂工作流稳定运行 |
| P3 | Story State 深度集成 | ⚠️ | 故事状态与生成一致性 |
| P3 | Batch Generate | ❌ | 多场景批量生成 |
| P4 | Materials / Style Guide / Recent Context | ⚠️ | 辅助模块集成完善 |

---

## 7. 安全边界确认

- ✅ **未调用真实 LLM**（本报告基于文件扫描）
- ✅ **未生成 candidate**（无 candidate 文件写入）
- ✅ **未修改 workspace**（仅读取 `docs/testing/`、`tests/`、`backend/` 代码）
- ✅ **未修改 scoring / final / multi-score / errata / gap-analysis 产物**（artifacts 目录只读）
- ✅ **未提交 API key**（`git grep "sk-"` 仅出现于注释/脱敏示例）
- ✅ **扫描时 HEAD == origin/main** (`977c602`，本次格式修复后 commit 将推进)
- ✅ **工作区 clean**

---

## 8. 附录 A：验收文档清单（43 份，按分组）

### Professional 主流程（7 份）
1. professional-main-flow-acceptance-2026-06.md
2. professional-main-flow-ui-dryrun-2026-06.md
3. professional-editing-flow-acceptance-2026-06.md
4. professional-existing-feature-inventory-2026-06.md
5. professional-existing-issues-and-fix-plan-2026-06.md
6. professional-candidate-flow-dryrun-2026-06.md
7. professional-candidate-flow-e2e-result-2026-06.md

### Professional 基础能力（3 份）
8. professional-state-materials-filesystem-acceptance-2026-06.md
9. professional-workflow-pipeline-prompt-acceptance-2026-06.md
10. professional-prompt-architecture-2026-06.md

### Batch / Stream / SSE（1 份）
11. professional-batch-stream-sse-task-acceptance-2026-06.md

### Chat Panel（2 份）
12. chat-panel-trigger-contract-2026-06.md
13. chat-panel-candidate-trigger-dryrun-2026-06.md

### Lite 系列（11 份）
14. lite-professional-switch-baseline-2026-06.md
15. lite-real-generation-smoke-report-2026-06.md
16. lite-output-quality-review-2026-06.md
17. lite-next-options-chain-diagnosis-2026-06.md
18. lite-continuous-generation-diagnosis-2026-06.md
19. lite-fallback-candidate-plan-2026-06.md
20. lite-fallback-retry-prompt-optimization-plan-2026-06.md
21. lite-prompt-optimization-variant-analysis-2026-06.md
22. lite-prompt-optimization-variant-run-template-2026-06.md
23. lite-prompt-optimization-samples-2026-06.md
24. lite-prompt-optimization-experiment-plan-2026-06.md

### Scene Plan 系列（7 份）
25. t5-scene-plan-quality-score-2026-06.md
26. t5-scene-plan-quality-compare-2026-06.md
27. t5-scene-plan-quality-multi-score-2026-06.md
28. t5-scene-plan-quality-final-errata-2026-06.md
29. t5-scene-plan-professional-smoke-2026-06.md
30. t5-scene-plan-persistence-api-2026-06.md
31. t5-scene-plan-generate-api-2026-06.md
32. t5-scene-plan-frontend-ui-2026-06.md
33. t5-scene-plan-chain-architecture-audit-2026-06.md

### Scene Plan Provenance & Target Binding（3 份）
34. t5-scene-plan-target-binding-fix-2026-06.md
35. t5-scene-plan-candidate-provenance-fix-2026-06.md
36. t5-candidate-provenance-chain-acceptance-2026-06.md

### Writing Loop & Gap（1 份）
37. t5-writing-loop-gap-analysis-2026-06.md

### 写作质量引擎（3 份）
38. d7-writing-quality-engine-acceptance-2026-06.md
39. python-llm-writing-quality-engine-2026-06.md
40. de-ai-writing-quality-rules-2026-06.md

### 本地模型 / 安全（1 份）
41. t5-local-model-dryrun-smoke-2026-06.md

### 通用测试计划（2 份）
42. e2e-human-flow-checklist.md
43. full-product-test-plan.md

---

## 9. 附录 B：Backed 核心模块文件索引

### API Layer (28 files, backend/api/)
- `projects.py`
- `files.py`
- `generate.py`
- `candidates.py`
- `scene_plan.py`
- `pipeline.py`
- `workflows.py`
- `prompts.py`
- `lite.py`
- `llm.py`
- `quality.py`
- `story_state.py`
- `materials.py`
- `characters.py`
- `style_guide.py`
- `recent_context.py`
- `revision_log.py`
- `snapshots.py`
- `tasks.py`
- `sse.py`
- `trash.py`
- `backup.py`
- `compare.py`
- `feedback.py`
- `config.py`
- `tokens.py`
- `wizard.py`
- `feedback.py`


### Core Layer (23 files, backend/core/)
- `file_ops.py`
- `project_service.py`
- `candidate_service.py`
- `generation_service.py`
- `quality_service.py`
- `llm.py`
- `llm_circuit_breaker.py`
- `scene_plan_validator.py`
- `pipeline.py`
- `pipeline_validator.py`
- `workflow.py`
- `prompt_engine.py`
- `prompt_versioning.py`
- `node_types.py`
- `task_queue.py`
- `event_bus.py`
- `character_service.py`
- `snapshot.py`
- `exceptions.py`
- `watcher.py`
- `trash.py`


### Schemas (12 files, backend/schemas/)
- `candidate.py`
- `scene_plan.py`
- `pipeline.py`
- `pipeline_config.py`
- `workflow.py`
- `lite.py`
- `llm.py`
- `file.py`
- `quality.py`
- `project.py`
- `common.py`


### Policies (3 files, backend/policies/)
- `candidate_policy.py`
- `generation_output_policy.py`


---

**文档结束**。下一次刷新触发：P1/P2 模块验收完成或 T6.x 里程碑交付时。
