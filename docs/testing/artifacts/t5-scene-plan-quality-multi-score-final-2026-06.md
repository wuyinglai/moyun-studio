# T5.16.2: 多案例评分 final 快照（真实样本）

**版本**: 2026-06 (T5.16.2 real rebuild)
**样本**: demo-novel-sec-001, demo-novel-sec-002
**生成方式**: `python scripts/eval/scene_plan_quality_score.py --cases docs/testing/artifacts/t5-scene-plan-quality-cases-2026-06.json`

## sec-001

- baseline: `cand_a00fb183`
- with-plan: `cand_effcf335`
- scene_plan_title: 雨夜：旧港站的未知召唤
- 样本说明：真实 LLM 生成，不含测试数据占位。

## sec-002

- 保持不变（已有真实样本）。

## 安全声明

- 未提交 workspace 原始 .candidates 文件，仅通过受控证据文件披露正文快照。
- 未提交 API key。
- 未执行 adopt；未覆盖 target_file 正文。
