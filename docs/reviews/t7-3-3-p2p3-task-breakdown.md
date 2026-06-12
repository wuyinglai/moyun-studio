# T7.3.3 前端 P2/P3 问题整理与任务拆分

## 1. 任务背景

T7.3 前端用户流程验收阶段。T7.3.1 完成了前端用户流程真实 review 文档归档（commit `8253d55`），发现了 3 个 P1 问题。T7.3.2 修复了全部 3 个 P1 问题（commit `499211e`）。

本文档是 T7.3.3 的产出：将 T7.3.1 review 和 T7.3.2 修复过程中暴露的 P2/P3 问题整理成可执行的小任务清单，不做代码修改，不做大重构。

## 2. 当前基线

| 项目 | 内容 |
|------|------|
| 分支 | main |
| 基线 commit | `499211e` fix: pass previous_text in scene candidate flow |
| 工作区状态 | clean |

## 3. T7.3.2 已完成事项

T7.3.2 修复了 T7.3.1 review 中标记的 3 项 P1 问题：

| 原始编号 | P1 问题 | T7.3.2 修复内容 |
|----------|---------|-----------------|
| T7.3-FE-001 | "写下一场景"直接覆盖正文 | `runSceneAction()` 统一走 candidate 模式，所有场景生成不再直接写入正文 |
| T7.3-FE-002 | adopt 无二次确认 | `adoptCandidate()` 增加 `confirm()` 对话框，含连续性警告提示；后端 FILE_CONFLICT 冲突检测已对接 |
| T7.3-FE-003 | continuity warning 无前端 UI | `CandidatePanel.vue` 增加连续性警告 badge、warning_message 显示、preview 弹窗警告、adopt 确认中风险前置提示 |

T7.3.2 同时补齐了 `runSceneAction()` 中 `previous_text` / `current_scene_text` 的传递，使后端 `_extract_continuity_anchors()` 能从当前场景正文提取锚点，continuity 链路闭环。

## 4. P2 问题清单（5 项）

### T7.3.3-P2-01 candidate action 标签错误："续写"显示为"重写"

| 项目 | 内容 |
|------|------|
| 问题等级 | P2 |
| 所属流程 | Professional 写下一场景 -> candidate 展示 |
| 用户影响 | 用户通过"写下一场景"生成的候选稿，在卡片上显示为"重写"而非"续写"，语义混乱 |
| 根因 | 前端 `runSceneAction()` 将 `_action: 'write_next_scene'` 放入 `extra_vars`，但后端 `api/pipeline.py` 的 pipeline handler 从不提取 `_action`，导致 `_infer_candidate_action()` 以 `action=None` 回退到 pipeline_name 匹配，`"generate"` 管线默认映射为 `REWRITE` |
| 建议修复方向 | 在 `backend/api/pipeline.py` 中从 `request.extra_vars` 提取 `_action` 并传给 `runner.run(action=...)` |
| 是否建议立即处理 | 是 -- 改动小（1-2 行），效果立竿见影 |
| 是否需要测试 | 需要：验证 pipeline 生成的 candidate 在列表/详情中 action 字段为 `continue` |

### T7.3.3-P2-02 adopt 时未保存的本地编辑被静默覆盖

| 项目 | 内容 |
|------|------|
| 问题等级 | P2 |
| 所属流程 | candidate adopt -> 编辑器状态同步 |
| 用户影响 | 用户正在编辑器中修改场景文件（尚未保存），此时 adopt 一个 candidate 覆盖同一文件，本地未保存的修改会被静默丢弃，用户无任何提示 |
| 根因 | `syncAdoptedSource()` 直接调用 `editorStore.loadContent()` 覆盖编辑器缓冲区，未检查 `fileStore.unsavedFiles` 是否有该文件的脏标记；后端 hash 冲突检测只看磁盘文件，看不到编辑器内存中的未保存改动 |
| 建议修复方向 | adopt 前检查 `fileStore.unsavedFiles.has(sourcePath)`，若有则弹出确认框；或 adopt 按钮在文件脏时 disabled |
| 是否建议立即处理 | 否 -- 涉及交互设计决策，建议作为短期优先任务 |
| 是否需要测试 | 需要：构造编辑器脏状态后 adopt，验证确认框出现 |

### T7.3.3-P2-03 continuity anchor 提取质量偏低

