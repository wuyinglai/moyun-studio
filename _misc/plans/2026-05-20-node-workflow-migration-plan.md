# 2026-05-20 节点化工作流迁移计划

本计划给后续 AI 或开发者执行使用。目标是把专业版、爽文模式和后端工作流逐步对齐到统一节点模型。

## 0. 边界

禁止事项：

- 不修改 `workspace/` 用户数据。
- 不移动 `backend/`、`frontend/` 目录。
- 不破坏旧项目和旧 YAML 工作流。
- 不让聊天输入直接覆盖正式文件。

优先事项：

- 先统一术语和契约。
- 再补前端状态表达。
- 最后逐步扩展后端节点类型。

## 1. 术语对齐

新增或引用以下文档：

- `docs/产品架构-人机协同工作流.md`
- `docs/专业版节点化改造计划.md`
- `docs/adr/2026-05-20-人机协同节点架构.md`

后续所有实现 PR 都应说明自己影响的节点类型和工作流阶段。

## 2. 前端优先改造点

### 2.1 专业版工作流运行面板

目标：

- 显示当前节点、执行者、状态。
- 区分 `running`、`waiting_for_user`、`failed`、`done`。
- 暂停时说明等待原因和可选动作。

验收：

- 用户能一眼看出系统是在调用 AI、读写文件，还是等用户确认。

### 2.2 专业版变量池

目标：

- 分组显示用户输入、AI 草稿、人工确认结果、系统变量。
- 明确 `draft_`、`final_`、`approved_` 变量命名。

验收：

- 后续节点不会误用未确认草稿。

### 2.3 专业版候选稿面板

目标：

- 列出候选稿。
- 支持预览、采用、放弃、继续修改。
- 采用后触发记忆更新。

验收：

- 重写、润色、聊天改稿都不会直接覆盖原文。

### 2.4 聊天入口

目标：

- 用户聊天后选择作用范围：当前文件、选中文件、下一节、故事引擎、仅备注。
- 第一版先生成候选改稿。

验收：

- 用户可以通过聊天修改前文，但必须经过候选稿确认。

## 3. 后端优先改造点

### 3.1 统一节点响应结构

为工作流运行状态补充：

- `current_node`
- `node_type`
- `executor`
- `waiting_reason`
- `available_actions`
- `input_refs`
- `output_refs`
- `affected_files`

### 3.2 File Node 扩展

从现有 mkdir/copy/delete 扩展为：

- read
- write
- append
- patch
- create_candidate
- adopt_candidate
- delete_candidate
- snapshot

### 3.3 Human Node

支持：

- human_review
- human_edit
- human_choice
- human_score
- human_instruction

运行到 Human Node 时进入等待用户状态。用户提交后，输出进入变量池。

### 3.4 Memory Node

支持：

- update_story_engine
- update_recent_context
- update_character_state
- update_foreshadowing

默认在正式文件写入或候选稿采用后执行。高风险记忆写入可进入 Human Review。

### 3.5 Quality Node

支持：

- 审稿摘要
- 质量评分
- 阈值判断
- 自动补强分支
- 失败提示

## 4. 爽文模式对齐点

爽文模式不展示复杂节点，但内部应该逐步使用同一套能力：

- 选爽点卡 = Human Choice。
- 流式生成 = Prompt Node。
- 候选改稿 = Version/Patch Node。
- 采用候选稿 = File Node + Memory Node。
- 质量摘要 = Quality Node。
- 故事引擎更新 = Memory Node。

## 5. 推荐执行顺序

1. 专业版运行状态面板清晰化。
2. 候选稿面板抽成共用组件。
3. 后端补节点状态响应字段。
4. File Node 扩展候选稿动作。
5. Human Node 等待/恢复协议落地。
6. Memory Node 审核写入。
7. 聊天入口结构化为作者意图。
8. 旧工作流展示映射到新节点模型。

## 6. 测试要求

每个阶段都要做模拟用户 E2E：

- 新建项目。
- 运行工作流。
- 等待 AI 流式输出。
- 暂停在人工节点。
- 用户编辑或确认。
- 恢复执行。
- 生成候选稿。
- 采用候选稿。
- 检查正式文件、故事引擎、近期上下文是否更新。

同时保留旧项目回归：

- 旧 YAML 工作流能打开。
- 旧项目文件树能打开。
- 专业版 Prompt、Pipeline、文件管理不回归。

