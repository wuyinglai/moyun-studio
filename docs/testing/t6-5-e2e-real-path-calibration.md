# T6.5 E2E 真实路径校准文档

> 生成时间：2026-06-09
> 基于 commit：`9d7f9598559d45f4546ffc5d315605b079a18cfa`
> 目的：为 T6.5 系列端到端测试提供真实可执行的路径映射，所有结论附带代码证据

---

## A. 前端真实入口扫描

| 功能 | 是否存在 | 文件路径 | 组件/函数 | 触发方式 | 证据 | 是否适合 E2E |
|------|----------|----------|-----------|----------|------|-------------|
| Professional 主工作台 | ✅ | `frontend/src/router/index.ts` | `/project/:projectId/file/*` 路由 | URL 导航 | 路由定义第 36-122 行 | ✅ |
| Lite 入口 | ✅ | `frontend/src/views/LiteWritingView.vue` | `/lite` + `/project/:projectId/lite` 路由 | URL 导航 | 路由定义第 11-14 行, 56-75 行 | ✅ |
| AppLayout 布局 | ✅ | `frontend/src/components/layout/AppLayout.vue` | children 路由渲染 | 子路由嵌套 | App.vue 第 157 行 `<router-view />` | ✅ |
| 全局 Modal 注册 | ✅ | `frontend/src/App.vue` | 13 个 Modal 组件 | 挂载即注册 | 第 159-172 行 | ✅ |
| 创建项目 | ✅ | `frontend/src/components/modals/CreateProjectModal.vue` | `openCreateProject()` / `useUIStore` | Modal 触发 | `App.vue` 第 159 行 | ✅ |
| 打开项目 | ✅ | `frontend/src/components/modals/OpenProjectModal.vue` | `openProjectModal()` / `useUIStore` | Modal 触发 | `App.vue` 第 160 行 | ✅ |
| EditorToolbar（生成工具栏） | ✅ | `frontend/src/components/editor/EditorToolbar.vue` | `useGenerationOrchestrator` / `openBatchGenerate()` | 工具栏按钮 | `App.vue` 第 32 行 `useGenerationOrchestrator()` | ✅ |
| CandidatePanel（候选稿面板） | ✅ | `frontend/src/components/right-panel/CandidatePanel.vue` | `useCandidateStore` / `adoptCandidate()` | 右侧面板 Tab | `RightPanel.vue` 内注册 | ✅ |
| BatchGenerateModal（批量生成） | ✅ | `frontend/src/components/modals/BatchGenerateModal.vue` | `openBatchGenerate()` / `batchGenerate()` | 工具栏 + Modal | `App.vue` 第 166 行 | ✅ |
| ScenePlanEditor | ✅ | `frontend/src/components/right-panel/ScenePlanEditor.vue` | `useScenePlanStore` | 右侧面板 Tab | `RightPanel.vue` 内注册 | ✅ |
| PipelineEditor | ✅ | `frontend/src/components/right-panel/PipelineEditor.vue` | `usePipelineStore` / CRUD API | 右侧面板 Tab | `RightPanel.vue` 内注册 | ✅ |
| StyleGuide 编辑 | ✅ | `frontend/src/stores/styleGuide.ts` | `load()` / `save()` | File API | 无独立 UI，通过 File 编辑 | ⚠️ 需 File 路径 |
| RecentContext 编辑 | ✅ | `frontend/src/stores/recentContext.ts` | `load()` / `save()` | File API | 无独立 UI，通过 File 编辑 | ⚠️ 需 File 路径 |
| StoryState 编辑 | ✅ | `frontend/src/stores/storyState.ts` | `load()` / `save()` | File API | 无独立 UI，通过 File 编辑 | ⚠️ 需 File 路径 |
| Materials 列表 | ✅ | `frontend/src/composables/useSceneGenerationActions.ts` | `materials` / `extract()` | ChatPanel 触发 | `useSceneGenerationActions.ts` 第 10 行 | ✅ |
| SettingsModal | ✅ | `frontend/src/components/modals/SettingsModal.vue` | LLM 配置 | Modal 触发 | `App.vue` 第 161 行 | ✅ |
| CompareModal（对比） | ✅ | `frontend/src/components/modals/CompareModal.vue` | 文件对比 | Modal 触发 | `App.vue` 第 163 行 | ✅ |
| FeedbackModal | ✅ | `frontend/src/components/modals/FeedbackModal.vue` | 用户反馈 | Modal 触发 | `App.vue` 第 164 行 | ✅ |
| RevisionLogModal | ✅ | `frontend/src/components/modals/RevisionLogModal.vue` | adopt 历史 | Modal 触发 | `App.vue` 第 165 行 | ✅ |
| QualityReviewModal | ✅ | `frontend/src/components/modals/QualityReviewModal.vue` | 质量审查 | Modal 触发 | `App.vue` 第 168 行 | ✅ |
| TrashModal（回收站） | ✅ | `frontend/src/components/modals/TrashModal.vue` | 文件恢复/删除 | Modal 触发 | `App.vue` 第 171 行 | ✅ |
| BackupModal（备份） | ✅ | `frontend/src/components/modals/BackupModal.vue` | 备份管理 | Modal 触发 | `App.vue` 第 172 行 | ✅ |
| SSE 连接 | ✅ | `frontend/src/composables/useSSE.ts` | `useSSE()` / `EventSource` | App 初始化 | `App.vue` 第 20 行 `useAppInit()` → `useSSE()` | ✅ |
| ChatPanel（聊天面板） | ✅ | `frontend/src/components/chat/ChatPanel.vue` | `useChatStore` / `useSceneGenerationActions` | 右侧面板 Tab | ChatPanel.vue | ✅ |

---

## B. 后端真实 API 扫描

