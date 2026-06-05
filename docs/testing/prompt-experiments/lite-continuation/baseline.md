# Baseline：当前生产 Prompt 对照组

## 说明

Baseline 表示当前生产 Prompt，不做额外约束。

本文件不复制生产 Prompt 内容，避免实验文档和生产 Prompt 产生漂移。

## 当前生产 Prompt 位置

```
prompts/generate/continuation/main.md
```

## 当前已知特点

1. 目标字数约 800 中文字
2. 允许范围约 600-1000 中文字
3. 有结尾留承接点要求
4. 有去 AI 味要求
5. 未明确要求三段行动链
6. 未明确要求冲突推进
7. 未明确禁止模板占位词

## 实验用途

Baseline 用作对照组，用于比较 Variant A-D 是否能降低：

1. too_short
2. template_leak
3. 结构松散
4. 冲突推进不足
5. 结尾钩子不稳定

## 记录指标

每次运行 Baseline 时记录：

1. 每场字数
2. quality_flags
3. quality_score
4. fallback_used
5. retry_count
6. write_skipped
7. 人工评分