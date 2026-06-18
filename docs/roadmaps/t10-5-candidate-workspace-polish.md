# T10.5：Candidate Workspace Polish — 候选稿工作区整理

## 任务状态

**状态**: ✅ 已完成
**基线 commit**: bfddf92（T10.4b 完成点）
**范围**: `frontend/src/components/right-panel/CandidatePanel.vue` + E2E

---

## 一、实现范围总览

| 功能 | 说明 | 修改位置 |
|------|------|---------|
| 候选稿筛选 | 全部 / 待处理 / 已采纳 / 已丢弃 | CandidatePanel.vue template + CSS |
| 来源/类型 badge 优化 | parent_candidate_id 时显示来源说明 | CandidatePanel.vue template |
| 当前聚焦高亮 | 正在预览/比较的卡片有 focus 样式 | CandidatePanel.vue script + CSS |
| 空状态文案 | 各筛选条件下的空状态 | CandidatePanel.vue template |
| 小屏幕布局 | card-actions 已在 T10.4a 中换行；本次 header 也支持 flex-wrap | CandidatePanel.vue CSS |

---

## 二、候选稿筛选

### 2.1 规则

| 筛选值 | candidate.status 匹配 |
|--------|----------------------|
| all | 无筛选 |
| pending | pending |
| adopted | adopted |
| discarded | discarded **或** rejected |

`rejected` 是历史状态值，与 `discarded` 语义一致，故合并处理。

### 2.2 实现细节

- **template**: 新增 `.filter-bar` 容器，内含 4 个按钮
- **count badge**: 每个筛选按钮显示当前状态下的候选稿数量
- **computed `filteredCandidates`**: 基于 `filterStatus` 过滤 `candidates`
- **computed `filterOptions`**: 计算各状态候选稿数量
- **`setFilter(value)`**: 设置 `filterStatus`，无后端调用，纯前端
- **data-testid**: `candidate-filter-bar`, `candidate-filter-{value}`, `candidate-filter-count-{value}`

### 2.3 安全检查

- ✅ 不创建/删除 candidate
- ✅ 不修改 candidate status
- ✅ 不触发 LLM
- ✅ 无后端 API 新增
- ✅ 纯前端展示筛选

---

## 三、来源/类型显示优化

### 3.1 新增的 source-parent-badge

当候选稿有 `parent_candidate_id` 时，在 card-header 显示紫色 badge：

| candidate.action | 文案 |
|-----------------|------|
| repair | 修复自上一版 |
| feedback_revision | 根据反馈再生成 |
| 其他 | 来自父候选稿 |

### 3.2 样式

```css
.source-parent-badge {
  padding: 1px 5px;
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
  border-radius: 4px;
  font-size: 10px;
  white-space: nowrap;
}
```

### 3.3 card-header 布局

原 header 使用简单 inline，新增 `.card-header-row` flexbox：

```css
.card-header-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
```

确保窄面板时 action/status/source badges 自动换行。

---

## 四、当前候选稿聚焦

### 4.1 实现逻辑

- **新状态** `focusedCandidateId`: 指向当前预览或正在比较的候选稿
- **触发点**: `previewCandidate()` / `openCompare()` 设置为对应 candidate.id
- **清除**: `closePreview()` / `closeCompare()` 检查如果当前聚焦 id 等于关闭的 id，则清空 focus
- **CSS**: `.card-focus` 使用 `outline: 2px solid var(--accent-primary)` + 轻微渐变背景

### 4.2 设计考虑

- 不使用 selectedId（已有选中逻辑用于其他目的）
- 刷新后不保持，符合 MVP scope
- 只做本地 UI state，不写后端，不影响 candidate 状态

---

## 五、空状态文案

| 场景 | 文案 |
|------|------|
| 候选稿列表为空（candidates.length === 0） | 暂无候选稿。生成内容后会出现在这里。 |
| pending 筛选无结果 | 暂无待处理候选稿。 |
| adopted 筛选无结果 | 暂无已采纳候选稿。 |
| discarded 筛选无结果 | 暂无已丢弃候选稿。 |
| 其他可能的筛选组合 | 当前筛选条件下暂无候选稿。 |

---

## 六、小屏幕布局复查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 按钮换行 | ✅ T10.4a 已实现 card-actions flex-wrap | 继承自 T10.4a |
| 文件名截断 | ✅ T10.4a 已实现 ellipsis | 继承自 T10.4a |
| preview 滚动 | ✅ T10.4a 已实现 overflow-y: auto | 继承自 T10.4a |
| compare modal 不溢出 | ✅ 无变更 | 无修改 |
| quality explanation 不撑破 | ✅ 无变更 | 无修改 |
| filter bar 换行 | ✅ flex-wrap: wrap | 本次新增 |
| card-header badges 换行 | ✅ .card-header-row flex-wrap | 本次新增 |

---

## 七、Candidate-only 安全边界复核

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 自动 adopt？ | ✅ 无 | 无相关调用 |
| 自动 overwrite？ | ✅ 无 | 无相关调用 |
| 自动 delete？ | ✅ 无 | 无相关调用 |
| 触发 LLM？ | ✅ 无 | 无相关调用 |
| 创建 repair/revision？ | ✅ 无 | 仅修改 source 展示，不新增生成逻辑 |
| 新增后端 API？ | ✅ 无 | |
| 不改变 candidate status | ✅ 无 | 仅展示筛选 |
| 不改变 preview/compare/adopt/delete 行为 | ✅ 无 | 现有函数保持原语义 |

CompareModal 纯展示 diff + safety notice，没有 adopt/delete/repair 按钮，保持不变。

---

## 八、测试结果

### 8.1 Frontend build

```
✓ 3440 modules transformed
```

### 8.2 Focused E2E

```
tests/e2e/14-candidate-workflow.spec.ts — 43 passed
tests/e2e/32-continuity-anchors.spec.ts — 2 passed (independent)
```

### 8.3 Full mock E2E

```
97 passed, 93 skipped, 0 failed
```

### 8.4 diff check

```
git diff --check — clean
```

### 8.5 git status

```
clean
```

---

## 九、Known Issues / Remaining

| # | 描述 | 严重程度 | 决策 |
|---|------|---------|------|
| R1 | revision modal 内容过长时 overflow: hidden 可能截断 | 低 | 后续独立修复，不阻塞 T10.5 |
| R2 | source-parent-badge 使用 hard-coded hex color 而非 CSS var | 低 | 为视觉一致性；紫色主题色非标准 accent，如需要可调整 |
| R3 | filter count badge 不区分 "0"（0 仍显示） | 极低 | 保持与产品常见模式一致 |

---

## 十、是否建议进入 T10.6 / v0.2.3 planning

**建议**: ✅ 可以进入 T10.6 或 v0.2.3 planning

T10.1b – T10.5 候选稿工作流 MVP 已闭环：

| 能力 | 状态 |
|------|------|
| quality explanation（5 维度） | ✅ |
| compare modal（正文 vs candidate / parent vs child） | ✅ |
| button groups（primary/secondary/trailing） | ✅ |
| adopt hint（有 warning 时提示，不阻断） | ✅ |
| 筛选（4 状态） | ✅ |
| 聚焦高亮（预览/比较时） | ✅ |
| 来源 badge（parent_candidate_id） | ✅ |
| 空状态文案 | ✅ |
| 小屏幕布局 | ✅ |
| E2E 回归 | ✅ 97 passed |
| 安全边界 | ✅ candidate-only |

可考虑 v0.2.3 release 时纳入这些变更。