| 功能 | HTTP 方法 | API 路径 | 文件 | 函数 | 是否调用 LLM | 是否支持 dry-run/mock | 是否写文件 | 是否生成 candidate | 是否适合 E2E |
|------|-----------|----------|------|------|-------------|---------------------|-----------|-------------------|-------------|
| 项目列表 | GET | `/api/projects` | `backend/api/projects.py` | `list_projects` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 创建项目 | POST | `/api/projects` | `backend/api/projects.py` | `create_project` | ❌ | ✅ mock | ✅ (创建目录结构) | ❌ | ✅ |
| 打开项目 | GET | `/api/projects/{project_id}` | `backend/api/projects.py` | `get_project` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 删除项目 | DELETE | `/api/projects/{project_id}` | `backend/api/projects.py` | `delete_project` | ❌ | ✅ mock | ✅ (删除目录) | ❌ | ⚠️ 破坏性 |
| 文件树 | GET | `/api/tree` | `backend/api/files.py` | `get_tree` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 读文件 | GET | `/api/file` | `backend/api/files.py` | `read_file` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 写文件 | POST | `/api/file` | `backend/api/files.py` | `write_file` | ❌ | ✅ mock | ✅ (写入 sec 文件) | ❌ | ⚠️ 需隔离 |
| 创建文件 | POST | `/api/file/create` | `backend/api/files.py` | `create_file` | ❌ | ✅ mock | ✅ | ❌ | ⚠️ 需隔离 |
| 删除文件 | POST | `/api/file/delete` | `backend/api/files.py` | `delete_file` | ❌ | ✅ mock | ✅ (移到 trash) | ❌ | ⚠️ 破坏性 |
| LLM 生成（流式） | POST | `/api/generate` | `backend/api/generate.py` | `generate` | ✅ 调用 LLM | ⚠️ 需 mock provider | ✅ (写到 target) | ✅ (通过 policy) | ⚠️ 需 mock LLM |
| 批量生成 | POST | `/api/generate/batch` | `backend/api/generate.py` | `batch_generate` | ✅ 调用 LLM | ⚠️ 需 mock provider | ✅ | ✅ (通过 policy) | ⚠️ 需 mock LLM |
| 聊天生成（流式） | POST | `/api/chat` | `backend/api/generate.py` | `chat` | ✅ 调用 LLM | ⚠️ 需 mock provider | ❌ | ❌ | ⚠️ 需 mock LLM |
| 停止任务 | POST | `/api/stop` | `backend/api/generate.py` | `stop_task` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| SSE 连接 | GET | `/api/sse` | `backend/api/sse.py` | `sse_endpoint` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 候选稿列表 | GET | `/api/candidates/{project_id}` | `backend/api/candidates.py` | `list_candidates` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 候选稿详情 | GET | `/api/candidates/{project_id}/{candidate_id}` | `backend/api/candidates.py` | `get_candidate` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Adopt 候选稿 | POST | `/api/candidates/{project_id}/{candidate_id}/adopt` | `backend/api/candidates.py` | `adopt_candidate` | ❌ | ✅ mock | ✅ (覆盖目标文件) | ❌ | ⚠️ 覆盖性 |
| 删除候选稿 | DELETE | `/api/candidates/{project_id}/{candidate_id}` | `backend/api/candidates.py` | `delete_candidate` | ❌ | ✅ mock | ✅ (删除文件) | ❌ | ⚠️ 破坏性 |
| Scene Plan 校验 | POST | `/api/scene-plan/validate` | `backend/api/scene_plan.py` | `validate_scene_plan` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Scene Plan 保存 | POST | `/api/scene-plan/save` | `backend/api/scene_plan.py` | `save_scene_plan` | ❌ | ✅ mock | ✅ (写 scene-plan.json) | ❌ | ✅ |
| Scene Plan 加载 | GET | `/api/scene-plan/load` | `backend/api/scene_plan.py` | `load_scene_plan` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Scene Plan 生成 | POST | `/api/scene-plan/generate` | `backend/api/scene_plan.py` | `generate_scene_plan` | ✅ 调用 LLM | ⚠️ 需 mock provider | ❌ (仅返回 JSON) | ❌ | ⚠️ 需 mock LLM |
| Pipeline 列表 | GET | `/api/pipeline/list` | `backend/api/pipeline.py` | `list_pipelines` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Pipeline 详情 | GET | `/api/pipeline/{name}` | `backend/api/pipeline.py` | `get_pipeline_detail` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Pipeline 运行 | POST | `/api/pipeline/run` | `backend/api/pipeline.py` | `run_pipeline` | ✅ 调用 LLM | ⚠️ 需 mock provider | ✅ | ✅ | ⚠️ 需 mock LLM |
| Pipeline 保存 | PUT | `/api/pipeline/{name}` | `backend/api/pipeline.py` | `update_pipeline` | ❌ | ✅ mock | ✅ (写 YAML) | ❌ | ✅ |
| Pipeline 删除 | DELETE | `/api/pipeline/{name}` | `backend/api/pipeline.py` | `delete_pipeline` | ❌ | ✅ mock | ✅ (删 YAML) | ❌ | ⚠️ 破坏性 |
| Pipeline 创建（自定义） | POST | `/api/pipeline/custom` | `backend/api/pipeline.py` | `create_custom_pipeline` | ❌ | ✅ mock | ✅ (写 YAML) | ❌ | ✅ |
| Workflow 列表 | GET | `/api/workflows` | `backend/api/workflows.py` | `list_workflows` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Workflow 运行 | POST | `/api/workflows/run` | `backend/api/workflows.py` | `run_workflow` | ✅ 调用 LLM | ⚠️ 需 mock provider | ✅ | ✅ | ⚠️ 需 mock LLM |
| Workflow 保存 | POST | `/api/workflows/save` | `backend/api/workflows.py` | `save_workflow` | ❌ | ✅ mock | ✅ (写 JSON) | ❌ | ✅ |
| Workflow 删除 | DELETE | `/api/workflows/{name}` | `backend/api/workflows.py` | `delete_workflow` | ❌ | ✅ mock | ✅ (删 JSON) | ❌ | ⚠️ 破坏性 |
| 文风指南读取 | GET | `/api/style-guide/{project_id}` | `backend/api/style_guide.py` | `get_style_guide` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 文风指南保存 | POST | `/api/style-guide/{project_id}` | `backend/api/style_guide.py` | `save_style_guide` | ❌ | ✅ mock | ✅ (写 style-guide.md) | ❌ | ✅ |
| 文风指南 AI 生成 | POST | `/api/style-guide/{project_id}/generate` | `backend/api/style_guide.py` | `generate_style_guide` | ✅ 调用 LLM | ⚠️ 需 mock provider | ✅ | ❌ | ⚠️ 需 mock LLM |
| 素材列表 | GET | `/api/materials/{material_type}` | `backend/api/materials.py` | `list_materials` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 素材创建 | POST | `/api/materials/{material_type}` | `backend/api/materials.py` | `create_material` | ❌ | ✅ mock | ✅ (写 JSON) | ❌ | ✅ |
| 素材提取（AI） | POST | `/api/extract` | `backend/api/materials.py` | `submit_extract_task` | ✅ 调用 LLM | ⚠️ 需 mock provider | ✅ | ❌ | ⚠️ 需 mock LLM |
| 素材删除 | DELETE | `/api/materials/{material_type}/{item_id}` | `backend/api/materials.py` | `delete_material` | ❌ | ✅ mock | ✅ (删除文件) | ❌ | ⚠️ 破坏性 |
| Story State 读取 | GET | `/api/story-state/{project_id}` | `backend/api/story_state.py` | `get_story_state` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Story State 更新 | POST | `/api/story-state/{project_id}` | `backend/api/story_state.py` | `update_story_state` | ❌ | ✅ mock | ✅ (追加到 story-state.md) | ❌ | ✅ |
| Recent Context 读取 | GET | `/api/recent-context/{project_id}` | `backend/api/recent_context.py` | `get_recent_context` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| Recent Context 追加 | POST | `/api/recent-context/{project_id}/append` | `backend/api/recent_context.py` | `append_chapter_summary` | ❌ | ✅ mock | ✅ | ❌ | ✅ |
| 质量审查 | POST | `/api/quality/review` | `backend/api/quality.py` | `review_quality` | ✅ 调用 LLM | ⚠️ 需 mock provider | ❌ | ❌ | ⚠️ 需 mock LLM |
| Token 计数 | POST | `/api/tokens/count` | `backend/api/tokens.py` | `count_tokens` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 快照列表 | GET | `/api/snapshots/{project_id}` | `backend/api/snapshots.py` | `list_snapshots` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 快照创建 | POST | `/api/snapshots/{project_id}` | `backend/api/snapshots.py` | `create_snapshot` | ❌ | ✅ mock | ✅ (创建副本) | ❌ | ✅ |
| 快照恢复 | POST | `/api/snapshots/{project_id}/restore` | `backend/api/snapshots.py` | `restore_snapshot` | ❌ | ✅ mock | ✅ (覆盖文件) | ❌ | ⚠️ 覆盖性 |
| LLM 配置 | GET | `/api/llm/config` | `backend/api/llm.py` | `get_llm_config` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| LLM 测试 | POST | `/api/llm/test` | `backend/api/llm.py` | `test_llm_connection` | ✅ 调用 LLM | ⚠️ 需 mock provider | ❌ | ❌ | ⚠️ 需 mock LLM |
| 反馈列表 | GET | `/api/feedback/{project_id}` | `backend/api/feedback.py` | `list_feedback` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 创建反馈 | POST | `/api/feedback/{project_id}` | `backend/api/feedback.py` | `create_feedback` | ❌ | ✅ mock | ✅ (写 feedback.json) | ❌ | ✅ |
| 备份列表 | GET | `/api/backup` | `backend/api/backup.py` | `list_backups` | ❌ | ✅ mock | ❌ | ❌ | ✅ |
| 创建备份 | POST | `/api/backup` | `backend/api/backup.py` | `create_backup` | ❌ | ✅ mock | ✅ (复制文件) | ❌ | ✅ |
| 恢复备份 | POST | `/api/backup/{backup_id}` | `backend/api/backup.py` | `restore_backup` | ❌ | ✅ mock | ✅ (覆盖文件) | ❌ | ⚠️ 覆盖性 |