| 项目 | 内容 |
|------|------|
| 问题等级 | P2 |
| 所属流程 | 后端 pipeline continuity 检测 |
| 用户影响 | 提取的锚点是长句子片段（如"林澈站在站"、"指尖还残留着芯片"）而非干净的实体名（"林澈"、"芯片"），导致连续性检测准确性下降 |
| 根因 | (1) `_CONTINUITY_KEYWORD_PATTERN` 的 `{1,8}` 贪婪前缀吞掉关键词前的动词/介词；(2) 后处理分隔符列表太短（仅 6 项）；(3) 关键词匹配优先级高于更干净的命名/引号匹配，8 个槽位被低质量匹配占满 |
| 建议修复方向 | (1) 调整匹配优先级：命名 > 引号 > 关键词；(2) 缩短前缀量词；(3) 扩充后处理分隔符和噪声字符集 |
| 是否建议立即处理 | 否 -- 属于算法优化，需更多文本样本验证，建议放到 T7.4 |
| 是否需要测试 | 需要：准备 5-10 个不同风格的场景文本，对比修复前后锚点质量 |

### T7.3.3-P2-04 dry-run / 真实 LLM 来源对用户不透明

| 项目 | 内容 |
|------|------|
| 问题等级 | P2 |
| 所属流程 | candidate 展示 -> 来源区分（对应原 T7.3-FE-005） |
| 用户影响 | T7.3.2 已在 CandidatePanel 中添加了 `source_type` badge（"AI 生成" / "模拟运行"），代码层面已实现；但 dry-run 工具条仅在 `isDevMode` 可见，生产用户在生成前无法知道当前是否会消耗 token |
| 根因 | ExecutionPanel 的 dry-run 开关被 `v-if="isDevMode"` 保护；状态栏只展示"已连接"，不区分 LLM 调用模式 |
| 建议修复方向 | 在顶部状态栏或生成按钮旁增加"当前模式：模拟 / 真实"指示器 |
| 是否建议立即处理 | 否 -- badge 已有，状态栏改造属于体验优化 |
| 是否需要测试 | 需要：验证 dry-run 模式下 candidate 卡片显示"模拟运行" badge |

### T7.3.3-P2-05 错误提示含技术术语

| 项目 | 内容 |
|------|------|
| 问题等级 | P2 |
| 所属流程 | 全局 notification（对应原 T7.3-FE-006） |
| 用户影响 | 部分通知/错误消息包含 `dry_run=`、`Pipeline Dry Run`、`FILE_CONFLICT` 等开发术语，普通用户无法理解 |
| 根因 | notification store 直接展示后端返回的原始 message 或前端拼接的调试字符串 |
| 建议修复方向 | 建立统一文案映射层：`errorCode -> userFacingMessage`；notification 默认展示人类可读文案，点击可展开 developerDetail |
| 是否建议立即处理 | 否 -- 需逐条排查，工作量较大 |
| 是否需要测试 | 需要：触发各类错误场景验证文案 |

## 5. P3 问题清单（5 项）

### T7.3.3-P3-01 项目列表体验差

| 项目 | 内容 |
|------|------|
| 问题等级 | P3 |
| 所属流程 | 打开项目（对应原 T7.3-FE-004） |
| 用户影响 | 100+ 项目平铺列表，无分组/排序/搜索聚焦，用户难以定位目标项目 |
| 建议修复方向 | "最近打开"置顶 + 搜索框默认聚焦 + 每项显示修改时间/字数 |
| 是否建议立即处理 | 否 |
| 是否需要测试 | 是 |

### T7.3.3-P3-02 新建项目默认爽文模式

| 项目 | 内容 |
|------|------|
| 问题等级 | P3 |
| 所属流程 | 新建项目（对应原 T7.3-FE-008） |
| 用户影响 | 新项目创建后自动进入爽文模式并生成一批素材，严肃小说用户感到突兀 |
| 建议修复方向 | 新建表单增加"默认模式"选项，或不自动触发爽文模式 |
| 是否建议立即处理 | 否 |
| 是否需要测试 | 是 |

### T7.3.3-P3-03 表单验证提示弱 + 弹窗布局问题

