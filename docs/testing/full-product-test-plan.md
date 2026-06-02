# Moyun Studio Full Product Test Plan

本文档定义墨韵的产品级测试计划。它不是单个 E2E 脚本，而是后续所有人工验收、Mock E2E、真实 LLM 冒烟测试和发布前检查的统一矩阵。

## 1. 测试目标

墨韵的核心风险不是“按钮能不能点”，而是写作链路是否真的闭环：

- 用户能创建项目、打开项目、编辑场景、保存正文。
- `sec-*.md` 始终作为单场景写作单元，不被当成传统章节。
- 专业模式“写下一场景”走安全 pipeline，不静默覆盖已有正文。
- polish / rewrite / chat edit / more exciting / more reasonable 等高风险修改默认进入 candidate。
- Lite 模式能完成从开局卡到连续场景写作的普通用户体验。
- SSE 和流式输出能让用户知道系统正在工作。
- story memory、recent-context、ch-meta 在正确时机更新。
- API Key、正文内容、路径和文件保存都满足安全规则。

## 2. 测试分层

| 层级 | 目的 | 是否进 CI | 是否需要真实 LLM |
|---|---|---:|---:|
| Static guardrails | 路径、安全、禁用依赖、API Key 泄露、文案扫描 | Yes | No |
| Unit tests | 单函数、策略、路径、candidate、FileService、PromptEngine | Yes | No |
| Contract tests | API 返回结构、事件结构、candidate 契约、scene path 契约 | Yes | No |
| Mock E2E | 浏览器真实点击，后端/LLM 使用 mock 或 fixture | Yes | No |
| Real LLM smoke | 使用真实 Agnes/OpenAI-compatible 模型生成少量内容 | No | Yes |
| Human acceptance | 人工按真实流程验收 UI、质量、连续性、可用性 | No | Optional |

## 3. 基础启动测试

### 3.1 后端启动

检查项：

- `uvicorn backend.main:app --reload` 能启动。
- `/docs` 和 `/redoc` 可访问。
- `/api/health` 或等价健康检查可用。
- 启动日志不打印 API Key。
- Pipeline YAML 启动校验通过。
- SSE endpoint 可连接。

失败即 P0。

### 3.2 前端启动

检查项：

- `npm run dev` 能启动。
- 首页 `/` 可打开。
- 前端能连接后端。
- SSE 状态能显示连接或重连。
- 刷新页面不会白屏。
- 浏览器控制台无阻塞级错误。

失败即 P0。

### 3.3 LLM 设置

检查项：

- 设置页能保存 OpenAI-compatible 配置。
- Agnes 兼容配置能通过连接测试。
- API Key 不进入 localStorage 明文。
- API Key 不进入截图、测试报告、控制台日志。
- 后端 LLM 失败时有明确提示，不让用户一直等待。

## 4. 项目管理流程

### 4.1 专业项目

测试路径：

1. 从 `/` 点击“新建”。
2. 填写项目名、题材、文风、背景。
3. 点击创建。
4. 跳转 `/project/:projectId`。
5. 等待或观察 `书名与创意.md` 的 pending generation。
6. 不要直接假设已经进入正文场景；专业模式会先进入项目初始化链路。

期望：

- 项目出现在项目列表。
- 文件树加载。
- 初始文件是 `书名与创意.md` 或当前 pending generation 目标。
- pending generation 生成的是项目创意材料，不是正文场景。
- 用户可在右侧 Prompt 面板调整当前步骤 prompt。
- 用户通过“写下一场景”继续推进专业链路。
- 刷新后项目仍可恢复。

### 4.2 Lite 项目

测试路径：

1. 打开 `/lite`。
2. 等待 5 张开局卡。
3. 点击一张开局卡。
4. 创建项目并跳转 `/project/:projectId/lite`。

期望：

- 不跳回专业模式。
- 自动打开第一场景。
- 左侧显示卷、章、场景。
- 右侧显示下一场景爽点卡。
- 第一场景为空时，选卡能直接写入。

## 5. 文件系统与保存

### 5.1 文件树

检查项：