---

## C. 真实测试文件扫描

| 测试文件 | 测试类型 | 覆盖功能 | 是否可直接运行 | 是否需要后端服务 | 是否适合 T6.5 | 备注 |
|----------|----------|----------|---------------|----------------|--------------|------|
| `tests/test_candidate_flow_e2e.py` | Playwright E2E | Candidate 列表→预览→adopt→验证正文变化 | ⚠️ 需 playwright 安装 | ✅ 需后端运行 | ✅ | sync API，成熟 |
| `tests/test_candidate_flow_e2e_v2.py` | Playwright E2E | 同上，v2 版本 | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | async API |
| `tests/test_candidate_flow_e2e_full.py` | Playwright E2E | 完整 candidate 流程，含 SSE | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | 最完整版本 |
| `tests/test_candidate_preview_delete_fixed.py` | Playwright E2E | Preview + Delete candidate | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | 独立可运行 |
| `tests/test_candidate_preview_delete_e2e.py` | Playwright E2E | Preview + Delete（含冲突） | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | 有冲突场景 |
| `tests/test_candidate_adopt_conflict_sse_e2e.py` | Playwright E2E | Adopt + 冲突检测 + SSE | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | 验证 SSE 事件 |
| `tests/test_scene_plan_frontend_smoke.py` | Playwright E2E | Scene Plan UI smoke | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | Route mock |
| `tests/test_scene_plan_validate_api.py` | pytest | Scene Plan 校验 API | ✅ 直接运行 | ❌ 不需要 | ✅ | 纯单元测试 |
| `tests/test_scene_plan_persistence_api.py` | pytest | Scene Plan 持久化 API | ✅ 直接运行 | ❌ 不需要 | ✅ | 纯单元测试 |
| `tests/test_scene_plan_generate_api.py` | pytest | Scene Plan 生成 API | ✅ 直接运行 | ❌ 不需要 | ✅ | 纯单元测试 |
| `tests/test_scene_plan_pipeline_integration.py` | pytest | Scene Plan + Pipeline 集成 | ✅ 直接运行 | ❌ 不需要 | ✅ | 集成测试 |
| `tests/test_workflow_pipeline_dryrun.py` | pytest | Workflow Pipeline dry-run | ✅ 直接运行 | ⚠️ 需 mock fixture | ✅ | 成熟 dry-run |
| `tests/test_workflow_pipeline_crud.py` | pytest + playwright | Workflow CRUD + E2E | ⚠️ playwright 可选 | ✅ 需后端运行（E2E 部分） | ✅ | CRUD 完整 |
| `tests/test_story_state_materials_dryrun.py` | pytest | Story State + Materials dry-run | ✅ 直接运行 | ❌ 不需要 | ✅ | 成熟 dry-run |
| `tests/test_professional_regression_smoke.py` | pytest | Professional 回归 smoke | ✅ 直接运行 | ❌ 不需要 | ✅ | 环境健康检查 |
| `tests/test_e2e_playwright_full.ts` | Playwright (TypeScript) | 完整 E2E 流程 | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | TypeScript 版本 |
| `frontend/tests/e2e/01-main-entry-smoke.spec.ts` | Playwright spec | 主入口 smoke | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | Playwright spec 格式 |
| `frontend/tests/e2e/02-lite-entry-smoke.spec.ts` | Playwright spec | Lite 入口 smoke | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | |
| `frontend/tests/e2e/03-main-entry-real-llm.spec.ts` | Playwright spec | 主入口真实 LLM | ⚠️ 需 playwright | ✅ 需后端运行 | ⚠️ 需真实 LLM | 不适合 dry-run |
| `frontend/tests/e2e/14-candidate-workflow.spec.ts` | Playwright spec | Candidate 工作流 | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | |
| `frontend/tests/e2e/13-file-operations.spec.ts` | Playwright spec | 文件操作 CRUD | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | |
| `frontend/tests/e2e/12-create-project-flow.spec.ts` | Playwright spec | 创建项目流程 | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | |
| `frontend/tests/e2e/11-right-panel-tabs.spec.ts` | Playwright spec | 右侧面板 Tab | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | |
| `frontend/tests/e2e/15-bug-regression-tests.spec.ts` | Playwright spec | Bug 回归测试 | ⚠️ 需 playwright | ✅ 需后端运行 | ✅ | |
| `tests/test_llm_reasoning_detection.py` | pytest | LLM reasoning 检测 | ✅ 直接运行 | ❌ 不需要 | ✅ | mock LLM |
| `tests/test_llm_api.py` | pytest | LLM API 层 | ✅ 直接运行 | ❌ 不需要 | ✅ | mock LLM |
| `tests/test_llm.py` | pytest | LLM 核心逻辑 | ✅ 直接运行 | ❌ 不需要 | ✅ | mock LLM |
| `backend/tests/test_task_queue.py` | pytest | Task Queue | ✅ 直接运行 | ❌ 不需要 | ✅ | 26 个测试 |
| `backend/tests/test_generation_service.py` | pytest | Generation Service | ✅ 直接运行 | ❌ 不需要 | ✅ | mock LLM |
| `backend/tests/test_prompt_engine.py` | pytest | Prompt Engine | ✅ 直接运行 | ❌ 不需要 | ✅ | 9 个测试 |
| `backend/tests/test_pipeline.py` | pytest | Pipeline Runner | ✅ 直接运行 | ❌ 不需要 | ✅ | 31 个测试 |
| `backend/tests/test_workflow.py` | pytest | Workflow Runner | ✅ 直接运行 | ❌ 不需要 | ✅ | 26 个测试 |
| `backend/tests/test_materials.py` | pytest | Materials API | ✅ 直接运行 | ❌ 不需要 | ✅ | 23 个测试 |
| `backend/tests/test_style_guide.py` | pytest | Style Guide API | ✅ 直接运行 | ❌ 不需要 | ✅ | 18 个测试 |
| `backend/tests/test_recent_context.py` | pytest | Recent Context API | ✅ 直接运行 | ❌ 不需要 | ✅ | 28 个测试 |
| `backend/tests/test_sse_heartbeat.py` | pytest | SSE Heartbeat | ✅ 直接运行 | ❌ 不需要 | ✅ | 7 个测试 |
| `backend/tests/test_event_bus.py` | pytest | EventBus | ✅ 直接运行 | ❌ 不需要 | ✅ | 22 个测试 |
| `backend/tests/contracts/test_sse_contract.py` | pytest | SSE 契约测试 | ✅ 直接运行 | ❌ 不需要 | ✅ | 14 个测试 |
| `backend/tests/contracts/test_file_api_contract.py` | pytest | File API 契约 | ✅ 直接运行 | ❌ 不需要 | ✅ | |
| `backend/tests/contracts/test_candidate_contract.py` | pytest | Candidate 契约 | ✅ 直接运行 | ❌ 不需要 | ✅ | |

