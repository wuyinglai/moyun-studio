# Phase T4.4 — Workflow / Pipeline / Prompt 模块验收

## 1. 背景

上一阶段 T4.3 已完成原专业版编辑能力静态验收。本阶段验收支撑这些能力的 Workflow / Pipeline / Prompt 模块。只做静态验收和文档，不新增功能。

---

## 2. Workflow Findings

✅ **Workflow 模块存在且完整**

### 后端
- ✅ `backend/core/workflow.py` — 工作流引擎
- ✅ `backend/schemas/workflow.py` — 工作流 Schema
- ✅ **功能：
  - 多步骤编排能力
  - loop 循环嵌套
  - 文件操作
  - 变量解析与传递
  - Human 节点暂停与恢复
- ✅ `WorkflowRunState` 结构
- ✅ `WorkflowDef` 结构

### 前端
- ✅ `frontend/src/composables/useWorkflow.ts` — Workflow 管理
- ✅ 类型定义：
  - `Workflow`
  - `WorkflowStep`
  - `WorkflowRunState`
  - `RunningNode`
- ✅ 状态管理：
  - 节点状态 (pending/running/waiting_for_user/completed/failed/skipped)
  - 运行日志
- ✅ SSE 事件
- ✅ 变量池

### 定位
- **Workflow** — 高级编排层，用于编排多个 pipeline 或复杂流程
- **Pipeline** — 单任务执行层，按步骤执行 LLM 调用

---

## 3. Pipeline Findings

✅ **Pipeline 模块存在且完整**

### 后端
- ✅ `backend/core/pipeline.py` — 管线引擎
- ✅ `backend/api/pipeline.py` — Pipeline API
- ✅ `backend/schemas/pipeline.py` — Pipeline Schema
- ✅ **职责：
  - 加载 Pipeline YAML 定义
  - 按步骤顺序执行 LLM 调用
  - 失败时自动 fallback
  - AsyncGenerator 形式输出 SSE 事件
- ✅ Pipeline YAML 路径：`prompts/pipeline/{name}.yaml`
- ✅ 每步 Prompt 路径：`prompts/pipeline/{name}/{step_id}.md`

### 前端
- ✅ `frontend/src/composables/useFileGeneration.ts — Pipeline 调用
  - ✅ `runPipeline()` 函数
  - ✅ 支持 `output_mode` 参数
  - ✅ **第 167 行：`polish/rewrite` 默认 `output_mode='candidate'`
- ✅ `frontend/src/stores/generation.ts
- ✅ `frontend/src/composables/useGenerationOrchestrator.ts

### 调用链
```
EditorToolbar/PromptPanel/...
  ↓
runPipeline(name, options)
  ↓
/api/pipelines/run
  ↓
PipelineRunner.run()
  ↓
按步骤执行
  ↓
LLMService.call()
  ↓
PromptEngine.render()
  ↓
CandidateService.create() (if output_mode='candidate')
```

---

## 4. Prompt Engine Findings

✅ **Prompt Engine 存在且完整**

### 后端
- ✅ `backend/core/prompt_engine.py` — Prompt 模板引擎
- ✅ 渲染 Jinja2 模板
- ✅ 支持片段引用 `@{file_path}`
- ✅ 依赖注入解耦 FileService
- ✅ 模板加载：
  - 从 `prompts/` 目录
  - 从 `workspace/prompts/` 目录
- ✅ `render()` 方法
- ✅ 支持 category/template_type 结构

### 模板结构：
- `prompts/generate/` — 生成类
- `prompts/extract/` — 提取类
- `prompts/transform/` — 转换类
- `prompts/pipeline/` — Pipeline 步骤

---

## 5. Pipeline YAML Findings

✅ **Pipeline YAML 完整**

### polish.yaml
- ✅ **步骤：
  1. depai (去AI味)
  2. prose (提升文笔)
  3. logic (修正逻辑)
  4. rhythm (优化节奏)
  5. diff (修改摘要)
- ✅ fallback 机制

### rewrite.yaml
- ✅ **步骤：**
  1. diagnose (诊断问题)
  2. draft (重写初稿)
  3. depai (去AI味)
  4. logic (逻辑修正)
  5. rhythm (优化节奏)
  6. diff (修改摘要)
- ✅ fallback 机制

### 其他
- ✅ **不会直接写正文**：由 `output_mode='candidate'` 控制
- ✅ **默认输出 candidate**：由 `useFileGeneration.ts` 第 167 行

---

## 6. Prompt Editor / Variant Findings

⚠️ **Prompt 面板存在，但 Prompt Editor / Variant 部分实现

### 前端
- ✅ `frontend/src/components/right-panel/PromptPanel.vue` — Prompt 面板
- ✅ 显示工作流步骤
- ✅ 显示当前 Prompt 预览
- ✅ 查看 Pipeline 链接
- ❌ **未发现完整的 Prompt Editor（可视化编辑器）
- ❌ **未发现完整的 Prompt Variant（项目级 Prompt 变体保存）

---

## 7. Candidate Boundary

✅ **Candidate 边界清晰且安全**

- ✅ Pipeline 结果进入 Candidate：是
  - `output_mode='candidate'`
- ✅ `pipeline.py` 调用 `CandidateService.create()`
- ✅ **不会直接覆盖正文：
  - 除非 `output_mode='write_scene' 或 overwrite
- ✅ 需要用户 adopt：是
  - CandidatePanel 提供 adopt/reject
- ✅ adopt 前有冲突检查：是
  - base_hash / base_mtime 验证

---

## 8. Lite Impact

✅ **Lite 完全独立，不受影响**

- ✅ Lite 使用 `useLiteGeneration.ts`
- ✅ Lite 使用独立 API 路由
- ✅ Lite 不依赖 Workflow/Pipeline（可选）
- ✅ T4.4 验收不修改 Lite

---

## 9. Missing or Uncertain Areas

- ❌ Prompt Editor 可视化编辑器：未发现完整实现
- ❌ Prompt Variant 项目级 Prompt 变体保存：未发现完整实现
- ❌ Prompt 项目级 Prompt 配置 UI：未发现
- ⚠️ Workflow 完整 UI 编排工具：部分存在

---

## 10. 验收结论

⚠️ **静态验收通过，核心模块完整**

✅ 通过项：
- ✅ Workflow 引擎完整
- ✅ Pipeline 引擎完整
- ✅ Prompt Engine 完整
- ✅ Pipeline YAML 完整
- ✅ Candidate 边界安全
- ✅ 不会自动覆盖正文
- ✅ Lite 不受影响
- ❌ Prompt Editor / Variant 未完整实现

**文档完成日期：2026-06-05
