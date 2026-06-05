# Phase T3-D6.3 — Lite Prompt Variant 真实实验对比分析

> **创建时间**：2026-06-05
> **阶段**：Phase T3-D6.3
> **状态**：分析模板，待真实实验填写
> **重要声明**：本文档是分析框架，不代表真实实验已完成

---

## 1. 前置依据

- **T3-D6 dry-run 结果**：`docs/testing/prompt-experiments/lite-continuation/t3d6-variant-dryrun-results.json`
- **Variant C 被标记为**：`recommended_first_variant = true`
- **Variant C ID**：`variant-c-action-conflict-hook`

---

## 2. 重要声明

### dry-run 不等于真实验证

1. **dry-run 只验证文件存在与结构**：T3-D6.2 dry-run 脚本只检查了 variant 文件是否存在、行数是否大于 10
2. **dry-run 不调用 LLM**：没有真实生成任何内容
3. **dry-run 不能证明 Variant C 最优**：只证明 Variant C 文件结构完整
4. **Variant C 只是优先进入真实测试的候选**：需要真实实验验证

### 本文档用途

- 作为真实实验结果的分析框架
- 用于记录和对比各 variant 的实际表现
- 为 T3-D6.4 决策提供依据

---

## 3. 实验组说明

| Variant | ID | 说明 |
|---------|-----|------|
| Baseline | baseline | 当前生产 Prompt，不做额外约束 |
| Variant A | variant-a-length | 只增加字数约束（1000-1500字，最低900字） |
| Variant B | variant-b-length-action-chain | 字数 + 三段行动链 |
| **Variant C** | **variant-c-action-conflict-hook** | **字数 + 行动链 + 冲突推进 + 结尾钩子** |
| Variant D | variant-d-full-constraints | 完整约束 + 禁止模板词 + 降低 AI 腔 |

**注**：Variant C 加粗表示 dry-run 推荐的优先测试候选

---

## 4. 自动指标表

待真实实验填写。

| Variant | Run ID | 字数 | too_short | template_leak | fallback_used | retry_count | write_skipped | quality_flags | quality_score |
|---------|--------|------|-----------|--------------|--------------|-------------|---------------|---------------|---------------|
| Baseline | run_001 | | | | | | | | |
| Baseline | run_002 | | | | | | | | |
| Baseline | run_003 | | | | | | | | |
| Variant A | run_001 | | | | | | | | |
| Variant A | run_002 | | | | | | | | |
| Variant A | run_003 | | | | | | | | |
| Variant B | run_001 | | | | | | | | |
| Variant B | run_002 | | | | | | | | |
| Variant B | run_003 | | | | | | | | |
| **Variant C** | run_001 | | | | | | | | |
| **Variant C** | run_002 | | | | | | | | |
| **Variant C** | run_003 | | | | | | | | |
| Variant D | run_001 | | | | | | | | |
| Variant D | run_002 | | | | | | | | |
| Variant D | run_003 | | | | | | | | |

### 自动指标说明

| 指标 | 说明 |
|------|------|
| 字数 | 每场正文字数 |
| too_short | 是否触发 low quality flag（< 800 字） |
| template_leak | 是否触发模板泄漏检测 |
| fallback_used | 是否触发 fallback |
| retry_count | 重试次数 |
| write_skipped | 是否跳过写正文 |
| quality_flags | 质量标记列表 |
| quality_score | 1-5 质量评分 |

---

## 5. 人工评分表

待真实实验填写。

| Variant | Run ID | 连贯性 | 可读性 | 画面感 | 冲突推进 | 人物行动 | 节奏 | AI腔 | 结尾钩子 | 是否适合小范围接入 |
|---------|--------|--------|--------|--------|----------|----------|------|------|----------|------------------|
| Baseline | run_001 | | | | | | | | | |
| Baseline | run_002 | | | | | | | | | |
| Baseline | run_003 | | | | | | | | | |
| Variant A | run_001 | | | | | | | | | |
| Variant A | run_002 | | | | | | | | | |
| Variant A | run_003 | | | | | | | | | |
| Variant B | run_001 | | | | | | | | | |
| Variant B | run_002 | | | | | | | | | |
| Variant B | run_003 | | | | | | | | | |
| **Variant C** | run_001 | | | | | | | | | |
| **Variant C** | run_002 | | | | | | | | | |
| **Variant C** | run_003 | | | | | | | | | |
| Variant D | run_001 | | | | | | | | | |
| Variant D | run_002 | | | | | | | | | |
| Variant D | run_003 | | | | | | | | | |

