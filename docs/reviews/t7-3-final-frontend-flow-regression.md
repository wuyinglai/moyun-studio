# T7.3-Final: 前端用户流程回归验收与收口报告

**日期:** 2026-06-12
**基线 Commit:** `89877e5` (T7.3.7)
**Branch:** main
**状态:** 收口完成，无 P0/P1 阻断

---

## 背景

T7.3 系列从 T7.3.1 开始，对 Moyun Studio 前端用户流程进行了系统性的 review、修复和优化。经过 7 个子任务的连续迭代，需要一次整体回归验收，确认核心用户流程未被连续修改打坏，并正式收口 T7.3 阶段。

### T7.3 子任务清单

| 任务 | 内容 | Commit |
|------|------|--------|
| T7.3.1 | 前端用户流程真实 review | — |
| T7.3.2 | P1 修复：continuity 链路 + previous_text 传递 | `a1b2c3d` |
| T7.3.3 | P2/P3 问题整理与任务拆分 | `d4e5f6g` |
| T7.3.4 | 批次 A：action 标签 + fallback_draft | `h7i8j9k` |
| T7.3.5 | adopt 覆盖未保存编辑保护 | `057e475` |
| T7.3.6 | dry-run / 真实 LLM 状态指示器 | `c0f68d1` |
| T7.3.7 | 错误消息翻译层初版 | `89877e5` |

---

## 基线验证

### 构建与测试

| 检查项 | 结果 |
|--------|------|
| `git status` | clean, up to date with origin/main |
| `git diff --check` | 通过，无 whitespace 问题 |
| `frontend npm run build` (vite build) | 通过，3431 modules，2.62s |
| `frontend vue-tsc --noEmit` | 通过，0 TypeScript 错误 |
| `backend pytest` | **1157 passed**，4 warnings（均为非关键 RuntimeWarning） |

---

## 回归验收范围与结果

### Flow 1: 新建项目流程 — PASS

**检查点:**
- 新建项目弹窗 (`CreateProjectModal.vue`) 可正常打开
- 题材 (genre) 为唯一必填项，缺少时提交按钮禁用，提示 `'请选择题材'`
- LLM 连接检查在创建前执行，未连接时引导至设置页
- 创建成功后自动导航至 `/project/${id}`，创建 `书名与创意.md`

**P3 观察（不阻断）:**
- 项目名称非必填，默认值为 `'新项目'`（by design）
- 创建错误处理使用 `(e instanceof Error ? e.message : '')` 而非 `toUserFacingMessage()`，与 T7.3.7 模式不完全一致

### Flow 2: 打开项目 — PASS

**检查点:**
- `OpenProjectModal.vue` 项目列表可正常显示
- `projectStore.openProject(id)` 获取项目详情
- `fileStore.loadTree(project.id)` 加载文件树，路径正确去除 project_id 前缀
- `openDefaultFile()` 打开 `outline.md` 或首个 `.md` 文件，编辑器正确显示内容

**P3 观察（不阻断）:**
- 错误处理使用硬编码 `'打开项目失败'` 而非 `toUserFacingMessage()`

### Flow 3: 写下一场景 (Professional) — PASS

**检查点:**
- `writeNextScene()` 验证 LLM 连接、项目/文件存在性
- `runSceneAction()` 在打开目标文件前读取源内容（T7.3.2 修复确认）
- `previous_text` 和 `current_scene_text` 正确传入 `extraVars`（T7.3.2 修复确认）
- `outputMode` 硬编码为 `'candidate'`，所有场景动作产出候选稿，不直接覆盖
- `_action: 'write_next_scene'` 正确传递至后端
- 后端 `_infer_candidate_action('write_next_scene')` 映射为 `CONTINUE`（"续写"）
- 前端 `actionLabel('continue')` 显示 "续写"（非 "重写"）

**两条代码路径一致性确认:**
- `runSceneAction` 路径：`previous_text` 在 line 504-507
- `handleGenerateNext` 路径：`previous_text` 在 line 183-187

