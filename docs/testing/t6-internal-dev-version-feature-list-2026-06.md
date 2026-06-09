# T6.0: 内部开发版功能清单与状态盘点

**版本**: 2026-06
**基准 Commit**: f735eca
**生成日期**: 2026-06-09
**执行方式**: 纯静态文件扫描与文档盘点，未调用 LLM，未生成 candidate，未修改 workspace

---

## 1. 总览

| 项目 | 值 |
|------|-----|
| 功能模块总数（按验收阶段划分） | 17 |
| 已完整验收（有验收文档 + 回归测试） | 9 |
| 部分验收（有文档但测试覆盖不足） | 4 |
| 未验收（代码存在但无独立验收文档） | 4 |
| 有验收文档的模块占比 | ~53% |
| 有回归测试的模块占比 | ~70% |

**整体结论**: 当前项目已形成一条可用的写作最小闭环（打开项目 → 编辑 → 润色/精修 → Candidate 采用 → 继续写作）。Scene Plan 系列功能的后端链路已完整（生成/保存/验证 API + candidate provenance + scoring 报告），但前端 UI、批量生成、流式 SSE 推送等能力尚待实现与验收。

---

## 2. 已完整验收的功能模块（9）

### 2.1 文件系统 / 文件读写

- **验收阶段**: T4.5（Story State / Materials / 文件系统验收）
- **验收文档**: `docs/testing/professional-state-materials-filesystem-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/core/file_ops.py`, `backend/api/files.py`
  - 前端: `frontend/src/composables/useEditorFileActions.ts`, `frontend/src/stores/file.ts`
- **测试文件**: 包含于 `test_api_validation.py`, `test_candidate_flow_e2e*.py`
- **验收状态**: ✅ 已验收
- **关键能力**:
  - 安全的文件读写（通过 FileService，禁止直接路径拼接）
  - 支持 expected_mtime / expected_hash 冲突检测
  - 不会静默覆盖正文

### 2.2 Candidate 候选稿机制

- **验收阶段**: T4.1 + T4.3（主流程 + 编辑能力）
- **验收文档**: `docs/testing/professional-main-flow-acceptance-2026-06.md`, `docs/testing/professional-editing-flow-acceptance-2026-06.md`, `docs/testing/professional-candidate-flow-e2e-result-2026-06.md`
- **核心文件**:
  - 后端: `backend/core/candidate_service.py`, `backend/api/candidates.py`, `backend/schemas/candidate.py`, `backend/policies/candidate_policy.py`
  - 前端: `frontend/src/modules/candidate/`, `frontend/src/components/right-panel/CandidatePanel.vue`
- **测试文件**:
  - `tests/test_candidate_flow_e2e.py`, `tests/test_candidate_flow_e2e_v2.py`, `tests/test_candidate_flow_e2e_full.py`
  - `tests/test_candidate_panel_probe.py`, `tests/test_candidate_panel_probe_simple.py`
  - `tests/test_candidate_preview_delete_e2e.py`, `tests/test_candidate_preview_delete_fixed.py`
  - `tests/test_candidate_adopt_conflict_sse_e2e.py`
  - `tests/test_professional_candidate_flow.py`
  - `tests/test_candidate_provenance.py` (T5.17-H2)
  - `tests/test_scene_plan_quality_provenance_scoring.py` (T5.18-H1)
- **验收状态**: ✅ 已验收
- **关键能力**:
  - polish / rewrite / chat-edit 默认生成 candidate，不覆盖正文
  - CandidatePanel 支持预览、采用、删除
  - Adopt 前冲突检查（base_hash / base_mtime）
  - Adopt 后写入 revision-log
  - T5.17-H2 新增 provenance metadata（generation_context / scene_plan_hash / scene_plan_path）

### 2.3 Lite 快速写作

- **验收阶段**: T1-T3（Lite 系列早期验收）
- **验收文档**: `docs/testing/lite-professional-switch-baseline-2026-06.md`, 多个 Lite 专项文档
- **核心文件**:
  - 后端: `backend/api/lite.py`
  - 前端: `frontend/src/views/LiteWritingView.vue`, `frontend/src/composables/useLiteGeneration.ts`
- **测试文件**: 包含于 `test_professional_regression_smoke.py`
- **验收状态**: ✅ 已验收
- **关键能力**:
  - selected-card 模式，无需场景计划即可快速写作
  - 不影响 Professional 主流程（T4.2 已验证共存）