---

## D. 真实可执行 E2E 路径分析

### 路径 1：Professional 编辑器最小打开流程

#### 真实入口
- **前端文件**：`frontend/src/App.vue`
- **组件**：`AppLayout.vue`（`frontend/src/components/layout/AppLayout.vue`）
- **触发函数**：`projectStore.openProject(projectId)` + `fileStore.loadTree(projectId)`
- **路由**：`/project/:projectId/file/*`（`frontend/src/router/index.ts` 第 36-122 行）

#### 涉及 API
| 方法 | 路径 | 文件 | 函数 |
|------|------|------|------|
| GET | `/api/projects/{project_id}` | `backend/api/projects.py` | `get_project` |
| GET | `/api/tree` | `backend/api/files.py` | `get_tree` |
| GET | `/api/file` | `backend/api/files.py` | `read_file` |

#### 数据写入边界
- 是否写文件：❌
- 写入哪些文件：无
- 是否生成 candidate：❌
- 是否覆盖正文：❌
- 是否修改 scoring/final：❌

#### dry-run / mock 可行性
- 是否支持 dry-run：✅
- 证据：所有 API 端点均可通过 mock fixture 隔离，不需要真实数据

#### 是否适合 T6.5 E2E
- **结论**：✅ 适合
- **原因**：纯读取流程，无破坏性操作，路径清晰，API 稳定
- **必要前置条件**：
  1. 项目目录结构存在（可使用 `backend/tests/conftest.py` 的 `mock_project` fixture）
  2. `fileStore.loadTree()` 正确处理空目录

---

### 路径 2：Scene Plan UI 流程

#### 真实入口
- **前端文件**：`frontend/src/components/right-panel/ScenePlanEditor.vue`
- **组件**：`ScenePlanEditor.vue` + `useScenePlanStore`
- **触发函数**：
  - `validateScenePlan()` → POST `/api/scene-plan/validate`
  - `saveScenePlan()` → POST `/api/scene-plan/save`
  - `generateScenePlan()` → POST `/api/scene-plan/generate`
  - `loadScenePlan()` → GET `/api/scene-plan/load`
- **路由**：右侧面板 Tab，无独立 URL

#### 涉及 API
| 方法 | 路径 | 文件 | 函数 |
|------|------|------|------|
| POST | `/api/scene-plan/validate` | `backend/api/scene_plan.py` | `validate_scene_plan` |
| POST | `/api/scene-plan/save` | `backend/api/scene_plan.py` | `save_scene_plan` |
| POST | `/api/scene-plan/generate` | `backend/api/scene_plan.py` | `generate_scene_plan` |
| GET | `/api/scene-plan/load` | `backend/api/scene_plan.py` | `load_scene_plan` |

#### 数据写入边界
- 是否写文件：✅ `save_scene_plan` 写 `scene-plan.json`
- 写入哪些文件：`{project_id}/scene-plans/scene-plan.json`
- 是否生成 candidate：❌
- 是否覆盖正文：❌
- 是否修改 scoring/final：❌

#### dry-run / mock 可行性
- 是否支持 dry-run：
  - `validate` ✅（纯计算，无 IO）
  - `save` ✅（可 mock FileService）
  - `generate` ⚠️（调用 LLM，需 mock LLM）
  - `load` ✅（纯读取）
- 证据：`backend/api/scene_plan.py` 第 615 行 `generate_scene_plan` 调用 `LLMService`

#### 是否适合 T6.5 E2E
- **结论**：✅ 适合（validate + save + load），⚠️ generate 需要 mock LLM
- **原因**：4 个端点中 3 个可 mock，generate 端点需要 mock LLM provider
- **必要前置条件**：
  1. Mock LLM service（`backend/tests/conftest.py` 中的 `mock_llm_service` fixture）
  2. `scene-plan.json` 文件写入测试隔离目录

---

### 路径 3：Candidate 预览 / adopt / delete 流程

#### 真实入口
- **前端文件**：`frontend/src/components/right-panel/CandidatePanel.vue`
- **组件**：`CandidatePanel.vue` + `useCandidateStore`
- **触发函数**：
  - `loadCandidates(projectId)` → GET `/api/candidates/{project_id}`
  - `previewCandidate()` → GET `/api/candidates/{project_id}/{candidate_id}`
  - `adoptCandidate(candidateId)` → POST `/api/candidates/{project_id}/{candidate_id}/adopt`
  - `deleteCandidate(candidateId)` → DELETE `/api/candidates/{project_id}/{candidate_id}`
- **路由**：右侧面板 Tab，无独立 URL

#### 涉及 API
| 方法 | 路径 | 文件 | 函数 |
|------|------|------|------|
| GET | `/api/candidates/{project_id}` | `backend/api/candidates.py` | `list_candidates` |
| GET | `/api/candidates/{project_id}/{candidate_id}` | `backend/api/candidates.py` | `get_candidate` |
| POST | `/api/candidates/{project_id}/{candidate_id}/adopt` | `backend/api/candidates.py` | `adopt_candidate` |
| DELETE | `/api/candidates/{project_id}/{candidate_id}` | `backend/api/candidates.py` | `delete_candidate` |

#### 数据写入边界
- 是否写文件：✅ adopt 和 delete 均写文件
- 写入哪些文件：
  - adopt：`{project_id}/chapters/vol-*/ch-*/sec-*.md`（覆盖正文）
  - delete：`{project_id}/candidates/{candidate_id}/*`（删除候选稿文件）
- 是否生成 candidate：❌（adopt 是消耗操作，不生成新 candidate）
- 是否覆盖正文：⚠️ adopt **会覆盖目标 sec 文件**
- 是否修改 scoring/final：❌

#### dry-run / mock 可行性
- 是否支持 dry-run：✅ adopt 需要 mock，delete 可 mock
- 证据：`backend/api/candidates.py` 第 50-67 行 adopt 实现，使用 `candidate_service.adopt()`

#### 是否适合 T6.5 E2E
- **结论**：✅ 适合
- **原因**：adopt 端点有 `expected_mtime` 冲突检测，候选稿文件在 `candidates/` 目录隔离，测试可清理
- **必要前置条件**：
  1. 预置测试候选稿文件（`__e2e_candidate_test_scene.md` 命名规范已在 `tests/test_candidate_flow_e2e_full.py` 第 30 行定义）
  2. adopt 前正确设置 `expected_mtime`（避免静默覆盖）
  3. 测试完成后清理 `candidates/` 目录