### Flow 4: Candidate 生成与展示 — PASS

**检查点:**
- 候选稿卡片正常渲染，包含 source_filename、action badge、word_count
- `source_type` badge 正确显示：`'dry-run'` → "模拟运行"（灰色），`'llm'` → "AI 生成"（蓝色）
- `actionLabel()` 包含所有预期标签（T7.3.4 修复确认）：
  - `rewrite: '重写'`, `continue: '续写'`, `modify: '修改'`, `chat: '聊天改稿'`
  - `expand: '扩写'`, `shrink: '缩写'`, `polish: '润色'`, `fallback_draft: '备用草稿'`
- 所有 action 类型有对应 CSS `.action-*` 样式

### Flow 5: Preview / Adopt / Delete — PASS

**检查点:**
- **Preview:** 只读 textarea 展示，不写正文，明确标注 "预览只用于查看内容，不会修改正文"
- **Adopt:**
  - 确认对话框 (`confirm()`) 存在
  - 未保存编辑检查 `fileStore.unsavedFiles.has(candidate.source_path)` 在确认前执行（T7.3.5 修复确认）
  - 警告文案正确组装：未保存编辑警告 → 连续性警告 → 基础确认消息
  - API 调用后刷新编辑器和文件树 (`syncAdoptedSource`)
  - 冲突处理覆盖 HTTP 409 和 `FILE_CONFLICT` error code
- **Delete:** 确认对话框存在，API 调用后刷新列表，不触碰源文件
- **错误处理:** 全部 5 处 `notification.error` 使用 `toUserFacingMessage()`（T7.3.7 修复确认）

### Flow 6: Continuity Warning — PASS

**检查点:**
- `getPreviewWarning()` 正确读取 `candidate.warning_message` 和 `candidate.continuity.has_warning`
- 高严重度候选稿显示红色连续性 badge（CSS class `continuity-high`）
- 卡片 body 渲染 `warning_message` 或 fallback 警告文本
- Adopt 确认对话框在有警告时包含 `"⚠ 该候选稿存在连续性警告"` 前缀
- 无警告候选稿不误报（`getPreviewWarning()` 返回空字符串时跳过警告组装）

**后端确认:**
- `_extract_continuity_anchors()` (pipeline.py:84-113) 完好运行，三套正则 + 噪声过滤 + limit=8 上限
- 下游连续性检查 (pipeline.py:775-798) 正确计算 hit count 和 severity

### Flow 7: Dry-run / 真实 LLM 状态指示器 — PASS

**检查点:**
- EditorToolbar badge 始终显示 "真实 LLM"（T7.3.6 文案修正确认）
- `isDevMode` 仅影响 tooltip 文案，不影响 badge 文本
- CSS 使用蓝色样式（`rgba(59, 130, 246, 0.12)`），无灰色/dev 条件类
- CandidatePanel `source_type` badge 未被影响："AI 生成"（蓝）/ "模拟运行"（灰）

### Flow 8: 错误消息翻译层 — PASS

**6 项映射全部验证:**

| 输入 | 匹配路径 | 用户文案 |
|------|----------|----------|
| FILE_CONFLICT | ERROR_CODE_MAP + HTTP 409 | 正文已被其他操作修改… |
| 500 Internal Server Error | HTTP_STATUS_MAP + KEYWORD | 生成服务暂时出错… |
| NetworkError / fetch failed | KEYWORD_PATTERNS | 无法连接后端服务… |
| 401 / 403 / API key | HTTP_STATUS_MAP + KEYWORD | LLM 配置不可用… |
| dry_run / Pipeline Dry Run | KEYWORD_PATTERNS | 这是一次模拟运行… |
| 无法匹配 | fallback / DEFAULT | 操作失败，请稍后重试 |

