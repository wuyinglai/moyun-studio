# Task Entrypoints / 任务入口指南

> 本文档告诉 AI：接到某类任务时应该先读哪些文件、不能违反哪些规则、修改后跑哪些测试。

---

## 1. 创建项目

Read first:
- docs/frontend-user-flow.md
- docs/contracts/api-contract.md
- docs/文件系统设计.md
- frontend/src/stores/project.ts
- frontend/src/modules/project/api.ts
- frontend/src/modules/project/types.ts
- frontend/src/composables/useProjectWizard.ts
- frontend/src/components/modals/CreateProjectModal.vue
- backend/api/projects.py
- backend/core/project_service.py
- backend/schemas/project.py

Related docs:
- docs/功能清单.md
- docs/code-map.md

Do not:
- 不要在 workspace/ 下直接创建目录，必须通过 ProjectService。
- 不要跳过项目元数据校验（project_name 长度、非法字符）。
- 不要硬编码默认卷章结构，应使用配置常量。

Tests:
- python -m pytest backend/tests -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 2. 打开项目

Read first:
- docs/frontend-user-flow.md
- docs/contracts/api-contract.md
- frontend/src/stores/project.ts
- frontend/src/modules/project/api.ts
- frontend/src/components/modals/OpenProjectModal.vue
- backend/api/projects.py
- backend/core/project_service.py

Related docs:
- docs/code-map.md

Do not:
- 不要假设项目目录一定存在，需处理 ProjectNotFound。
- 不要在打开时加载全部文件内容，应按需加载。

Tests:
- python -m pytest backend/tests -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 3. 打开文件

Read first:
- docs/contracts/api-contract.md
- docs/文件系统设计.md
- frontend/src/stores/file.ts
- frontend/src/stores/fileMeta.ts
- frontend/src/composables/useEditorFileActions.ts
- frontend/src/components/editor/EditorTabs.vue
- frontend/src/components/editor/MarkdownEditor.vue
- backend/api/files.py
- backend/core/file_ops.py
- backend/schemas/file.py

Related docs:
- docs/contracts/scene-path-contract.md

Do not:
- 不要绕过 FileService 直接读文件。
- 不要在 API 层用 `project_dir / req.path` 拼接路径。
- 不要忽略 expected_mtime / expected_hash 冲突检测。

Tests:
- python -m pytest backend/tests/test_file_ops.py backend/tests/contracts/test_file_api_contract.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 4. 保存文件

Read first:
- docs/contracts/api-contract.md
- docs/contracts/event-contract.md
- frontend/src/stores/file.ts
- frontend/src/composables/useAutoSave.ts
- frontend/src/composables/useEditorFileActions.ts
- backend/api/files.py
- backend/core/file_ops.py
- backend/schemas/file.py

Related docs:
- docs/编码规范.md

Do not:
- 不要省略 expected_mtime / expected_hash，必须处理 FILE_CONFLICT。
- 不要在 file.updated SSE 事件中携带完整正文 content。
- 不要用同步 open() 写文件，必须用 aiofiles。

Tests:
- python -m pytest backend/tests/test_file_ops.py backend/tests/contracts/test_file_api_contract.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 5. 写下一场景

Read first:
- docs/frontend-user-flow.md
- docs/contracts/scene-path-contract.md
- docs/contracts/candidate-contract.md
- frontend/src/composables/useSceneGenerationActions.ts
- frontend/src/composables/useFileGeneration.ts
- frontend/src/composables/useGenerationOrchestrator.ts
- frontend/src/stores/generation.ts
- frontend/src/modules/scene/scenePath.ts
- frontend/src/modules/scene/types.ts
- frontend/src/components/editor/EditorToolbar.vue
- backend/api/generate.py
- backend/application/scene_service.py
- backend/core/generation_service.py
- backend/policies/generation_output_policy.py
- backend/core/pipeline.py
- prompts/pipeline/generate.yaml

Related docs:
- docs/功能清单.md
- docs/Prompt模板说明.md

Do not:
- 不要在组件中重新实现 scene path 递增逻辑。
- 不要把 sec-*.md 当成章节。
- 不要静默覆盖已有 sec 文件。
- 不要绕过 CandidatePolicy / GenerationOutputPolicy。
- 不要让场景输出超过 600-1000 中文字范围。

Tests:
- python -m pytest backend/tests -q --tb=short
- cd frontend && npm run lint && npm run build && npm run test:e2e:main

---

## 6. 润色 / 重写

Read first:
- docs/contracts/candidate-contract.md
- docs/contracts/event-contract.md
- frontend/src/composables/useSceneGenerationActions.ts
- frontend/src/components/right-panel/CandidatePanel.vue
- frontend/src/modules/candidate/api.ts
- frontend/src/modules/candidate/types.ts
- backend/api/candidates.py
- backend/core/candidate_service.py
- backend/policies/candidate_policy.py
- backend/core/generation_service.py
- prompts/pipeline/rewrite.yaml
- prompts/pipeline/polish.yaml

