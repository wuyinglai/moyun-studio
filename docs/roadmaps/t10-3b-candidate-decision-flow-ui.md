# T10.3b：Candidate Decision Flow UI

## Status

**阶段**: T10.3b (UI Implementation)
**状态**: ✅ 已完成
**创建日期**: 2026-06-18
**基于设计**: [t10-3a-candidate-decision-flow-design.md](./t10-3a-candidate-decision-flow-design.md)

---

## 1. 实现范围

根据 T10.3a 设计文档，本任务仅修改前端 UI，不涉及后端逻辑：

- 修改 [CandidatePanel.vue](../frontend/src/components/right-panel/CandidatePanel.vue)
- 修复 [CompareModal.vue](../frontend/src/components/right-panel/CompareModal.vue) 未使用导入（build fix）
- 运行 frontend build 和 focused E2E

### 1.1 不修改项

- 不改后端 API
- 不改 candidate 状态机
- 不改 adopt/delete/repair/revision 逻辑
- 不改 CompareModal 核心行为
- 不改 qualityExplanation 逻辑

---

## 2. 按钮分组

### 2.1 分组结构

按 T10.3a 设计，将按钮分为三层：

```
card-actions-primary（主操作区）：
  - 预览
  - 比较差异
  - 采用（仅 pending）

card-actions-secondary（修订操作区）：
  - 反馈再生成（仅 pending）
  - 修复候选稿（仅 pending + repairable warning）

card-actions-trailing（尾部危险操作区）：
  - 删除（始终可见）
```

### 2.2 布局实现

修改前：所有按钮在 `card-actions` 和 `card-actions-primary` 中混排，删除按钮在 primary 区域内。

修改后：
- `card-actions` 使用 flex justify-content: space-between
- `card-actions-primary` 在左侧（预览、比较差异、采用）
- `card-actions-secondary` 在中间（反馈再生成、修复候选稿）
- `card-actions-trailing` 在右侧（删除）

### 2.3 视觉区分

- 删除按钮单独放在尾部，视觉上与查看/终态操作分离
- 采用按钮使用成功色（绿色），视觉突出
- 修订按钮使用紫色/橙色
- 删除按钮 hover 时变红

---

## 3. 状态矩阵对齐

### 3.1 操作可用矩阵

| 操作 | pending | adopted | discarded |
|------|---------|---------|-----------|
| 预览 | ✅ 可见 | ✅ 可见 | ✅ 可见 |
| 比较差异 | ✅ 可见 | ✅ 可见 | ✅ 可见 |
| 采用 | ✅ 可见 | ❌ 隐藏 | ❌ 隐藏 |
| 反馈再生成 | ✅ 可见 | ❌ 隐藏 | ❌ 隐藏 |
| 修复候选稿 | ✅ 可见（有 warning） | ❌ 隐藏 | ❌ 隐藏 |
| 删除 | ✅ 可见 | ✅ 可见 | ✅ 可见 |

### 3.2 实现方式

- `v-if="candidate.status === 'pending'"` 控制采用、反馈再生成、修复候选稿按钮
- 删除按钮无状态限制（始终可见）
- 预览、比较差异按钮无状态限制（始终可见）

### 3.3 现有实现对齐

当前代码已正确实现状态矩阵：
- 采用按钮：`v-if="candidate.status === 'pending'"`
- 反馈再生成：`v-if="candidate.status === 'pending'"`
- 修复候选稿：`v-if="candidate.status === 'pending' && hasRepairableWarning(candidate)"`
- 删除：始终可见（无 v-if）
- 预览、比较差异：始终可见（无 v-if）

本次修改仅调整了按钮分组结构，未改变可见性逻辑。

---

## 4. Adopt 前提示策略

### 4.1 触发条件

当 candidate 是 pending 且满足以下任一条件时，在采用按钮附近显示轻量提示：

1. `hasRepairableWarning(candidate)` — 有可修复的质量警告（instruction_following=warning / forbidden_check=warning / change_scope=large）
2. `beat_validation.status === 'warning'` — 信息点检查有警告
3. `continuity.has_warning` — 连续性有警告

### 4.2 提示文案

```
采纳前建议先查看质量提示和比较差异。
```

### 4.3 提示样式

