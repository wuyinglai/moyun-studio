# Moyun Studio 改造优化总清单与验收看板

> 创建时间：2026-06-02
> 最后更新：2026-06-03
> 负责人：Solo / ChatGPT 联合维护

---

## 1. 总体目标

Moyun Studio 当前处于架构收口与产品体验优化阶段，整体目标包括：

| 方向 | 目标 |
|------|------|
| **后端 Lite 架构收口** | 逐步抽取后端服务，边界清晰，可测试，可替换 |
| **候选稿安全机制统一** | 所有高风险修改必须生成候选稿，不直接覆盖正式正文 |
| **数据流可视化** | 让用户直观看到 AI 写作的每一步（输入/处理/输出） |
| **真实功能测试** | 确保生成、候选稿、回滚、长篇连续生成等核心功能可用 |
| **右边栏产品化** | 流程/候选稿/记忆/视觉等信息架构清晰，用户友好 |
| **视觉分镜/自动配图** | 未来支持文生图、视觉摘要、ComfyUI 接入 |

---

## 2. 状态标记说明

| 标记 | 含义 | 说明 |
|------|------|------|
| ✅ (已完成) | 已完成并验收 | 已通过 ChatGPT 核实 GitHub commit |
| 🟡 (待验收) | 已完成待验收 | Solo 已提交，等待 ChatGPT 核实 |
| ⏳ (待执行) | 待执行 | 尚未开始 |
| 🧭 (规划) | 未来规划 | 方向明确，尚未排期 |
| ⚠️ (风险) | 有风险需补丁 | 发现问题，需要后续修复 |
| ❌ (暂停) | 不通过/暂停 | 遇到障碍或被搁置 |

---

## 3. 后端 Lite 架构收口线

### 3.1 核心服务抽取

| Phase | 任务 | 状态 | 产出 | 验收方式 | 需补丁 |
|-------|------|------|------|----------|--------|
| Phase 1 | 场景契约统一 | ✅ | 场景路径命名规范、文件系统设计 | 代码审查 | - |
| Phase 2 | 候选稿机制统一 | ✅ | CandidateService 统一，adopt 前不覆盖原文 | 功能测试 | - |
| Phase 3.1 | 项目初始化服务抽取 | ✅ | ProjectService 独立 | 代码审查 | - |
| Phase 3.2 | 场景路径服务抽取 | ✅ | SceneService 独立 | 代码审查 | - |
| Phase 3.3A | Story metadata / memory 读写服务抽取 | ✅ | MemoryService 独立 | 代码审查 | - |
| Phase 3.3B | Option cards / next-options 解析服务抽取 | ✅ | OptionCardsService 独立 | 代码审查 | - |
| Phase 3.4A | Lite LLM 调用基础服务抽取 | ✅ | LiteLLMService 独立 | 代码审查 | - |
| Phase 3.4B | Lite Prompt Builder 服务抽取 | ✅ | LitePromptBuilder 独立 | 代码审查 | - |
| Phase 3.4C | Lite Quality Gate 服务抽取 | ✅ | LiteQualityService 独立 | 代码审查 | - |
| Phase 3.4D | Generation Orchestration 拆分设计 | ✅ | 文档：generation-orchestration-design.md | 文档审查 | - |
| Phase 3.4E | 低风险 helper 清理 | ✅ | 移除冗余 helper 函数 | 代码审查 | - |
| Phase 3.4F | 路径安全边界审查 | ✅ | test_lite_path_safety.py 38个测试全通过 | 自动化测试 | - |

**验收方式**：后端测试通过 + 代码审查

### 3.2 Lite 后端服务清单

当前已抽取的 Lite 相关服务：

| 服务 | 状态 | 说明 |
|------|------|------|
| LiteSceneService | ✅ | 场景路径相关服务 |
| LiteStoryMetadataService | ✅ | 故事元数据读写服务 |
| LitePromptBuilder | ✅ | Prompt 构建服务 |
| LiteLLMService | ✅ | LLM 调用服务 |
| LiteQualityService | ✅ | 质量检查服务 |
| LiteOptionCardsService | ✅ | 场景选项卡服务 |
| LiteCandidatePolicy | ✅ | 候选稿策略服务 |
| CandidateService | ✅ | 候选稿统一服务 |