| 项目 | 内容 |
|------|------|
| 问题等级 | P3 |
| 所属流程 | 新建项目 / 打开项目（对应原 T7.3-FE-007） |
| 用户影响 | 必填项为空时仅按钮 disabled 无红色提示；打开项目弹窗底部按钮在矮屏下需滚动 |
| 建议修复方向 | 表单级验证提示 + 弹窗 sticky footer |
| 是否建议立即处理 | 否 |
| 是否需要测试 | 是 |

### T7.3.3-P3-04 `fallback_draft` action 前后端不一致

| 项目 | 内容 |
|------|------|
| 问题等级 | P3 |
| 所属流程 | candidate 展示 |
| 用户影响 | 后端 `CandidateAction` 枚举包含 `fallback_draft`，但前端 TypeScript 类型和 `actionLabel()` 均未处理；若出现 fallback_draft candidate 会显示原始英文字符串 |
| 建议修复方向 | 前端 `CandidateAction` 类型、`actionLabel()` 函数、CSS class 三处补齐 |
| 是否建议立即处理 | 是（改动极小，3 行代码） |
| 是否需要测试 | 是 |

### T7.3.3-P3-05 adopt 后文件树 refresh 未 await + candidate 列表重复拉取

| 项目 | 内容 |
|------|------|
| 问题等级 | P3 |
| 所属流程 | candidate adopt -> 状态同步 |
| 用户影响 | `refreshTree()` fire-and-forget，若失败文件树可能短暂显示旧状态；candidate 列表被直接调用和 SSE 事件各触发一次 fetch（无害但浪费） |
| 建议修复方向 | (1) `await fileStore.refreshTree()`；(2) SSE handler 中对 `candidate-adopted` 做去重或 debounce |
| 是否建议立即处理 | 否 |
| 是否需要测试 | 是 |

## 6. 推荐分批方案

### 批次 A -- 立即处理（T7.3.3 本体，预估 1-2 小时）

| 编号 | 问题 | 预估改动 | 涉及文件 |
|------|------|----------|----------|
| P2-01 | candidate action 标签错误 | 1-2 行 | `backend/api/pipeline.py` |
| P3-04 | `fallback_draft` 前端缺失 | 3 行 | `frontend/src/shared/api/types.ts`, `frontend/src/components/right-panel/CandidatePanel.vue` |

### 批次 B -- 短期跟进（T7.3.4 或 T7.4，预估 2-4 小时）

| 编号 | 问题 | 预估改动 |
|------|------|----------|
| P2-02 | adopt 覆盖未保存编辑 | `CandidatePanel.vue` adopt 前检查 unsavedFiles，10-15 行 |
| P2-04 | dry-run 状态栏指示器 | 顶部状态栏组件改造 |
| P2-05 | 错误提示翻译层 | notification store + 文案映射表 |

### 批次 C -- 中长期优化（T7.5+）

| 编号 | 问题 | 预估改动 |
|------|------|----------|
| P2-03 | anchor 提取算法 | 正则优化 + 后处理扩充，需样本验证 |
| P3-01 | 项目列表体验 | 打开项目面板重构 |
| P3-02 | 默认爽文模式 | 新建项目表单改造 |
| P3-03 | 表单验证 / 弹窗布局 | CSS + 表单组件调整 |
| P3-05 | adopt sync 细节 | await + debounce |

## 7. 风险说明

1. **P2-01（action 标签）如果不修**：所有通过 Professional "写下一场景"生成的 candidate 永远显示"重写"，与"续写"语义不符，用户困惑持续累积。
2. **P2-02（adopt 覆盖未保存编辑）如果不修**：用户在编辑器中精心修改了正文但忘记保存，adopt candidate 后丢失工作成果，属于数据安全隐忧。建议作为后续短期优先任务处理。
3. **P2-03（anchor 质量）如果急于修改**：正则调整可能影响已有 continuity 检测的准确性，需要充分回归测试，不建议在当前冲刺中处理。

## 8. 后续建议

1. **T7.3.3 本体**（批次 A）：修复 P2-01 和 P3-04，改动量极小，可在 1-2 小时内完成并验证。
2. **T7.3.4**（批次 B）：处理 P2-02 adopt 安全检查、P2-04 dry-run 状态指示器、P2-05 错误提示翻译层。
3. **T7.5+**（批次 C）：anchor 提取算法优化、项目列表体验、新建项目模式选择等中长期改进。
4. 完成上述修复后可进入：真实 LLM 长文本生成与候选稿管理的正式发布前打磨阶段。