### 2.4 Professional 主流程（编辑器 + 对话面板）

- **验收阶段**: T4.1（主流程端到端验收）
- **验收文档**: `docs/testing/professional-main-flow-acceptance-2026-06.md`, `docs/testing/professional-main-flow-ui-dryrun-2026-06.md`
- **核心文件**:
  - 后端: `backend/api/generate.py`, `backend/api/candidates.py`, `backend/core/generation_service.py`
  - 前端: `frontend/src/components/editor/EditorToolbar.vue`, `frontend/src/components/chat/ChatPanel.vue`, `frontend/src/composables/useGenerationOrchestrator.ts`
- **测试文件**: `tests/test_professional_regression_smoke.py`, `tests/test_user_story.py`
- **验收状态**: ✅ 已验收
- **关键能力**:
  - 打开项目 → 编辑 → 触发润色/精修 → 生成 candidate → 预览/采用 → 继续写作
  - 两条入口：EditorToolbar 按钮 + ChatPanel 对话

### 2.5 Chat Panel 与 Candidate 触发

- **验收阶段**: T4.1 + ChatPanel 专项
- **验收文档**: `docs/testing/chat-panel-trigger-contract-2026-06.md`, `docs/testing/chat-panel-candidate-trigger-dryrun-2026-06.md`
- **核心文件**:
  - 后端: `backend/api/candidates.py`, `backend/core/quality_service.py`
  - 前端: `frontend/src/components/chat/ChatPanel.vue`, `frontend/src/stores/chat.ts`
- **测试文件**: `tests/test_chatpanel_selected_text_ui_e2e.py`, `tests/test_chatpanel_selected_text_candidate_simple.py`, `tests/test_chatpanel_selected_text_candidate_link.py`
- **验收状态**: ✅ 已验收
- **关键能力**:
  - ChatPanel 中选中文字触发 rewrite / polish
  - 默认走 candidate 机制，不直接覆盖正文

### 2.6 Scene Plan API（生成 / 保存 / 验证）

- **验收阶段**: T5.13 - T5.18
- **验收文档**:
  - `docs/testing/t5-scene-plan-generate-api-2026-06.md`（生成 API）
  - `docs/testing/t5-scene-plan-persistence-api-2026-06.md`（保存 API）
  - `docs/testing/t5-scene-plan-chain-architecture-audit-2026-06.md`（架构审计）
  - `docs/testing/t5-scene-plan-target-binding-fix-2026-06.md`（target_file 绑定）
  - `docs/testing/t5-scene-plan-candidate-provenance-fix-2026-06.md`（provenance 修复）
  - `docs/testing/t5-candidate-provenance-chain-acceptance-2026-06.md`（provenance 链路验收）
- **核心文件**:
  - 后端: `backend/api/scene_plan.py`, `backend/core/scene_plan_validator.py`, `backend/schemas/scene_plan.py`
- **测试文件**:
  - `tests/test_scene_plan_generate_api.py`
  - `tests/test_scene_plan_persistence_api.py`
  - `tests/test_scene_plan_validate_api.py`
  - `tests/test_scene_plan_validator.py`
  - `tests/test_scene_plan_pipeline_integration.py`
  - `tests/test_candidate_provenance.py`
  - `tests/test_scene_plan_quality_provenance_scoring.py`
- **验收状态**: ✅ 已验收（后端 API + provenance 链路）
- **关键能力**:
  - `/api/scene-plan/generate`: 生成 Scene Plan JSON
  - `/api/scene-plan/save`: 持久化 scene_plan.json（绑定 target_file）
  - `/api/scene-plan/validate`: 校验 scene_plan 字段合法性与 target_file 绑定
  - provenance metadata（generation_context / scene_plan_hash / scene_plan_path）
  - scoring 报告中 provenance 状态标注（T5.18-H1）

### 2.7 Scoring 评分（规则评分 + multi-score 报告）

- **验收阶段**: T5.10 - T5.18
- **验收文档**:
  - `docs/testing/t5-scene-plan-quality-score-2026-06.md`（规则评分）
  - `docs/testing/t5-scene-plan-quality-compare-2026-06.md`（对比评分）
  - `docs/testing/t5-scene-plan-quality-multi-score-2026-06.md`（multi-score 报告）
  - `docs/testing/t5-scene-plan-quality-final-errata-2026-06.md`（勘误）