Related docs:
- docs/功能清单.md
- docs/Prompt模板说明.md

Do not:
- 不要直接覆盖正式正文，必须生成 candidate。
- 不要跳过 base_hash / base_mtime 校验。
- 不要让 candidate.source_path 带重复 project_id。
- 不要在 file.updated SSE 事件中发送正文 content。

Tests:
- python -m pytest backend/tests/test_candidate_service.py backend/tests/contracts/test_candidate_contract.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 7. 采用候选稿

Read first:
- docs/contracts/candidate-contract.md
- frontend/src/components/right-panel/CandidatePanel.vue
- frontend/src/modules/candidate/api.ts
- frontend/src/modules/candidate/types.ts
- frontend/src/composables/useLiteCandidateActions.ts
- backend/api/candidates.py
- backend/core/candidate_service.py
- backend/policies/candidate_policy.py

Related docs:
- docs/功能清单.md

Do not:
- 不要跳过 base_hash / base_mtime 冲突检测。
- 不要在采用前省略 revision-log 写入。
- 不要让 candidate.source_path 带重复 project_id。
- 不要在 file.updated 事件中发送正文 content。

Tests:
- python -m pytest backend/tests/test_candidate_service.py backend/tests/contracts/test_candidate_contract.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 8. Lite 开局卡

Read first:
- docs/frontend-user-flow.md
- frontend/src/views/LiteWritingView.vue
- frontend/src/composables/useLiteGeneration.ts
- frontend/src/composables/useLitePrefetch.ts
- frontend/src/composables/useLiteCandidateActions.ts
- frontend/src/services/liteService.ts
- backend/api/lite.py
- backend/schemas/lite.py

Related docs:
- docs/功能清单.md
- docs/contracts/candidate-contract.md

Do not:
- 不要只改 Lite 入口而忽略 Professional 入口。
- 不要绕过 CandidatePolicy。
- 不要硬编码 Lite 专用 API 路径，应复用已有模块。

Tests:
- python -m pytest backend/tests/contracts/test_lite_contract.py backend/tests/test_lite_longform_flow.py -q --tb=short
- cd frontend && npm run lint && npm run build && npm run test:e2e:lite

---

## 9. Lite 写下一场景

Read first:
- docs/frontend-user-flow.md
- docs/contracts/scene-path-contract.md
- frontend/src/views/LiteWritingView.vue
- frontend/src/composables/useLiteGeneration.ts
- frontend/src/composables/useLitePrefetch.ts
- frontend/src/modules/scene/scenePath.ts
- backend/api/lite.py
- backend/application/scene_service.py
- backend/core/generation_service.py
- backend/policies/generation_output_policy.py
- prompts/pipeline/generate.yaml

Related docs:
- docs/功能清单.md

Do not:
- 不要在 Lite 中重新实现 scene path 递增逻辑，应复用 scenePath.ts。
- 不要静默覆盖已有 sec 文件。
- 不要让场景输出超过 600-1000 中文字范围。
- 不要只改 Lite 入口而忽略 Professional 入口。

Tests:
- python -m pytest backend/tests/contracts/test_lite_contract.py -q --tb=short
- cd frontend && npm run lint && npm run build && npm run test:e2e:lite

---

## 10. SSE 事件

Read first:
- docs/contracts/event-contract.md
- frontend/src/composables/useSSE.ts
- frontend/src/modules/sse/index.ts
- frontend/src/modules/sse/types.ts
- frontend/src/modules/sse/composables.ts
- backend/api/sse.py
- backend/core/event_bus.py
- backend/main.py

Related docs:
- docs/后端架构设计.md

Do not:
- 不要在 file.updated 事件中携带完整正文 content。
- 不要修改心跳间隔（15 秒）和超时重连（45 秒）除非有明确需求。
- 不要在 SSE 事件中发送 API Key 或敏感信息。
- 不要绕过 EventBus 直接推送事件。

Tests:
- python -m pytest backend/tests/test_event_bus.py backend/tests/test_sse_heartbeat.py backend/tests/contracts/test_sse_contract.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 11. LLM 设置

Read first:
- docs/技术选型速查.md
- frontend/src/stores/llm.ts
- frontend/src/components/modals/SettingsModal.vue
- backend/api/llm.py
- backend/core/llm.py
- backend/core/llm_circuit_breaker.py
- backend/schemas/llm.py
- backend/config.py

Related docs:
- docs/编码规范.md

