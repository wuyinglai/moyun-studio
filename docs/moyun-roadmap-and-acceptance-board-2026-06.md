# Moyun Studio Roadmap and Acceptance Board 2026-06

## 1. Overview

| 项目 | 当前进度 | 说明 |
| ---- | ---- | ---- |
| v0.1.x 总体进度 | ~88% | Lite Prompt 优化 + D7 质量引擎 MVP |
| Lite Prompt 优化 | ~70% | 快速生成已可用 |
| 专业版设计准备 | ~58% | T4 问题清单完成，准备修复 |
| Python + LLM 写作质量与一致性引擎 | ~65% | D7 MVP 链路完成 |

---

## 2. Phase T3-A: Lite Prompt 快速迭代线

| 阶段 | 状态 | 说明 | 验收方式 |
| ---- | ---- | ---- | ---- |
| Phase T3-A | ✅ | Lite Prompt 初步完成 | - |

---

## 3. Phase T3-B: Lite Prompt 深度优化线

| 阶段 | 状态 | 说明 | 验收方式 |
| ---- | ---- | ---- | ---- |
| Phase T3-B.1 | ✅ | 真实场景深度续写测试 | - |
| Phase T3-B.2 | ✅ | 长篇稳定性测试 | - |
| Phase T3-B.3 | ✅ | 质量评分体系验证 | - |

---

## 4. Phase T3-C: 专业版写作 Prompt 实验线

| 阶段 | 状态 | 说明 | 验收方式 |
| ---- | ---- | ---- | ---- |
| Phase T3-C.1 | ✅ | 专业版 Prompt 实验设计 | - |
| Phase T3-C.2 | ✅ | 专业版 Prompt 迭代验证 | - |
| Phase T3-C.3 | ✅ | 专业版 Prompt 稳定化 | - |

---

## 5. Phase T3-D: Python + LLM 写作质量与一致性引擎线