- **核心文件**:
  - `scripts/eval/scene_plan_quality_score.py`
  - `docs/testing/artifacts/t5-scene-plan-quality-cases-2026-06.json`
  - `docs/testing/artifacts/t5-scene-plan-quality-multi-score-final-2026-06.json`
- **测试文件**:
  - `tests/test_scene_plan_quality_provenance_scoring.py`
- **验收状态**: ✅ 已验收（含 provenance 集成）
- **关键能力**:
  - 规则评分（scene_goal_alignment / beats_coverage / conflict_presence / characters_consistency / location_consistency / time_consistency / no_reasoning_logs / language_quality / plan_contradiction_check）
  - Baseline vs With-Plan 对比
  - provenance 状态标注（T5.18-H1 新增）
  - note 字段保留（不被 provenance 覆盖）

### 2.8 Story State / Materials / Style Guide

- **验收阶段**: T4.5
- **验收文档**: `docs/testing/professional-state-materials-filesystem-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/api/story_state.py`, `backend/api/materials.py`, `backend/api/style_guide.py`
  - 前端: `frontend/src/stores/storyState.ts`, `frontend/src/stores/styleGuide.ts`
- **测试文件**: `tests/test_story_state_materials_dryrun.py`
- **验收状态**: ✅ 已验收（静态层）
- **关键能力**:
  - Story State：主角状态、势力关系、伏笔、主线进度等结构化沉淀
  - Materials：素材文件读写
  - Style Guide：风格指南管理
  - 均需用户确认后写入，不会自动覆盖

### 2.9 LLM 调用与熔断器（API Key 安全）

- **验收阶段**: 多阶段安全检查
- **验收文档**:
  - `docs/testing/t5-local-model-dryrun-smoke-2026-06.md`（本地模型 dry-run）
  - `docs/testing/professional-state-materials-filesystem-acceptance-2026-06.md` 中安全章节
  - `docs/testing/t5-scene-plan-chain-architecture-audit-2026-06.md` 中安全章节
- **核心文件**:
  - 后端: `backend/core/llm.py`, `backend/core/llm_circuit_breaker.py`, `backend/api/llm.py`, `backend/api/config.py`
  - 前端: `frontend/src/stores/llm.ts`
- **测试文件**: `tests/test_llm.py`, `tests/test_llm_api.py`, `tests/test_llm_reasoning_detection.py`
- **验收状态**: ✅ 已验收（安全层）
- **关键能力**:
  - 统一 LLM 入口（通过 LiteLLM）
  - Reasoning log 检测（防止 `<thinking>` 等原始推理输出到正文）
  - API Key 不写入 localStorage / 日志 / 截图
  - 熔断器机制防止连续失败拖慢系统

---

## 3. 部分验收的功能模块（4）

### 3.1 Workflow 工作流引擎

- **验收阶段**: T4.4（静态验收）
- **验收文档**: `docs/testing/professional-workflow-pipeline-prompt-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/core/workflow.py`, `backend/api/workflows.py`, `backend/schemas/workflow.py`
  - 前端: `frontend/src/composables/useWorkflow.ts`
- **测试文件**: `tests/test_workflow_pipeline_dryrun.py`, `tests/test_workflow_pipeline_crud.py`
- **验收状态**: ⚠️ 部分验收（静态结构验证通过，无完整端到端验收）
- **已验证**: 工作流定义结构、多步骤编排、loop 嵌套、Human 节点、变量池
- **待进一步验证**: 实际工作流运行场景、复杂 loop 嵌套的稳定性、错误恢复

### 3.2 Pipeline 管线

- **验收阶段**: T4.4 + T5.17（部分）
- **验收文档**: `docs/testing/professional-workflow-pipeline-prompt-acceptance-2026-06.md`, `docs/testing/t5-scene-plan-chain-architecture-audit-2026-06.md`
- **核心文件**:
  - 后端: `backend/core/pipeline.py`, `backend/api/pipeline.py`
  - 前端: `frontend/src/stores/pipeline.ts`
  - Prompt 模板: `prompts/pipeline/`
