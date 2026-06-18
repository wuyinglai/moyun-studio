# T10.2a：Candidate Compare MVP 设计

> **阶段**: T10.2a (Design Documentation)
> **状态**: ✅ 设计完成
> **创建日期**: 2026-06-18
> **下一步**: T10.2b — Candidate Compare MVP 实现

---

## 1. 当前背景

截至 T10.1b 完成（commit `4e511d5`），Moyun Studio 的候选稿系统已具备：

```
candidate-only 安全工作流
preview / adopt / delete
feedback revision child candidate
repair candidate child candidate
candidate lineage（parent_candidate_id / revision_group_id / revision_index）
quality metadata（5 维度 rule-based）
quality explanation UI（可展开解释区）
```

用户能看懂候选稿质量提示，但还不能方便地比较候选稿与基准文本之间的差异。当前 preview 只能看候选稿全文，无法直观看出"改了什么"。

T10.2 的目标是设计最小比较能力，让用户在 adopt 前更放心。

---

## 2. 为什么 T10.2 做 Candidate Compare

T10.1 先做了 Quality Explanation UI，因为：

- 解释层成本低、价值高
- 为 Compare 提供了维度标签基础
- 避免一开始就陷入 diff UI 复杂度

T10.2 现在做 Candidate Compare，因为：

- 用户在 adopt 前最常问的问题是"AI 到底改了什么"
- repair / feedback revision 生成了 child candidate，用户需要知道 child 相比 parent 修了什么
- quality explanation 已经告诉用户"哪里需要注意"，compare 让用户"看到具体差异"

两者互补：explanation 告诉"是什么状态"，compare 展示"改了什么内容"。

---

## 3. MVP 范围

### 3.1 做

- 当前正文 vs candidate 的左右并排文本比较
- parent candidate vs child candidate 的左右并排文本比较
- 轻量段落级 / 行级差异高亮（新增绿色、删除红色、修改黄色）
- 长度变化提示（字数增减）
- 比较基准标签（"当前正文" / "父候选稿" / "当前候选稿"）
- candidate-only 安全边界

### 3.2 不做

- 不做任意 candidate A vs candidate B 比较
- 不做复杂 word-level diff
- 不做 merge editor
- 不做 AI 自动总结差异
- 不做自动采纳
- 不做自动修复
- 不做后端 compare API
- 不做真实 LLM 调用
- 不改 candidate 状态机
- 不改 source 写入逻辑

---

## 4. 不做事项

### 4.1 不做任意多候选稿比较

原因：

- 任意比较需要候选稿选择器，UI 复杂度高
- MVP 阶段用户的实际需求是"这个候选稿改了什么"，不是"两个候选稿哪个更好"
- 后续 T10.3+ 可以考虑

### 4.2 不做复杂 word-level diff

原因：

- 中文 word-level diff 需要分词，依赖额外库
- 段落级 / 行级 diff 已经足够满足 MVP 需求
- 如果需要更细粒度的 diff，用户可以逐段阅读

### 4.3 不做 merge editor

原因：

- merge editor 是编辑器级功能，复杂度远超 Compare MVP
- candidate-only 工作流要求用户显式 adopt，merge editor 模糊了这个边界

### 4.4 不做 AI 自动总结差异

原因：

- 需要额外 LLM 调用
- 可能引入延迟和成本
- 用户可以直接看 diff 高亮

### 4.5 不做后端 compare API

原因：

- MVP 比较逻辑可以纯前端实现
- 前端已经有 `get_candidate` 和 `read_file` 接口，可以分别获取两侧文本
- 如果后续需要服务端 diff（如大文件优化），再考虑

---

## 5. 比较模式

MVP 支持两种比较模式：

### 5.1 模式 A：当前正文 vs candidate

适用场景：

- 普通 candidate（action = polish / rewrite / continue / expand / shrink 等）
- 用户想看"AI 相对当前正文改了什么"

