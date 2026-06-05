# Phase T4.1.3 — ChatPanel → Candidate/Workflow 触发 dry-run 修复

## 1. 背景
Phase T4.1.2 已确认 ChatPanel 存在关键缺口：
- 欢迎建议只是纯文本聊天，不触发 generation
- chat:request-generate 和 chat:request-rewrite 有 listener，但没有 dispatch 源

本阶段任务是打通最小触发链路，让 ChatPanel 欢迎建议能触发生成/改写机制。

## 2. 执行内容

### 2.1 修改了哪些入口
- [frontend/src/components/chat/ChatPanel.vue](file:///d:/newmoyun/frontend/src/components/chat/ChatPanel.vue#L106-L119)：修改了 `handleSuggestion` 函数

### 2.2 Intent 分流逻辑
| 欢迎建议 | Intent | 触发事件 | 实现方式 |
|---------|--------|---------|---------|
| ✏️ 续写场景 | continue_current_scene | chat:request-generate | 复用已有 listener → handleAIContinue → generationStore.continueWriting |
| 🪶 润色文字 | polish_selection | chat:request-rewrite | 复用已有 listener → handleAIRewrite → generationStore.rewriteContent |
| 💡 讨论情节 | chat_discussion | - | 保持普通 sendMessage |

### 2.3 事件流转路径
1. 用户点击欢迎建议 → handleSuggestion
2. 根据内容匹配 intent → dispatch chat:request-generate / chat:request-rewrite
3. ChatPanel 的 onMounted 监听器捕获事件
4. 调用 handleAIContinue / handleAIRewrite
5. 最终调用 generationStore 的对应方法

## 3. 安全边界检查
✅ 不自动覆盖正文（generationStore 已有 candidate 机制）
✅ 不自动入库
✅ 不调用真实 LLM（除非用户已配置并触发）
✅ 不修改生产 Prompt
✅ 不修改正式 scene/settings

## 4. Candidate 机制
- ChatPanel 触发的 generation/rewrite 会直接进入现有 candidate 机制
- CandidatePanel 可以正常查看和 adopt
- 符合原有安全边界，不静默覆盖正文

## 5. 仍未解决的问题
1. ❌ 未接入 selected text
2. ❌ 未接入 ChatPanel → Candidate link 展示
3. ❌ 未接入 ChatPanel 发起 adopt/reject
4. ❌ 后端 /chat API 未接入 main.py
5. ❌ 没有 ChatPanel 侧专用的 dry-run candidate 机制

## 6. 验收状态
⚠️ 部分实现（已打通欢迎建议 → generation/candidate 触发链路）

---
**文档完成日期**：2026-06-05