- **测试文件**: `tests/test_workflow_pipeline_dryrun.py`, `tests/test_scene_plan_pipeline_integration.py`
- **验收状态**: ⚠️ 部分验收（dry-run 通过，scene-plan 集成部分完成）
- **已验证**: pipeline 定义与 dry-run、与 Scene Plan validator 的软接入
- **待进一步验证**: 完整 pipeline 运行场景、复杂 pipeline 的稳定性、与前端 PipelineEditor 的深度集成

### 3.3 Prompt Engine / Prompt Editor

- **验收阶段**: T4.4（静态）
- **验收文档**: `docs/testing/professional-workflow-pipeline-prompt-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/core/prompt_engine.py`, `backend/api/prompts.py`
  - 前端: `frontend/src/composables/usePromptSync.ts`
  - Prompt 文件: `prompts/`
- **测试文件**: 无独立测试（依赖 pipeline 测试）
- **验收状态**: ⚠️ 部分验收（静态结构验证通过，无独立回归测试）
- **已验证**: Jinja2 模板渲染、Prompt 版本管理
- **待进一步验证**: Prompt 变体（variant）系统、模板编辑与预览的端到端能力

### 3.4 Recent Context 最近上下文

- **验收阶段**: T4.5（静态）
- **验收文档**: `docs/testing/professional-state-materials-filesystem-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/api/recent_context.py`, `backend/core/memory_service.py`
  - 前端: `frontend/src/stores/recentContext.ts`
- **测试文件**: 无独立测试（包含于 story_state_materials 测试）
- **验收状态**: ⚠️ 部分验收（静态 API 存在，无独立端到端验证）
- **已验证**: API 端点存在、数据结构合理
- **待进一步验证**: 上下文生成质量、与 generation 流程的集成深度

---

## 4. 未验收 / 待实现的功能模块（4）

### 4.1 Batch Generate 批量生成

- **验收阶段**: 未验收（T4.6 文档已定位问题）
- **验收文档**: `docs/testing/professional-batch-stream-sse-task-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/api/tasks.py`, `backend/core/task_queue.py`（底层已就绪）
  - 前端: `frontend/src/stores/task.ts`（底层已就绪）
- **测试文件**: `tests/test_t472_backend_verification.py`
- **验收状态**: ❌ 未验收（功能未完整实现）
- **问题说明**:
  - 未找到 `backend/*batch*.py` 独立批量生成模块
  - 未找到 `*Batch*.vue` 组件
  - TaskQueue 底层已就绪，但 Batch 上层功能未实现
- **依赖关系**: 依赖 TaskQueue、Pipeline、Candidate
- **阻塞风险**: 低（非写作最小闭环所需，属于增强能力）

### 4.2 Stream Generation / 流式 SSE 推送

- **验收阶段**: 未验收（T4.6 文档已定位问题）
- **验收文档**: `docs/testing/professional-batch-stream-sse-task-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/api/sse.py`, `backend/core/event_bus.py`, `backend/core/task_queue.py`
  - 前端: `frontend/src/composables/useSSE.ts`
- **测试文件**: 无独立测试
- **验收状态**: ❌ 未验收（流式已部分实现，未推送至前端）
- **问题说明**:
  - 后端流式 LLM 调用已实现（chunk 收集）
  - 流式内容收集后一次性返回，**尚未实现流式 SSE 推送给前端**
  - SSE 心跳机制存在（15 秒间隔，45 秒超时自动重连），但内容流式推送未接入
- **依赖关系**: 依赖 SSE、TaskQueue、LLM 流式输出
- **阻塞风险**: 中（影响用户体验，长任务无实时进度反馈）

### 4.3 Scene Plan 前端 UI

- **验收阶段**: 未验收
- **验收文档**: `docs/testing/t5-scene-plan-frontend-ui-2026-06.md`（已发现问题）
- **核心文件**:
  - 前端: 尚未有专门的 ScenePlan 编辑器组件
  - 已有: `frontend/src/components/editor/EditorToolbar.vue`（有按钮框架，未接入 Scene Plan 生成）
- **测试文件**: `tests/test_scene_plan_frontend_smoke.py`（仅 smoke 测试）
- **验收状态**: ❌ 未验收（前端 UI 未实现）
- **问题说明**:
  - Scene Plan 生成/保存/验证的后端 API 完整
  - 前端**没有** Scene Plan 编辑器 / 面板 / 配置界面
  - 用户无法在前端可视化地创建、编辑、管理 Scene Plan