- 使用浅黄色背景（rgba(234, 179, 8, 0.08)）
- 使用警告色文字（var(--accent-warning)）
- 使用灯泡图标（fa-lightbulb）
- 字体大小：11px
- 带 1px 边框

### 4.4 重要约束

- **不阻断 adopt**：提示只是建议，用户仍可直接点击采用
- **不禁用 adopt 按钮**
- **不弹出强制确认**
- 仅对 pending 状态显示

### 4.5 实现函数

```typescript
function showAdoptHint(candidate: CandidateInfo): boolean {
  if (candidate.status !== 'pending') return false
  if (hasRepairableWarning(candidate)) return true
  const q = candidate.quality
  if (q && q.change_scope === 'large') return true
  const bv = candidate.beat_validation
  if (bv && bv.status === 'warning') return true
  if (candidate.continuity && candidate.continuity.has_warning) return true
  return false
}
```

---

## 5. Candidate-only 安全边界

### 5.1 不变的安全规则

本次修改保持以下安全边界不变：

| 操作 | 行为 | 是否写入正文 |
|------|------|-------------|
| 预览 | 只读 | 否 |
| 比较差异 | 只读 | 否 |
| Quality Explanation | 只读 | 否 |
| 反馈再生成 | 生成 child candidate | 否 |
| 修复候选稿 | 生成 child candidate | 否 |
| 采用 | 写入正文 | 是（唯一入口） |
| 删除 | 删除候选稿 | 否 |

### 5.2 Compare Modal 安全

- CompareModal 中仍然没有 adopt 按钮
- 安全提示文案保持不变："比较视图仅用于查看差异，不会修改正文。只有点击采纳后，正文才会更新。"

---

## 6. 测试结果

### 6.1 Frontend Build

```text
cd frontend
npm run build
```

**结果**: ✅ 3440 modules transformed

### 6.2 Focused E2E

```text
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

**结果**: ✅ 37 passed

### 6.3 Diff Check

```text
git diff --check
```

**结果**: ✅ 无错误

### 6.4 Git Status

```text
git status --short
```

**结果**: ✅ clean

---

## 7. 新增/修改文件

### 7.1 主要修改

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/components/right-panel/CandidatePanel.vue` | 按钮分组、adopt 提示、CSS 样式 |
| `frontend/src/components/right-panel/CompareModal.vue` | 移除未使用导入（build fix） |

### 7.2 新增文档

| 文件 | 用途 |
|------|------|
| `docs/roadmaps/t10-3b-candidate-decision-flow-ui.md` | 本报告 |

---

## 8. Remaining Issues

- 无新 blocking issues
- E2E 未新增针对按钮分组和 adopt 提示的测试（当前测试仍通过，但建议后续补充）

---

## 9. 建议

### 9.1 是否建议进入 T10.3b-final-verify

**建议**: ✅ 可以进入 final-verify

### 9.2 Final-verify 建议检查项

1. 手动验证按钮分组布局在不同屏幕尺寸下的表现
2. 验证 adopt 提示在有 warning 时正确显示
3. 验证 adopted/discarded 状态下按钮可见性符合矩阵
4. 验证 compare modal 仍无 adopt 按钮
5. 验证 adopt 操作仍可正常执行（提示不阻断）

---

## 10. 与设计文档的差异

### 10.1 已实现

- ✅ 按钮分组：primary / secondary / trailing
- ✅ Adopt 前轻量提示（不阻断）
- ✅ 状态矩阵对齐
- ✅ 删除按钮放在尾部危险区

### 10.2 未实现（设计文档中标记为"建议不做"）

- ❌ 不新增按钮
- ❌ 不新增 API
- ❌ 不改后端
- ❌ 不做强制 gate

---

## 11. 结论

T10.3b Candidate Decision Flow UI 实现完成：

- 按钮分组更清晰（查看 / 修订 / 危险操作）
- pending/adopted/discarded 状态下按钮可见性符合矩阵
- adopt 前提示只提示不阻断
- preview / compare / adopt / delete 行为不变
- compare modal 仍无 adopt 按钮
- frontend build 通过
- focused E2E 通过
- 无后端修改
- 无 candidate 状态机修改

所有验收标准已满足，建议进入 final-verify。