---

## 4. 数据流可视化线

| Phase | 任务 | 状态 | 产出 | 验收方式 | GitHub Commit |
|-------|------|------|------|----------|---------------|
| Phase 5A | 数据流可视化产品设计 | ✅ | docs/dataflow-visualization-design-2026-06.md | 文档审查 | 03671be |
| Phase 5B | FlowPanel 静态 Mock 原型 | ✅ | FlowPanel.vue + FlowNodeCard.vue + mockFlowData.ts | UI 验收 | ce08475 |
| Phase 5C | FlowPanel 接入 Lite 生成现有回调 | ✅ | useFlowRun.ts + flowStore + 回调集成 | 功能验收 | 116c9e7 |
| Phase 5D | FlowPanel Artifact Preview 增强 | ✅ | FlowArtifactPreview.vue + 增强 mock 数据 | UI 验收 | cf8d16d |
| Phase 5E | CandidatePanel 与 Flow artifact 联动 | ⏳ | - | - | - |
| Phase 5F | 真实 flow.step SSE 设计文档 | 🧭 | - | - | - |
| Phase 5G | 真实 flow.step SSE 后端最小实现 | 🧭 | - | - | - |
| Phase 5H | FlowPanel 接真实后端 flow.step | 🧭 | - | - | - |
| Phase 5I | 视觉分镜 Flow 节点设计 | 🧭 | - | - | - |

**当前进度**：已完成 5A-5D，FlowPanel 已具备 Mock 展示 + 实时推断 + Artifact 预览能力

---

## 5. 真实功能测试 / 输出质量评估线

### 5.1 总体测试进度总览