左侧（基准）：

- 当前正文（source_path 对应的文件内容）

右侧（候选）：

- candidate 内容

### 5.2 模式 B：parent candidate vs child candidate

适用场景：

- repair child（action = repair）
- feedback revision child（action = feedback_revision）
- 用户想看"修复 / 修订版本相对父版本改了什么"

左侧（基准）：

- parent candidate 内容

右侧（候选）：

- child candidate 内容

### 5.3 模式选择规则

```
if candidate.parent_candidate_id exists and parent is accessible:
    → 模式 B（parent vs child）
else:
    → 模式 A（当前正文 vs candidate）
```

如果 parent 存在但内容缺失（文件被删除），fallback 到模式 A。

---

## 6. 比较基准选择规则

### 6.1 左侧基准

| 场景 | 左侧内容 | 左侧标签 |
|------|----------|----------|
| 普通 candidate | 当前正文 | 当前正文 |
| repair child | parent candidate | 父候选稿 |
| feedback revision child | parent candidate | 父候选稿 |
| parent 缺失 | 当前正文 | 当前正文（fallback） |
| 正文也缺失 | 显示空状态 | — |

### 6.2 右侧候选

始终是当前 candidate 的内容。

右侧标签根据 action 类型显示：

| action | 右侧标签 |
|--------|----------|
| polish | 润色候选稿 |
| rewrite | 重写候选稿 |
| continue | 续写候选稿 |
| repair | 修复版候选稿 |
| feedback_revision | 反馈修订候选稿 |
| 其他 | 当前候选稿 |

### 6.3 基准时间戳

对于模式 A（当前正文 vs candidate），当前正文可能已经被其他操作修改过。

比较视图不依赖 candidate 的 `base_hash` / `base_mtime` 做冲突检测。比较只展示当前状态，不判断"基准是否过期"。

如果用户需要知道基准是否过期，应通过 quality explanation 的 instruction_following 维度和 beat validation 结果判断。

---

## 7. UI 信息架构

### 7.1 入口

在 CandidatePanel 的候选稿卡片中，preview 按钮旁边新增"比较差异"按钮。

按钮图标：`fa-solid fa-code-compare`（或 `fa-solid fa-arrows-left-right`）

按钮位置：card-actions-primary 区域，preview 按钮之后、adopt 按钮之前。

按钮 title：`比较差异`

data-testid：`candidate-compare-button`

### 7.2 Compare Modal

点击"比较差异"后打开 modal，结构与 preview modal 类似：

```
┌─────────────────────────────────────────────┐
│ 候选稿比较                              [X] │
├─────────────────────────────────────────────┤
│ 安全提示条                                    │
│ "比较视图仅用于查看差异，不会修改正文。         │
│  只有点击采纳后，正文才会更新。"               │
├─────────────────────────────────────────────┤
│ [左侧标签]            │ [右侧标签]            │
│ ┌─────────────────┐   │ ┌─────────────────┐  │
│ │                 │   │ │                 │  │
│ │  基准文本        │   │ │  候选稿文本      │  │
│ │  (只读)          │   │ │  (只读)          │  │
│ │                 │   │ │                 │  │
│ │                 │   │ │                 │  │
│ └─────────────────┘   │ └─────────────────┘  │
├─────────────────────────────────────────────┤
│ 摘要信息栏                                    │
│ "左侧：当前正文 (823字)  右侧：润色候选稿 (856字) │
│  字数变化：+33字"                             │
├─────────────────────────────────────────────┤
│                                    [关闭]    │
└─────────────────────────────────────────────┘
```

### 7.3 Diff 视图

MVP 采用左右并排文本 + 行级高亮：

- 新增行：绿色背景（`rgba(34, 197, 94, 0.12)`）
- 删除行：红色背景（`rgba(239, 68, 68, 0.12)`）
- 修改行：黄色背景（`rgba(234, 179, 8, 0.12)`）
- 未变化行：无背景