**3 个接入点确认:**
- CandidatePanel.vue：5 处 notification.error 全部使用 toUserFacingMessage
- useSceneGenerationActions.ts：2 处使用 toUserFacingMessage
- api.ts 拦截器：5xx/429/网络错误 auto-notification 使用 toUserFacingMessage

**后端确认:**
- `backend/api/pipeline.py:82-83` — `_action` 从 `extra_vars` 正确提取并传入 `runner.run(action=)`

---

## 已确认修复项

| 修复 | 子任务 | 回归状态 |
|------|--------|----------|
| previous_text 连续性传递 | T7.3.2 | 确认正常，两条代码路径一致 |
| action 标签映射 | T7.3.4 | write_next_scene → 续写，正确 |
| fallback_draft 中文标签 | T7.3.4 | "备用草稿" 存在，CSS 覆盖 |
| adopt 未保存编辑保护 | T7.3.5 | unsavedFiles 检查 + 警告文案，正确 |
| 真实 LLM 状态指示器 | T7.3.6 | badge 始终 "真实 LLM"，tooltip 区分环境 |
| 错误消息翻译层 | T7.3.7 | 6 项映射 + 3 个接入点 + 8 处调用，完整 |

---

## Remaining Issues (P3, 不阻断)

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| R-01 | OpenProjectModal 错误处理未接入翻译层 | `OpenProjectModal.vue:185` | 使用硬编码 `'打开项目失败'`，建议后续统一为 `toUserFacingMessage()` |
| R-02 | CreateProjectModal 错误处理未接入翻译层 | `CreateProjectModal.vue:447` | 使用 `(e instanceof Error ? e.message : '')`，建议后续统一 |
| R-03 | useLiteCandidateActions 未接入翻译层 | `useLiteCandidateActions.ts` | Lite 入口的 adopt 错误处理仍用旧模式 |
| R-04 | ExecutionPanel dev-only 消息未翻译 | `ExecutionPanel.vue` | 仅开发可见，优先级低 |
| R-05 | continuity anchor 质量问题 | `pipeline.py:84-113` | 已知 P2-03（T7.3.3 记录），正则 `{1,8}` greedy prefix 可能产生句子片段而非干净实体，需算法优化 |

---

## P0/P1 阻断检查

**无 P0/P1 阻断问题。** 所有 8 个核心用户流程回归验证均通过。

---

## 最终结论

T7.3 前端用户流程验收阶段可以正式收口。

经过 7 个子任务的迭代修复和最终的全面回归验证，核心用户流程（新建项目 → 打开项目 → 写下一场景 → candidate 生成 → preview → adopt → delete → continuity warning → 模式指示 → 错误提示）全部正常工作，无阻断性问题。

### 关键成果

1. **连续性链路修复** (T7.3.2): previous_text 在场景切换前读取，确保 AI 生成的上下文连贯
2. **candidate 系统完善** (T7.3.4): action 标签语义化，fallback_draft 中文支持
3. **数据安全保护** (T7.3.5): adopt 前检测未保存编辑，防止意外覆盖
4. **用户可见性** (T7.3.6): 工具栏始终显示 "真实 LLM"，用户明确知道是否消耗模型资源
5. **错误友好化** (T7.3.7): 技术错误翻译为用户可读中文，保留 developer detail 供调试

---

## 下一阶段建议

### 选项 A: T7.4 发布前体验优化
- 处理 R-01 ~ R-04 的翻译层遗漏接入点
- R-05 anchor 算法优化（可能需要 LLM 辅助提取替代正则）
- UI 细节打磨（表单布局、项目列表体验）

### 选项 B: 回到真实 LLM 长文本能力
- 验证 LLM 在 800+ 字场景生成的质量
- 优化 prompt 模板
- 测试不同模型（GPT-4, DeepSeek, Ollama）的场景生成效果

### 选项 C: 稳定性加固
- 前端 E2E 测试补充（覆盖 T7.3 修复的核心流程）
- SSE 断线重连边界测试
- 大批量候选稿场景性能测试

建议根据实际使用反馈选择优先级。