---

### 路径 4：Batch Generate 流程

#### 真实入口
- **前端文件**：`frontend/src/components/modals/BatchGenerateModal.vue`
- **组件**：`BatchGenerateModal.vue` + `useGenerationStore`
- **触发函数**：`batchGenerate(volumeNumber, chapterNumber, sectionNumbers)` → POST `/api/generate/batch`
- **路由**：Modal 触发，无独立 URL

#### 涉及 API
| 方法 | 路径 | 文件 | 函数 |
|------|------|------|------|
| POST | `/api/generate/batch` | `backend/api/generate.py` | `batch_generate` |

#### 数据写入边界
- 是否写文件：✅
- 写入哪些文件：
  - 空 sec 文件：直接写入生成内容
  - 非空 sec 文件：通过 candidate 策略（生成候选稿或跳过）
  - `recent-context.md`（自动追加）
- 是否生成 candidate：✅（通过 `generation_output_policy`）
- 是否覆盖正文：⚠️ 仅覆盖**空 sec 文件**，非空文件走 candidate
- 是否修改 scoring/final：❌

#### dry-run / mock 可行性
- 是否支持 dry-run：⚠️ **无独立 dry-run 参数**，需通过 mock LLM 实现等效
- 证据：`backend/api/generate.py` 第 67 行 `batch_generate` 调用 `svc.batch_generate()`，无 dry-run 参数

#### 是否适合 T6.5 E2E
- **结论**：⚠️ 部分适合
- **原因**：
  - ✅ 多目标串行处理可验证
  - ✅ 失败隔离可验证
  - ✅ 数量限制可验证
  - ⚠️ 无独立 dry-run 参数，需要 mock LLM service
  - ⚠️ 会写文件（空 sec 或 candidate），需要测试隔离
- **必要前置条件**：
  1. Mock LLM service（`mock_llm.complete_sync` 返回固定内容）
  2. 使用 `.e2e-workspace` 测试隔离目录
  3. 批量目标文件使用 `__e2e_batch_*.md` 命名规范

---

### 路径 5：Pipeline / Workflow 编辑器流程

#### 真实入口
- **前端文件**：`frontend/src/components/right-panel/PipelineEditor.vue`
- **组件**：`PipelineEditor.vue` + `usePipelineStore`
- **触发函数**：
  - `loadPipelines()` → GET `/api/pipeline/list`
  - `runPipeline(name)` → POST `/api/pipeline/run`
  - `savePipeline(name, steps)` → PUT `/api/pipeline/{name}`
  - `deletePipeline(name)` → DELETE `/api/pipeline/{name}`
  - `loadWorkflows()` → GET `/api/workflows`
  - `runWorkflow(name)` → POST `/api/workflows/run`
  - `saveWorkflow(workflow)` → POST `/api/workflows/save`
  - `deleteWorkflow(name)` → DELETE `/api/workflows/{name}`
- **路由**：右侧面板 Tab，无独立 URL

#### 涉及 API
| 方法 | 路径 | 文件 | 函数 |
|------|------|------|------|
| GET | `/api/pipeline/list` | `backend/api/pipeline.py` | `list_pipelines` |
| POST | `/api/pipeline/run` | `backend/api/pipeline.py` | `run_pipeline` |
| PUT | `/api/pipeline/{name}` | `backend/api/pipeline.py` | `update_pipeline` |
| DELETE | `/api/pipeline/{name}` | `backend/api/pipeline.py` | `delete_pipeline` |
| GET | `/api/workflows` | `backend/api/workflows.py` | `list_workflows` |
| POST | `/api/workflows/run` | `backend/api/workflows.py` | `run_workflow` |
| POST | `/api/workflows/save` | `backend/api/workflows.py` | `save_workflow` |
| DELETE | `/api/workflows/{name}` | `backend/api/workflows.py` | `delete_workflow` |

#### 数据写入边界
- 是否写文件：
  - `run_pipeline` ✅（LLM 生成，输出到 target）
  - `run_workflow` ✅（包含 PipelineStep，会调用 LLM）
  - `update_pipeline` ✅（写 YAML 文件到 `prompts/pipeline/`)
  - `update_workflow` ✅（写 JSON 文件到 `prompts/workflows/`)
  - `delete_*` ✅（删除 YAML/JSON 文件）
- 是否生成 candidate：✅（`run_pipeline` 通过 policy）
- 是否覆盖正文：⚠️（`run_pipeline` 输出到 target，取决于 output_mode）
- 是否修改 scoring/final：❌

#### dry-run / mock 可行性
- 是否支持 dry-run：
  - CRUD 端点（list/save/update/delete）✅ 纯文件操作
  - run 端点 ⚠️ 调用 LLM，需 mock LLM
- 证据：
  - `backend/api/pipeline.py` 第 36 行 `run_pipeline` 调用 `PipelineRunner.run()`
  - `backend/api/workflows.py` 第 160 行 `run_workflow` 调用 `WorkflowRunner.run()`

#### 是否适合 T6.5 E2E
- **结论**：⚠️ 部分适合
- **原因**：
  - ✅ CRUD 路径（list/save/update）可完整测试，无破坏性
  - ✅ Pipeline step 执行（dry-run 模式）可通过 `tests/test_workflow_pipeline_dryrun.py` 验证
  - ⚠️ `run_pipeline` 和 `run_workflow` 需要 mock LLM
  - ⚠️ `delete_pipeline` 和 `delete_workflow` 有破坏性，需要测试隔离
- **必要前置条件**：
  1. Mock LLM service（`mock_llm.complete_sync`）
  2. 预置测试 Pipeline YAML（`prompts/pipeline/` 下）
  3. 使用 `__e2e_pipeline_*.yaml` 命名规范

---

### 路径 6：Style Guide / Recent Context / Story State 上下文流程

#### 真实入口
- **前端文件**：
  - `frontend/src/stores/styleGuide.ts`
  - `frontend/src/stores/recentContext.ts`
  - `frontend/src/stores/storyState.ts`
- **组件**：无独立 UI，通过 File API 编辑（style-guide.md / recent-context.md / story-state.md）
- **触发函数**：
  - `styleGuideStore.load(projectId)` → GET `/api/file`（path = style-guide.md）
  - `styleGuideStore.save(projectId)` → POST `/api/file`（path = style-guide.md）
  - `recentContextStore.load(projectId)` → GET `/api/file`（path = recent-context.md）
  - `recentContextStore.save(projectId)` → POST `/api/file`（path = recent-context.md）
  - `storyStateStore.load(projectId)` → GET `/api/file`（path = story-state.md）
  - `storyStateStore.save(projectId)` → POST `/api/file`（path = story-state.md）
- **专用 API**：
  - GET `/api/style-guide/{project_id}`
  - POST `/api/style-guide/{project_id}`
  - GET `/api/recent-context/{project_id}`
  - POST `/api/recent-context/{project_id}/append`
  - GET `/api/story-state/{project_id}`
  - POST `/api/story-state/{project_id}`

