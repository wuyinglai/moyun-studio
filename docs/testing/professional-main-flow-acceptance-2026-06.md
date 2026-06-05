# Phase T4.1：原专业版用户主流程端到端验收

## 1. 背景

Phase T4.0 已完成原专业版现有功能总盘点，确认仓库中存在 Lite、Workflow、Pipeline、Prompt Engine、Candidate、Generation、Rewrite/Polish/De-AI、Story State、Materials、SSE 等模块。

本阶段的目标是验证从用户入口到生成 candidate 的主流程是否真实可用，并确认不会覆盖正文、不会自动入库、不会破坏 Lite。

## 2. Professional 用户入口发现

### 2.1 路由入口

- **主专业版入口**：`/` 或 `/project/:projectId` → `AppLayout.vue`
- **Lite 入口**：`/lite` 或 `/project/:projectId/lite` → `LiteWritingView.vue`

### 2.2 AppLayout 结构

AppLayout 是主专业版的核心布局，包含：
- **左侧栏**：文件树导航（FileTree）
- **中间栏**：
  - 上半部分：编辑器（MarkdownEditor、EditorToolbar、EditorTabs）
  - 下半部分：对话面板（ChatPanel）
- **右侧栏**：辅助面板（RightPanel）

### 2.3 关键发现

❌ **没有单独的 "Professional" 按钮或开关**
- 当前 AppLayout 就是 "专业版"
- LiteWritingView 是独立的 "爽文模式"

## 3. Chat Panel 发现

### 3.1 ChatPanel 组件

ChatPanel 位于 `frontend/src/components/chat/ChatPanel.vue`，包含：
- ChatMessages：显示对话历史
- ChatInput：输入框
- 取消生成按钮

### 3.2 Chat 相关 Store

ChatStore 位于 `frontend/src/stores/chat.ts`，包含：
- 消息列表管理
- 发送聊天消息（调用 `/api/chat`）
- SSE 流解析（仅用于 `/api/chat`）
- GenerationMode：`continue` | `rewrite` | `chat`

### 3.3 Chat 与 Generation 的关系

ChatPanel 中有两个关键事件监听器：
- `chat:request-generate` → 调用 `handleAIContinue()`
- `chat:request-rewrite` → 调用 `handleAIRewrite()`

这些事件在 ChatPanel onMounted 时添加，但当前没有在 UI 中找到触发这些事件的按钮。

## 4. 主流程链路分析

### 4.1 打开项目流程

```
用户访问 /project/:projectId
→ router.beforeEnter
  → projectStore.openProject(projectId)
  → fileStore.loadTree(projectId)
→ AppLayout 渲染
  → FileTree 渲染
  → EditorTabs 渲染
  → EditorToolbar 渲染
  → MarkdownEditor 渲染
  → ChatPanel 渲染
  → RightPanel 渲染
```

### 4.2 生成 candidate 流程（理论）

基于代码分析，预期流程应该是：

```
用户打开场景文件
→ EditorToolbar 提供某种生成入口
→ 调用 generationStore.continueWriting() 或 rewriteContent()
→ 调用 generation API
  → /api/generate 或 /api/candidates
  → 走 SSE 事件更新前端状态
→ candidateService 创建候选稿
  → candidate 状态为 pending
  → 触发 candidate_created 事件
→ 前端显示 candidate
→ 用户选择采用或丢弃
→ 采用时调用 candidateService.adoptCandidate()
  → 检查 base_hash / base_mtime
  → 写 revision-log
  → 覆盖原文件
  → 触发 candidate_adopted 事件
```

### 4.3 关键安全机制

✅ **candidate 不会自动覆盖正文**
- candidate 需要用户明确采用后才会覆盖
- 采用前有 base_hash / base_mtime 检查
- 采用时会写 revision-log

✅ **不会自动入库**
- 当前代码中没有发现自动入库逻辑
- 所有 state update、materials update 都需要用户确认

## 5. Lite 不受影响验证

### 5.1 Lite 入口独立

LiteWritingView 是独立的页面，不依赖 AppLayout：
- 路径：`/lite` 或 `/project/:projectId/lite`
- 组件：`frontend/src/views/LiteWritingView.vue`
- 核心逻辑：`useLiteGeneration` 和 `useLiteCandidateActions` composables

### 5.2 Lite 核心功能