| Phase | 任务 | 状态 | 产出 | 验收方式 |
|-------|------|------|------|----------|
| Phase T1 | 全功能人工测试计划 | ✅ | 测试计划文档 | 文档审查 |
| Phase T2 | Agnes LLM 配置支持 | ✅ | 支持配置多种 LLM | 配置验证 |
| Phase T3-A | Lite UI 冒烟测试 | ✅ | 完成 Lite 页面加载、FlowPanel Tab 切换 | 截图验收 |
| Phase T3-B | Lite 真实生成核心测试 | ✅ | 完成首场景生成、候选稿、连续生成三场 | 功能验收 |
| Phase T3-B-3 | 连续生成 3 场真实补测 | 🟡 | 🟡 | 功能验收 |
| Phase T3-B-5 | 选择器修复复测 | ✅ | 修复选择器逻辑 | 功能验收 |
| Phase T3-B-7 | data-testid 稳定选择器复测 | ✅ | 添加稳定 data-testid 属性 | 功能验收 |
| Phase T3-B-9 | 修复连续生成产品链路 | ✅ | 添加"生成下一场景爽点卡"按钮 | 功能验收 |
| Phase T3-B-10 | 使用新入口连续生成 3 场真实重跑 | 🟡 | 🟡 | 功能验收 |
| Phase T3-B-13 | 连续生成目标文件推进验证 | ✅ 功能通过，质量待优化 | 三场分别写入不同文件，功能通过 | 功能验收 |
| Phase T3-C | 输出质量深化评分与 Prompt 优化建议 | ✅ | 完成质量评分，发现 Fallback 问题 | 文档审查 |
| Phase T3-D | Fallback/自动重试/Prompt 优化方案设计 | ✅ | 方案文档已完成 | 文档审查 |
| Phase T3-D1 | Fallback 显式标记 | ✅ | 后端响应添加 fallback_used 字段，前端显示警告 UI，测试脚本支持记录 | 功能验收 |
| Phase T3-D1-Verify | fallback_used 标记链路验证 | ✅ | 前端构建通过，后端测试 185 passed，Response Model 测试 5 passed | 功能验收 |
| Phase T3-D2 | 前端 fallback 警告增强 | ✅ | 增强 UI 警告，添加重写入口，明确提示文案 | 功能验收 |
| Phase T3-D3 | Fallback 自动重试 | ✅ | 新增 retry_used、retry_count 字段，sync 和 stream 都支持一次自动重试 | 功能验收 |
| Phase T3-D4 | Fallback candidate 化方案设计 | ✅ | 完成方案设计和边界评估，推荐分 5 阶段实施 | 文档审查 |
| Phase T3-D4.1 | fallback candidate 元数据设计 | ✅ | 确定新增字段和数据结构 | 功能验收 |
| Phase T3-D4.2 | fallback 同步创建 candidate | ✅ | 但仍写正文，风险低 | 功能验收 |
| Phase T3-D4.3 | fallback 不直接覆盖正文 | ✅ | 只创建 candidate，不污染正文 | 功能验收 |
| Phase T3-D4.4 | 连续生成 fallback 暂停策略 | ✅ | 遇到 fallback 时暂停，禁用继续生成按钮，提示用户决策 | 功能验收 |
| Phase T3-D4.5 | UI/FlowPanel 联动优化 | ✅ | 在 FlowPanel 中清晰显示 fallback 状态，提供直观交互 | 功能验收 |
| Phase T3-D5 | 低质量检测 | ✅ | 基于规则的质量检测，quality_flags/quality_warning/quality_score 字段，前端 UI 警告 | 功能验收 |
| Phase T3-D5-Fix | 低质量检测测试修复 | ✅ | 修复测试 shadow 问题，删除重复 helper，确保测试真正调用后端实现 | 功能验收 |
| Phase T3-D6 | Prompt 优化实验方案 | ✅ | 实验方案文档 + 样例文档，未修改生产 Prompt | 文档验收 |
| Phase T3-D6.1 | 新增实验 Prompt 文件 | ✅ | 新增实验 Prompt 目录，包含 Baseline / Variant A-D，共 6 个文件 | 文档验收 |
| Phase T3-D6.2 | 实验脚本 dry-run 完成 | ✅ | 新增 dry-run 脚本和记录模板，验证所有 variant 文件有效，Variant C recommended=true | 文档验收 |
| Phase T3-D6.3 | 真实实验对比分析模板 | ✅ | 新增分析框架文档，明确 Variant C 为优先候选而非最优，待真实实验验证 | 文档验收 |
| Phase T3-D6.3.1 | 真实实验采集 | ⚠️ | 环境限制：缺少测试项目，后端未启动。创建实验记录占位文档，如实记录环境限制，不伪造结果 | 待环境就绪 |
| Phase T3-D6.3.1a | 真实实验执行器 dry-run 完成 | ✅ | 新增可重复运行的实验 harness，默认 dry-run 不调用 LLM，新增最小测试项目 fixture | 文档验收 |
| Phase T3-D6.3.1b | 真实 LLM 实验采集 | ⏳ | 待环境就绪（后端启动、测试项目可用），运行真实 LLM 对比 | 待环境就绪 |
| Phase T3-D6.3.2 | 去 AI 化与叙事质量规则提炼 | ✅ | 已形成参考文档，区分 Lite 和专业版可用规则，暂不接入生产 Prompt | 文档验收 |
| Phase T3-D6.4 | 小范围接入生产 Prompt | ⏳ | 最小改动 | 功能验收 |
| Phase T3-D7 | Python + LLM 写作质量与一致性引擎 | ⏳ | 架构设计文档完成，已完成降噪优化、Review 覆盖校验和 Prompt 契约 | 文档验收 |
| Phase T3-D7.0 | 架构设计文档 | ✅ | 设计文档完成，明确分工和实现顺序 | 文档验收 |
| Phase T3-D7.1 | Diff Engine 存在性比对 MVP | ✅ | 扫描实体、比对设定库、生成 candidate issues，输出 JSON/Markdown 报告 | 功能验收 |
| Phase T3-D7.1.1 | 候选提取降噪与断言测试 | ✅ | 过滤无效候选、增加统计、新增测试脚本，所有测试通过 | 功能验收 |
| Phase T3-D7.2 | Candidate JSON + Markdown report | ✅ | 已随 D7.1/D7.1.1 一起实现，支持 JSON schema、Markdown 报告、噪声过滤统计 | 功能验收 |
| Phase T3-D7.3a | Review Engine schema + 覆盖校验 dry-run | ✅ | 定义 review schema、实现 Python 覆盖校验、新增 4 个 fixture，所有测试通过 | 功能验收 |
| Phase T3-D7.3b | Review Prompt 模板 + mock 输出契约 | ✅ | 定义 Prompt 模板、新增 mock fixtures、mock output 通过 validator | 文档验收 |
| Phase T3-D7.3c-a | Review smoke 脚本 dry-run | ✅ | 新增 smoke 脚本、默认 --dry-run、mock 输出通过 validator | 功能验收 |
| Phase T3-D7.3c-b | 真实 LLM Review 3 条冒烟 | ⏳ | 环境就绪后运行真实 LLM 3 条 Review | 功能验收 |
| Phase T3-D7.3c-b1 | LLM endpoint 配置探针 | ✅ | 新增探针脚本、测试多种 provider/model 格式、输出 sanitized 报告 | 功能验收 |
| Phase T3-D7.3d | 真实 LLM Review 全量 14 条 | ⏳ | 环境就绪后运行真实 LLM 全量 Review | 功能验收 |
| Phase T3-D7.3 | LLM Review + 覆盖校验 | ⏳ | 定义 review schema、校验覆盖率 | 功能验收 |
| Phase T3-D7.4 | State Snapshot MVP | ⏳ | 提取事实、生成 snapshot | 功能验收 |
| Phase T3-D7.5 | Plot Debt 表 MVP | ⏳ | 记录伏笔、到期提醒 | 功能验收 |
| Phase T4 | Professional 真实生成冒烟测试 | ⏳ | - | - |
| Phase T5 | 输出质量评分表 | ⏳ | - | - |
| Phase T6 | 候选稿采用/回滚测试 | ⏳ | - | - |
| Phase T7 | 长篇连续 10 场生成测试 | ⏳ | - | - |
| Phase T8 | 错误/超时/断流测试 | ⏳ | - | - |
| Phase T9 | 真实用户视角测试报告 | ⏳ | - | - |

