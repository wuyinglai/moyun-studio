# T5.16.2a: 多案例评分 final 快照（真实样本）

**版本**: 2026-06 (T5.16.2 real rebuild，T5.16.2a note 字段清理)
**样本**: demo-novel-sec-001, demo-novel-sec-002
**生成方式**: `python scripts/eval/scene_plan_quality_score.py --cases docs/testing/artifacts/t5-scene-plan-quality-cases-2026-06.json`

## 当前状态说明

- sec-001 与 sec-002 均使用**真实** Scene Plan，不再包含测试占位数据。
- sec-001 baseline candidate_id = `cand_a00fb183`，with-plan candidate_id = `cand_effcf335`。
- 历史测试数据问题与纠偏过程，详见 [勘误文档](../t5-scene-plan-quality-final-errata-2026-06.md)。

## sec-001

- baseline: `cand_a00fb183`，总分 17
- with-plan: `cand_effcf335`，总分 15
- delta: -2，结论：❌ With-Plan 表现较差
- scene_plan_title: 雨夜：旧港站的未知召唤

## sec-002

- baseline: `cand_acc252e0`，总分 14
- with-plan: `cand_a673ebd3`，总分 14
- delta: 0，结论：⚠️ 两者相近
- scene_plan_title: 场景：旧港站接头
- 自 T5.15 起保持不变（已有真实样本）

## 安全声明

- 未提交 workspace 原始 `.candidates/` 文件，仅通过受控证据文件披露正文快照。
- 未提交 API key。
- 未执行 adopt；未覆盖 target_file 正文。
- 历史勘误保留用于审计。
