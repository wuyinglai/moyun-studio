# T5.15 最终快照数据勘误

**执行日期**: 2026-06-08
**勘误日期**: 2026-06-08
**状态**: ⚠️ 需要勘误 / 数据质量存在限制

---

## 1. 发现问题

T5.15 归档动作已完成，但 ChatGPT 二次验收发现最终快照（final）中仍存在测试数据痕迹，不能作为最终可靠质量归档。

### 1.1 受影响文件

| 文件 | 状态 |
|------|------|
| `docs/testing/artifacts/t5-scene-plan-quality-multi-score-final-2026-06.json` | ⚠️ 含测试数据 |
| `docs/testing/artifacts/t5-scene-plan-quality-multi-score-final-2026-06.md` | ⚠️ 含测试数据 |
| `docs/testing/artifacts/t5-scene-plan-quality-multi-score-snapshot-2026-06.json` | ⚠️ 含测试数据 |
| `docs/testing/artifacts/t5-scene-plan-quality-multi-score-snapshot-2026-06.md` | ⚠️ 含测试数据 |
| `docs/testing/artifacts/t5-scene-plan-quality-multi-score-2026-06.json` | ⚠️ 含测试数据 |
| `docs/testing/artifacts/t5-scene-plan-quality-multi-score-2026-06.md` | ⚠️ 含测试数据 |

### 1.2 受影响 Case

| case_id | scene_plan_type | 问题 |
|---------|-----------------|------|
| `demo-novel-sec-001` | **测试数据** | scene_plan 包含"测试场景计划"、"测试场景目标"、"测试冲突"、"测试角色" |
| `demo-novel-sec-002` | 真实数据 | scene_plan 包含"场景：旧港站接头"、"林澈"、"沈知夏" |

### 1.3 "测试场景计划"证据

**JSON 文件（t5-scene-plan-quality-multi-score-final-2026-06.json）：**

- 第 12 行：`"scene_plan_title": "测试场景计划"`
- 第 33 行：`"evidence": "未提及指定人物: 测试角色"`
- 第 58 行：`"evidence": "缺少人物: 测试角色"`
- 第 85 行：`"evidence": "未提及指定人物: 测试角色"`
- 第 110 行：`"evidence": "缺少人物: 测试角色"`

**来源文件（workspace/projects/demo-novel/materials/scene_plans/chapters__vol-01__ch-001__sec-001.scene-plan.json）：**

```json
{
  "title": "测试场景计划",
  "goal": "测试场景目标",
  "conflict": "测试冲突",
  "characters": ["测试角色"]
}
```

---

## 2. 为什么不能当作最终质量评估依据

1. **sec-001 的 Scene Plan 是测试数据**，不是真实创作场景
2. **"测试角色"、"测试场景目标" 等内容不是真实人物/场景**
3. **评分结果中 evidence 包含"测试角色"等字样**，证明评分基于测试数据
4. **文件名包含 `final`**，容易让人误以为这是最终可靠质量数据
5. **这会污染后续质量评估结论**

---

## 3. 当前 final 文件只能作为技术归档

⚠️ **重要声明**：

以下文件只能作为**技术归档**（验证多案例评分框架功能），**不能作为最终质量评估依据**：

- `t5-scene-plan-quality-multi-score-final-2026-06.json`
- `t5-scene-plan-quality-multi-score-final-2026-06.md`
- `t5-scene-plan-quality-multi-score-snapshot-2026-06.json`
- `t5-scene-plan-quality-multi-score-snapshot-2026-06.md`
- `t5-scene-plan-quality-multi-score-2026-06.json`
- `t5-scene-plan-quality-multi-score-2026-06.md`

---

## 4. 后续需要用真实 Scene Plan 重新跑 T5.13/T5.15

### 4.1 真实 Scene Plan 要求

要获得真实的质量评估结论，需要：

1. **sec-001 需要真实 Scene Plan**：替换当前的测试 Scene Plan
   - 真实场景应为"旧港站"相关场景
   - 包含真实人物（如"林澈"、"沈知夏"）
   - 包含真实的 goal、conflict、required_beats

2. **sec-002 已是真实 Scene Plan**：无需修改

### 4.2 重新跑 T5.13/T5.15 的条件

- 用户授权使用真实 LLM 生成新的 candidate
- 或者用户手动提供真实的 Scene Plan 文件

---

## 5. 未违反的安全规则

| 规则 | 是否遵守 |
|------|----------|
| 不新增生产功能 | ✅ 遵守 |
| 不修改前端 | ✅ 遵守 |
| 不调用真实 LLM | ✅ 遵守 |
| 不创建 candidate | ✅ 遵守 |
| 不执行 adopt | ✅ 遵守 |
| 不直接修改 workspace 正文 | ✅ 遵守 |
| 不手工伪造 scene_plan 或 candidate | ✅ 遵守 |
| 不提交 workspace 原始 `.candidates/` 目录 | ✅ 遵守 |
| 不提交 API key | ✅ 遵守 |
| 不掩盖"测试数据"事实 | ✅ 遵守 |

---

## 6. 下一步行动建议

1. **用户授权后**：使用真实 LLM 为 sec-001 生成新的 Scene Plan 和 candidate
2. **或者**：用户提供 sec-001 的真实 Scene Plan 文件
3. **重新跑 T5.13**：使用真实 Scene Plan 重新执行多案例评分
4. **重新归档 T5.15**：在真实数据基础上生成新的 final 快照

---

**勘误完成日期**: 2026-06-08
**勘误人**: Solo Agent
