# Phase T4.7 — 原专业版问题修复收口

## 1. 背景

T4.0–T4.6 已完成原专业版现有功能的静态验收：
- T4.0–T4.1：Professional 主流程静态 UI 确认
- T4.2：Lite/Professional 共存与切换基线
- T4.3：编辑能力验收
- T4.4：Workflow/Pipeline/Prompt 模块验收
- T4.5：Story State/Materials/File Service 验收
- T4.6：Batch/Stream/SSE/Task 验收

已确认 Professional 工作台已有基础模块，但多个模块仍存在缺口，且大部分验收为静态验收，未做真实 E2E。

---

## 2. 总体结论

**原专业版基础模块存在，但仍有若干缺口。**

下一步不能直接进入 Scene Plan，必须先确定哪些问题要先修，确保现有功能的稳定性和可用性。

---

## 3. 问题总表

| ID | 问题 | 来源阶段 | 严重程度 | 是否阻断 Scene Plan | 建议处理 |
|----|------|----------|----------|-------------------|----------|
| ISSUE-001 | ChatPanel 没有 candidate link | T4.1.2, T4.3 | P1 | 是 | T4.7.2 最小修复 |
| ISSUE-002 | ChatPanel 未接入 selected text | T4.1.2 | P1 | 是 | T4.7.2 最小修复 |
| ISSUE-003 | ChatPanel 不能 adopt/reject | T4.1.2 | P2 | 否 | 后置 |
| ISSUE-004 | 后端 /chat API 未接入 main | T4.1.2 | P2 | 否 | 后置 |
| ISSUE-005 | Prompt Editor / Variant 未完整实现 | T4.4 | P2 | 否 | 后置 |
| ISSUE-006 | Batch Generate 未完整实现 | T4.6 | P3 | 否 | 后置 |
| ISSUE-007 | Stream 前端实时渲染未完整实现 | T4.6 | P3 | 否 | 后置 |
| ISSUE-008 | Materials API 权限控制未详细验证 | T4.5 | P2 | 否 | 后置 |
| ISSUE-009 | Story State / Materials / FileService 未做真实读写 E2E | T4.5 | P1 | 是 | T4.7.3 dry-run |
| ISSUE-010 | Workflow / Pipeline / Prompt 未做真实运行 E2E | T4.4 | P1 | 是 | T4.7.4 dry-run |
| ISSUE-011 | Professional 主流程没有真实浏览器 E2E | T4.0–T4.2 | P1 | 是 | T4.7.1 dry-run |
| ISSUE-012 | Mode Switch UI 未实现 | T4.2 | P3 | 否 | 后置 |

---

## 4. P0 阻断问题

**暂无 P0 阻断问题。**

现有功能模块完整，可正常启动和基本使用。

---

## 5. P1 高优先级问题

### ISSUE-001：Professional 主流程真实 E2E 未跑
- **状态**：❌
- **建议**：T4.7.1 执行 dry-run
- **说明**：需要在真实浏览器中走一遍 Professional 主流程，确认各模块正常工作

### ISSUE-002：ChatPanel candidate link / selected text 缺口
- **状态**：❌
- **建议**：T4.7.2 最小修复
- **说明**：ChatPanel 作为 Professional 自然语言入口，应该至少支持 selected text 和 candidate link

### ISSUE-003：Story State / Materials 真实读写 E2E 未跑
- **状态**：❌
- **建议**：T4.7.3 dry-run
- **说明**：需要实际读写 story-state 和 materials，验证数据持久化正常

### ISSUE-004：Workflow/Pipeline polish/rewrite E2E 未跑
- **状态**：❌
- **建议**：T4.7.4 dry-run
- **说明**：需要真实运行 polish/rewrite pipeline，验证 candidate 机制正常

---

## 6. P2 体验/完整性问题

### ISSUE-005：Prompt Editor / Variant 未完整实现
- **状态**：❌
- **建议**：后置到 T5
- **说明**：非核心功能，可后续迭代

### ISSUE-006：Batch Generate 未完整实现
- **状态**：❌
- **建议**：后置到 T5
- **说明**：非核心功能，可后续迭代

### ISSUE-007：Stream 前端实时渲染未完整实现
- **状态**：❌
- **建议**：后置到 T5
- **说明**：非核心功能，可后续迭代

### ISSUE-008：ChatPanel adopt/reject 未接入
- **状态**：❌
- **建议**：后置到 T5
- **说明**：可通过 CandidatePanel 完成 adopt/reject，非必须

---

## 7. P3 后续扩展问题

- Mode Switch UI
- Scene Plan
- Confirmation Queue
- Context Retrieval
- 完整 Prompt Editor
- 完整 Batch Generate

---

## 8. Scene Plan 前必须完成的事项

| 任务 | 说明 | 阶段 |
|------|------|------|
| T4.7.1 | Professional 主流程真实 dry-run/E2E | ✅ 必须完成 |
| T4.7.2 | ChatPanel selected text + candidate link 最小修复 | ✅ 必须完成 |
| T4.7.3 | Story State / Materials 读写 dry-run | ✅ 必须完成 |
| T4.7.4 | Workflow/Pipeline polish/rewrite dry-run | ✅ 必须完成 |
| T4.7.5 | 原功能收口复验 | ✅ 必须完成 |

---

## 9. 可后置事项

- Batch Generate 完整实现
- Stream 实时渲染完整实现
- Prompt Editor 可视化编辑器
- Mode Switch UI
- ChatPanel adopt/reject 完整实现

---

## 10. 修复路线建议

### T4.7.1：Professional 主流程 E2E dry-run
- 打开项目
- 新建场景
- 写下一场景
- 润色/精修
- 查看 candidate
- adopt candidate
- 验证文件更新
- SSE 事件监听

### T4.7.2：ChatPanel selected text + candidate link 最小修复
- ChatPanel 发送消息时带上 selected text
- ChatPanel 收到 candidate 时显示 link

### T4.7.3：Story State / Materials read-write dry-run
- 读取现有 story-state
- 更新 story-state
- 保存
- 验证持久化
- Materials 提取和保存

### T4.7.4：Workflow/Pipeline polish/rewrite dry-run
- 运行 polish pipeline
- 验证 candidate 生成
- adopt candidate
- 验证文件更新
- 运行 rewrite pipeline

### T4.7.5：原功能收口复验
- 统一检查以上所有 dry-run 通过
- 验证 Lite 不受影响

---

## 11. 不做的事

- 不修代码（除非 dry-run 发现 blocking bug）
- 不调用真实 LLM（除非 dry-run 必须）
- 不改生产 Prompt
- 不新增 Scene Plan
- 不实现完整 Batch/Stream/PromptEditor

---

## 12. 当前结论

**T4.7 是问题收口，不是功能扩展。**

完成 T4.7 后，应优先执行 T4.7.1–T4.7.4 中的关键 dry-run，再进入 T4.8。

---

**文档完成日期**：2026-06-06