### 评分说明

- **连贯性**：内容是否流畅，前后是否一致
- **可读性**：文字是否易于阅读
- **画面感**：是否有具体场景描写
- **冲突推进**：是否有明确的冲突和进展
- **人物行动**：人物是否有明确行动
- **节奏**：节奏是否紧凑
- **AI腔**：AI 腔是否明显（越低越好）
- **结尾钩子**：结尾是否有吸引人继续阅读的钩子
- **是否适合小范围接入**：综合判断是否适合接入生产

评分标准：1-5 分，5 分最好

---

## 6. 决策规则

### 规则 1：Variant C 进入条件

如果 Variant C 满足以下条件，则进入 T3-D6.4 小范围接入：

- `too_short` 出现次数不高于 Baseline
- `template_leak` 出现次数不高于 Baseline
- `fallback_used` 出现次数不高于 Baseline
- 人工评分综合不劣于 Baseline

### 规则 2：Variant D 过度约束检测

如果 Variant D 出现以下情况，不直接接入生产：

- `fallback_used` 或 `retry_count` 明显增加
- 人工评分显示文本僵硬、套路化
- 部分题材适配效果差

处理方式：拆分约束，保留核心约束，移除过度约束

### 规则 3：所有 Variant 效果不明显

如果所有 variant 相比 Baseline 都没有明显提升：

- 回到 Prompt 设计阶段
- 重新审视约束设计
- 可能需要不同方向的设计

---

## 7. 综合对比摘要

待真实实验填写。

### 7.1 自动指标汇总

| Variant | 平均字数 | too_short 次数 | template_leak 次数 | fallback 次数 | 平均 quality_score |
|---------|----------|----------------|-------------------|--------------|-------------------|
| Baseline | | | | | |
| Variant A | | | | | |
| Variant B | | | | | |
| **Variant C** | | | | | |
| Variant D | | | | | |

### 7.2 人工评分汇总

| Variant | 平均连贯性 | 平均可读性 | 平均画面感 | 平均冲突推进 | 平均 AI腔 |
|---------|------------|------------|------------|-------------|-----------|
| Baseline | | | | | |
| Variant A | | | | | |
| Variant B | | | | | |
| **Variant C** | | | | | |
| Variant D | | | | | |

---

## 8. 结论

待真实实验后填写。

### 8.1 最优 Variant

- **最优 Variant**：
- **原因**：

### 8.2 是否进入 T3-D6.4

- **推荐决策**：
- **条件满足情况**：

### 8.3 主要发现

- **too_short 改善情况**：
- **template_leak 改善情况**：
- **AI 腔改善情况**：
- **其他发现**：

### 8.4 风险

- **Variant C 风险**：
- **Variant D 风险**：
- **其他风险**：

---

## 9. 下一步

1. **真实运行实验**：使用 T3-D6.2 dry-run 脚本作为参考，运行真实 variant 对比
2. **填写结果**：将真实实验结果填入本文档
3. **分析决策**：根据决策规则判断是否进入 T3-D6.4
4. **T3-D6.4**：如果决策通过，进行小范围生产 Prompt 接入

---

## 10. 附录

### 10.1 Variant 文件位置

| Variant | 位置 |
|--------|------|
| Baseline | `docs/testing/prompt-experiments/lite-continuation/baseline.md` |
| Variant A | `docs/testing/prompt-experiments/lite-continuation/variant-a-length.md` |
| Variant B | `docs/testing/prompt-experiments/lite-continuation/variant-b-length-action-chain.md` |
| Variant C | `docs/testing/prompt-experiments/lite-continuation/variant-c-action-conflict-hook.md` |
| Variant D | `docs/testing/prompt-experiments/lite-continuation/variant-d-full-constraints.md` |

### 10.2 相关文档

| 文档 | 说明 |
|------|------|
| `docs/testing/lite-prompt-optimization-experiment-plan-2026-06.md` | 实验方案 |
| `docs/testing/lite-prompt-optimization-samples-2026-06.md` | 实验样例 |
| `docs/testing/prompt-experiments/lite-continuation/t3d6-variant-dryrun-results.json` | dry-run 结果 |
| `docs/testing/lite-prompt-optimization-variant-run-template-2026-06.md` | 实验记录模板 |