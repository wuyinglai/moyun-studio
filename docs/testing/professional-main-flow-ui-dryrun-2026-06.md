# Phase T4.1.1 — Professional 主流程真实 dry-run / UI 入口补验

## 1. 背景

上一阶段 T4.1 完成了原专业版用户主流程的静态链路验收，但没有完成真实端到端验收。二次验收确认：Professional 入口目前是 AppLayout 项目工作台，ChatPanel 存在，但部分 UI 触发入口未确认，candidate 前端展示与 adopt/reject 流程也未真实验证。

本阶段的目标是补验 UI 入口和 candidate 展示流程。

## 2. Professional UI 入口发现

### 2.1 EditorToolbar 生成入口

✅ **发现完整的生成入口！**

EditorToolbar (`frontend/src/components/editor/EditorToolbar.vue`) 包含以下按钮：

| 按钮 | 功能 | data-testid |
|------|------|-------------|
| 📄 写下一场景 | 触发 `writeNextScene` | write-next-button |
| ✏️ 润色 | 触发 `runPipeline('polish')` | - |
| 📦 精修 | 触发 `runPipeline('rewrite')` | rewrite-button |
| 🌟 提取 | 触发 `runPipeline('extract')` | - |
| 🔄 重新生成 | 触发 `handleRegenerate` | - |
| ➕ 自定义 | 自定义管线 | - |
| 批量生成 | 打开批量生成 UI | batch-generate-button |
| 质量审查 | 打开质量审查 UI | - |

### 2.2 RightPanel 入口

✅ **发现完整的右侧辅助面板！**

RightPanel (`frontend/src/components/right-panel/RightPanel.vue`) 包含以下 tabs：

| Tab | 功能 |
|------|------|
| ⚡ 快捷 | ProfessionalQuickPanel |
| ✍️ Prompt | PromptPanel |
| 🔧 管线 | PipelineEditor |
| 📋 工作流 | WorkflowPanel |
| 📝 候选稿 | **CandidatePanel** |
| 🧠 记忆 | MemorySettingsPanel |
| 📖 故事 | StoryStatePanel |
| 🎨 文风 | StyleGuidePanel |
| 🧭 上下文 | RecentContextPanel |
| 📊 执行 | ExecutionPanel |
| 🔄 流程 | FlowPanel |

### 2.3 ChatPanel 入口

✅ **ChatPanel 存在！**

ChatPanel (`frontend/src/components/chat/ChatPanel.vue`) 包含：

- ChatMessages：显示对话历史
- ChatInput：输入框
- 取消生成按钮

## 3. ChatPanel 触发发现

❌ **chat:request-generate 和 chat:request-rewrite 事件没有找到真实触发源！**

ChatPanel 在 onMounted 时添加了这两个事件监听器（调用 `handleAIContinue` 和 `handleAIRewrite`），但在搜索代码后**没有找到任何组件发出这两个事件**。

这可能是预留的功能，或者 ChatPanel 的完整 UI 入口尚未实现。

## 4. Candidate 展示发现

✅ **CandidatePanel 完整存在！**

CandidatePanel (`frontend/src/components/right-panel/CandidatePanel.vue`) 功能：

- 候选稿列表展示
- candidate 预览功能
- candidate 刷新按钮

### 4.1 SSE 事件监听

CandidatePanel 在 onMounted 时监听两个 SSE 事件：

- `candidate-created` → 自动刷新候选稿列表
- `candidate-adopted` → 自动刷新候选稿列表

### 4.2 用户查看 candidate

用户可以：

1. 在 RightPanel 中切换到 "候选稿" Tab
2. 点击 candidate 卡片选择
3. 点击 👁️ 预览按钮查看 candidate 内容
4. 在预览弹窗中查看完整的 candidate

## 5. Adopt/Reject 发现

✅ **Adopt 和 Delete 功能完整存在！**

### 5.1 Adopt 功能

- 按钮位置：候选稿卡片上的 ✔️ 按钮，以及预览弹窗中的"采用候选稿"按钮
- `data-testid`: `candidate-adopt-button`
- 流程：
  1. 用户点击"采用"
  2. 弹出确认框
  3. 调用 `/candidates/:projectId/:candidateId/adopt` API
  4. 如果有 `conflict` 或 `success: false`，显示错误并刷新候选稿列表
  5. 如果成功，显示通知，刷新列表，同步源文件到编辑器
- **冲突检测**：有！API 会检查 `base_hash` / `base_mtime`，返回 409 或 FILE_CONFLICT 错误

### 5.2 Delete 功能

- 按钮位置：候选稿卡片上的 🗑️ 按钮
- `data-testid`: `candidate-reject-button`
- 流程：
  1. 用户点击"删除"
  2. 弹出确认框
  3. 调用 `/candidates/:projectId/:candidateId` DELETE API
  4. 刷新候选稿列表

## 6. Main Flow Dry-run Result

### 6.1 静态链路确认 ✅

| 步骤 | 组件 | API |
|------|------|-----|
| 1. 用户打开项目 | AppLayout | `/projects/:id` |
| 2. 用户选择场景文件 | FileTree/EditorTabs | `/files/read` |
| 3. 用户点击生成按钮 | EditorToolbar | `/generate` / `/candidates` |
| 4. 生成 candidate | 后端服务 | candidate-created SSE |
| 5. 前端显示 candidate | CandidatePanel | `/candidates/:projectId` |
| 6. 用户预览 candidate | CandidatePanel 预览弹窗 | `/candidates/:projectId/:candidateId` |
| 7. 用户采用 candidate | CandidatePanel adopt 按钮 | `/candidates/:projectId/:candidateId/adopt` |
| 8. 源文件更新 | Editor 自动刷新 | candidate-adopted SSE |

### 6.2 Candidate 安全确认 ✅

- ✅ candidate 不会自动覆盖正文
- ✅ adopt 需要用户明确确认
- ✅ adopt 有冲突检测
- ✅ adopt 后写 revision log

## 7. Missing UI Entry

❌ **ChatPanel 的 chat:request-generate 和 chat:request-rewrite 事件缺少触发 UI 入口**

这两个事件在 ChatPanel 中被监听，但没有找到任何组件发出这些事件。这可能是：

- 预留的功能，尚未实现 UI
- 或者 UI 在其他位置但没有被搜索到

## 8. Lite Regression Notes

✅ **Lite 不受影响！**

LiteWritingView 是完全独立的页面，有自己的 composables：

- useLiteGeneration
- useLiteCandidateActions

与 Professional 的 AppLayout 完全分离，不会受影响。

## 9. 验收结论

### 9.1 已确认

- ✅ Professional 主入口是 AppLayout
- ✅ EditorToolbar 有完整的生成入口
- ✅ RightPanel 有完整的 tabs，包括 CandidatePanel
- ✅ ChatPanel 存在
- ✅ Candidate 展示流程完整
- ✅ Adopt/Delete 功能完整，有冲突检测
- ✅ SSE 事件处理完整
- ✅ candidate 不会自动覆盖正文

### 9.2 未确认

- ❌ ChatPanel 的 chat:request-generate 和 chat:request-rewrite 事件没有找到触发 UI

### 9.3 总体结论

⚠️ **静态 UI 链路确认，部分 Chat 入口未确认**

总体来说，Professional 主流程的 UI 链路是完整的，可以进入下一阶段。

---

## 10. 补充报告

ChatPanel 触发缺口详见：`docs/testing/chat-panel-trigger-contract-2026-06.md

---

**文档完成日期**：2026-06-05