- 文件树能加载项目内所有目录。
- 后端路径如果带 projectId 前缀，前端能正确剥离。
- 打开 `chapters/vol-01/ch-001/sec-001.md` 后 editor 显示正文。
- `/project/:projectId/file/*` 能直接定位文件。

### 5.2 保存正文

检查项：

- `fileStore.readFile` 保存 `mtime` 和 `hash`。
- `fileStore.saveFile` 发送 `expected_mtime` 和 `expected_hash`。
- 保存成功后本地元数据更新。
- 自动保存与手动保存走同一冲突逻辑。
- Lite 的 textarea 保存也走同一安全路径。

### 5.3 冲突处理

测试路径：

1. 打开一个场景，记录 `mtime/hash`。
2. 用 API 或另一个操作修改同一文件。
3. 前端用旧 `mtime/hash` 保存。

期望：

- 后端返回 409 / `FILE_CONFLICT`。
- 前端不清除 dirty 状态。
- 前端提示“文件已被其他操作修改，请重新加载或取消保存”。
- 用户选择重新加载后 editor 显示服务器版本。
- 不允许静默覆盖。

## 6. 场景路径与写作单元

规则：

- `sec-*.md` = 单场景，不是传统章节。
- 标准路径：`chapters/vol-01/ch-001/sec-001.md`。
- 默认每章 5 个场景，每卷 12 章。
- 每个场景目标 600-1000 中文字，默认约 800 字。

必须测试：

- `sec-001 -> sec-002`。
- `sec-005 -> ch-002/sec-001`。
- `ch-012/sec-005 -> vol-02/ch-001/sec-001`。
- 非场景文件不显示“重写当前场景”等按钮。
- UI 文案使用“场景”，不把 `sec` 显示成“节”。

## 7. 专业模式真实工作流

专业模式不是“新建项目后直接打开 `sec-001.md` 写正文”。真实操作是一个可暂停的项目链路：

```text
新建项目
→ 书名与创意.md
→ style-guide.md
→ blueprint.md
→ outline.md
→ materials/worldbuilding.md
→ characters/main.md
→ chapters/vol-01/ch-001/sec-001.md
→ 后续 sec 场景
```

“写下一场景”这个按钮在专业模式里更接近“推进下一步写作任务”。当当前文件不是场景文件时，它推进的是项目初始化链上的下一个文件；当当前文件是 `sec-*.md` 时，它才推进到下一场景。

### 7.1 新建后推进项目链

路径：

1. 从 `/` 创建专业项目。
2. 进入 `/project/:projectId`。
3. 等待 `书名与创意.md` 生成或显示当前初始文件。
4. 用户检查/修改右侧 Prompt。
5. 点击“写下一场景”。
6. 观察系统打开并生成 `style-guide.md`。
7. 继续按 L1 模式手动点击，或切到 L2 自动推进。

期望：

- 每一步生成的是当前链路文件，而不是直接生成正文。
- 文件顺序符合 `style-guide -> blueprint -> outline -> worldbuilding -> characters -> sec-001`。
- L1 模式下，每完成一个需要确认的文件后暂停，等待用户再次点击。
- L2 模式下，完成后可以自动推进下一步，停止按钮能中断。
- 右侧 Prompt / Pipeline / Workflow 面板能反映当前步骤。

### 7.2 进入第一个正文场景

路径：

1. 当前链路推进到 `characters/main.md` 后。
2. 点击“写下一场景”。
3. 系统目标变为 `chapters/vol-01/ch-001/sec-001.md`。

期望：

- 前端推导目标 `sec-001.md`。
- 调用 pipeline，`output_mode` 使用 `write_scene` 或等价安全模式。
- 如果 `sec-001.md` 不存在或为空，可以写入。
- 如果 `sec-001.md` 已有正文，不得静默覆盖，应生成 candidate 或提示确认。
- SSE 流式显示生成进度。
- 结束后重新从后端读取目标文件。
- 文件树刷新或目标文件可见。

### 7.3 后续正文场景

路径：

1. 当前文件是 `chapters/vol-01/ch-001/sec-001.md`。
2. 点击“写下一场景”。

期望：

