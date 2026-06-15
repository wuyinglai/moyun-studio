# T8.7 Candidate Quality Panel 整理报告

## 一、背景

T8 阶段陆续为 CandidatePanel 增加了 beat validation、continuity warning、feedback revision、revision lineage 等功能。这些信息堆在 card-body 中，用户难以快速区分候选稿状态、质量问题和可执行操作。

T8.7 的目标是将 CandidatePanel 中与"写作质量"相关的信息整理为更清楚的结构，不新增功能、不改后端。

## 二、当前 commit

Base: `36f73fc` (test: stabilize full E2E mock suite)

## 三、改动范围

仅修改两个文件:

- `frontend/src/components/right-panel/CandidatePanel.vue` — 模板重构 + CSS 新增 + 删除一个 unused function
- `frontend/tests/e2e/14-candidate-workflow.spec.ts` — 新增 1 个 mock candidate + 4 个 T8.7 测试

后端零修改。

## 四、CandidatePanel 结构调整

### 4.1 Card Header（身份标识区）

整理前: action badge + continuity badge + beat-validation badge + source-type badge + status badge（5 种 badge 挤在一行）

整理后: action badge + source-type badge + status badge（3 种核心标识，干净清晰）

continuity 和 beat-validation 信息移入新的 Quality Check 区域。

### 4.2 Quality Check 区域（新增 `.card-quality`）

独立区块，浅灰底色，只在候选稿有质量信息时显示:

- **pass 状态**: 绿色 ✓ "信息点检查通过"（低噪音）
- **warning 状态**: 橙色 ⚠ "信息点有警告" + 缺失/不确定详情列表
- **unknown 状态**: 灰色 ? "信息点未确认 — 不影响采用，请预览确认"
- **continuity warning**: 独立一行，按 severity 着色
- **warning_message**: 带左侧 border 的详细说明块
- **beat validation details**: 保留原有 beat-message-pass/warning/unknown 样式

关键设计: `hasQualityInfo()` 函数统一判断是否显示该区域，避免空区块。无 beat_validation 的旧候选稿不会显示任何质量区域。

### 4.3 Revision Info 区域（新增 `.card-revision`）

独立区块，仅在 feedback revision 候选稿上显示:

- 保留原有 `candidate-revision-summary` 样式（紫色底色 + code-branch icon）
- 显示: "反馈修订稿 · 第 X 版" + 来源 + 反馈摘要（42 字截断）
- 普通候选稿不显示此区域

### 4.4 Card Body（基础信息）

精简为: 文件名 + meta（时间 + 字数）。不再混入质量警告和修订信息。

### 4.5 Card Actions（操作区）

重构为两级:

- **Primary（左侧）**: 预览 / 采用 / 删除
- **Secondary（右侧）**: "按反馈再生成" 按钮，带文字标签，仅 pending 状态显示

采用 `justify-content: space-between` 布局，主次分明。

## 五、Quality Check 展示效果

| 状态 | 显示 | 颜色 | 说明 |
|------|------|------|------|
| pass | ✓ 信息点检查通过 | 绿色 | 低噪音，不阻断 |
| warning | ⚠ 信息点有警告 + 缺失详情 | 橙色 | 醒目，advisory |
| unknown | ? 信息点未确认 — 不影响采用 | 灰色 | 解释性文案 |
| continuity | ⚠ 连续性警告 | 按 severity | high/medium/low |
| 无数据 | 不显示 quality 区域 | — | 旧候选稿兼容 |

## 六、Revision Info 展示效果

仅 feedback revision 候选稿显示:

```
🔀 反馈修订稿 · 第 1 版
来自 cand-001
反馈：加强冲突，不要新增人物
```

普通候选稿: 不显示此区域。

## 七、Feedback Modal 文案

更新 revision-notice 文案:

- 旧: "会生成一个新的候选稿，原候选稿和正式正文都不会被自动修改。"
- 新: "告诉 AI 你想怎么改这个候选稿。新内容会作为新的候选稿生成，不会覆盖正文。"

更直接地传达"不覆盖正文"的安全保证。

## 八、兼容性处理

| 场景 | 结果 |
|------|------|
| 旧 candidate 无 metadata | ✓ 不崩，quality 区域不显示 |
| candidate 无 beat_validation | ✓ 不崩，quality 区域不显示 |
| candidate 无 generation_context | ✓ 不崩，revision 区域不显示 |
| 普通 candidate | ✓ 只显示 header + body + actions |
| revision candidate | ✓ 额外显示 revision 区域 |
| adopted / discarded | ✓ 正常显示，adopt/revise 按钮隐藏 |
| preview / adopt / delete | ✓ 功能未变 |
| feedback revision | ✓ 功能未变 |

## 九、E2E 结果

### Focused E2E (14-candidate-workflow.spec.ts)

```
16 passed (1.6m)
```

- 12 个原有测试全部通过（含 T8.5-mini、T8.6 系列）
- 4 个新增 T8.7 测试全部通过:
  - 质量检查区展示 beat warning 状态和缺失详情
  - 质量检查区展示 unknown 状态并说明不影响采用
  - 反馈再生成 modal 说明不会覆盖正文
  - 无 beat_validation 的候选稿不展示质量检查区

### Full E2E

```
62 passed, 0 failed, 93 skipped (5.9m)
```

较 T8.6.1 的 58 passed 增加 4（新增的 T8.7 测试），0 failed 保持不变。

## 十、基础检查

- Frontend build: ✓ clean (vue-tsc + vite build)
- Diff check: ✓ 仅 CRLF 警告（cosmetic）
- Git status: 2 modified files, 0 untracked

## 十一、Bugs Found

1. **Strict mode violation** (已修复): T8.5-mini 测试使用 `filter({ hasText: '反馈再生成' })` 匹配 candidate-card，但新增的 revise 按钮标签使所有 pending 卡片都包含该文本，导致匹配 4 个元素。修复: 改用 `[data-testid="candidate-revision-summary"]` 定位 revision child。

2. **Unused function** (已修复): 移除 header 中的 beat-validation badge 后，`beatValidationLabel()` 不再被调用，导致 TS6133。已删除该函数。

## 十二、Remaining Issues

无。

## 十三、是否建议 T8.7 收口

是。T8.7 目标全部达成:

1. ✓ 用户能一眼看出 candidate 状态（header 精简为 3 badge）
2. ✓ 用户能一眼看出有没有信息点 warning（quality 区域醒目展示）
3. ✓ 用户能看出这是普通候选稿还是反馈修订稿（revision 区域独立）
4. ✓ 用户能看出反馈摘要（revision summary 保留）
5. ✓ 用户知道可以 preview / adopt / delete（primary actions）
6. ✓ 用户知道可以继续"按反馈再生成"（secondary action 带文字标签）
7. ✓ warning 仍是 advisory，不阻断 adopt
8. ✓ 未改变后端 candidate 语义
9. ✓ 未改变 adopt/delete/hash/file safety

## 十四、下一步建议

- T8.7 可正式收口
- 后续可考虑: candidate card 折叠/展开（当列表很长时）、quality check 结果聚合摘要
- 不建议在当前阶段新增更多 candidate UI 功能
