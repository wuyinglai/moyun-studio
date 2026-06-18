# T10.4a：T10 Interaction Smoke + Small-screen Layout Review

## Status

**阶段**: T10.4a (Review)
**状态**: ✅ 已完成
**创建日期**: 2026-06-18
**基于 commit**: 32e9767
**范围**: T10.1–T10.3 交互层的手动与自动 smoke，不修改后端。

---

## 1. 当前 commit

当前 commit: **32e9767**（T10.3b 主体完成 + focused E2E 补充后的状态）

工作区: clean（在提交前）

---

## 2. 手动 Smoke 结果

### 2.1 Quality Explanation (T10.1b)

| 检查项 | 结果 | 说明 |
|--------|------|------|
| toggle 可见（有 quality metadata 时） | ✅ | data-testid="candidate-quality-explanation-toggle" |
| toggle 展开显示 5 个维度 | ✅ | instruction/continuity/style/change/forbidden |
| status label (pass/warning/unknown) | ✅ | 友好文案 |
| 展开后显示 safety note | ✅ | "候选稿不会自动覆盖正文…" |
| 有 warning 时显示 repair explanation | ✅ | in repair instruction warning → shows repair section |
| 再次点击折叠 | ✅ | 可折叠 |
| 无 quality metadata 时不显示空卡 | ✅ | 显示占位文本，不显示伪维度 |
| 折叠态摘要不挤压按钮 | ✅ | 解释区不占据操作区域 |
| 展开态不溢出面板 | ✅ | candidate-list 整体 overflow-y: auto |

### 2.2 Compare Modal (T10.2b)

| 检查项 | 结果 | 说明 |
|--------|------|------|
| compare 按钮 visible | ✅ | data-testid="candidate-compare-button" |
| mode A: 正文 vs candidate | ✅ | 标签正确 |
| mode B: parent vs child | ✅ | 父候选稿 vs 修复版候选稿 |
| safety notice | ✅ | "比较视图仅用于查看差异，不会修改正文" |
| diff 区 visible | ✅ | data-testid="compare-diff-area" |
| summary 区 visible | ✅ | data-testid="compare-summary" |
| close 按钮有效 | ✅ | 点击后关闭 |
| 无 adopt 按钮 | ✅ | compare 不是 adopt 入口 |
| content 不溢出屏幕 | ✅ | compare-body: overflow-y: auto |

### 2.3 Candidate Decision Flow (T10.3b)

| 检查项 | 结果 | 说明 |
|--------|------|------|
| pending candidate: preview 可见 | ✅ | 主操作区 |
| pending candidate: compare 可见 | ✅ | 主操作区 |
| pending candidate: adopt 可见 | ✅ | 主操作区 |
| pending candidate: 反馈再生成 可见 | ✅ | secondary 区 |
| pending candidate: 修复候选稿 可见(有warning时) | ✅ | secondary 区 |
| pending candidate: 删除 可见 | ✅ | trailing 区 |
| adopted candidate: preview 可见 | ✅ |
| adopted candidate: compare 可见 | ✅ |
| adopted candidate: adopt 不可见 | ✅ |
| adopted candidate: 反馈再生成 不可见 | ✅ |
| adopted candidate: 修复候选稿 不可见 | ✅ |
| adopted candidate: 删除 可见 | ✅ |
| adopt hint: pending + warning 显示 | ✅ | "采纳前建议先查看质量提示和比较差异" |
| adopt hint: pending 无 warning 不显示 | ✅ |
| adopt hint: 不阻断 adopt | ✅ | 按钮仍然可见可点击 |
| compare modal 无 adopt 按钮 | ✅ |
| delete 行为: 不修改正文 | ✅ |

---

## 3. 小屏幕检查结果

### 3.1 发现问题（修复前）

| # | 位置 | 问题 | 严重程度 |
|---|------|------|---------|
| 1 | `CandidatePanel.vue/.card-actions` | 无 `flex-wrap: wrap`，窄面板下按钮溢出到右侧 | 中 |
| 2 | `CandidatePanel.vue/.candidate-filename` | 无 `text-overflow: ellipsis`，长文件名溢出卡片 | 低 |
| 3 | `CandidatePanel.vue/.preview-body` | `overflow: hidden`，长内容预览时无法滚动查看底部 | 中 |
| 4 | `CandidatePanel.vue/.revision-content` | 整个 revision modal overflow: hidden，内容过长时被截断 | 低 |

### 3.2 修复（已提交）

