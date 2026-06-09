# T5.18-H1: Candidate Provenance 真实链路验收报告

**版本**: 2026-06
**验收目标**: 验证 candidate provenance 元数据在代码层、scoring 层、文档层的完整链路支持，并明确当前历史样本的 legacy 状态。
**执行日期**: 2026-06-09
**执行人**: Solo Agent

---

## 1. 验收目标

T5.18-H1 是对 T5.17-H2（candidate provenance metadata 支持）的验收阶段，目标是：

1. **代码层验证**：确认 backend 已具备 provenance metadata 写入能力；
2. **Scoring 层验证**：确认 `scene_plan_quality_score.py` 能够读取 provenance、兼容 legacy candidate、不修改评分；
3. **文档层验证**：确认 final 快照与报告明确标注历史 candidate 的 provenance 状态；
4. **证据闭环**：明确 4 个 candidate 的真实状态，不伪造、不美化。

---

## 2. 当前 Cases 清单

| case_id | target_file | baseline | with-plan | scene_plan_path |
|---------|-------------|----------|-----------|-----------------|
| demo-novel-sec-001 | `chapters/vol-01/ch-001/sec-001.md` | `cand_a00fb183` | `cand_effcf335` | `materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json` |
| demo-novel-sec-002 | `chapters/vol-01/ch-001/sec-002.md` | `cand_acc252e0` | `cand_a673ebd3` | `materials/scene_plans/chapters__vol-01__ch-001__sec-002.scene-plan.json` |

---

## 3. Candidate Provenance 检查表

### 3.1 Candidate 元数据文件检查

| candidate_id | 场景 | 角色 | 有 .json | 有 .polish.md | provenance_status | 说明 |
|--------------|------|------|----------|---------------|-------------------|------|
| `cand_a00fb183` | sec-001 | baseline | ❌ 无 | ✅ 有 | legacy_candidate | T5.17-H2 之前生成 |
| `cand_effcf335` | sec-001 | with-plan | ❌ 无 | ✅ 有 | legacy_candidate | T5.17-H2 之前生成 |
| `cand_acc252e0` | sec-002 | baseline | ❌ 无 | ✅ 有 | legacy_candidate | T5.17-H2 之前生成 |
| `cand_a673ebd3` | sec-002 | with-plan | ❌ 无 | ✅ 有 | legacy_candidate | T5.17-H2 之前生成 |

### 3.2 期望的 provenance 字段（对照）

当前 T5.17-H2 之后的新 candidate 应包含以下字段。**此 4 个 candidate 均不包含**：

| 字段 | 类型 | 说明 | 当前 4 个 candidate |
|------|------|------|---------------------|
| `generation_context` | dict | 包含 `scene_plan_used` (bool) | ❌ 缺失 |
| `scene_plan_hash` | string | scene_plan 文件哈希 | ❌ 缺失 |
| `scene_plan_path` | string | scene_plan 文件路径 | ❌ 缺失 |
| `target_file` | string | 目标正文文件路径 | ❌ 缺失 |
| `pipeline` | string | pipeline 名称 | ❌ 缺失 |
| `created_at` | string | ISO 时间戳 | ❌ 缺失 |

---

## 4. 评分（Scoring）输出验证

执行命令：

```bash
python scripts/eval/scene_plan_quality_score.py --cases docs/testing/artifacts/t5-scene-plan-quality-cases-2026-06.json
```

### 4.1 评分结果（与 T5.16.2a 一致，未修改分数）

| 场景 | Baseline | With-Plan | Delta | 结论 |
|------|----------|-----------|-------|------|
| sec-001 | 17 | 15 | -2 | ❌ With-Plan 表现较差 |
| sec-002 | 14 | 14 | +0 | ⚠️ 两者相近 |

### 4.2 Provenance 在 JSON 输出中的形式

每个 case 新增 `provenance` 和 `provenance_overall` 字段：

```json
"provenance": {
  "baseline": {
    "status": "legacy_candidate",
    "scene_plan_used": false,
    "scene_plan_hash": null,
    "scene_plan_path": null,
    "message": "Candidate was created before T5.17-H2 provenance metadata support."
  },
  "with_plan": {
    "status": "legacy_candidate",
    "scene_plan_used": true,
    "scene_plan_hash": null,
    "scene_plan_path": null,
    "message": "Candidate was created before T5.17-H2 provenance metadata support."
  }
},
"provenance_overall": {
  "all_complete": false,
  "note": "T5.18-H1: All 4 candidates are legacy_candidate; T5.17-H2 code support is in place but predates these samples."
}
```

### 4.3 Scoring 兼容性检查

✅ **评分脚本兼容 legacy candidate**：缺少 `.json` metadata 不会导致脚本崩溃，会输出 `legacy_candidate` 状态。
✅ **不改变分数**：sec-001 baseline=17, with-plan=15；sec-002 baseline=14, with-plan=14。
✅ **不读取 API key**：纯本地规则评分，无外部调用。

---

## 5. 结论

| 验证项 | 状态 | 说明 |
|--------|------|------|
| 4 个 candidate 均为 legacy | ✅ 确认 | 均无 `.json` metadata 文件 |
| 不伪造 provenance | ✅ 确认 | 如实标注为 `legacy_candidate` |
| Scoring 兼容 legacy | ✅ 确认 | 脚本在 missing metadata 时正常退出 |
| Scoring 不修改评分 | ✅ 确认 | 分数与 T5.16.2a 完全一致 |
| T5.17-H2 代码能力具备 | ✅ 确认 | backend 已支持 provenance metadata 写入 |
| Final 快照已标注 provenance | ✅ 确认 | `t5-scene-plan-quality-multi-score-final-2026-06.md` 新增验收小节 |
| 未调用真实 LLM | ✅ 确认 | 纯本地规则评分 |
| 未生成新 candidate | ✅ 确认 | 无新文件写入 `.candidates/` |
| 未修改 workspace 原始正文 | ✅ 确认 | target_file 未被覆盖 |
| 未提交 API key | ✅ 确认 | 无敏感信息写入 |

---

## 6. 下一步建议

> **建议在下次大迭代中**（如 T5.18-H2 或后续 candidate 重建任务），生成一组新的 baseline/with-plan candidates，使其包含 T5.17-H2 provenance metadata，以便 scoring 能够完整验证 `complete` 路径。这不会影响现有历史样本的 legacy 标注。

---

## 7. 安全声明

- 未调用真实 LLM；
- 未生成新 candidate；
- 未修改 workspace 原始正文；
- 未提交 `.candidates/` 原始文件；
- 未提交 API key；
- 所有修改仅限于 `scripts/eval/` 与 `docs/testing/`。

---

**T5.18-H1 验收完成**。当前 4 个 candidate 均为 `legacy_candidate`，scoring 链路已兼容 legacy 状态，T5.17-H2 代码能力具备，证据闭环。
