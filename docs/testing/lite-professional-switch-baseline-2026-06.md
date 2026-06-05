# Phase T4.2 — Lite / Professional 共存与切换基线验收

## 1. 背景
当前 Moyun Studio 有三个主要入口：
1. **Lite 入口**：快速生成，无大纲创作
2. **Professional 入口**：完整功能，专业写作
3. **ChatPanel**：专业版自然语言入口

本阶段任务是验证这三个入口能共存，不互相破坏，并定义 Lite ↔ Professional 切换的安全边界。

---

## 2. 路由发现

| 路由 | 组件 | 模式 | 说明 |
|------|------|------|------|
| `/lite` | LiteWritingView | Lite | 无项目入口 |
| `/project/:projectId/lite` | LiteWritingView | Lite | 带项目入口 |
| `/` | AppLayout | Professional | 首页 |
| `/project/:projectId` | AppLayout | Professional | 项目首页 |
| `/project/:projectId/file/*` | AppLayout | Professional | 文件编辑器 |

---

## 3. 入口发现

### 3.1 Lite 入口 ✅

**组件**：`LiteWritingView.vue`

**特点**：
- ✅ 独立页面，完全不依赖 AppLayout
- ✅ 使用独立 composables：`useLiteGeneration`、`useLiteCandidateActions`、`useLitePrefetch`
- ✅ 有自己的 selected-card（idea-cards）
- ✅ 有章节列表（chapter-list）
- ✅ 有独立编辑器
- ✅ 使用 ErrorBoundary 包裹

**生成按钮**：
- 续写按钮（基于 selected-card）
- 批量生成
- 自定义

### 3.2 Professional 入口 ✅

**组件**：`AppLayout.vue`

**布局**：
- 左栏：FileTree（文件树）
- 中栏：EditorTabs + EditorToolbar + MarkdownEditor
- 底部：ChatPanel
- 右栏：RightPanel（包含 CandidatePanel）

**EditorToolbar 按钮**：
- 📄 写下一场景
- ✏️ 润色
- 📦 精修
- 🌟 提取
- 🔄 重新生成
- ➕ 自定义
- 批量生成
- 质量审查

**RightPanel Tabs**：
- ⚡ 快捷
- ✍️ Prompt
- 🔧 管线
- 📋 工作流
- 📝 候选稿
- 🧠 记忆
- 📖 故事
- 🎨 文风
- 🧭 上下文
- 📊 执行
- 🔄 流程

### 3.3 ChatPanel 入口 ✅

**组件**：`ChatPanel.vue`（仅在 AppLayout 中）

**欢迎建议**：
- ✏️ 续写场景 → 触发 `chat:request-generate` → `generationStore.continueWriting`
- 🪶 润色文字 → 触发 `chat:request-rewrite` → `generationStore.rewriteContent`
- 💡 讨论情节 → 普通聊天

**特点**：
- ✅ 使用独立事件监听机制
- ✅ 不使用 Lite 的 composables
- ✅ 触发 generationStore（Professional 专用）

---

## 4. Candidate 共用边界

### 4.1 Lite Candidate
- **组件**：`useLiteCandidateActions` composable
- **结构**：`CandidateDraft` 类型
- **特点**：内嵌在 LiteWritingView 中

### 4.2 Professional Candidate
- **组件**：`CandidatePanel`（RightPanel Tab）
- **Store**：`generation.ts`
- **特点**：独立面板，支持 adopt/reject

### 4.3 Candidate 安全机制 ✅
- ✅ adopt 前有冲突检查（base_hash / base_mtime）
- ✅ adopt 后写 revision log
- ✅ delete/reject 存在
- ✅ 不静默覆盖正文

### 4.4 ChatPanel Candidate
- ChatPanel 触发的 generation/rewrite 会进入 Professional candidate 机制
- 不生成独立的 ChatPanel candidate

---

## 5. 模式切换基线设计

### 5.1 Lite → Professional 升级路径

**触发方式**：
- 用户从 `/project/:projectId/lite` 导航到 `/project/:projectId`
- 用户从 LiteWritingView 点击"进入专业模式"按钮（待实现）

