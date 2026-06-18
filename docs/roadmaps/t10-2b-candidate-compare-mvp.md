# T10.2b：Candidate Compare MVP

> **阶段**: T10.2b (Frontend UI Implementation)
> **状态**: ✅ 实现完成
> **日期**: 2026-06-18
> **设计文档**: `docs/roadmaps/t10-2a-candidate-compare-mvp-design.md`

---

## 1. 实现范围

### 1.1 新增文件

- `frontend/src/modules/candidate/compareDiff.ts` — 行级 diff 算法 + 类型定义
- `frontend/src/components/right-panel/CompareModal.vue` — 比较 modal 组件

### 1.2 修改文件

- `frontend/src/components/right-panel/CandidatePanel.vue` — 添加比较按钮 + 集成 modal + repair action label
- `frontend/tests/e2e/14-candidate-workflow.spec.ts` — 添加 7 个 T10.2b focused E2E 测试 + cand-005 mock

---

## 2. 比较模式

### 模式 A：当前正文 vs candidate

- 适用于普通 candidate、parent 不存在、old candidate
- 左侧：当前正文（通过 `fileStore.readFile` 获取）
- 右侧：当前候选稿（通过 `api.get` 获取）

### 模式 B：parent candidate vs child candidate

- 适用于 repair child、feedback revision child
- 左侧：父候选稿（通过 `api.get` 获取 parent 内容）
- 右侧：当前候选稿
- parent 缺失时自动 fallback 到模式 A

---

## 3. UI 行为

- 候选稿卡片 `card-actions-primary` 区域新增"比较差异"按钮（`fa-code-compare` 图标）
- 按钮位于 preview 按钮之后、adopt 按钮之前
- 点击后打开 CompareModal
- Modal 标题："候选稿比较"
- Modal 安全提示："比较视图仅用于查看差异，不会修改正文。只有点击采纳后，正文才会更新。"
- Modal 底部只显示"关闭"按钮，不提供 adopt 入口
- 左右标签根据比较模式和 action 类型动态显示

### 3.1 标签映射

| 场景 | 左侧标签 | 右侧标签 |
|------|----------|----------|
| 普通 candidate | 当前正文 | 润色/重写/续写候选稿 |
| repair child | 父候选稿 | 修复版候选稿 |
| feedback revision child | 父候选稿 | 反馈修订候选稿 |
| parent 缺失 fallback | 当前正文（父候选稿已删除） | 当前候选稿 |

---

## 4. Diff 规则

- 纯前端实现，无后端 API 依赖
- LCS-based 行级 diff 算法
- 4 种行类型：same / added / removed / changed
- changed 由相邻 removed + added 配对生成
- 行数上限 2000（防止大文件性能问题）
- 颜色语义：added 绿色、removed 红色、changed 黄色、same 无高亮
- 摘要栏显示：左侧字数 | 右侧字数 | 字数变化
- 两侧内容完全一致时显示"两侧内容完全一致，无差异。"

---

## 5. 空状态与异常状态

| 场景 | 行为 |
|------|------|
| candidate content missing | 右侧显示空，摘要提示 |
| source content missing | 左侧显示空，摘要提示 |
| parent candidate missing | fallback 到模式 A，左侧标签标注"父候选稿已删除" |
| old candidate 无 lineage | 使用模式 A |
| repair child 无 parent | fallback 到模式 A |
| candidate 已 adopted/discarded | 仍可打开比较，不改变状态 |
| 两侧内容完全一致 | 显示"两侧内容完全一致，无差异。" |

---

## 6. candidate-only 安全边界

- Compare modal 不调用任何写入 API（无 adopt / repair / revise / save）
- Compare modal 不改变 candidate status
- Compare modal 不触发 LLM 调用
- Compare modal 不提供 adopt 按钮
- Compare modal 不提供 repair / revision 入口
- 安全提示条始终可见

---

## 7. 测试结果

### 7.1 TypeScript 类型检查

```
vue-tsc --noEmit: PASS (no errors)
```

### 7.2 Vite Build

```
vite build: PASS (3.79s, 3440 modules)
```

### 7.3 Focused E2E

```
37 passed (2.5m)
- 30 existing tests: all pass
- 7 new T10.2b tests: all pass
```

### 7.4 Bug Found During Testing

- `actionLabel()` 缺少 `repair` 映射，导致修复版候选稿卡片显示原始 action 字符串
- Fix: 添加 `repair: '修复版'` 到 labels + 添加 `.action-repair` CSS badge

---

## 8. Remaining Issues

None.

---

## 9. 建议

T10.2b 已完成全部验收标准。建议进入 T10.2b-final-verify 或直接进入 T10.3。

---

## 10. Git 信息

- Base commit: `edd3775` (docs: design T10.2 candidate compare MVP)
- Branch: main
- Commit message: `feat: add candidate compare MVP`
