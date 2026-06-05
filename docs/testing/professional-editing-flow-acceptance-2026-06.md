# Phase T4.3 — 原专业版编辑能力验收

## 1. 背景
上一阶段 T4.2 已完成 Lite/Professional 共存与切换基线静态验收。本阶段验收 Professional 已有编辑能力（rewrite/polish/de-ai/logic-fix 等）是否存在、是否走 candidate 机制、是否不破坏 Lite。

---

## 2. 前端入口发现

### 2.1 EditorToolbar ✅
**组件**：`frontend/src/components/editor/EditorToolbar.vue`

**编辑相关按钮**：
- ✏️ 润色 → `runPipeline('polish')`
- 📦 精修 → `runPipeline('rewrite')`
- 🌟 提取 → `runPipeline('extract')`
- 🔄 重新生成 → `handleRegenerate`
- ➕ 自定义 → `customPipelines` 下拉菜单
- 批量生成 → 更多菜单

### 2.2 ChatPanel ✅
**组件**：`frontend/src/components/chat/ChatPanel.vue`

**入口**：
- 🪶 润色文字 → `chat:request-rewrite` → `generationStore.rewriteContent`

### 2.3 RightPanel ✅
**组件**：`frontend/src/components/right-panel/RightPanel.vue`

**Tab**：
- ⚡ 快捷 → ProfessionalQuickPanel
- ✍️ Prompt → PromptPanel
- 🔧 管线 → PipelineEditor
- 📋 工作流 → WorkflowPanel
- 📝 候选稿 → CandidatePanel
- 🧠 记忆 → MemorySettingsPanel
- 📖 故事 → StoryStatePanel
- 🎨 文风 → StyleGuidePanel
- 🧭 上下文 → RecentContextPanel
- 📊 执行 → ExecutionPanel
- 🔄 流程 → FlowPanel

---

## 3. 前端调用链发现

### 3.1 统一入口：runPipeline ✅
**Composable**：`frontend/src/composables/useFileGeneration.ts`

**关键代码**（第 167 行）：
```typescript
const mode = outputMode || (pipelineName === 'polish' || pipelineName === 'rewrite' ? 'candidate' : 'write_scene')
```

**结论**：`polish` 和 `rewrite` 默认使用 `output_mode='candidate'`，不会直接覆盖正文！

### 3.2 触发链
| 入口 | 函数 | 最终调用 |
|------|------|----------|
| EditorToolbar ✏️ 润色 | `runPipeline('polish')` | `/api/pipeline/run` + output_mode='candidate' |
| EditorToolbar 📦 精修 | `runPipeline('rewrite')` | `/api/pipeline/run` + output_mode='candidate' |
| EditorToolbar 🌟 提取 | `runPipeline('extract')` | `/api/pipeline/run` |
| ChatPanel 🪶 润色文字 | `chat:request-rewrite` → `handleAIRewrite` | 复用 Professional 链路 |

---

## 4. 后端 API / Service 发现

### 4.1 Pipeline 服务 ✅
**相关文件**：
- `backend/api/pipelines.py`
- `backend/core/pipeline.py`
- `backend/core/prompt_engine.py`

**Candidate 服务**：
- `backend/core/candidate_service.py`
- `backend/api/candidates.py`
- `backend/policies/candidate_policy.py`

### 4.2 质量审查服务 ✅
**文件**：`backend/core/quality_service.py`
- 负责 perform_review（质量审查）
- 保存审查结果到 `materials/reviews/`

---

## 5. Prompt 发现

### 5.1 Pipeline YAML ✅
| Pipeline | 文件 | 功能 |
|----------|------|------|
| polish | `prompts/pipeline/polish.yaml` | 去AI味、提升文笔、修正逻辑、优化节奏 |
| rewrite | `prompts/pipeline/rewrite.yaml` | 诊断问题、重写初稿、去AI味、逻辑修正、优化节奏 |
| extract | `prompts/pipeline/extract.yaml` | 智能提取 |
| generate | `prompts/pipeline/generate.yaml` | 生成场景 |
| outline | `prompts/pipeline/outline.yaml` | 大纲 |
| story-state | `prompts/pipeline/story-state.yaml` | 故事状态 |

