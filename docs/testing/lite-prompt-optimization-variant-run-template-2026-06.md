# Lite Prompt Variant 实验记录模板

> **创建时间**：2026-06-05
> **阶段**：Phase T3-D6.2
> **状态**：模板，待填写

---

## 1. 实验说明

本模板用于记录 Baseline / Variant A-D 的实验结果。

**重要说明**：

- 本模板不代表实验已经执行
- 真实实验需要使用 Phase T3-D6.2 脚本读取 variant 文件
- 真实运行需要调用 LLM，本模板只是记录结构

---

## 2. 实验基本信息

| 项 | 内容 |
| --- | --- |
| Phase | T3-D6.2 |
| 模式 | dry-run / real-run |
| 日期 | |
| 模型 | |
| 项目 | |
| 题材 | |
| 是否调用 LLM | |
| 是否修改生产 Prompt | 否 |

---

## 3. Variant 清单

| Variant | 文件 | 是否存在 | 是否运行 | 说明 |
| ------- | ---- | -------- | -------- | ---- |
| Baseline | baseline.md | | | 当前生产 Prompt 对照组 |
| Variant A | variant-a-length.md | | | 字数约束 |
| Variant B | variant-b-length-action-chain.md | | | 字数 + 行动链 |
| Variant C | variant-c-action-conflict-hook.md | | | 推荐优先测试 |
| Variant D | variant-d-full-constraints.md | | | 完整约束 |

---

## 4. 自动指标记录

| Variant | 场次 | 字数 | quality_flags | quality_score | fallback_used | retry_count | write_skipped |
| ------- | --- | --- | ------------- | ------------- | ------------- | ----------- | ------------- |
| Baseline | 1 | | | | | | |
| Baseline | 2 | | | | | | |
| Baseline | 3 | | | | | | |
| Variant A | 1 | | | | | | |
| Variant A | 2 | | | | | | |
| Variant A | 3 | | | | | | |
| Variant B | 1 | | | | | | |
| Variant B | 2 | | | | | | |
| Variant B | 3 | | | | | | |
| Variant C | 1 | | | | | | |
| Variant C | 2 | | | | | | |
| Variant C | 3 | | | | | | |
| Variant D | 1 | | | | | | |
| Variant D | 2 | | | | | | |
| Variant D | 3 | | | | | | |

---

## 5. 人工评分记录

| Variant | 场次 | 连贯性 | 可读性 | 画面感 | 冲突推进 | 人物行动 | 节奏 | AI腔 | 是否适合继续 |
| ------- | --- | ------ | ------ | ------ | -------- | -------- | ---- | ---- | ------------ |
| Baseline | 1 | | | | | | | | |
| Baseline | 2 | | | | | | | | |
| Baseline | 3 | | | | | | | | |
| Variant A | 1 | | | | | | | | |
| Variant A | 2 | | | | | | | | |
| Variant A | 3 | | | | | | | | |
| Variant B | 1 | | | | | | | | |
| Variant B | 2 | | | | | | | | |
| Variant B | 3 | | | | | | | | |
| Variant C | 1 | | | | | | | | |
| Variant C | 2 | | | | | | | | |
| Variant C | 3 | | | | | | | | |
| Variant D | 1 | | | | | | | | |
| Variant D | 2 | | | | | | | | |
| Variant D | 3 | | | | | | | | |

---

## 6. 结论

待填写：

- **最优 Variant**：
- **是否降低 too_short**：
- **是否降低 template_leak**：
- **是否增加 fallback**：
- **是否推荐进入生产 Prompt 小范围接入**：
- **主要问题**：
- **下一步建议**：

---

## 7. 附录：Variant 文件位置

| Variant | 位置 |
| ------- | ---- |
| Baseline | `docs/testing/prompt-experiments/lite-continuation/baseline.md` |
| Variant A | `docs/testing/prompt-experiments/lite-continuation/variant-a-length.md` |
| Variant B | `docs/testing/prompt-experiments/lite-continuation/variant-b-length-action-chain.md` |
| Variant C | `docs/testing/prompt-experiments/lite-continuation/variant-c-action-conflict-hook.md` |
| Variant D | `docs/testing/prompt-experiments/lite-continuation/variant-d-full-constraints.md` |