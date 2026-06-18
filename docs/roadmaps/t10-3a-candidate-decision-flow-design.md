# T10.3a：Candidate Decision Flow 设计

> **阶段**: T10.3a (Design Documentation)
> **状态**: ✅ 设计完成
> **创建日期**: 2026-06-18
> **下一步**: T10.3b — Candidate Decision Flow UI 实现

---

## 1. 当前背景

截至 T10.2b 完成（commit `dadbe1e`），CandidatePanel 已具备以下操作能力：

| 操作 | 按钮 title | 可见条件 | 写入行为 |
|------|-----------|---------|---------|
| 预览 | 预览 | 始终可见 | 无（只读） |
| 比较差异 | 比较差异 | 始终可见 | 无（只读） |
| 采用 | 采用 | status=pending | 写入正文 |
| 删除 | 删除 | 始终可见 | 删除候选稿 |
| 反馈再生成 | 按反馈再生成 | status=pending | 生成 child candidate |
| 修复候选稿 | 基于警告修复 | status=pending 且有 repairable warning | 生成 child candidate |

此外还有非按钮操作：

| 功能 | 可见条件 |
|------|---------|
| Quality Summary badges | candidate.quality 存在 |
| Quality Explanation 可展开区 | 始终显示（old candidate 显示占位） |
| Quality Check 区（beat validation / continuity） | hasQualityInfo() |
| Revision 来源区 | isFeedbackRevision(candidate) |

这些能力单独都成立，但用户在候选稿生成后面临一个决策困境：

```
我应该先看什么？先做什么？
有 warning 时应该 repair 还是 feedback revision？
什么时候应该 adopt？
```

T10.3a 的目标是把这些操作组织成一个清晰的用户决策流。

---

## 2. 为什么需要 Candidate Decision Flow

### 2.1 用户心智模型不匹配

当前系统给用户呈现的是一组并列的操作按钮，但用户的实际决策过程是有顺序的：

```
先看懂 → 再比较 → 再确认 → 最后采纳
```

如果所有按钮平等展示，用户可能：

- 跳过质量提示直接 adopt
- 不知道 repair 和 feedback revision 的区别
- 在有 warning 时仍然直接 adopt
- 对已 adopted 的 candidate 仍然看到一些不可用按钮

### 2.2 操作数量增长

T10.1 新增了 Quality Explanation（1 个可展开区）。
T10.2 新增了 Compare（1 个按钮 + 1 个 modal）。
加上原有的 Preview / Adopt / Delete / Repair / Feedback Revision，面板已经有 6 个按钮和 3 个非按钮功能。

需要明确哪些操作是主要路径、哪些是辅助路径、哪些是危险操作。

### 2.3 安全边界需要显式化

candidate-only 安全工作流的核心是"用户显式 adopt 才写入正文"。但如果 adopt 按钮和 preview 按钮在视觉上平等，用户可能形成"随手点 adopt"的习惯，削弱安全边界的意义。

---

## 3. 当前候选稿操作清单

### 3.1 查看类操作（只读，不改变任何状态）

| 操作 | 入口 | 产出 | 适用场景 |
|------|------|------|---------|
| Quality Explanation | 卡片内可展开区 | 5 维度质量提示 | 所有 candidate |
| Compare | 比较差异按钮 + modal | 行级 diff 视图 | 所有 candidate |
| Preview | 预览按钮 + modal | 候选稿全文 | 所有 candidate |

### 3.2 修改类操作（生成 child candidate，不写入正文）

| 操作 | 入口 | 产出 | 适用条件 |
|------|------|------|---------|
| Repair | 修复候选稿按钮 | child candidate (action=repair) | pending + repairable warning |
| Feedback Revision | 按反馈再生成按钮 + modal | child candidate (action=feedback_revision) | pending |

### 3.3 终态操作（改变 candidate 状态或正文）

| 操作 | 入口 | 产出 | 适用条件 |
|------|------|------|---------|
| Adopt | 采用按钮 | 写入正文 + status→adopted | pending |
| Delete | 删除按钮 | 删除候选稿 | 所有 status |

---

## 4. 推荐用户路径

### 4.1 主路径（推荐顺序）