Diff 算法建议：

- 前端实现，使用 `diff` npm 包（`diff-lines` 模式）
- 如果包体积不可接受，可退化为简单逐行比较
- 不做 word-level diff

### 7.4 摘要信息栏

modal 底部显示一行摘要：

```
左侧：当前正文 (823字)  |  右侧：润色候选稿 (856字)  |  字数变化：+33字
```

如果字数变化为 0：

```
字数变化：无变化
```

如果字数减少：

```
字数变化：-120字
```

---

## 8. Preview / Compare / Adopt 关系

三者是互补的用户决策工具，不是替代关系：

```
Preview：看候选稿完整效果（全文只读）
Compare：看候选稿相对基准改了什么（diff 视图）
Adopt：用户确认后才写入正文（显式操作）
```

### 8.1 用户路径

```
用户在 CandidatePanel 看到候选稿
  → 点击"预览"：看全文效果
  → 点击"比较差异"：看改了什么
  → 满意后点击"采用"：写入正文
```

### 8.2 Compare Modal 中的按钮

MVP 建议 Compare modal 中只放"关闭"按钮。

不放 Adopt 按钮的原因：

- 避免用户在 diff 视图中快速 adopt 而忽略全文效果
- Adopt 应该从 CandidatePanel 卡片或 Preview modal 中触发
- 减少误操作风险

不放"预览候选稿"按钮的原因：

- 用户可以先 preview 再 compare，或先 compare 再 preview
- 两个 modal 不应嵌套
- 保持 modal 简洁

### 8.3 Adopt 入口保持不变

- CandidatePanel 卡片中的 adopt 按钮不变
- Preview modal 中的 adopt 按钮不变
- Compare modal 不新增 adopt 入口

---

## 9. candidate-only 安全边界

### 9.1 比较视图不会写入文件

Compare modal 只读取内容，不调用任何写入 API。

不涉及：

- `candidateAdopt`
- `candidateRepair`
- `candidateRevise`
- `fileSave`

### 9.2 比较视图不会改变 candidate status

打开 Compare modal 不影响 candidate 的 `status` 字段。

candidate 仍然保持 `pending` / `adopted` / `discarded` 状态不变。

### 9.3 比较视图不会触发 LLM

Compare 不调用任何 LLM 接口。

不触发 pipeline、不触发 beat validation、不触发 repair。

### 9.4 比较视图不会创建 repair / revision

Compare modal 中不提供"修复"或"反馈再生成"入口。

这些操作仍然从 CandidatePanel 卡片中触发。

### 9.5 比较视图不会自动 adopt

Compare modal 中不提供 adopt 按钮。

用户必须关闭 Compare modal 后，从 CandidatePanel 或 Preview modal 中手动 adopt。

---

## 10. 空状态与异常状态

### 10.1 candidate content missing

如果 `get_candidate` 返回空内容或请求失败：

```
右侧显示：候选稿内容加载失败，请稍后重试。
```

不阻塞 modal 打开，但右侧区域显示错误提示。

### 10.2 source content missing

如果当前正文文件不存在（source_path 指向的文件被删除）：

```
左侧显示：暂无可比较的原文。
```

不阻塞 modal 打开，但左侧区域显示空状态。

### 10.3 parent candidate missing

如果 child candidate 的 `parent_candidate_id` 存在，但 parent candidate 已被删除：

```
fallback 到模式 A（当前正文 vs candidate）
左侧标签改为：当前正文（父候选稿已删除）
```

### 10.4 old candidate 没有 lineage

old candidate 没有 `parent_candidate_id`、`revision_group_id`、`revision_index`。

这些 candidate 始终使用模式 A（当前正文 vs candidate）。

### 10.5 repair child 没有 parent

如果 repair child 的 parent 被删除，fallback 到模式 A。

### 10.6 feedback child 没有 parent

同上，fallback 到模式 A。