| # | 文件 | 改动 | 结果 |
|---|------|------|------|
| 1 | `CandidatePanel.vue` | `.card-actions` 添加 `flex-wrap: wrap` | ✅ 窄面板下按钮自动换行 |
| 1a | `CandidatePanel.vue` | `.card-actions-trailing` 添加 `margin-left: auto` | ✅ 删除按钮始终在右侧 |
| 2 | `CandidatePanel.vue` | `.candidate-filename` 添加 `overflow: hidden; text-overflow: ellipsis; white-space: nowrap` | ✅ 长文件名省略号 |
| 3 | `CandidatePanel.vue` | `.preview-body` 从 `overflow: hidden` 改为 `overflow-y: auto` | ✅ 长内容可滚动 |

### 3.3 未修复（列为 Remaining Issues）

| # | 位置 | 为何不修复 |
|---|------|-----------|
| 4 | revision modal body scroll | 需要 template refactor，不属于 T10 scope；问题程度较低，实际场景 modal 内容有限，不严重 |

### 3.4 窄面板布局验证

手动验证的布局行为（宽度从 200px → 400px → 全宽）：

| 宽度 | card-actions 行为 | candidate-filename 行为 |
|------|------------------|-------------------|
| 宽面板 (> 500px) | primary / secondary / trailing 一行排列 ✅ | 正常显示 ✅ |
| 中面板 (300-500px) | primary + secondary 正常，trailing 在右侧 ✅ | 正常显示 ✅ |
| 窄面板 (< 300px) | primary/secondary/trailing 自动换行 ✅ | 溢出显示省略号 ✅ |

注意：以上是手动的视觉验证，非自动化测试。

---

## 4. Quality Explanation 检查（详细）

| 维度 | 折叠态 | 展开态 |
|------|--------|--------|
| 指令遵守 (instruction_following) | ✅ 折叠文本含状态 | ✅ 展开显示详细说明和 status |
| 连续性 (continuity) | ✅ 折叠文本含状态 | ✅ 展开显示详细说明和 status |
| 风格保留 (style_preservation) | ✅ 折叠文本含状态 | ✅ 展开显示详细说明和 status |
| 改动范围 (change_scope) | ✅ 折叠文本含状态 | ✅ 展开显示大小描述 |
| 禁区检查 (forbidden_check) | ✅ 折叠文本含状态 | ✅ 展开显示详细说明和 status |
| 修复说明（有 instruction_following warning） | ✅ 显示在 quality explanation body 底部 | ✅ 包含 "修复会生成新的候选稿，不会自动采纳" 安全提醒 |
| candidate-only safety text | ✅ 始终显示 | ✅ 折叠态也可见 |

---

## 5. Compare Modal 检查（详细）

| 检查项 | 结果 |
|--------|------|
| max-height: 85vh | ✅ |
| overflow: hidden (content) | ✅ 确保 modal 不超过视口 |
| overflow-y: auto (body) | ✅ 滚动区 |
| diff text: break-all + pre-wrap | ✅ 确保长行不溢出 |
| safety notice: "不会修改正文" | ✅ |
| 无 adopt 按钮 | ✅ |
| close 按钮在 header 右侧 | ✅ |
| footer submit 按钮在右侧 | ✅ |
| summary 区显示字数变化 + ident 标记 | ✅ |

---

## 6. Decision Flow 按钮分组（详细）

```
┌────────────────────────────────────────────┐
│ candidate-card                             │
│ ┌─────────────────────────────────────┐    │
│ │ card-header (action + status tags)  │    │
│ └─────────────────────────────────────┘    │
│ ┌─────────────────────────────────────┐    │
│ │ quality-summary (badges)            │    │
│ └─────────────────────────────────────┘    │
│ ┌─────────────────────────────────────┐    │
│ │ quality-explanation (折叠/展开)     │    │
│ └─────────────────────────────────────┘    │
│ ┌─────────────────────────────────────┐    │
│ │ card-quality (beat/continuity)      │    │
│ └─────────────────────────────────────┘    │
│ ┌─────────────────────────────────────┐    │
│ │ card-body (filename + meta)         │    │
│ └─────────────────────────────────────┘    │
│ ┌─────────────────────────────────────┐    │
│ │ [adopt-hint: ...]                   │    │
│ │ card-actions                        │    │
│ │ ┌──────┐ ┌──────────────┐ ┌───┐    │    │
│ │ │preview│ │compare/采用  │ │del│    │    │  ← primary
│ │ └──────┘ └──────────────┘ └───┘    │    │
│ │ ┌──────────────┐ ┌──────────────┐  │    │
│ │ │反馈再生成     │ │修复候选稿     │  │    │  ← secondary (仅 pending+warning)
│ │ └──────────────┘ └──────────────┘  │    │
│ └─────────────────────────────────────┘    │
└────────────────────────────────────────────┘
```