```
候选稿生成
  ↓
① Quality Explanation（折叠态摘要）
  ↓  展开查看 5 维度提示
② Compare（比较差异）
  ↓  查看相对原文/父候选稿的改动
③ Preview（预览全文）
  ↓  阅读完整效果
④ 满意 → Adopt
   不满意 → Repair 或 Feedback Revision → 回到 ①
```

### 4.2 快捷路径（质量全通过时）

```
候选稿生成
  ↓
① Quality Explanation 全部 pass
  ↓
② Preview 快速确认
  ↓
③ Adopt
```

### 4.3 修订路径（有问题时）

```
候选稿生成
  ↓
① Quality Explanation 有 warning
  ↓
② 判断类型：
   - 系统可识别的 warning → Repair
   - 用户主观不满意 → Feedback Revision
  ↓
③ Child candidate 生成
  ↓
④ 回到主路径 ①
```

### 4.4 重要声明

```
以上路径只是推荐，不是强制流程。
用户可以按任何顺序使用任何功能。
系统不做强制 gate，不阻断 adopt。
```

---

## 5. Quality / Compare / Preview 的关系

三者是互补的查看工具，不是替代关系：

### 5.1 Quality Explanation

**回答的问题**：这个候选稿哪里可能有问题？

**信息来源**：rule-based 5 维度检查（instruction_following, continuity, style_preservation, change_scope, forbidden_check）

**用户获得**：哪些维度通过、哪些需注意、哪些未检测

**不包含**：具体改了什么内容、候选稿读起来如何

### 5.2 Compare

**回答的问题**：相对原文/父候选稿改了什么？

**信息来源**：行级 diff 算法

**用户获得**：新增/删除/修改了哪些行、字数变化

**不包含**：改得好不好、读起来流畅不流畅

### 5.3 Preview

**回答的问题**：候选稿完整读起来如何？

**信息来源**：候选稿全文

**用户获得**：完整的阅读体验

**不包含**：改了什么、哪里有问题

### 5.4 关系总结

```
Quality Explanation → "哪里可能有问题"
Compare → "改了什么"
Preview → "读起来怎么样"
```

三个入口不互相替代，不互相重复。用户可以按任何顺序使用。

---

## 6. Repair / Feedback Revision 的边界

### 6.1 Repair

**适用场景**：系统可识别的质量 warning

具体触发条件（`hasRepairableWarning`）：

```
instruction_following === 'warning'
forbidden_check === 'warning'
change_scope === 'large'
```

**用户心智**：

```
"AI 在信息点检查/禁区检查方面有问题，让系统尝试修复"
```

**不做**：

```
Repair 不是自动修文
Repair 不保证修复成功
Repair 只生成 child candidate，不自动采纳
```

### 6.2 Feedback Revision

**适用场景**：用户主观意见

具体触发条件：

```
用户点击"按反馈再生成"按钮
填写反馈文本或选择快捷反馈
```

**用户心智**：

```
"AI 写得不够好，我想告诉它怎么改"
```

**不做**：

```
Feedback Revision 不是直接覆盖正文
Feedback Revision 只生成 child candidate
Feedback Revision 不自动采纳
```

### 6.3 两者的关键区别

| 维度 | Repair | Feedback Revision |
|------|--------|-------------------|
| 触发来源 | 系统 warning | 用户主观意见 |
| 用户输入 | 无需（一键触发） | 需要填写反馈 |
| 生成依据 | warning 类型 | 用户反馈文本 |
| 按钮可见条件 | pending + repairable warning | pending |
| 产出 | child (action=repair) | child (action=feedback_revision) |

### 6.4 共同规则

```
两者都只生成 child candidate
两者都不自动采纳
两者都不写入正文
两者都继承 parent 的 source_path
两者都可被再次 repair / feedback revision
```

---

## 7. Adopt 前提示策略

### 7.1 当前行为

当前 adopt 前已有 confirm dialog：

```
确认将该候选稿写入当前正文？
此操作会替换 "sec-001.md" 的当前内容。

采用前会检查正文是否被其他操作修改，避免误覆盖。
```

如果 candidate 有 warning，会额外提示：