**数据保留**：
- ✅ 项目配置（projectStore）共用
- ✅ 文件系统（fileStore）共用
- ✅ story-state（如果存在）
- ✅ style-guide（如果存在）
- ⚠️ recent-context（可能需要单独迁移）
- ❌ Lite selected-card（不迁移，Professional 用 EditorToolbar）

**切换规则**：
- ❌ 不自动覆盖正文
- ❌ 不自动入库
- ❌ 不自动更新 story-state
- ✅ 保留所有已打开的文件和编辑状态
- ✅ 保留所有已创建的 candidate

### 5.2 Professional → Lite 降级路径

**触发方式**：
- 用户从 `/project/:projectId` 导航到 `/project/:projectId/lite`
- 用户从 AppLayout 点击"进入爽文模式"按钮（待实现）

**数据保留**：
- ✅ 项目配置（projectStore）共用
- ✅ 文件系统（fileStore）共用
- ⚠️ recent-context（可能需要单独迁移）
- ⚠️ style-guide（可能不适用）
- ❌ EditorToolbar 生成配置（不迁移）
- ❌ RightPanel 配置（不迁移）

**切换规则**：
- ❌ 不自动覆盖正文
- ❌ 不自动入库
- ❌ 不自动更新 story-state
- ✅ 保留所有场景文件
- ✅ 保留所有已创建的 candidate（但 Lite 不显示）

### 5.3 切换安全边界

无论从 Lite → Professional 还是 Professional → Lite：
- ❌ 不得自动覆盖正文
- ❌ 不得自动入库
- ❌ 不得自动更新 story-state
- ❌ 不得自动接受 rewrite suggestion
- ❌ 不得自动确认 Plot Debt
- ✅ 必须保留文件系统的完整性
- ✅ 必须保留 candidate 的完整性

---

## 6. 静态验收结果

### 6.1 路由隔离 ✅
- ✅ Lite 有独立路由
- ✅ Professional 有独立路由
- ✅ 路由互不干扰

### 6.2 组件隔离 ✅
- ✅ LiteWritingView 是独立页面
- ✅ AppLayout 是独立页面
- ✅ 没有交叉导入

### 6.3 Store 隔离 ✅
- ✅ Lite 使用独立 composables
- ✅ Professional 使用 generationStore
- ✅ ChatPanel 使用 generationStore
- ✅ 状态不混淆

### 6.4 Candidate 隔离 ✅
- ✅ Lite candidate 在 LiteWritingView 内部
- ✅ Professional candidate 在 CandidatePanel
- ✅ 两者不冲突
- ✅ ChatPanel 复用 Professional candidate

### 6.5 ChatPanel 隔离 ✅
- ✅ ChatPanel 仅在 AppLayout 中
- ✅ 不出现在 LiteWritingView
- ✅ 不干扰 Lite

---

## 7. 仍未实现

### 7.1 模式切换 UI
- ❌ 没有"进入专业模式"按钮
- ❌ 没有"进入爽文模式"按钮
- ❌ 没有切换确认对话框

### 7.2 数据迁移
- ❌ recent-context 未设计迁移方案
- ❌ style-guide 未设计迁移方案
- ❌ selected-card 未设计迁移方案

### 7.3 状态同步
- ❌ Lite 和 Professional 状态未设计同步机制
- ❌ candidate 状态未设计同步机制

---

## 8. 验收结论

⚠️ **静态验收通过，模式切换 UI 尚未实现**

### 已确认
- ✅ Lite 和 Professional 路由完全隔离
- ✅ 组件完全独立
- ✅ Store/composables 完全独立
- ✅ Candidate 机制隔离
- ✅ ChatPanel 仅在 Professional 中
- ✅ 不互相破坏

### 未实现
- ❌ 模式切换 UI 入口
- ❌ 数据迁移机制
- ❌ 状态同步机制

---

## 9. 后续建议

Phase T4.2.1：实现模式切换 UI 入口
- 在 LiteWritingView 添加"进入专业模式"按钮
- 在 AppLayout 添加"进入爽文模式"按钮
- 设计切换确认对话框

Phase T4.2.2：设计数据迁移方案
- recent-context 迁移
- style-guide 迁移
- selected-card 迁移

Phase T4.2.3：实现状态同步
- candidate 同步
- story-state 同步

---

**文档完成日期**：2026-06-05