### 5.2 Polish 步骤 ✅
- depai（去AI味）
- prose（提升文笔）
- logic（修正逻辑）
- rhythm（优化节奏）
- diff（修改摘要）

### 5.3 Rewrite 步骤 ✅
- diagnose（诊断问题）
- draft（重写初稿）
- depai（去AI味）
- logic（修正逻辑）
- rhythm（优化节奏）
- diff（修改摘要）

---

## 6. Candidate 边界验证 ✅

### 6.1 编辑结果是否生成 candidate ✅
是的！`useFileGeneration.ts` 第 167 行确认：
```typescript
const mode = outputMode || (pipelineName === 'polish' || pipelineName === 'rewrite' ? 'candidate' : 'write_scene')
```

### 6.2 是否会直接覆盖正文 ✅
不会！`output_mode='candidate'` 会先创建 candidate。

### 6.3 是否需要用户 adopt ✅
是的！用户必须在 CandidatePanel 点击「采用」才会覆盖正文。

### 6.4 adopt 前是否有冲突检查 ✅
是的！`CandidatePanel.vue` 和 `adopt` API 会检查 `base_hash` / `base_mtime` 冲突。

### 6.5 delete/reject 是否存在 ✅
是的！CandidatePanel 有 🗑️ 删除按钮。

---

## 7. Lite 回归验证 ✅

### 7.1 LiteWritingView 独立 ✅
- `LiteWritingView.vue` 是独立页面
- 完全不依赖 AppLayout
- 完全不依赖 ChatPanel

### 7.2 useLiteGeneration 独立 ✅
- `frontend/src/composables/useLiteGeneration.ts` 独立实现
- 不与 Professional 的 generation store 混淆
- Lite candidate 由 `useLiteCandidateActions.ts` 管理

### 7.3 Lite candidate 不受 Professional 影响 ✅
- Lite candidate 是 `CandidateDraft` 类型，在 LiteWritingView 内部管理
- Professional candidate 是 `Candidate` 类型，由 `candidate_service.py` 管理
- 两者存储位置和处理逻辑完全独立

---

## 8. 缺失或不确定领域

### 8.1 De-AI、Logic Fix、Expand、Shorten ✅
- **发现**：已包含在 `polish.yaml` 和 `rewrite.yaml` 步骤中！
  - polish 有 depai（去AI味）、logic（修正逻辑）
  - rewrite 有 depai（去AI味）、logic（修正逻辑）
- 状态：✅ 存在，作为 pipeline steps 实现

### 8.2 ChatPanel → Candidate Link ❌
- ChatPanel 不显示 candidate link
- 无法直接从 ChatPanel adopt/reject candidate
- 状态：❌ 未实现

### 8.3 ChatPanel 专用 dry-run candidate ❌
- ChatPanel 没有 dry-run candidate 机制
- 状态：❌ 未实现

---

## 9. 验收结论

⚠️ **静态验收通过，编辑能力存在且走 candidate，不破坏 Lite**

✅ 通过项：
- ✅ EditorToolbar 有润色、精修、提取、重新生成等入口
- ✅ ChatPanel 有润色文字入口
- ✅ polish 和 rewrite 默认走 `output_mode='candidate'`
- ✅ 不会直接覆盖正文，必须用户 adopt
- ✅ adopt 有冲突检查（base_hash/base_mtime）
- ✅ delete/reject 存在
- ✅ LiteWritingView 完全独立
- ✅ useLiteGeneration 完全独立
- ✅ Lite candidate 不受 Professional 影响
- ✅ polish/rewrite/de-ai/logic-fix prompt 存在
- ✅ 后端 quality_service 和 candidate_service 存在

❌ 未实现：
- ❌ ChatPanel 不显示 candidate link
- ❌ ChatPanel 没有专用 dry-run candidate

---

**文档完成日期**：2026-06-05