```
⚠ 该候选稿存在采用前警告：
[warning message]
```

如果文件有未保存修改，会额外提示：

```
⚠ 该文件有未保存的修改，采用候选稿将覆盖这些修改且无法恢复。
```

### 7.2 T10.3 建议：轻量提示，不强制 gate

建议在现有 confirm dialog 中增加一行提示（如果用户尚未查看质量提示）：

```
提示：建议先查看质量提示和比较差异，确认无误后再采纳。
```

但这个提示只是建议性的，不阻断 adopt。

### 7.3 不做强制 gate 的原因

```
强制 gate 会增加操作成本
用户可能只是想快速 adopt 一个简单润色
quality metadata 只是 advisory，不是硬性评分
用户始终拥有最终判断权
```

### 7.4 后续可选优化

如果后续需要更强的提示，可以考虑：

```
在 adopt 按钮旁边显示一个小图标提示（如 ⓘ）
hover 时显示 "建议先查看质量提示"
但点击仍然直接触发 adopt confirm
```

---

## 8. 按钮优先级

### 8.1 推荐排序

```
card-actions-primary（主要操作区）：
  1. 预览 — 最常用的查看操作
  2. 比较差异 — 第二常用查看操作
  3. 采用 — 终态操作（仅 pending）

card-actions-secondary（辅助操作区）：
  4. 反馈再生成 — 修订操作（仅 pending）
  5. 修复候选稿 — 修订操作（仅 pending + repairable warning）

card-actions（始终可见）：
  6. 删除 — 危险操作，始终可用
```

### 8.2 视觉分层建议

```
查看动作（预览、比较差异）：
  - 使用中性色调（var(--text-secondary)）
  - 图标为主，紧凑

终态动作（采用）：
  - 使用成功色（var(--accent-success)）
  - 视觉上突出

修订动作（反馈再生成、修复候选稿）：
  - 使用特殊色（紫色 / 橙色）
  - 带文字标签

危险动作（删除）：
  - 使用中性色，hover 时变红
  - 不与查看动作紧邻
```

### 8.3 当前实现 vs 建议

当前实现中所有按钮在 `card-actions` 和 `card-actions-primary` 中混排。

建议 T10.3b 调整为：

```
card-actions-primary: [预览] [比较差异] [采用]
card-actions-secondary: [反馈再生成] [修复候选稿]
card-actions-trailing: [删除]
```

这样危险操作（删除）在视觉上和查看/终态操作分离。

---

## 9. Candidate 状态矩阵

### 9.1 状态定义

| 状态 | 含义 |
|------|------|
| pending | 待处理，可被 adopt / repair / revise |
| adopted | 已采用，正文已更新 |
| discarded | 已放弃（未来状态，当前未实现） |

### 9.2 操作可用矩阵

| 操作 | pending | adopted | discarded |
|------|---------|---------|-----------|
| Quality Explanation | ✅ 可见 | ✅ 可见 | ✅ 可见 |
| Compare | ✅ 可用 | ✅ 可用 | ✅ 可用 |
| Preview | ✅ 可用 | ✅ 可用 | ✅ 可用 |
| Adopt | ✅ 可用 | ❌ 隐藏 | ❌ 隐藏 |
| Repair | ✅ 可用（有 warning 时） | ❌ 隐藏 | ❌ 隐藏 |
| Feedback Revision | ✅ 可用 | ❌ 隐藏 | ❌ 隐藏 |
| Delete | ✅ 可用 | ✅ 可用 | ✅ 可用 |

### 9.3 特殊场景

| 场景 | 说明 |
|------|------|
| repair child (pending) | 可 preview / compare / adopt / 再次 repair / feedback revision |
| feedback revision child (pending) | 可 preview / compare / adopt / repair / 再次 feedback revision |
| old candidate 无 quality metadata | Quality Explanation 显示占位文本，其他操作正常 |
| parent 缺失 | Compare fallback 到模式 A（当前正文 vs candidate） |
| adopted candidate | 可查看但不可再次 adopt / repair / revise |

### 9.4 child candidate 的 lineage 显示

repair child 和 feedback revision child 应显示修订来源区：

