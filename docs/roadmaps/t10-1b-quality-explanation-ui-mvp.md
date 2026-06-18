# T10.1b：Quality Explanation UI MVP

> **阶段**: T10.1b (Frontend UI Implementation)
> **状态**: ✅ 实现完成
> **日期**: 2026-06-18
> **设计文档**: `docs/roadmaps/t10-1-quality-explanation-ui-design.md`

---

## 1. 任务目标

在 CandidatePanel 中实现 Quality Explanation 可展开区，把 quality metadata 从"内部状态"变成"用户可理解的解释"。

---

## 2. 实现范围

### 2.1 新增文件

- `frontend/src/modules/candidate/qualityExplanation.ts` — 质量解释辅助模块

### 2.2 修改文件

- `frontend/src/components/right-panel/CandidatePanel.vue` — 添加可展开解释区
- `frontend/tests/e2e/14-candidate-workflow.spec.ts` — 添加 7 个 T10.1b focused E2E 测试

---

## 3. 实现内容

### 3.1 qualityExplanation.ts

定义了五个质量维度的解释逻辑：

| 维度 | 键名 | pass 文案 | warning 文案 | unknown 文案 |
|------|------|-----------|-------------|-------------|
| 指令遵守 | instruction_following | 通过 | 需注意 | 未检测 |
| 连续性 | continuity | 通过 | 需注意 | 未检测 |
| 文风保持 | style_preservation | 通过 | 需注意 | 未检测 |
| 改动幅度 | change_scope | 变化较小 | 变化适中 | 无法判断 |
| 禁区检查 | forbidden_check | 通过 | 需注意 | 未检测 |

每个维度包含：label、statusLabel、description（动态生成）、cssClass。

辅助函数：

- `buildQualityExplanation(candidate)` — 构建完整解释摘要，old candidate 返回 null
- `shouldShowRepairExplanation(candidate)` — 判断是否显示修复解释
- `repairExplanation(candidate)` — 生成修复解释文案
- `CANDIDATE_SAFETY_TEXT` — 固定安全文案常量

### 3.2 CandidatePanel.vue 变更

- 新增 `expandedQuality` Set ref 追踪展开状态
- 新增 `toggleQualityExpanded(id)` 切换展开/折叠
- 新增 `getQualityExplanation(candidate)` 调用 helper
- 新增 `isQualityExpanded(candidate)` 检查展开状态
- 模板：在 quality-summary 和 card-quality 之间插入可展开区
- 可展开区包含：折叠态摘要、5 个维度解释、修复解释（条件）、安全文案（固定）

### 3.3 CSS 样式

- `.quality-explanation` — 外容器，浅色背景+边框
- `.quality-explanation-toggle` — 折叠按钮，全宽
- `.quality-explanation-body` — 展开区 grid 布局
- `.quality-dimension` — 单个维度条目
- `.quality-dimension-status` — 状态标签 (expl-pass/warning/danger/unknown)
- `.quality-repair-explanation` — 修复解释，橙色左边框
- `.quality-safety-text` — 安全文案，蓝色背景

### 3.4 E2E 测试（7 个）

| 测试 | 覆盖 |
|------|------|
| toggle visible | 折叠态按钮可见，包含"质量提示"文字 |
| 5 dimensions expand | 点击后展示 5 个维度 |
| correct status labels | pass → "通过"，warning → "需注意"，medium → "变化适中" |
| repair explanation | warning 时显示修复解释，包含"不会自动采纳" |
| safety text | 展开后始终显示"所有质量提示仅供参考" |
| old candidate compat | 无 quality 元数据的候选稿不显示解释区 |
| collapse on second click | 再次点击折叠 |

---

## 4. 测试结果

### 4.1 TypeScript 类型检查

```
vue-tsc --noEmit: PASS (no errors)
```

### 4.2 Vite Build

```
vite build: PASS (1.98s, 3436 modules)
```

### 4.3 Focused E2E

```
30 passed (1.6m)
- 23 existing tests: all pass
- 7 new T10.1b tests: all pass
```

---

## 5. 不做事项（确认）

- 不改后端代码
- 不改 quality metadata 计算逻辑
- 不改 adopt / delete / preview 行为
- 不做总分或排名
- 不做自动 repair
- 不做 Candidate Compare

---

## 6. 向后兼容

- Old candidate 无 `quality` 字段时，`buildQualityExplanation()` 返回 null
- `v-if="getQualityExplanation(candidate)"` 不渲染解释区
- 现有 quality-summary badges 和 card-quality 区不受影响
- 现有 E2E 测试全部通过

---

## 7. 安全边界

- Candidate-only 安全文案始终展示在展开区底部
- 修复解释明确说明"不会自动采纳，也不会覆盖正文"
- warning 文案使用"需注意"而非"失败"/"错误"
- unknown 文案使用"未检测"而非"未通过"
- large 文案使用"变化较大，建议预览"而非"改动过大，不能用"

---

## 8. 后续任务

### T10.2a：Candidate Compare MVP Design

- 设计原文 vs candidate 比较模式
- 设计 parent vs child 比较模式
- 不做复杂 diff UI

### T10.2b：Candidate Compare MVP

- 实现最小比较 UI

---

## 9. Git 信息

- Base commit: `6220773` (docs: design T10.1 quality explanation UI)
- Branch: main
- Commit message: `feat: implement T10.1b quality explanation UI`