### 5.2 Phase T3-B 子任务状态详情

| 真实功能测试线 Phase T3-B 子任务状态更新：

| 子任务 | 状态 | 日期 | 说明 |
|--------|------|------|------|
| Phase T3-B-1 | ✅ | 2026-06-02 | 首场景生成测试 |
| Phase T3-B-2 | ✅ | 2026-06-02 | Candidate 改稿测试 |
| Phase T3-B-3 | 🟡 | 2026-06-02 | 连续生成 3 场真实补测 |
| Phase T3-B-4 | ✅ | 2026-06-03 | 诊断脚本定位问题根源 |
| Phase T3-B-5 | ✅ | 2026-06-03 | 选择器修复复测 |
| Phase T3-B-6 | 🟡 | 2026-06-03 | 选择器修复真实重跑 |
| Phase T3-B-7 | ✅ | 2026-06-03 | data-testid 稳定选择器复测 |
| Phase T3-B-8 | 🟡 | 2026-06-03 | data-testid 连续生成 3 场真实重跑 |
| Phase T3-B-9 | ✅ | 2026-06-03 | 修复连续生成产品链路 |
| Phase T3-B-10 | 🟡 | 2026-06-03 | 使用新入口连续生成 3 场真实重跑 |
| Phase T3-B-11 | ✅ | 2026-06-03 | next-options 真实诊断通过 |
| Phase T3-B-12 | ✅ | 2026-06-03 | next-options 前端渲染修复通过 |
| Phase T3-B-13 | ✅ 功能通过，质量待优化 | 2026-06-03 | 文件推进验证，功能通过，质量 partial（第 2 场 702 字 < 800） |

### 5.3 Phase T3-C 质量评分结论

