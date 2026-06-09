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

### 6.1 已完成的前置任务 (T5.16.1)

在用户授权调用真实 LLM 之前，已完成**后端 API 修复**：

| 项目 | 状态 |
|------|------|
| `backend/api/scene_plan.py` 中 `llm_service.generate()` → `complete_sync()` | ✅ 已修复 |
| `llm_cfg.model` (dict) → `llm_cfg.get("model")` (安全 dict 访问) | ✅ 已修复 |
| `tests/test_scene_plan_generate_api.py` 10 个单元测试（含回归测试） | ✅ 10/10 通过 |
| `tests/test_scene_plan_validator.py` 9 个单元测试 | ✅ 9/9 通过 |
| 文档与回归测试（故意不提供 `generate()` 方法的 Fake LLM 仍可通过） | ✅ 已覆盖 |

**结论**: T5.16.1 已完成，`/api/scene-plan/generate` 现在可以正常工作（不再依赖不存在的 `generate()` 方法）。

### 6.2 待执行的任务

1. **T5.16**（需用户授权）：使用修复后的真实 LLM 为 sec-001 生成新的 Scene Plan，并创建 paired baseline candidate + with-plan candidate
2. **T5.17**：在真实数据基础上重新执行多案例评分、更新 final 快照
3. **或者**：用户提供 sec-001 的真实 Scene Plan 文件供脚本读取
4. 最终重新跑 T5.13，并在真实数据基础上归档新的 final 快照

### 6.3 安全承诺

- 本勘误文档不包含任何候选稿正文或推理日志
- 未对 `workspace/` 目录下任何场景正文做修改
- 未提交任何 API key
- T5.16.1 的修复严格限定在 `backend/api/scene_plan.py`（修复）与 `tests/test_scene_plan_generate_api.py`（测试）

---

**勘误完成日期**: 2026-06-08
**勘误人**: Solo Agent
