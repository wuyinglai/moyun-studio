# Phase T4.7.1a — Professional Candidate Flow Dry-run

**执行日期**: 2026-06-06

**执行方式**: 代码分析 + UI 审查

**目标**: 验证从 Professional 工具栏到 candidate 展示的最小链路

---

## Test Setup

- **Status**: ✅ 通过
- **Project URL**: http://localhost:5174/project/demo-novel
- **Scene Opened**: ✅ 通过

### 测试环境
- 后端: http://localhost:8000 (运行中)
- 前端: http://localhost:5174 (运行中)
- 测试项目: demo-novel

---

## Generation/Editing Trigger Result

### 工具栏按钮分析

**Status**: ✅ 找到工具栏按钮

**可用的生成/编辑入口**:

1. **📄 写下一场景** (EditorToolbar.vue)
   - 位置: EditorToolbar 组件
   - 功能: 生成下一个场景
   - 调用: `continueWriting()` → `/api/generate` 或 `runPipeline()`

2. **✏️ 润色** (EditorToolbar.vue)
   - 位置: EditorToolbar 组件
   - 功能: 润色当前场景
   - 调用: `polishContent()` → `runPipeline('polish')`

3. **📦 精修** (EditorToolbar.vue)
   - 位置: EditorToolbar 组件
   - 功能: 精修当前场景
   - 调用: `refineContent()` → `runPipeline('polish')`

4. **🌟 提取** (EditorToolbar.vue)
   - 位置: EditorToolbar 组件
   - 功能: 提取素材
   - 调用: `extractMaterial()` → `/api/extract`

5. **🔄 重新生成** (EditorToolbar.vue)
   - 位置: EditorToolbar 组件
   - 功能: 重新生成当前场景
   - 调用: `regenerateContent()` → `runPipeline('rewrite')`

6. **➕ 自定义** (EditorToolbar.vue)
   - 位置: EditorToolbar 组件
   - 功能: 自定义生成
   - 调用: 用户自定义 prompt

### 候选稿入口

**Status**: ✅ 入口存在，但需要进一步验证

**入口点**:
- EditorToolbar 组件中的"润色"、"精修"、"重新生成"按钮
- ChatPanel 中的生成建议
- Workflow Panel 中的管线执行

---

## Candidate Creation Result

### API 链路分析

**Status**: ⚠️ 需要真实 LLM 才能验证

**Pipeline YAML 链路**:

```
polish.yaml:
  - step: depai
    prompt: prompts/pipeline/polish/depai.md
    output: candidates/{timestamp}_depai.md
  
  - step: logic
    prompt: prompts/pipeline/polish/logic.md
    output: candidates/{timestamp}_logic.md
  
  - step: prose
    prompt: prompts/pipeline/polish/prose.md
    output: candidates/{timestamp}_prose.md
  
  - step: rhythm
    prompt: prompts/pipeline/polish/rhythm.md
    output: candidates/{timestamp}_rhythm.md
  
  - step: merge
    input: [depai, logic, prose, rhythm]
    output: candidates/{timestamp}_final.md (as candidate)
```

**问题**:
1. **无法 dry-run**: polish/rewrite pipeline 会调用真实 LLM
2. **需要 mock 数据**: 如果要测试 candidate 展示，需要手动创建测试 candidate

### Auto Mode 设置

**Auto Mode**: L1 (默认)

**影响**:
- L1 模式: 任务会等待用户确认（`taskStore.waitForConfirm()`）
- L2 模式: 任务自动完成

---

## CandidatePanel Display Result

### UI 组件分析

**Status**: ✅ UI 组件完整

**CandidatePanel.vue 组件结构**:

1. **面板头部**
   - 标题: "候选稿"
   - 刷新按钮

2. **空状态**
   - 图标: `fa-file-text`
   - 文案: "暂无候选稿" 或 "加载中..."

3. **候选稿列表**
   - 循环渲染 `candidate` 数组
   - 每个 `candidate-card` 包含:
     - 操作类型标签 (action)
     - 状态标签 (status)
     - 文件名
     - 元信息 (时间、字数)
     - 操作按钮

4. **预览弹窗**
   - 预览标题
   - 源文件信息
   - 内容文本域 (只读)
   - 底部操作按钮

### 找到的元素

- ✅ Tab 标签: `text=候选稿`
- ✅ Panel 容器: `[data-testid="candidate-panel"]`
- ✅ 空状态: `text=暂无候选稿`
- ✅ 预览按钮: `.action-btn` (fa-eye 图标)
- ✅ 采用按钮: `.action-adopt` (fa-check 图标)
- ✅ 删除按钮: `.action-delete` (fa-trash-can 图标)

---

## Preview Result

### 预览功能分析

**Status**: ⚠️ UI 完整，需要真实数据验证

**Preview 功能**:
1. 点击预览按钮 → `previewCandidate(candidate)`
2. 打开预览弹窗
3. 显示候选稿内容
4. 可选择 adopt 或关闭

**UI Elements**:
- ✅ 预览按钮: `.action-btn` (title="预览")
- ✅ 预览弹窗: `.preview-modal`
- ✅ 预览内容: `.preview-textarea` (readonly)
- ✅ 关闭按钮: `.btn-close`
- ✅ adopt 按钮: `.btn-adopt` (在预览弹窗中)

---

## Adopt/Delete Result

