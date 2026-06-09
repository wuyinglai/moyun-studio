# T5.11 / T5.13 / T5.16.2a: 多案例评分报告（真实样本，最终状态）

**执行日期**: 2026-06-09
**执行人**: Solo Agent
**状态**: ✅ PASS（2/2 案例完成）

---

## 重要说明

✅ **sec-001 与 sec-002 当前均使用真实 Scene Plan**。
- sec-001: `雨夜：旧港站的未知召唤`，T5.16.2 完成真实样本重建。
- sec-002: `场景：旧港站接头`，自 T5.15 起即为真实样本。
- 历史测试数据问题与纠偏过程，详见 [勘误文档](t5-scene-plan-quality-final-errata-2026-06.md)。

---

## 1. 总体统计

| 统计项 | 值 |
|--------|-----|
| 总测试用例数 | 2 |
| With-Plan 更优 | 0 |
| Baseline 更优 | 1 |
| 持平 | 1 |
| 平均 Delta | -1.0 |

---

## 2. 各案例详情

| 案例 ID | Target File | Baseline ID | With-Plan ID | Baseline | With-Plan | Delta | 结论 |
|---------|-------------|-------------|--------------|----------|-----------|-------|------|
| demo-novel-sec-001 | chapters/vol-01/ch-001/sec-001.md | cand_a00fb183 | cand_effcf335 | 17 | 15 | -2 | ❌ With-Plan 表现较差 |
| demo-novel-sec-002 | chapters/vol-01/ch-001/sec-002.md | cand_acc252e0 | cand_a673ebd3 | 14 | 14 | +0 | ⚠️ 两者相近 |

---

## 2B. Candidate Provenance 状态

| 案例 ID | Baseline 状态 | With-Plan 状态 | 说明 |
|---------|---------------|----------------|------|
| demo-novel-sec-001 | legacy_candidate | legacy_candidate | T5.18-H1: candidate provenance metadata only exists for candidates created after T5.17-H2. Missing p |
| demo-novel-sec-002 | legacy_candidate | legacy_candidate | T5.18-H1: candidate provenance metadata only exists for candidates created after T5.17-H2. Missing p |

> 说明：`legacy_candidate` 表示 candidate 创建于 T5.17-H2 之前，不包含 provenance metadata。这是正常的历史状态，不影响评分。
> `complete` 表示 candidate 已包含 `generation_context` / `scene_plan_hash` / `scene_plan_path` 三个字段。

---

## 3. 稳定性评估

✅ **当前状态**：2 个案例均使用真实 Scene Plan，评分框架正常工作。
- 评分结论如实记录，未强行要求 with-plan 获胜。
- 如需更完整的稳定性评估，建议补充至少 2-3 个不同类型场景的完整样本。

---

## 4. 说明

1. **sec-001**：经 T5.16.2 纠偏，当前已替换为真实样本。
2. **sec-002**：自 T5.15 起保持真实样本，未改动。
3. 评分使用规则匹配，未调用 LLM 进行深度语义理解。
4. 仅作为辅助参考，不替代人工判断。

---

## 5. 安全声明

- 未提交 workspace 原始 `.candidates/` 文件，仅通过受控证据文件披露正文快照。
- 未提交 API key。
- 未执行 adopt；未覆盖 target_file 正文。
- 历史勘误保留用于审计。

---

**T5.11 / T5.13 / T5.16.2a 最终状态**：✅ PASS（2/2 案例，真实样本；测试数据问题已在勘误中记录与纠偏）