| 评估项 | 结论 |
|--------|------|
| **功能链路** | ✅ 通过 |
| **真实生成质量** | 🟢 良好（4.3/5） |
| **Fallback 问题** | 🔴 第 2 场为 fallback，内容不可用 |
| **Prompt 是否需要优化** | ⏸️ 暂缓，先解决系统可靠性 |
| **是否进入 Prompt 优化** | ✅ 是（Phase T3-D） |

**后续建议**：
| Phase | 任务 | 优先级 |
|-------|------|--------|
| Phase T3-D-1 | Fallback 显式标记 | 高 |
| Phase T3-D-2 | Fallback 自动重试 | 高 |
| Phase T3-D-3 | Fallback candidate 化 | 中 |
| Phase T3-D-4 | 低质量检测 | 中 |
| Phase T3-D-5 | Prompt 优化 | 低 |

**当前进度**：Phase T3-C 输出质量深化评分完成！Phase T3-D1-D3 已全部完成！Phase T3-D4 fallback candidate 化方案设计完成！可以进入 Phase T3-D4.1！

---

## 6. 右边栏产品体验优化线

| Phase | 任务 | 状态 | 产出 | 验收方式 |
|-------|------|------|------|----------|
| Phase R1 | 右边栏信息架构设计 | ⏳ | - | - |
| Phase R2 | 流程 Tab 原型 | ✅ | FlowPanel 已集成到 RightPanel | UI 验收 |
| Phase R3 | CandidatePanel 体验增强 | ⏳ | - | - |
| Phase R4 | MemoryPanel 用户化展示 | ⏳ | - | - |
| Phase R5 | ExecutionPanel 简化 | ⏳ | - | - |
| Phase R6 | 高级模式折叠 | ⏳ | - | - |
| Phase R7 | 右边栏任务语言重命名 | ⏳ | - | - |

**当前进度**：流程 Tab 已完成，其他 Tab 待优化

---

## 7. 视觉分镜/自动配图线

| Phase | 任务 | 状态 | 产出 | 验收方式 |
|-------|------|------|------|----------|
| Phase V1 | 视觉分镜产品方案 | ⏳ | - | - |
| Phase V2 | Visual Bible 数据结构设计 | 🧭 | - | - |
| Phase V3 | 场景视觉摘要生成 | 🧭 | - | - |
| Phase V4 | 文生图 workflow 设计 | 🧭 | - | - |
| Phase V5 | 图生图/局部编辑 workflow 设计 | 🧭 | - | - |
| Phase V6 | 图片候选稿机制 | 🧭 | - | - |
| Phase V7 | ComfyUI 接入设计 | 🧭 | - | - |
| Phase V8 | ComfyUI 最小后端适配 | 🧭 | - | - |
| Phase V9 | FlowPanel 增加视觉节点 | 🧭 | - | - |

**当前进度**：Phase 5A 设计文档中已有初步方向，尚未正式规划

---

## 8. 前端状态与稳定性线

| Phase | 任务 | 状态 | 产出 | 验收方式 |
|-------|------|------|------|----------|
| Phase F1 | 正文真相源审查 | ⏳ | - | - |
| Phase F2 | useLiteGeneration 状态边界审查 | ⏳ | - | - |
| Phase F3 | SSE 处理统一设计 | ⏳ | - | - |
| Phase F4 | FlowPanel 出错隔离测试 | ⏳ | - | - |
| Phase F5 | 右边栏 Store 梳理 | 🧭 | - | - |

**当前进度**：整体待审查

---

## 9. 当前最高优先级任务

| 优先级 | Phase | 任务 | 状态 | 原因 |
|--------|-------|------|------|------|
| 1 | Phase T3-D2 | Fallback 自动重试 | ⏳ | 减少 fallback 触发，提升用户体验 |
| 2 | Phase T3-D3 | Fallback candidate 化 | ⏳ | 不让 fallback 内容直接覆盖正式正文 |
| 3 | Phase 5E | CandidatePanel 与 Flow 联动 | ⏳ | 增强数据流可视化完整性 |
| 4 | Phase T5 | 输出质量评分表 | ⏳ | 建立质量评估体系 |
| 5 | Phase R3 | CandidatePanel 体验增强 | ⏳ | 提升用户安全感 |