### 10.7 candidate 已 adopted / discarded

已 adopted 或 discarded 的 candidate 仍然可以打开 Compare modal 查看差异。

但 Compare modal 中的内容均为只读，不影响 candidate 状态。

### 10.8 两侧内容相同

如果左侧和右侧内容完全相同：

```
摘要栏显示：两侧内容完全一致，无差异。
```

diff 区域不高亮任何行。

---

## 11. T10.2b 实现建议

### 11.1 新增文件

建议新增：

```
frontend/src/modules/candidate/compareDiff.ts
```

职责：

- `computeLineDiff(leftText, rightText)` — 行级 diff
- `DiffResult` 类型 — 每行的状态（added / removed / modified / unchanged）
- `diffSummary(leftText, rightText)` — 字数变化统计

### 11.2 修改文件

- `frontend/src/components/right-panel/CandidatePanel.vue` — 添加"比较差异"按钮
- `frontend/src/components/right-panel/CompareModal.vue` — 新增 Compare modal 组件

### 11.3 数据获取

不需要新增后端 API。使用现有接口：

```
左侧基准（模式 A）：api.get(`/files/${projectId}?path=${sourcePath}`)
左侧基准（模式 B）：api.get(`/candidates/${projectId}/${parentCandidateId}`)
右侧候选：api.get(`/candidates/${projectId}/${candidateId}`)
```

### 11.4 实现步骤

1. 实现 `compareDiff.ts` — diff 算法 + 类型定义
2. 实现 `CompareModal.vue` — modal 布局 + diff 渲染
3. CandidatePanel 添加 compare 按钮 + 打开 modal
4. 添加 E2E 测试
5. 运行 build + E2E

### 11.5 不做事项

- 不新增后端 API
- 不改 candidate 状态机
- 不改 adopt / preview / repair / revision 行为
- 不做 word-level diff
- 不做 AI 总结

---

## 12. 验收标准

### 12.1 功能验收

- [ ] 普通 candidate 可以打开 Compare modal，左侧为当前正文，右侧为 candidate
- [ ] repair child 可以打开 Compare modal，左侧为 parent candidate，右侧为 child
- [ ] feedback revision child 可以打开 Compare modal，左侧为 parent candidate，右侧为 child
- [ ] parent 缺失时 fallback 到当前正文
- [ ] diff 高亮正确显示新增 / 删除 / 修改行
- [ ] 摘要栏正确显示字数变化
- [ ] 空状态正确显示

### 12.2 安全验收

- [ ] Compare modal 不触发任何写入 API
- [ ] Compare modal 不改变 candidate status
- [ ] Compare modal 不触发 LLM 调用
- [ ] Compare modal 不提供 adopt / repair / revision 入口
- [ ] 安全提示条始终可见

### 12.3 兼容性验收

- [ ] old candidate 无 lineage 时使用模式 A
- [ ] candidate 已 adopted / discarded 仍可比较
- [ ] 两侧内容相同时显示"无差异"

### 12.4 工程验收

- [ ] TypeScript 类型检查通过
- [ ] Vite build 通过
- [ ] 现有 E2E 测试不回归
- [ ] 新增 focused E2E 测试通过

---

## 13. 最终结论

T10.2 Candidate Compare MVP 是一个纯前端的轻量比较功能。

核心价值：

- 让用户在 adopt 前看到"AI 改了什么"
- repair / feedback revision 用户能看到"修复了什么"
- 不改变现有安全工作流

MVP 聚焦两种比较模式（当前正文 vs candidate、parent vs child），不做任意比较多候选稿比较。

Diff 采用行级高亮，不做 word-level diff。Compare modal 只提供查看功能，不提供 adopt / repair / revision 入口，严格保持 candidate-only 安全边界。

T10.2b 实现预计修改 2-3 个文件，新增 1 个辅助模块和 1 个 modal 组件，不新增后端 API。