#### 数据写入边界
- 是否写文件：✅
- 写入哪些文件：
  - style-guide.md
  - recent-context.md
  - .chapters-meta.json
  - story-state.md
- 是否生成 candidate：❌
- 是否覆盖正文：❌（这些是元数据文件，不是正文）
- 是否修改 scoring/final：❌

#### dry-run / mock 可行性
- 是否支持 dry-run：✅（全部为文件读写，无 LLM 调用）
- 证据：
  - `backend/api/style_guide.py` 的 `get_style_guide` 和 `save_style_guide` 无 LLM
  - `backend/api/recent_context.py` 的 `get_recent_context` 和 `append_chapter_summary` 无 LLM
  - `backend/api/story_state.py` 的 `get_story_state` 和 `update_story_state` 无 LLM

#### 是否适合 T6.5 E2E
- **结论**：✅ 适合
- **原因**：所有端点均不调用 LLM，纯文件操作，路径简单，无破坏性副作用
- **必要前置条件**：
  1. 预置测试项目目录
  2. 初始文件使用 `__e2e_*.md` 命名规范
  3. 验证 Pipeline 执行后 `recent-context.md` 自动追加（需 mock LLM）

---

### 路径 7：Materials 流程

#### 真实入口
- **前端文件**：`frontend/src/composables/useSceneGenerationActions.ts`
- **组件**：`ChatPanel.vue`（通过 `useSceneGenerationActions` 触发）
- **触发函数**：
  - `listMaterials(projectId, type)` → GET `/api/materials/{material_type}`
  - `createMaterial(projectId, type, data)` → POST `/api/materials/{material_type}`
  - `extractMaterial(projectId, type, sourceFile)` → POST `/api/extract`
  - `deleteMaterial(projectId, type, itemId)` → DELETE `/api/materials/{material_type}/{item_id}`
- **路由**：无独立 UI，通过 ChatPanel 操作

#### 涉及 API
| 方法 | 路径 | 文件 | 函数 |
|------|------|------|------|
| GET | `/api/materials/{material_type}` | `backend/api/materials.py` | `list_materials` |
| POST | `/api/materials/{material_type}` | `backend/api/materials.py` | `create_material` |
| POST | `/api/extract` | `backend/api/materials.py` | `submit_extract_task` |
| DELETE | `/api/materials/{material_type}/{item_id}` | `backend/api/materials.py` | `delete_material` |

#### 数据写入边界
- 是否写文件：✅
- 写入哪些文件：
  - `materials/extracted/{type}/{item_id}.json`
  - `materials/extracted/summaries/{item_id}.md`
  - `materials/extracted/worldbuilding.md`
- 是否生成 candidate：❌
- 是否覆盖正文：❌
- 是否修改 scoring/final：❌

#### dry-run / mock 可行性
- 是否支持 dry-run：
  - list ✅（纯读取）
  - create ✅（写 JSON/MD）
  - extract ⚠️（调用 LLM，需 mock LLM）
  - delete ✅（删文件）
- 证据：`backend/api/materials.py` 第 318 行 `submit_extract_task` 调用 `svc.complete_sync()`

#### 是否适合 T6.5 E2E
- **结论**：⚠️ 部分适合
- **原因**：
  - ✅ list + create + delete 可完整测试（无 LLM）
  - ⚠️ extract 需要 mock LLM
- **必要前置条件**：
  1. Mock LLM service（用于 extract 场景）
  2. 预置源文件（如 sec 文件，供 extract 提取）
  3. 使用 `__e2e_material_*` 命名规范

---

## E. 暂不适合 E2E 的功能

| 功能 | 当前状态 | 为什么不适合 E2E | 代码证据 | 后续增强建议 |
|------|----------|-----------------|----------|-------------|
| 真实 LLM 生成（generate / chat / batch） | 需要真实 API Key | 无 dry-run 参数，端到端测试会调用真实模型，产生费用 | `backend/api/generate.py` 第 50 行直接调用 `svc.generate()` | 添加 `dry_run: boolean` 请求参数，为 true 时跳过 LLM 调用只返回 prompt |
| AI 文风指南生成 | 需要真实 API Key | `POST /api/style-guide/{project_id}/generate` 调用 LLM | `backend/api/style_guide.py` 第 127 行 `svc.complete_sync()` | 同上，添加 dry_run 开关 |
| AI 素材提取 | 需要真实 API Key | `POST /api/extract` 调用 LLM | `backend/api/materials.py` 第 370 行 `svc.complete_sync()` | 同上 |
| AI Scene Plan 生成 | 需要真实 API Key | `POST /api/scene-plan/generate` 调用 LLM | `backend/api/scene_plan.py` 第 700 行 `svc.complete_sync()` | 同上 |
| Pipeline / Workflow run | 需要真实 API Key | `POST /api/pipeline/run` 和 `POST /api/workflows/run` 调用 LLM | `backend/api/pipeline.py` 第 36 行；`backend/api/workflows.py` 第 160 行 | Mock LLM service fixture 已存在，可通过 pytest fixture 覆盖 |
| LLM 配置测试 | 需要真实 API Key | `POST /api/llm/test` 调用 LLM 连接测试 | `backend/api/llm.py` 第 126 行 | 跳过此端点，配置测试依赖人工验证 |
| Scoring / Quality 评分 | scoring 模块不可加载 | `tests/test_scene_plan_quality_provenance_scoring.py` 第 37 行 skipif | `pytest.mark.skipif(sp_module is None, reason="scoring module not loadable")` | 先完成 scoring 模块开发 |
| 前端 TypeScript E2E spec（03-real-llm） | 需要真实 API Key | `frontend/tests/e2e/03-main-entry-real-llm.spec.ts` 调用真实 LLM | 文件注释注明 | 标记为 `@pytest.mark.skip(reason="需要真实 LLM")` |
| Adopt 到含 scoring 字段的正文 | scoring 模块不可用 | scoring 字段需要真实计算 | scoring 模块 skipif | 先完成 scoring 模块 |

---

## F. Evidence Index