Do not:
- 不要将 API Key 写入 localStorage、日志、截图、测试报告。
- 不要直接使用 openai 库，必须通过 LiteLLM。
- 不要修改熔断器阈值除非有明确需求。
- 不要用 os.getenv()，必须用 pydantic-settings。

Tests:
- python -m pytest backend/tests/test_llm.py backend/tests/test_llm_circuit_breaker.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 12. Pipeline YAML

Read first:
- docs/Prompt模板说明.md
- docs/功能清单.md
- backend/core/pipeline.py
- backend/core/pipeline_validator.py
- backend/application/pipeline/context.py
- backend/application/pipeline/registry.py
- backend/application/pipeline/executors.py
- backend/application/pipeline/runner.py
- backend/api/pipeline.py
- backend/api/workflows.py
- backend/schemas/pipeline.py
- backend/schemas/pipeline_config.py
- frontend/src/stores/pipeline.ts
- frontend/src/modules/pipeline/types.ts
- frontend/src/components/right-panel/PipelineEditor.vue
- frontend/src/components/right-panel/ExecutionPanel.vue
- frontend/src/components/right-panel/WorkflowPanel.vue
- frontend/src/components/right-panel/StepEditor.vue
- frontend/src/composables/useWorkflow.ts
- prompts/pipeline/ (所有 .yaml 文件)

Related docs:
- docs/产品架构-人机协同工作流.md
- docs/专业版节点化改造计划.md

Do not:
- 不要修改 Pipeline YAML 的 schema 时不更新 pipeline_validator.py。
- 不要在 Pipeline 步骤中硬编码 prompt 内容，必须引用 prompts/ 目录。
- 不要跳过启动时的 Pipeline YAML 校验。
- 不要让 output_mode 为 overwrite 时缺少人工确认。

Tests:
- python -m pytest backend/tests/test_pipeline.py backend/tests/test_pipeline_validator.py backend/tests/contracts/test_pipeline_contract.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 13. Prompt 修改

Read first:
- docs/Prompt模板说明.md
- docs/功能清单.md
- CONTEXT.md
- prompts/ 目录下相关文件
- backend/core/prompt_engine.py
- backend/core/prompt_versioning.py

Related docs:
- docs/编码规范.md

Do not:
- 不要在代码中硬编码 prompt 内容，必须从 prompts/ 目录加载。
- 不要把 sec 误解为 section 或 chapter，sec = scene。
- 不要让场景输出要求超出 600-1000 中文字范围。
- 不要修改 prompt 前不运行 `python scripts/prompt-impact.py <prompt-file>`。
- 高风险 rewrite/polish 的 prompt 必须保留 candidate 工作流。

Tests:
- python scripts/prompt-impact.py <modified-prompt-file>
- python -m pytest backend/tests/test_prompt_engine.py backend/tests/test_prompt_versioning.py -q --tb=short
- cd frontend && npm run lint && npm run build

---

## 14. E2E 测试

Read first:
- frontend/playwright.config.ts
- frontend/tests/e2e/helpers/ (所有辅助文件)
- frontend/tests/e2e/01-main-entry-smoke.spec.ts
- frontend/tests/e2e/02-lite-entry-smoke.spec.ts
- tests/ 目录下的测试文件

Related docs:
- docs/手动功能测试指南.md

Do not:
- 不要在 E2E 测试中硬编码 API Key。
- 不要在 E2E 质量报告中泄露 API Key。
- 不要跳过 smoke 测试直接写 full flow 测试。
- 不要忽略 Lite 和 Professional 双入口测试覆盖。

Tests:
- cd frontend && npm run test:e2e
- cd frontend && npm run test:e2e:lite
- cd frontend && npm run test:e2e:main

---

## 15. 真实 LLM 质量报告

Read first:
- frontend/tests/e2e/03-main-entry-real-llm.spec.ts
- frontend/tests/e2e/04-lite-entry-real-llm.spec.ts
- frontend/tests/e2e/05-candidate-batch-real-llm.spec.ts
- frontend/tests/e2e/06-quality-report.spec.ts
- frontend/tests/e2e/helpers/qualityReport.ts
- frontend/tests/e2e/helpers/qualityRubric.ts
- frontend/tests/e2e/helpers/llmEnv.ts
- frontend/tests/e2e/helpers/evaluateQuality.ts
- tests/test_llm.py
- tests/test_llm_api.py
- tests/test_api_quality.py

Related docs:
- docs/功能测试报告.md

Do not:
- 不要在质量报告中记录 API Key。
- 不要在没有 LLM API Key 的环境下运行 real-llm 测试。
- 不要将 real-llm 测试加入 CI 默认流程。
- 不要忽略质量评分 rubric 标准。

Tests:
- cd frontend && npm run test:e2e:llm
- python -m pytest tests/test_llm.py tests/test_api_quality.py -q --tb=short