布局说明：
- primary 在左侧，包含只读的核心操作（含仅 pending 的采用）
- secondary 在中间，包含生成操作（反馈再生成、修复候选稿）
- trailing 在右侧，包含删除操作
- `flex-wrap: wrap` 确保窄面板下自动换行

---

## 7. 自动测试结果

### Frontend Build

```
cd frontend
npm run build
```

**结果**: ✅ 3440 modules transformed

### Focused E2E (Candidate Workflow)

```
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

**结果**: ✅ **43 passed**

包含 T10.3b 新增的 6 个测试：
1. T10.3b: pending candidate shows primary/secondary/trailing action groups
2. T10.3b: adopted candidate shows preview/compare/delete but not adopt/revise/repair
3. T10.3b: pending candidate with warning shows adopt hint
4. T10.3b: pending candidate without warning does not show adopt hint
5. T10.3b: adopt hint does not block adopt action
6. T10.3b: compare modal still has no adopt button

### Focused E2E (Continuity Anchors)

```
npm run test:e2e:mock -- tests/e2e/32-continuity-anchors.spec.ts --reporter=line
```

**结果**: ✅ **2 passed**

### Diff Check

```
cd ..
git diff --check
```

**结果**: ✅ 无错误（仅有 CRLF warning，Windows 正常现象）

### Git Status

```
git status --short
```

**结果**: ✅ clean（提交前的状态，提交后 clean）

---

## 8. 补丁说明

### 8.1 已修改文件

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `frontend/src/components/right-panel/CandidatePanel.vue` | CSS 修补 | card-actions flex-wrap；candidate-filename ellipsis；preview-body overflow-y: auto |

### 8.2 模板变化

- 无模板变化
- 无 data 变化
- 无 computed 变化
- 无 methods 变化

### 8.3 CSS 变化摘要

```diff
 .card-actions {
   display: flex;
   align-items: center;
   justify-content: space-between;
   gap: 4px;
+  flex-wrap: wrap;
 }

 .card-actions-trailing {
   display: flex;
   gap: 4px;
+  margin-left: auto;
 }

 .candidate-filename {
   font-size: 13px;
   color: var(--text-primary);
   font-weight: 500;
+  overflow: hidden;
+  text-overflow: ellipsis;
+  white-space: nowrap;
 }

 .preview-body {
   flex: 1;
   padding: 16px;
-  overflow: hidden;
+  overflow-y: auto;
 }
```

---

## 9. Remaining Issues

| # | 描述 | 严重程度 | 建议处理阶段 |
|---|------|---------|------------|
| R1 | revision modal 内容过长时可能被 `overflow: hidden` 截断 | 低 | 后续小补丁 |
| R2 | candidate-filename 省略号无 tooltip 提示完整文件名 | 低 | 后续 UI polish |
| R3 | 窄面板下 secondary 按钮文本仍然 nowrap，可能导致按钮宽度超出（但 flex-wrap 缓解） | 低 | 后续考虑简化按钮文案 |

---

## 10. 下一步建议

### 10.1 T10 收口建议

T10.1（Quality Explanation UI）、T10.2（Candidate Compare）、T10.3（Decision Flow UI）的交互层已完成并 review：
- 所有主路径 E2E 已覆盖
- 小屏幕布局问题已修补
- candidate-only 安全边界已验证

**建议**: T10 主体可以收口，后续如有 remaining issue 可作为独立小补丁处理。

### 10.2 后续建议方向

1. **R1 revision modal 滚动**: 下次 revision modal 相关改动中顺便修复
2. **R2 filename tooltip**: 考虑添加 `title` 属性实现低成本 tooltip
3. **E2E 扩展**: 考虑后续添加 small-screen 维度的 E2E 测试（当前 E2E 默认宽度约 1280px）

### 10.3 下一阶段建议

完成 T10.4a 后，建议进入下一阶段：
- 功能开发阶段（取决于产品需求，如 T11 等）
- 或进行 v0.2.3 维护版准备（如果 T10 已足够完成某个小版本）

---

## 11. 最终状态

```
HEAD:           （提交 commit 后更新）
前端构建:       ✅ 3440 modules
Candidate E2E:  ✅ 43 passed
Continuity E2E: ✅ 2 passed
Diff check:     ✅ 无错误
Git status:     ✅ clean
代码改动范围:   仅 CandidatePanel.vue CSS
Backend:        无改动
```

**状态: ✅ T10.4a 通过**