| 阶段 | 状态 | 说明 | 验收方式 |
| ---- | ---- | ---- | ---- |
| Phase T3-D7.3 | ✅ | LLM Review + 覆盖校验 | ✅ | 定义 review schema、校验覆盖率、完成全量 14 条验证 | 功能验收 |
| Phase T3-D7.4 | ✅ | State Snapshot MVP | ✅ | 提取事实、生成 snapshot JSON 和 Markdown 报告 | 功能验收 |
| Phase T3-D7.5 | ✅ | Plot Debt 表 MVP | ✅ | 识别伏笔、承诺、威胁、开放问题，生成候选债务表 | 功能验收 |
| Phase T3-D7.5.1 | ✅ | Plot Debt 实体提取增强 | ✅ | 增强实体提取逻辑，提取玄黄秘录、玄铁令牌等关键实体 | 功能验收 |
| Phase T3-D7.5.2 | ✅ | Plot Debt 实体提取降噪 | ✅ | 过滤噪声实体，确保实体准确性优先于填充率 | 功能验收 |
| Phase T3-D7.6 | ✅ | 局部 Rewrite Engine MVP | ✅ | 从 Plot Debt 生成重写建议（dry-run），不调用 LLM，不修改正文 | 功能验收 |
| Phase T3-D7.7 | ✅ | D7 总体验收与流水线收口 | ✅ | 全链路总体验收，不新增功能，准备进入下一阶段 | 文档验收 |
| Phase T3-D7.8 | ✅ | D7 Pipeline 一键 dry-run | ✅ | 整合已有脚本，一条命令跑通 D7 全链路，不调用新 LLM | 功能验收 |
| Phase T3-D7.8.1 | ✅ | Pipeline summary 统计修正 + Diff 噪声记录 | ✅ | 修正 candidates 统计为 14，添加 known_diff_noise 字段，记录已知噪声实体 | 功能验收 |
| Phase T4 | Professional Prompt 专业版写作流程 | ⏳ | - |
| Phase T4.0 | 原专业版现有功能总盘点 | ✅ | 盘点原专业版功能，为验收做准备 | 文档验收 |
| Phase T4.1 | 原专业版用户主流程端到端验收 | ⚠️ | 静态链路验收完成，部分 UI 入口未确认 | 文档验收 |
| Phase T4.1.1 | Professional 主流程真实 dry-run / UI 入口补验 | ⚠️ | 静态 UI 链路确认，部分 Chat 入口未确认 | 文档验收 |
| Phase T4.1.2 | ChatPanel 触发契约与缺口确认 | ⚠️ | 静态 UI 链路确认，部分 Chat 入口未确认 | 文档验收 |
| Phase T4.1.3 | ChatPanel → Candidate/Workflow 触发 dry-run 修复 | ⚠️ | 已打通欢迎建议 → generation/candidate 触发链路 | 文档验收 |
| Phase T4.2 | Lite / Professional 共存与切换基线验收 | ⚠️ | 静态验收通过，模式切换 UI 尚未实现 | 文档验收 |
| Phase T4.3 | 原专业版编辑能力验收 | ⚠️ | 静态验收通过，编辑能力存在且走 candidate，不破坏 Lite | 文档验收 |
| Phase T4.4 | Workflow / Pipeline / Prompt 模块验收 | ⚠️ | 静态验收通过，核心模块完整，Prompt Editor/Variant 未完整实现 | 文档验收 |
| Phase T4.5 | Story State / Materials / 文件系统验收 | ⚠️ | 静态验收通过，核心能力完整且安全，不自动覆盖正文 | 文档验收 |
| Phase T4.6 | Batch / Stream / SSE / Task 验收 | ⚠️ | 静态验收通过，SSE/Task完整，Batch/Stream部分未实现 | 文档验收 |
| Phase T4.7 | 原专业版问题修复收口 | ⚠️ | 问题清单与修复计划完成，修复待执行 | 文档验收 |
| Phase T4.7.1 | Professional 主流程 E2E dry-run | ⚠️ | 基础 UI 验证通过，candidate 链路静态验证通过，需真实 LLM 完整验证 |
| Phase T4.7.1a | Professional candidate 链路 dry-run 补验 | ❌ | T4.7.1a-1: Locator 稳定性验证通过，所有 locator 稳定找到。等待行为验证 (preview/delete/adopt/conflict/SSE) | 测试验收 |
| Phase T4.7.2 | ChatPanel selected text + candidate link 最小修复 | ⏳ | - |
| Phase T4.7.3 | Story State / Materials read-write dry-run | ⏳ | - |
| Phase T4.7.4 | Workflow/Pipeline polish/rewrite dry-run | ⏳ | - |
| Phase T4.7.5 | 原功能收口复验 | ⏳ | - |
| Phase T4.8 | Scene Plan schema + validator dry-run | ⏳ | - |
| Phase T4.9 | Selected-card → Scene Brief / Scene Plan | ⏳ | - |
| Phase T4.10 | Professional Draft Prompt 模板 | ⏳ | - |
| Phase T4.11 | Professional 接入 D7 Pipeline | ⏳ | - |
| Phase T4.12 | 用户确认清单 MVP | ⏳ | - |
| Phase T5 | 输出质量评分表 | ⏳ | - |
| Phase T6 | 候选稿采用/回滚测试 | ⏳ | - |
| Phase T7 | 长篇连续 10 场生成测试 | ⏳ | - |
| Phase T8 | 错误/超时/断流测试 | ⏳ | - |
| Phase T9 | 真实用户视角测试报告 | ⏳ | - |

### 5.2 Phase T3-B 子任务状态详情

| 真实功能测试线 Phase T3-B 子任务状态更新：

