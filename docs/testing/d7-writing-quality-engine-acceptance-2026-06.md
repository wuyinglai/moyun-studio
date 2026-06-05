# Phase T3-D7 — Python + LLM 写作质量与一致性引擎总体验收

## 1. 阶段目标

D7 的目标不是单纯 Prompt 优化，而是建立：
- **Python** 负责比对、筛选、校验、沉淀；
- **LLM** 负责逐项判断、审稿、生成建议；
- **用户** 负责最终确认。

---

## 2. 总体流水线

写清楚完整流程：

```
scene markdown
↓
Diff Engine
↓
candidates JSON
↓
Review Engine Prompt
↓
真实 LLM Review
↓
Validator
↓
State Snapshot
↓
Plot Debt Table
↓
Rewrite Engine Suggestions
```

---

## 3. 模块验收表

| 模块 | 阶段 | 输入 | 输出 | LLM | 修改正文 | 自动入库 | 状态 |
| -- | -- | -- | -- | --- | ---- | ---- | -- |
| D7.1 Diff Engine 存在性比对 MVP | ✅ | 场景文件 | diff-engine-existence-mvp-sample.json | ❌ | ❌ | ❌ | Done |
| D7.1.1 Candidate 降噪 | ✅ | candidates JSON | 降噪后 candidates | ❌ | ❌ | ❌ | Done |
| D7.3a Review schema + validator | ✅ | schema 定义 | validator 脚本 | ❌ | ❌ | ❌ | Done |
| D7.3b Review Prompt 契约 | ✅ | Prompt 模板 | prompt 契约文档 | ❌ | ❌ | ❌ | Done |
| D7.3c-b 真实 LLM Review 3 条 | ✅ | candidates JSON | review 结果 | ✅ | ❌ | ❌ | Done |
| D7.3d 真实 LLM Review 14 条 | ✅ | candidates JSON | review 结果 | ✅ | ❌ | ❌ | Done |
| D7.4 State Snapshot MVP | ✅ | scene + reviews | state-snapshot-mvp-sample.json | ❌ | ❌ | ❌ | Done |
| D7.5 Plot Debt 表 MVP | ✅ | scene + snapshot | plot-debt-mvp-sample.json | ❌ | ❌ | ❌ | Done |
| D7.5.2 Plot Debt 实体降噪 | ✅ | plot debt | 降噪后的 plot debt | ❌ | ❌ | ❌ | Done |
| D7.6 Rewrite Engine MVP | ✅ | scene + snapshot + plot debt + reviews | rewrite-engine-mvp-sample.json | ❌ | ❌ | ❌ | Done |

---

## 4. 关键产物文件清单

### JSON 产物
- [diff-engine-existence-mvp-sample.json](../prompt-experiments/diff-engine-existence-mvp-sample.json)
- [review-engine-real-llm-full-output.json](../prompt-experiments/review-engine-real-llm-full-output.json)
- [state-snapshot-mvp-sample.json](../prompt-experiments/state-snapshot-mvp-sample.json)
- [plot-debt-mvp-sample.json](../prompt-experiments/plot-debt-mvp-sample.json)
- [rewrite-engine-mvp-sample.json](../prompt-experiments/rewrite-engine-mvp-sample.json)

### Markdown 报告
- [review-engine-real-llm-full-validator.md](../prompt-experiments/review-engine-real-llm-full-validator.md)
- [state-snapshot-mvp-sample.md](../prompt-experiments/state-snapshot-mvp-sample.md)
- [plot-debt-mvp-sample.md](../prompt-experiments/plot-debt-mvp-sample.md)
- [rewrite-engine-mvp-sample.md](../prompt-experiments/rewrite-engine-mvp-sample.md)

---

## 5. 已验证能力

- ✅ Python 可以提取设定候选
- ✅ LLM 可以逐条 review candidates
- ✅ Validator 可以防止 LLM 漏判
- ✅ Snapshot 可以沉淀状态
- ✅ Plot Debt 可以记录剧情债务候选
- ✅ Rewrite Engine 可以生成局部修订建议
- ✅ 全流程目前不自动改正文、不自动入库

---

## 6. 当前限制

必须诚实写：

- 目前主要基于 fixture 和样例文本验证
- 还不是产品 UI
- Rewrite Engine 当前是 dry-run/mock 建议，不是真实改文
- Plot Debt 仍可能有少量噪声
- LiteLLM 对 Agnes API 适配仍有问题，当前真实调用使用 OpenAI-compatible 方式跑通
- 用户确认流程尚未接入
- 设定库真实写入尚未接入

---

## 7. 是否可以进入下一阶段

**结论**：
可以进入 T4 Professional Prompt / D7 pipeline 一键 dry-run 的准备阶段。
但不建议直接接入生产自动改文。

---

## 8. 下一步建议

建议新增：

- Phase T3-D7.7：D7 总体验收与流水线收口 ✅
- Phase T3-D7.8：D7 Pipeline 一键 dry-run ✅
- Phase T3-D7.8.1：Pipeline summary 统计修正 + Diff 噪声记录 ✅

建议新增：

- Phase T3-D7.9：用户确认清单 MVP
- Phase T4.0：Professional Prompt 架构设计
- Phase T4.1：Professional 生成前 Scene Plan 验收

---

**文档完成日期**：2026-06-05