- **依赖关系**: 依赖 Scene Plan 后端 API（已完成）
- **阻塞风险**: 高（影响 Scene Plan 的真正落地使用，当前只能通过 API 手动调用）

### 4.4 Prompt / Pipeline 前端编辑器

- **验收阶段**: 未验收（T4.4 确认存在但未深度验收）
- **验收文档**: `docs/testing/professional-workflow-pipeline-prompt-acceptance-2026-06.md`
- **核心文件**:
  - 后端: `backend/api/prompts.py`, `backend/api/pipeline.py`
  - 前端: `frontend/src/components/right-panel/RightPanel.vue` 中 PipelineEditor Tab
- **测试文件**: `tests/test_workflow_pipeline_crud.py`
- **验收状态**: ❌ 未验收（代码存在，无端到端验证文档）
- **问题说明**:
  - PipelineEditor 组件存在，但功能深度未在验收文档中确认
  - Prompt 编辑器界面状态未明确
- **依赖关系**: 依赖 Workflow / Pipeline 底层能力（已完成）
- **阻塞风险**: 中（影响自定义 pipeline 的易用性）

---

## 5. 测试文件与验收文档映射表

| 模块 | 验收文档 | 回归测试 | 测试通过状态 |
|------|----------|----------|-------------|
| 文件系统 | professional-state-materials-filesystem-acceptance-2026-06.md | 含于 e2e 测试 | ✅ |
| Candidate | professional-main-flow-acceptance-2026-06.md + 多个文档 | test_candidate_flow_e2e*.py / test_candidate_provenance.py / test_scene_plan_quality_provenance_scoring.py | ✅ |
| Lite | lite-professional-switch-baseline-2026-06.md + 多个 Lite 文档 | test_professional_regression_smoke.py | ✅ |
| Professional 主流程 | professional-main-flow-acceptance-2026-06.md | test_professional_regression_smoke.py | ✅ |
| ChatPanel | chat-panel-trigger-contract-2026-06.md | test_chatpanel_selected_text_*.py | ✅ |
| Scene Plan API | t5-scene-plan-*-api-2026-06.md | test_scene_plan_*_api.py / test_scene_plan_validator.py | ✅ |
| Scoring | t5-scene-plan-quality-*-2026-06.md | test_scene_plan_quality_provenance_scoring.py | ✅ |
| Story State | professional-state-materials-filesystem-acceptance-2026-06.md | test_story_state_materials_dryrun.py | ✅ |
| LLM / Fuse | t5-local-model-dryrun-smoke-2026-06.md | test_llm.py / test_llm_api.py / test_llm_reasoning_detection.py | ✅ |
| Workflow | professional-workflow-pipeline-prompt-acceptance-2026-06.md | test_workflow_pipeline_dryrun.py | ⚠️ 部分 |
| Pipeline | professional-workflow-pipeline-prompt-acceptance-2026-06.md | test_workflow_pipeline_dryrun.py / test_scene_plan_pipeline_integration.py | ⚠️ 部分 |
| Prompt Engine | professional-workflow-pipeline-prompt-acceptance-2026-06.md | 无独立测试 | ⚠️ 不足 |
| Recent Context | professional-state-materials-filesystem-acceptance-2026-06.md | 无独立测试 | ⚠️ 不足 |
| Batch Generate | professional-batch-stream-sse-task-acceptance-2026-06.md | test_t472_backend_verification.py（底层） | ❌ 未独立验收 |
| Stream SSE | professional-batch-stream-sse-task-acceptance-2026-06.md | 无独立测试 | ❌ 未独立验收 |
| Scene Plan 前端 UI | t5-scene-plan-frontend-ui-2026-06.md | test_scene_plan_frontend_smoke.py | ❌ 未实现 |
| Prompt/Pipeline 编辑器 | professional-workflow-pipeline-prompt-acceptance-2026-06.md | test_workflow_pipeline_crud.py | ❌ 未深度验收 |

---

## 6. 建议的下一步验证顺序（低依赖 → 高依赖）