```
🔀 反馈修订稿 · 第 N 版
来自 [parent_id]
反馈：[feedback summary]
```

当前已实现（`card-revision` section）。

---

## 10. Candidate-only 安全边界

### 10.1 不变的安全规则

```
Quality Explanation 不阻断 adopt
Compare 不提供 adopt 按钮
Repair 不自动采纳
Feedback Revision 不自动采纳
Adopt 仍然是唯一写入正文的动作
Delete / Discard 不修改正文
```

### 10.2 决策流不改变安全边界

T10.3 的决策流设计是用户体验层面的优化：

```
不改变任何 API 行为
不改变 candidate 状态机
不改变 adopt 的冲突检测逻辑
不改变 repair / feedback revision 的生成逻辑
```

### 10.3 Adopt 是唯一写入动作

```
Preview → 只读
Compare → 只读
Quality Explanation → 只读
Repair → 生成 child candidate（不写正文）
Feedback Revision → 生成 child candidate（不写正文）
Adopt → 写入正文（唯一入口）
Delete → 删除候选稿（不改正文）
```

---

## 11. 不做事项

### 11.1 不做强制 adopt gate

原因：

- 增加操作成本
- quality metadata 只是 advisory
- 用户始终有最终判断权

### 11.2 不做 AI 自动推荐最佳候选稿

原因：

- 需要额外 LLM 调用
- 用户可能不信任 AI 推荐
- 当前质量提示已经提供了足够信息

### 11.3 不做候选稿评分排名

原因：

- quality metadata 不是评分
- 不同 action 的 candidate 不适合直接比较分数
- 排名可能误导用户

### 11.4 不改后端

所有变更限于前端 UI 层。

### 11.5 不改 candidate 状态机

不引入新状态，不改变现有状态转换规则。

---

## 12. T10.3b 实现建议

### 12.1 建议实现内容

1. **按钮分组调整**：将 card-actions 分为 primary / secondary / trailing 三层
2. **Adopt 提示优化**：在 confirm dialog 中增加"建议先查看质量提示"提示行
3. **状态矩阵对齐**：确认所有按钮的 v-if 条件与矩阵一致
4. **E2E 测试更新**：验证按钮优先级和状态矩阵

### 12.2 建议不做

- 不新增按钮
- 不新增 API
- 不改后端
- 不改 candidate 状态机
- 不做强制 gate

### 12.3 修改文件预估

- `frontend/src/components/right-panel/CandidatePanel.vue` — 按钮分组 + adopt 提示
- `frontend/tests/e2e/14-candidate-workflow.spec.ts` — 按钮顺序和状态矩阵测试

---

## 13. 验收标准

### 13.1 设计验收

- [ ] 明确候选稿推荐决策路径
- [ ] 明确 Quality / Compare / Preview 的关系
- [ ] 明确 Repair / Feedback Revision 的边界
- [ ] 明确 Adopt 前提示策略
- [ ] 明确按钮优先级
- [ ] 明确 candidate 状态矩阵
- [ ] 明确 candidate-only 安全边界

### 13.2 工程验收（T10.3b）

- [ ] 按钮按优先级分组
- [ ] Adopt confirm dialog 包含轻量提示
- [ ] 状态矩阵与实现一致
- [ ] Frontend build 通过
- [ ] Focused E2E 通过
- [ ] 不改后端代码
- [ ] 不改 candidate 状态机

---

## 14. 最终结论

T10.3 Candidate Decision Flow 是一个用户体验层面的设计优化。

核心价值：

- 帮助用户理解"候选稿生成后该做什么"
- 区分查看操作 / 修订操作 / 终态操作的优先级
- 明确 Repair 和 Feedback Revision 的使用场景
- 保持 candidate-only 安全边界不变

T10.3 不改变任何后端行为，不改变 candidate 状态机，不引入强制 gate。

推荐决策路径：Quality Explanation → Compare → Preview → Adopt / Repair / Feedback Revision。

这条路径是建议性的，不是强制性的。用户始终可以按自己的判断使用任何功能。

T10.3b 实现预计只修改 CandidatePanel.vue 的按钮分组和 adopt 提示，不新增组件或 API。