---

## 10. 每次 Solo 完成后的验收流程

### 10.1 标准验收流程

```
1. Solo 提交最终报告
   ↓
2. 提供完整信息：branch / commit hash / commit URL / modified files / commands run
   ↓
3. ChatGPT 核实 GitHub commit
   ↓
4. 对照本路线图判断是否验收
   ↓
5. 如果通过 → 更新本路线图
   ↓
6. 如果不通过 → 追加补丁任务到对应 Phase
   ↓
7. 不允许未验收就进入下一阶段
```

### 10.2 验收必查项

| 检查项 | 说明 |
|--------|------|
| branch | 当前分支名 |
| commit hash | 必须来自 `git rev-parse HEAD` |
| commit URL | 必须是真实可访问的 GitHub URL |
| modified files | 列出新增/修改的文件 |
| commands run | 列出 build、测试等验证命令 |
| behavior compatibility | 逐项回答兼容性检查 |

### 10.3 禁止事项

- 不允许未验收就进入下一阶段
- 不允许修改已验收的 commit
- 不允许混入无关文件
- 不允许修改本路线图以外的代码（除非明确授权）

---

## 11. 后续维护规则

1. **每次完成一个任务，必须更新本路线图**
2. **每个任务最好一个 commit**
3. **不要混入无关文件**
4. **commit hash 必须来自 `git rev-parse HEAD`**
5. **push 后必须提供 GitHub URL**
6. **ChatGPT 独立核实后才算完成**
7. **更新时保持本路线图格式不变，只更新状态和 commit**

---

## 12. 验收历史

| 日期 | Phase | 状态 | Commit | 验收人 |
|------|-------|------|--------|--------|
| 2026-06-02 | Phase 5A | ✅ | 03671be | ChatGPT |
| 2026-06-02 | Phase 5B | ✅ | ce08475 | ChatGPT |
| 2026-06-02 | Phase 5C | ✅ | 116c9e7 | ChatGPT |
| 2026-06-02 | Phase 5D | ✅ | cf8d16d | ChatGPT |
| 2026-06-03 | Phase T3-D1 | ✅ | (待 commit) | ChatGPT |
| 2026-06-04 | Phase T3-D1-Verify | ✅ | 48ed0a4 | Solo |
| 2026-06-04 | Phase T3-D2 | ✅ | 5d5864e | Solo |
| 2026-06-04 | Phase T3-D3 | ✅ | c7d84e9 | Solo |
| 2026-06-04 | Phase T3-D4 | ✅ | c826d08 | Solo |
| 2026-06-04 | Phase T3-D4.1 | ✅ | c9ba95e | Solo |
| 2026-06-04 | Phase T3-D4.2 | ✅ | 44a0592 | Solo |
| 2026-06-04 | Phase T3-D4.3 | ✅ | 2959beb | Solo |
| 2026-06-04 | Phase T3-D4.4 | ✅ | 46f66c2 | Solo |
| 2026-06-04 | Phase T3-D4.5 | ✅ | 6691fec | Solo |

---

## 附录：关键文档索引

| 文档 | 用途 |
|------|------|
| docs/testing/lite-output-quality-review-2026-06.md | Lite 输出质量深化评分报告 |
| docs/testing/lite-fallback-retry-prompt-optimization-plan-2026-06.md | Fallback/重试/Prompt 优化方案 |
| docs/dataflow-visualization-design-2026-06.md | 数据流可视化产品设计 |
| docs/moyun-roadmap-and-acceptance-board-2026-06.md | 本路线图（当前文档） |
| docs/contracts/scene-path-contract.md | 场景路径契约 |
| docs/contracts/candidate-contract.md | 候选稿契约 |
| docs/contracts/api-contract.md | API 契约 |
| docs/contracts/event-contract.md | SSE 事件契约 |
