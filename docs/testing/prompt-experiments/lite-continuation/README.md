# Lite Continuation Prompt Experiments

## 说明

本目录用于 Phase T3-D6.x 的 Lite 写正文 Prompt 优化实验。

这些文件是实验 Prompt patch，不是生产 Prompt。

## 禁止事项

1. 不要直接覆盖 `prompts/generate/continuation/main.md`
2. 不要直接接入生产生成链路
3. 不要修改 LLM 参数
4. 不要把实验结果写成已上线
5. 需要通过实验脚本对比后，再决定是否小范围接入生产 Prompt

## 文件说明

| 文件 | 说明 |
|------|------|
| baseline.md | 当前生产 Prompt 的对照组说明，不复制生产 Prompt |
| variant-a-length.md | 只增加字数约束 |
| variant-b-length-action-chain.md | 字数 + 三段行动链 |
| variant-c-action-conflict-hook.md | 字数 + 行动链 + 冲突推进 + 结尾钩子 |
| variant-d-full-constraints.md | 完整约束 + 禁止模板词 + 降低 AI 腔 |

## 推荐实验顺序

1. Baseline
2. Variant A
3. Variant C
4. Variant D
5. 如有需要，再测试 Variant B

## 推荐优先测试

优先测试 Variant C。

原因：

1. 比 Variant A 更能改善结构
2. 比 Variant B 更强调冲突推进
3. 比 Variant D 更少硬性限制
4. 在质量提升和自然度之间更平衡

## 实验记录

实验结果应记录到后续 T3-D6.2 / T3-D6.3 的测试报告中。