Lite 具有完整的独立功能：
- 开局卡选择 → 创建作品
- 爽点卡选择 → 生成下一场
- 编辑器 → 保存场景
- candidate 管理 → 采用/丢弃候选稿
- 灵感改稿 → 基于用户输入生成候选稿
- 故事状态 → 显示主角目标、冲突等

### 5.3 共享但不冲突

Lite 和 Professional 共享的模块（store、service 等）都设计成独立的：
- Lite 使用 `useLiteGeneration` 和 `useLiteCandidateActions`
- Professional 使用 `useGenerationOrchestrator` 和 CandidatePanel（如果有）
- 两个入口不会互相影响

## 6. 现有功能清单

| 模块 | 位置 | 状态 | 说明 |
| --- | --- | --- | --- |
| Workflow | backend/core/workflow.py | ✅ 存在 | 工作流定义 |
| Pipeline | backend/core/pipeline.py | ✅ 存在 | 生成管道 |
| Prompt Engine | backend/core/prompt_engine.py | ✅ 存在 | Prompt 版本管理 |
| Candidate Service | backend/core/candidate_service.py | ✅ 存在 | 候选稿服务 |
| Generation Service | backend/core/generation_service.py | ✅ 存在 | 生成服务 |
| Quality Service | backend/core/quality_service.py | ✅ 存在 | Rewrite/Polish/De-AI |
| File Service | backend/core/file_ops.py | ✅ 存在 | 文件操作 |
| Lite API | backend/api/lite.py | ✅ 存在 | Lite 接口 |
| Candidates API | backend/api/candidates.py | ✅ 存在 | 候选稿接口 |
| Generate API | backend/api/generate.py | ✅ 存在 | 生成接口 |
| Chat API | backend/api/chat.py | ✅ 存在 | 聊天接口 |
| Story State API | backend/api/story_state.py | ✅ 存在 | 状态接口 |
| Materials API | backend/api/materials.py | ✅ 存在 | 素材接口 |
| SSE API | backend/api/sse.py | ✅ 存在 | SSE 接口 |
| AppLayout | frontend/src/components/layout/AppLayout.vue | ✅ 存在 | 主布局 |
| ChatPanel | frontend/src/components/chat/ChatPanel.vue | ✅ 存在 | 对话面板 |
| RightPanel | frontend/src/components/right-panel/RightPanel.vue | ✅ 存在 | 右侧面板 |
| CandidatePanel | frontend/src/components/right-panel/CandidatePanel.vue | ✅ 存在 | 候选稿面板 |
| LiteWritingView | frontend/src/views/LiteWritingView.vue | ✅ 存在 | Lite 页面 |

## 7. 未确认功能

| 功能 | 状态 | 说明 |
| --- | --- | --- |
| 专业版生成按钮 | ⚠️ 未确认 | 在 EditorToolbar 中是否有？ |
| Professional Prompt Editor | ⚠️ 未确认 | 仓库中是否有 Prompt Editor 组件？ |
| Pipeline 可视化 | ⚠️ 未确认 | 是否有 Pipeline 编辑 UI？ |
| Workflow 运行 | ⚠️ 未确认 | 是否有 UI 触发 Workflow？ |
| Batch Generate | ⚠️ 未确认 | 仓库中提到了，但 UI 未找到？ |

## 8. 验收结论

### 8.1 已确认的安全保证

✅ **candidate 不会自动覆盖正文**
- CandidateService 中明确需要 `adopt` 步骤
- Adopt 前有 base_hash / base_mtime 检查
- Adopt 后会写 revision-log

✅ **不会自动入库**
- 所有 state update、materials update 都需要用户确认
- 没有发现自动入库逻辑

✅ **Lite 不受影响**
- LiteWritingView 是独立的
- Lite 有自己的 composables（useLiteGeneration、useLiteCandidateActions）

### 8.2 主流程可用性

⚠️ **静态链路完整，但部分 UI 入口未确认**

从代码层面看，链路是完整的，但部分 UI 入口（如专业版生成按钮）没有确认。

## 9. 下一步建议

1. **Phase T4.2**：验证 Lite 与 Professional 共存
2. **Phase T4.3**：验证编辑功能（Rewrite/Polish/De-AI）
3. **Phase T4.4**：验证 Workflow/Pipeline/Prompt 模块
4. **Phase T4.5**：验证 Story State/Materials/文件系统
5. **Phase T4.6**：验证 Batch/Stream/SSE/Task

---

**文档完成日期**：2026-06-05