| 优先级 | 模块 | 理由 | 前置依赖 |
|--------|------|------|---------|
| P1 | Scene Plan 前端 UI | 高阻塞：后端 API 已完整，缺前端 UI 无法真正使用 | Scene Plan API（已完成） |
| P1 | Stream SSE 推送 | 中阻塞：影响用户体验，尤其长任务无进度反馈 | SSE（底层已完成） |
| P2 | Prompt/Pipeline 编辑器 | 中阻塞：影响自定义能力易用性 | Workflow/Pipeline（已完成） |
| P2 | Prompt Engine 测试 | 补足测试覆盖 | Workflow/Pipeline（已完成） |
| P3 | Batch Generate | 低阻塞：增强能力，非最小闭环必需 | TaskQueue + Pipeline |
| P3 | Recent Context 深度集成 | 提升上下文质量，增强写作一致性 | Generation Service |

---

## 7. 安全边界与约束声明

- ✅ 未调用真实 LLM（本报告基于文档与代码静态扫描）
- ✅ 未生成 candidate
- ✅ 未修改 workspace（仅读取测试文档中的 candidate snapshot）
- ✅ 未覆盖 scoring / final / multi-score / errata / gap-analysis 产物
- ✅ 未提交 API key
- ✅ 所有修改仅限于本 Markdown 文档

---

## 8. 附录：验收文档清单（43 份）

按命名空间分组：

### A. Professional 主流程与编辑（8）
1. professional-main-flow-acceptance-2026-06.md
2. professional-main-flow-ui-dryrun-2026-06.md
3. professional-editing-flow-acceptance-2026-06.md
4. professional-existing-feature-inventory-2026-06.md
5. professional-existing-issues-and-fix-plan-2026-06.md
6. professional-candidate-flow-dryrun-2026-06.md
7. professional-candidate-flow-e2e-result-2026-06.md
8. professional-state-materials-filesystem-acceptance-2026-06.md

### B. Workflow / Pipeline / Prompt（3）
9. professional-workflow-pipeline-prompt-acceptance-2026-06.md
10. professional-prompt-architecture-2026-06.md
11. professional-workflow-pipeline-prompt-acceptance-2026-06.md（同 9）

### C. Batch / Stream / SSE（1）
12. professional-batch-stream-sse-task-acceptance-2026-06.md

### D. ChatPanel（2）
13. chat-panel-trigger-contract-2026-06.md
14. chat-panel-candidate-trigger-dryrun-2026-06.md

### E. Lite 系列（8）
15. lite-professional-switch-baseline-2026-06.md
16. lite-real-generation-smoke-report-2026-06.md
17. lite-output-quality-review-2026-06.md
18. lite-next-options-chain-diagnosis-2026-06.md
19. lite-continuous-generation-diagnosis-2026-06.md
20. lite-fallback-candidate-plan-2026-06.md
21. lite-fallback-retry-prompt-optimization-plan-2026-06.md
22. lite-prompt-optimization-*-2026-06.md（4 份变体实验文档）

### F. Scene Plan 系列（9）
23. t5-scene-plan-quality-score-2026-06.md
24. t5-scene-plan-quality-compare-2026-06.md
25. t5-scene-plan-quality-multi-score-2026-06.md
26. t5-scene-plan-quality-final-errata-2026-06.md
27. t5-scene-plan-professional-smoke-2026-06.md
28. t5-scene-plan-persistence-api-2026-06.md
29. t5-scene-plan-generate-api-2026-06.md
30. t5-scene-plan-frontend-ui-2026-06.md
31. t5-scene-plan-chain-architecture-audit-2026-06.md

### G. Scene Plan 修复与 provenance（3）
32. t5-scene-plan-target-binding-fix-2026-06.md
33. t5-scene-plan-candidate-provenance-fix-2026-06.md
34. t5-candidate-provenance-chain-acceptance-2026-06.md

### H. Writing Loop 与 Gap（1）
35. t5-writing-loop-gap-analysis-2026-06.md

### I. 写作质量引擎（3）
36. d7-writing-quality-engine-acceptance-2026-06.md
37. python-llm-writing-quality-engine-2026-06.md
38. de-ai-writing-quality-rules-2026-06.md

### J. 本地模型 / 安全（1）
39. t5-local-model-dryrun-smoke-2026-06.md

### K. 通用测试计划（2）
40. e2e-human-flow-checklist.md
41. full-product-test-plan.md

---

**文档生成者**: Solo Agent（静态文件扫描）
**下次更新触发条件**: 完成 Scene Plan 前端 UI、Stream SSE 或 Batch Generate 后，更新对应模块状态。