- 前端推导目标 `sec-002.md`。
- 空目标可直接写入。
- 已有内容目标不得静默覆盖。
- 完成后用户可继续推进 `sec-003`、`sec-004` 等场景。

### 7.4 生成完成后

期望：

- editor 中内容与磁盘一致。
- dirty 状态正确。
- recent-context / story-state / ch-meta 按后端规则更新。
- 当前处于哪一步，右侧 Workflow / Execution / Prompt 面板应能看清。

## 8. 专业模式改稿与 Candidate

高风险动作：

- polish 当前场景。
- rewrite 当前场景。
- chat edit 当前场景。
- more exciting。
- more reasonable。

统一期望：

- 默认生成 candidate。
- 原正式正文不变。
- Candidate 面板显示新候选稿。
- 候选稿带 source_path、base_hash、base_mtime、action、created_at。
- 用户预览后可采用。
- adopt 前检查 base_hash / base_mtime。
- adopt 前写 revision-log。
- adopt 后才覆盖正式正文。
- 删除 candidate 不影响原文。

## 9. Lite 爽文模式

### 9.1 无项目入口 `/lite`

期望：

- 显示 5 张开局卡。
- “换一批”能刷新。
- 参数面板可调整文风、爽点强度、节奏、主角性格、喜欢元素、禁忌内容。
- 选卡后创建项目，保持在 Lite 路由。

### 9.2 有项目入口 `/project/:projectId/lite`

期望：

- 加载当前项目上下文。
- 左侧显示作品与场景列表。
- 中间显示当前场景正文。
- 右侧显示下一场景爽点卡、参数、故事状态摘要。
- 用户选爽点卡即自动生成，不需要再点“生成”按钮。
- 卡片文案明确“选这个，自动生成第 X 场景”。

### 9.3 Lite 连续写作

测试路径：

1. 创建 Lite 项目。
2. 生成第 1 场景。
3. 生成第 2 场景。
4. 生成第 3 场景。
5. 在流式输出时切换到其他场景查看。

期望：

- 目标场景不跳错。
- 流式输出继续写入正确文件。
- 不因为切换场景污染当前 textarea。
- 下一场景爽点卡根据前文变化，不固定复用模板。
- 每完成章内最后一个场景后生成下一章规划。

### 9.4 Lite 改稿

动作：

- 重写当前场景。
- 让当前场景更爽。
- 让当前场景更合理。
- 聊天改稿。

期望：

- 都生成 candidate。
- 原文不变。
- 用户采用后才替换。
- 放弃 candidate 后原文不变。

## 10. 生成质量测试

每次真实 LLM 生成后，至少检查：

- 输出是正文，不是大纲、说明书或写作建议。
- 没有“本场景围绕某某展开”这类模板腔。
- 有具体人物、地点、动作、冲突。
- 有即时反馈和爽点兑现。
- 有结尾钩子。
- 与前文连续，不重复上一场景。
- 没有提前剧透或跳过关键冲突。
- 字数大致 600-1000 中文字。

建议评分维度：

| 维度 | 1 分 | 3 分 | 5 分 |
|---|---|---|---|
| 正文感 | 像说明书 | 半正文半说明 | 完整小说正文 |
| 连续性 | 与前文无关 | 有少量衔接 | 明确承接前文 |
| 冲突推进 | 没有冲突 | 有冲突但弱 | 冲突清楚且升级 |
| 爽点 | 没兑现 | 有但平 | 有即时反馈和获得感 |
| 人物一致性 | 人设漂移 | 基本合理 | 动机清楚且稳定 |
| 节奏 | 拖沓或跳跃 | 可读 | 600-1000 字内完成场景闭环 |

低于 18/30 应视为生成质量失败。

## 11. 故事记忆测试

检查项：

- 场景完成后更新 recent-context。
- 场景完成后更新 story-engine 或等价状态。
- 章内 ch-meta 记录当前场景记忆、待回收伏笔、active quests。
- 每章完成后生成或更新章规划。
- 用户手动修改正文后，可以重新同步记忆。
- 记忆更新不把全文直接塞进 story-state。

关键风险：

- 错误记忆会污染后续整本书。
- 提前写入未发生剧情会导致后文剧透。
- recent-context 过长会拖慢生成。