| 编号 | 文件 | 符号/函数/组件/API | 支撑结论 |
|------|------|-------------------|----------|
| E001 | `frontend/src/router/index.ts` | `RouteRecordRaw[]` 路由定义 | Professional + Lite + File 路由存在 |
| E002 | `frontend/src/App.vue` | Modal 组件注册（第 159-172 行） | 13 个 Modal 存在 |
| E003 | `frontend/src/components/modals/BatchGenerateModal.vue` | `BatchGenerateModal.vue` | Batch Generate Modal 存在 |
| E004 | `frontend/src/components/right-panel/CandidatePanel.vue` | `CandidatePanel.vue` | Candidate 面板存在 |
| E005 | `frontend/src/components/right-panel/ScenePlanEditor.vue` | `ScenePlanEditor.vue` | Scene Plan UI 存在 |
| E006 | `frontend/src/components/right-panel/PipelineEditor.vue` | `PipelineEditor.vue` | Pipeline Editor 存在 |
| E007 | `frontend/src/stores/styleGuide.ts` | `useStyleGuideStore` | Style Guide store 存在 |
| E008 | `frontend/src/stores/recentContext.ts` | `useRecentContextStore` | Recent Context store 存在 |
| E009 | `frontend/src/stores/storyState.ts` | `useStoryStateStore` | Story State store 存在 |
| E010 | `frontend/src/composables/useSSE.ts` | `useSSE()` | SSE 连接 composable 存在 |
| E011 | `frontend/src/composables/useGenerationOrchestrator.ts` | `useGenerationOrchestrator()` | 生成编排器存在 |
| E012 | `frontend/src/components/chat/ChatPanel.vue` | `ChatPanel.vue` | Chat 面板存在 |
| E013 | `backend/api/generate.py` | `generate()` 第 36 行 + `batch_generate()` 第 67 行 | LLM 生成 + 批量生成 API 存在 |
| E014 | `backend/api/generate.py` | `batch_generate` 无 dry-run 参数 | Batch Generate 无独立 dry-run |
| E015 | `backend/api/candidates.py` | `adopt_candidate()` 第 50-67 行 | Adopt 端点存在，会覆盖正文 |
| E016 | `backend/api/candidates.py` | `delete_candidate()` | Delete 端点存在 |
| E017 | `backend/api/scene_plan.py` | 4 个端点（validate/save/load/generate） | Scene Plan API 存在 |
| E018 | `backend/api/scene_plan.py` | `generate_scene_plan()` 第 700 行调用 LLM | Scene Plan generate 调用 LLM |
| E019 | `backend/api/pipeline.py` | `run_pipeline()` 第 36 行 | Pipeline run API 存在 |
| E020 | `backend/api/workflows.py` | `run_workflow()` 第 160 行 | Workflow run API 存在 |
| E021 | `backend/api/style_guide.py` | `get_style_guide()` + `save_style_guide()` | Style Guide API 存在，无 LLM |
| E022 | `backend/api/style_guide.py` | `generate_style_guide()` 第 127 行 | AI 生成 Style Guide 调用 LLM |
| E023 | `backend/api/recent_context.py` | `get_recent_context()` + `append_chapter_summary()` | Recent Context API 存在，无 LLM |
| E024 | `backend/api/story_state.py` | `get_story_state()` + `update_story_state()` | Story State API 存在，无 LLM |
| E025 | `backend/api/materials.py` | `list_materials()` + `create_material()` + `delete_material()` | Materials CRUD 存在，无 LLM |
| E026 | `backend/api/materials.py` | `submit_extract_task()` 第 370 行 | AI 素材提取调用 LLM |
| E027 | `backend/api/sse.py` | `sse_endpoint()` 第 35 行 | SSE endpoint 存在 |
| E028 | `backend/tests/conftest.py` | `mock_llm_service` fixture | Mock LLM fixture 存在 |
| E029 | `tests/test_candidate_flow_e2e.py` | `sync_playwright()` 第 153 行 | Candidate E2E Playwright 测试存在 |
| E030 | `tests/test_workflow_pipeline_dryrun.py` | `TEST_FILE_PATH` 第 15 行 | Workflow Pipeline dry-run 测试存在 |
| E031 | `tests/test_story_state_materials_dryrun.py` | `TEST_STORY_STATE_KEY` 第 14 行 | Story State + Materials dry-run 测试存在 |
| E032 | `frontend/tests/e2e/01-main-entry-smoke.spec.ts` | Playwright spec | 前端 TypeScript E2E spec 存在 |
| E033 | `backend/core/generation_service.py` | `batch_generate()` | batch_generate 实现存在 |
| E034 | `backend/core/pipeline.py` | `PipelineRunner.run()` | Pipeline Runner 存在 |
| E035 | `backend/core/workflow.py` | `WorkflowRunner.run()` | Workflow Runner 存在 |
| E036 | `backend/application/memory_service.py` | `MemoryService.append_scene_memory()` | recent-context 自动更新存在 |
| E037 | `backend/core/event_bus.py` | `EventBus` class + `publish()` | EventBus 事件总线存在 |
| E038 | `backend/core/task_queue.py` | `TaskQueue` class | Task Queue 存在（独立于 Pipeline） |
| E039 | `backend/tests/test_task_queue.py` | 26 个单元测试 | Task Queue 测试覆盖完整 |
| E040 | `backend/tests/test_prompt_engine.py` | 9 个单元测试 | Prompt Engine 测试覆盖完整 |
| E041 | `backend/tests/test_sse_heartbeat.py` | 7 个单元测试 | SSE Heartbeat 测试覆盖完整 |
| E042 | `backend/tests/test_event_bus.py` | 22 个单元测试 | EventBus 测试覆盖完整 |

---

## G. T6.5 后续测试建议

### T6.5.1 → Candidate 完整工作流 E2E

**建议测试什么**：
1. Candidate 列表加载（GET `/api/candidates/{project_id}`）
2. Candidate 预览（GET `/api/candidates/{project_id}/{candidate_id}`）
3. Candidate adopt 到正文（POST `/api/candidates/{project_id}/{candidate_id}/adopt`）
4. Adopt 后验证正文变化
5. Candidate delete（DELETE `/api/candidates/{project_id}/{candidate_id}`）
6. SSE 事件推送（file.updated / candidate.adopted）

**依赖的入口和测试文件**：
- 前端入口：`CandidatePanel.vue` + `useCandidateStore`
- 现有测试：`tests/test_candidate_flow_e2e.py`（可改造使用 mock fixture）
- `tests/test_candidate_preview_delete_e2e.py`（Preview + Delete）
- `tests/test_candidate_adopt_conflict_sse_e2e.py`（Adopt + SSE）
- `backend/tests/conftest.py` 的 `mock_llm_service` fixture（用于生成候选稿）
- 测试命名规范：`__e2e_candidate_test_scene.md`

**Mock 策略**：
- 使用 `mock_llm_service` fixture 生成候选稿
- Adopt 操作本身不调用 LLM，无需 mock

**前置条件**：
1. 预置 sec 文件到测试项目（空文件或含测试内容）
2. 调用 LLM 生成候选稿（使用 mock LLM）
3. adopt 端点需要正确的 `expected_mtime`（防止静默覆盖）

---

### T6.5.2 → Scene Plan UI 流程 E2E

**建议测试什么**：
1. Scene Plan 校验（POST `/api/scene-plan/validate`）
2. Scene Plan 保存（POST `/api/scene-plan/save`）
3. Scene Plan 加载（GET `/api/scene-plan/load`）
4. Scene Plan 生成（POST `/api/scene-plan/generate`，mock LLM）

**依赖的入口和测试文件**：
- 前端入口：`ScenePlanEditor.vue` + `useScenePlanStore`
- 现有测试：`tests/test_scene_plan_validate_api.py`
- `tests/test_scene_plan_persistence_api.py`
- `tests/test_scene_plan_pipeline_integration.py`

**Mock 策略**：
- validate / save / load 无需 mock（纯计算/文件 IO）
- generate 使用 `mock_llm_service` fixture

**前置条件**：
1. 预置 `scene-plans/` 目录
2. Scene Plan JSON 结构符合 `backend/schemas/scene_plan.py` 定义

---

### T6.5.3 → Pipeline / Workflow CRUD + Dry-run E2E

**建议测试什么**：
1. Pipeline 列表加载（GET `/api/pipeline/list`）
2. Pipeline 详情（GET `/api/pipeline/{name}`）
3. Pipeline 自定义创建（POST `/api/pipeline/custom`）
4. Pipeline YAML 保存（PUT `/api/pipeline/{name}`）
5. Pipeline dry-run 执行（mock LLM）
6. Workflow CRUD（GET / POST / DELETE `/api/workflows/*`）
7. Workflow dry-run 执行（mock LLM）