### Adopt 功能分析

**Status**: ⚠️ UI 完整，需要真实数据验证

**Adopt 流程**:
1. 点击 adopt 按钮 → `adoptCandidate(candidate)`
2. 检查 base_hash / base_mtime 冲突
3. 如果有冲突，显示确认对话框
4. 执行 adopt 操作
5. 更新文件内容
6. 触发 `candidate_adopted` SSE 事件

**Delete 功能分析**:

**Status**: ⚠️ UI 完整，需要真实数据验证

**Delete 流程**:
1. 点击 delete 按钮 → `deleteCandidate(candidate)`
2. 确认删除
3. 从候选稿列表移除
4. 删除候选稿文件

**UI Elements**:
- ✅ Adopt 按钮: `[data-testid="candidate-adopt-button"]` (仅 pending 状态可见)
- ✅ Delete 按钮: `[data-testid="candidate-reject-button"]`

**冲突检查机制**:
- ✅ 使用 `expected_mtime` / `expected_hash` 校验
- ✅ 如果冲突，显示确认对话框

---

## SSE/file.updated Result

### SSE 事件分析

**Status**: ⚠️ 未验证 - 需要真实生成才能触发

**预期的 SSE 事件**:

1. **candidate.created** (映射为 `file-created`)
   - 触发时机: 候选稿生成完成
   - 数据: `{ project_id, candidate_id, source_path }`

2. **candidate.adopted** (映射为 `file-updated`)
   - 触发时机: 候选稿被采用
   - 数据: `{ project_id, file_path, new_content }`

3. **file.updated**
   - 触发时机: 文件被修改
   - 数据: `{ project_id, file_path, mtime, hash }`

**SSE 连接状态**:
- ✅ 连接状态可见 (按钮显示 "已连接" 或 "已断开")

---

## Whether LLM was called

❌ **否** - 仅执行代码分析和 UI 审查，未调用真实 LLM

---

## Whether scene/settings were modified

❌ **否** - 仅分析代码和 UI，未修改任何文件或设置

---

## Blocking Issues

### 阻断问题

1. **无法 dry-run candidate 生成**
   - **原因**: polish/rewrite pipeline 会调用真实 LLM
   - **影响**: 无法测试 candidate 创建、展示、预览等端到端链路
   - **建议**: 需要 mock LLM 或使用真实 LLM 执行测试

2. **没有测试数据**
   - **原因**: 需要先生成候选稿才能测试展示、预览、adopt/delete
   - **影响**: 无法验证完整链路
   - **建议**: 手动创建测试候选稿数据

### 非阻断问题

1. **静态验证通过**
   - ✅ EditorToolbar 组件完整
   - ✅ CandidatePanel 组件完整
   - ✅ Adopt/Delete 按钮存在
   - ✅ Preview 弹窗存在
   - ✅ SSE 连接状态可见
   - ✅ 冲突检查机制存在

---

## Final Verdict

### T4.7.1a 结果

**状态**: ⚠️ PARTIAL

**结论**: T4.7.1a 的静态验证已完成，确认 Professional 工作台具备 candidate 链路的基础 UI 组件。

### 通过的验证

1. ✅ Professional 项目页可打开
2. ✅ 场景文件可打开
3. ✅ EditorToolbar 工具栏完整
4. ✅ 润色/精修/重新生成按钮存在
5. ✅ CandidatePanel 组件完整
6. ✅ 预览弹窗完整
7. ✅ Adopt/Delete 按钮存在
8. ✅ SSE 连接状态可见
9. ✅ 冲突检查机制存在

### 需要真实 LLM 才能验证

1. ❌ Candidate 生成 (润色/精修会调用真实 LLM)
2. ❌ Candidate 展示 (需要先生成)
3. ❌ Preview 功能 (需要 candidate 数据)
4. ❌ Adopt 功能 (需要 candidate 数据)
5. ❌ Delete 功能 (需要 candidate 数据)
6. ❌ SSE/file.updated 事件 (需要触发生成)
7. ❌ base_hash/base_mtime 冲突检查 (需要真实场景)

---

## Recommendations

### 建议 1: 使用真实 LLM 执行完整 E2E 测试

**目标**: 验证完整的 candidate 链路

**步骤**:
1. 配置有效的 LLM API Key
2. 打开 demo-novel 项目
3. 打开第1场景
4. 点击"润色"按钮
5. 等待候选稿生成
6. 在 CandidatePanel 查看候选稿
7. 点击预览
8. 点击 adopt
9. 验证文件更新
10. 验证 SSE 事件

**风险**: 会消耗 LLM token

### 建议 2: 创建 mock candidate 数据

**目标**: 测试 UI 组件，不调用 LLM

**步骤**:
1. 直接调用 `/api/candidates` 创建测试 candidate
2. 在 CandidatePanel 验证展示
3. 测试预览功能
4. 测试 adopt/delete 功能
5. 验证冲突检查机制

**优势**: 不消耗 LLM token

### 建议 3: 标记为 ⚠️ PARTIAL

**当前状态**: T4.7.1a 应标记为 ⚠️ PARTIAL

**理由**:
- 静态验证全部通过
- 但无法验证动态链路（需要真实 LLM）
- 建议后续在有真实 LLM 环境时执行完整测试

---

**文档完成日期**: 2026-06-06

**执行者**: Solo Agent

**版本**: v1.0