## 12. 右侧栏测试

逐个 tab 测试：

- Candidate：列表、预览、采用、删除、刷新。
- Workflow：当前节点、运行状态、等待用户、变量池。
- Prompt：查看、编辑、保存、运行。
- Memory / Story：recent-context、story-state、ch-meta 展示。
- LLM：连接状态、模型信息、错误提示。
- Quick Panel：续写、重写、润色、提取等快捷操作。

每个按钮必须记录：

- 点击前 UI 状态。
- API 调用。
- SSE 事件。
- 文件落盘。
- 点击后 UI 状态。
- 是否产生 candidate。

## 13. SSE 与流式输出

检查项：

- SSE 连接成功。
- 心跳 15 秒左右出现。
- 45 秒左右无心跳能自动重连。
- 生成开始、首 token、阶段提示、完成、失败都有 UI 反馈。
- 用户切换场景不打断后台任务。
- 生成失败或超时时有 fallback 或明确失败提示。
- `file.updated` 不携带完整正文 content。
- 事件带 `project_id`。

关键指标：

- 首 token 时间：目标小于 8 秒，超过 12 秒需要 UI 明确说明正在准备。
- 长生成期间每个阶段至少有一次状态提示。
- 失败后用户知道下一步该重试、改配置还是查看 candidate。

## 14. 安全与路径测试

必须覆盖：

- 拒绝 `../`。
- 拒绝绝对路径。
- 拒绝 Windows 盘符路径。
- 拒绝 UNC 路径。
- 拒绝 `.git`、`.env`、`.config.json`、`node_modules`、`__pycache__`。
- 写文件受大小限制。
- API 层不直接拼 `project_dir / req.path`。
- `candidate.source_path` 是项目内相对路径，不能带重复 project_id。
- SSE 不发送完整正文。

## 15. CI 命令

发布前最小命令：

```powershell
python -m py_compile backend/main.py backend/api/files.py backend/api/lite.py backend/api/pipeline.py backend/core/file_ops.py backend/core/generation_service.py backend/core/pipeline.py backend/core/candidate_service.py backend/core/prompt_engine.py backend/schemas/file.py
python -m pytest backend/tests -q --tb=short

cd frontend
npm run lint
npm run build
npm run test:e2e:mock
```

Guardrail：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/ai-check.ps1 -Mode all
powershell -ExecutionPolicy Bypass -File scripts/ai-guardrails.ps1
```

如果某个命令失败，必须修复失败原因，不得使用 `|| true` 掩盖。

## 16. 真实 LLM 冒烟测试

真实 LLM 不进入 CI，但每次大改 Lite、pipeline、prompt、LLM 适配时必须跑。

测试项：

- 生成开局卡。
- 创建 Lite 项目。
- 生成第一场景。
- 生成第二场景。
- 生成爽点卡。
- 重写当前场景生成 candidate。
- 采用 candidate。

记录：

- provider / model。
- 首 token 时间。
- 总耗时。
- 字数。
- 是否正文。
- 质量评分。
- 是否更新 story memory。
- 是否产生错误日志。

## 17. 测试报告模板

```md
# Moyun Test Report

## Environment
- Branch:
- Commit:
- Backend URL:
- Frontend URL:
- LLM provider:
- Model:

## Scope
- Professional:
- Lite:
- File save:
- Candidate:
- SSE:
- Memory:

## Passed
- ...

## Failed
- ...

## Blockers
- ...

## Quality Findings
- ...

## Next Fix Priority
- P0:
- P1:
- P2:
```

## 18. P0 / P1 / P2 分级

P0：

- 无法启动。
- 无法创建项目。
- 正文丢失或静默覆盖。
- API Key 泄露。
- candidate adopt 覆盖错误文件。
- Lite / Professional 任一主流程完全不可用。

P1：

- 生成链路可用但状态提示缺失。
- candidate 出现但刷新或采用体验有问题。
- 保存冲突提示不完整。
- memory 更新不稳定。
- 真实 LLM 输出经常像说明书。

P2：

- 文案不统一。
- 视觉细节。
- 非主流程按钮反馈不够清晰。
- 测试报告字段不完整。