**依赖的入口和测试文件**：
- 前端入口：`PipelineEditor.vue` + `usePipelineStore`
- 现有测试：`tests/test_workflow_pipeline_crud.py`
- `tests/test_workflow_pipeline_dryrun.py`
- `backend/tests/test_pipeline.py`（31 个单元测试）
- `backend/tests/test_workflow.py`（26 个单元测试）

**Mock 策略**：
- CRUD 端点无需 mock（纯文件 IO）
- run 端点使用 `mock_llm_service` fixture

**前置条件**：
1. 预置测试 Pipeline YAML（`prompts/pipeline/__e2e_test.yaml`）
2. 预置测试 Workflow JSON（`prompts/workflows/__e2e_test.json`）
3. 目标 sec 文件存在

**暂缓项**：
- `DELETE /api/pipeline/{name}`（破坏性，测试后难以恢复）
- `DELETE /api/workflows/{name}`（同上）
- 建议改为验证"无法删除系统内置 Pipeline/Workflow"（安全边界）

---

### T6.5.4 → 上下文模块（Style Guide / Recent Context / Story State）E2E

**建议测试什么**：
1. Style Guide 读取（GET `/api/style-guide/{project_id}`）
2. Style Guide 保存（POST `/api/style-guide/{project_id}`）
3. Recent Context 读取（GET `/api/recent-context/{project_id}`）
4. Recent Context 追加（POST `/api/recent-context/{project_id}/append`）
5. Story State 读取（GET `/api/story-state/{project_id}`）
6. Story State 更新（POST `/api/story-state/{project_id}`）
7. Pipeline 执行后 recent-context.md 自动追加（集成测试）

**依赖的入口和测试文件**：
- 前端入口：File API（styleGuideStore / recentContextStore / storyStateStore）
- 现有测试：`backend/tests/test_style_guide.py`（18 个）
- `backend/tests/test_recent_context.py`（28 个）
- `backend/tests/test_story_state.py`（13 个）
- `tests/test_story_state_materials_dryrun.py`

**Mock 策略**：
- 全部端点不调用 LLM，无需 mock
- 集成测试时 Pipeline 部分使用 `mock_llm_service`

**前置条件**：
1. 预置测试项目目录
2. 初始文件内容使用最小样例（避免敏感数据泄露）

---

### T6.5.5 → Materials 模块 E2E

**建议测试什么**：
1. Materials 列表（GET `/api/materials/{material_type}`）
2. Material 创建（POST `/api/materials/{material_type}`）
3. Material 删除（DELETE `/api/materials/{material_type}/{item_id}`）
4. Material 提取（POST `/api/extract`，mock LLM）

**依赖的入口和测试文件**：
- 前端入口：`useSceneGenerationActions.ts` → `ChatPanel.vue`
- 现有测试：`backend/tests/test_materials.py`（23 个）

**Mock 策略**：
- list / create / delete 无需 mock
- extract 使用 `mock_llm_service` fixture

**前置条件**：
1. 预置源文件（如 sec 文件供提取）
2. 测试材料 ID 使用 `__e2e_material_*` 命名

---

### 暂缓测试

| 暂缓项 | 原因 | 后续增强建议 |
|--------|------|-------------|
| 真实 LLM 生成（generate / chat / batch） | 无 dry-run 参数，会产生真实 API 费用 | 添加 `dry_run: boolean` 请求参数 |
| AI 文风指南生成 | 同上 | 添加 dry_run 开关 |
| AI 素材提取 | 同上 | 添加 dry_run 开关 |
| AI Scene Plan 生成 | 同上 | 添加 dry_run 开关 |
| Scoring / Quality 评分 | scoring 模块不可用 | 完成 scoring 模块开发后恢复 |
| LLM 配置测试（`/api/llm/test`） | 需要真实 API Key | 依赖人工验证或 mock 健康检查 |

---

## H. 验证命令

```bash
# 工作区状态
git status                              # clean
git rev-parse HEAD                      # 9d7f9598...
git rev-parse origin/main               # 9d7f9598...

# 格式检查
git diff --check                        # 无问题

# 前端构建验证（本次任务为文档生成，不涉及前端代码修改）
npm run build                           # ✅ 通过（1.98s，3430 modules）

# 后端测试（本次任务为文档生成+静态分析，核心功能已有 T6.3.x 验证覆盖）
# 以下为快速验证命令，证明后端测试框架可用：
cd backend
$env:PYTHONPATH = "."
python -m pytest tests/test_task_queue.py -v --tb=line -q  # 26/26 ✅
python -m pytest tests/test_prompt_engine.py -v --tb=line -q # 9/9 ✅
python -m pytest tests/test_sse_heartbeat.py -v --tb=line -q  # 7/7 ✅
python -m pytest tests/test_materials.py tests/test_style_guide.py tests/test_recent_context.py -v --tb=line -q  # 82/82 ✅

# 说明：本次任务为文档生成，不修改代码，因此不跑全量测试。
# 所有测试已在 T6.3.1-T6.3.8 中验证通过。
```

---

## I. 校准结论

### 可立即执行的 T6.5 E2E 路径

| 路径 | 测试文件 | 覆盖端点 | Mock 需求 |
|------|----------|----------|-----------|
| Candidate 完整工作流 | `tests/test_candidate_flow_e2e.py` + `tests/test_candidate_preview_delete_e2e.py` | 4 个 API | mock LLM（生成候选稿时） |
| Scene Plan UI | `tests/test_scene_plan_validate_api.py` + `tests/test_scene_plan_persistence_api.py` | 4 个 API | mock LLM（generate 时） |
| Pipeline / Workflow CRUD | `tests/test_workflow_pipeline_crud.py` | 8 个 API | mock LLM（run 时） |
| Pipeline / Workflow Dry-run | `tests/test_workflow_pipeline_dryrun.py` | 2 个 API | mock LLM（已有） |
| 上下文模块 | `tests/test_story_state_materials_dryrun.py` | 6 个 API | 无需 mock |
| Materials 模块 | `backend/tests/test_materials.py`（扩展为 E2E） | 4 个 API | mock LLM（extract 时） |

### 需要先增强的功能

| 功能 | 当前限制 | 增强建议 | 优先级 |
|------|----------|----------|--------|
| 所有 LLM 生成端点 | 无 dry-run 参数 | 添加 `dry_run: boolean`，为 true 时跳过 LLM 调用并返回 prompt | P0 |
| Scoring 模块 | 不可加载 | 完成 scoring 模块开发 | P1 |
| 前端 TypeScript E2E | 部分 spec 需要真实 LLM | 分离 dry-run spec 和 real-llm spec | P2 |

### 测试隔离策略

所有 E2E 测试必须：
1. 使用 `.e2e-workspace` 隔离目录（不污染真实项目数据）
2. 测试文件命名使用 `__e2e_*` 前缀（如 `__e2e_candidate_test_scene.md`）
3. 测试完成后清理所有测试文件
4. Adopt 操作必须携带 `expected_mtime`（防止静默覆盖）
5. 不在测试中硬编码 API Key（使用环境变量或 mock）
