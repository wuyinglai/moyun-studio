# Phase T4.1.2 — ChatPanel 触发契约与缺口确认

## 1. 背景

Phase T4.1.1 已完成 Professional 主流程静态 UI 确认，但发现 ChatPanel 的 chat:request-generate 和 chat:request-rewrite 事件缺少触发源。

本阶段的目标是：
- 确认 ChatPanel 目前能做什么、不能做什么
- 明确缺口
- 定义建议的契约

---

## 2. 当前代码发现

| 能力 | 是否存在 | 代码位置 | 说明 |
|---|---|---|---|
| **ChatPanel UI** | ✅ 是 | `frontend/src/components/chat/ChatPanel.vue` | 完整的聊天面板，含消息展示、输入框、欢迎建议 |
| **ChatInput** | ✅ 是 | `frontend/src/components/chat/ChatInput.vue` | 文本输入，支持 Enter 发送，Shift+Enter 换行 |
| **ChatMessages** | ✅ 是 | `frontend/src/components/chat/ChatMessages.vue` | 消息展示列表，含思考指示器和欢迎建议 |
| **ChatMessage** | ✅ 是 | `frontend/src/components/chat/ChatMessage.vue` | 单条消息组件 |
| **ChatStore** | ✅ 是 | `frontend/src/stores/chat.ts` | 状态管理，支持 sendMessage |
| **/chat API 路由定义** | ✅ 是 | `frontend/src/shared/api/routes.ts` (第 64 行) | API_ROUTES.chat = '/chat' |
| **/chat 后端实现** | ❌ 否 | `backend/api/__init__.py` (main.py 路由列表) | main.py 中没有 include chat router |
| **context_file 传递** | ✅ 是 | ChatPanel.vue 第 131 行 | sendMessage 时传 fileStore.currentFile?.path |
| **project_id 传递** | ✅ 是 | ChatPanel.vue 第 130 行 | sendMessage 时传 projectStore.currentProject?.id |
| **selected text 支持** | ❌ 否 | 未发现 | 没有看到 selected text 相关传递 |
| **active candidate 支持** | ❌ 否 | 未发现 | 没有看到 candidate 相关集成 |
| **chat:request-generate 监听** | ✅ 是 | ChatPanel.vue 第 182 行 | window.addEventListener，调用 handleAIContinue |
| **chat:request-rewrite 监听** | ✅ 是 | ChatPanel.vue 第 183 行 | window.addEventListener，调用 handleAIRewrite |
| **chat:request-generate dispatch 源** | ❌ 否 | 全局搜索，只有 ChatPanel 在监听 | 没有其他地方 dispatch 该事件 |
| **chat:request-rewrite dispatch 源** | ❌ 否 | 同上 | 没有其他地方 dispatch 该事件 |
| **Chat 回复生成 candidate** | ❌ 否 | 未发现 | Chat API 回复只是纯文本，不生成 candidate |
| **Chat 展示 candidate link** | ❌ 否 | 未发现 | ChatPanel 没有 candidate 相关展示 |
| **Chat 发起 adopt/reject** | ❌ 否 | 未发现 | 没有该功能 |

---

## 3. 当前缺口

### 缺口 1：欢迎建议只是纯文本聊天，不触发 generation

目前的欢迎建议按钮（"帮我续写当前场景"、"帮我润色这段文字"）点击后只是调用了 sendMessage，发送纯文本聊天消息，而不是触发生成流程（chat:request-generate 或 chat:request-rewrite）！

### 缺口 2：chat:request-generate 和 chat:request-rewrite 没有触发源

这两个事件作为 window 事件监听器存在，但没有找到任何 UI 或组件 dispatch 它们！

### 缺口 3：没有 selected text 集成

ChatPanel 发送消息时，没有利用当前编辑器选中的文本！

### 缺口 4：没有 candidate 集成

ChatPanel 不展示 candidate，不发起 adopt/reject，也不能从 candidate 触发聊天！

### 缺口 5：/chat 后端路由未实现

main.py 的路由列表里没有包含 chat 模块！

---

## 4. 建议契约

### 意图与事件映射

| 用户意图 | 事件名 | 目标 | 是否生成 candidate |
|---|---|---|---|
| 续写当前场景 | chat:request-generate | continueWriting | ✅ 是 |
| 重写选中文本 | chat:request-rewrite | rewriteContent | ✅ 是 |
| 润色选中文本 | chat:request-polish | 调用 quality pipeline | ✅ 是 |
| 去 AI 味 | chat:request-deai | 调用 quality pipeline | ✅ 是 |
| 逻辑修复 | chat:request-logic-fix | 调用 quality pipeline | ✅ 是 |
| 纯聊天 | chat:request-chat | sendMessage | ❌ 否 |

### Chat 消息结构建议

```json
{
  "type": "suggestion",
  "intent": "continue",
  "suggestion": {
    "type": "candidate",
    "id": "...",
    "path": "..."
  }
}
```

### 安全边界

ChatPanel **不得**：
- ❌ 自动覆盖正文
- ❌ 自动更新 story-state
- ❌ 自动入库
- ❌ 自动接受 rewrite suggestion
- ❌ 自动确认 Plot Debt
- ❌ 打印 API Key

---

## 5. 后续建议

如果缺口确认属实，下一阶段可进行：

**T4.1.3：ChatPanel → Candidate/Workflow 触发 dry-run 修复**

---

## 6. 验收结论

⚠️ **ChatPanel 目前是纯聊天面板，缺少与 generation/candidate 集成的触发入口**

- ✅ ChatPanel UI 完整
- ✅ 支持 project_id 和 context_file 传递
- ❌ chat:request-generate/rewrite 没有触发源
- ❌ 欢迎建议只是纯聊天，不触发生成
- ❌ 没有 selected text 集成
- ❌ 没有 candidate 集成

---

**文档完成日期**：2026-06-05