| 子任务 | 状态 | 日期 | 说明 |
|--------|------|------|------|
| Phase T3-B.1a | ✅ | 2026-06-03 | Lite Prompt 初步完成 |
| Phase T3-B.1b | ✅ | 2026-06-03 | Lite Prompt 实验设计 |
| Phase T3-B.1c | ✅ | 2026-06-03 | Lite Prompt 迭代验证 |
| Phase T3-B.2a | ✅ | 2026-06-04 | 真实场景深度续写测试 |
| Phase T3-B.2b | ✅ | 2026-06-04 | 长篇稳定性测试 |
| Phase T3-B.3a | ✅ | 2026-06-04 | 质量评分体系验证 |
| Phase T3-D7.3a | ✅ | 2026-06-04 | Review schema + validator |
| Phase T3-D7.3b | ✅ | 2026-06-04 | Review Prompt 契约 |
| Phase T3-D7.3c-b | ✅ | 2026-06-04 | 真实 LLM Review 3 条 |
| Phase T3-D7.3c-b1 | ✅ | 2026-06-04 | LLM endpoint 配置探针 |
| Phase T3-D7.3d | ✅ | 2026-06-04 | 真实 LLM Review 14 条 |
| Phase T3-D7.4 | ✅ | 2026-06-04 | State Snapshot MVP |
| Phase T3-D7.5 | ✅ | 2026-06-04 | Plot Debt 表 MVP |
| Phase T3-D7.5.1 | ✅ | 2026-06-05 | Plot Debt 实体提取增强 |
| Phase T3-D7.5.2 | ✅ | 2026-06-05 | Plot Debt 实体提取降噪 |
| Phase T3-D7.6 | ✅ | 2026-06-05 | 局部 Rewrite Engine MVP |
| Phase T3-D7.7 | ✅ | 2026-06-05 | D7 总体验收与流水线收口 |
| Phase T3-D7.8 | ✅ | 2026-06-05 | D7 Pipeline 一键 dry-run |
| Phase T3-D7.8.1 | ✅ | 2026-06-05 | Pipeline summary 统计修正 + Diff 噪声记录 |
| Phase T4.0 | ✅ | 2026-06-05 | 原专业版现有功能总盘点 |
| Phase T4.1 | ⚠️ | 2026-06-05 | 原专业版用户主流程端到端验收（静态链路验收） |
| Phase T4.1.1 | ⚠️ | 2026-06-05 | Professional 主流程真实 dry-run / UI 入口补验 |
| Phase T4.1.2 | ⚠️ | 2026-06-05 | ChatPanel 触发契约与缺口确认 |
| Phase T4.1.3 | ⚠️ | 2026-06-05 | ChatPanel → Candidate/Workflow 触发 dry-run 修复 |
| Phase T4.2 | ⚠️ | 2026-06-05 | Lite / Professional 共存与切换基线验收 |
| Phase T4.3 | ⚠️ | 2026-06-05 | 原专业版编辑能力验收 |
| Phase T4.4 | ⚠️ | 2026-06-05 | Workflow / Pipeline / Prompt 模块验收 |
| Phase T4.5 | ⚠️ | 2026-06-05 | Story State / Materials / 文件系统验收 |
| Phase T4.6 | ⚠️ | 2026-06-05 | Batch / Stream / SSE / Task 验收 |
| Phase T4.7 | ⚠️ | 2026-06-06 | 原专业版问题修复收口 |
| Phase T4.7.1 | ⚠️ | 2026-06-06 | Professional 主流程 E2E dry-run（基础 UI 验证通过，candidate 链路需真实 LLM） |
| Phase T4.7.1a | ✅ | 2026-06-06 | Professional candidate 链路 dry-run 补验（E2E 测试通过） |

---

## 6. 标签说明

| 标签 | 含义 |
| ---- | ---- |
| ✅ | 已完成 |
| ⏳ | 进行中 |
| 🔲 | 待开始 |
| ❌ | 已放弃 |

---

## 7. 文档更新说明

本文档每月更新一次，汇总各阶段的验收状态。

最后更新：2026-06-06
