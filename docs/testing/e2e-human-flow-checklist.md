# Moyun Studio E2E Human Flow Checklist

本文档给人工测试者或其他 AI 使用，用来模拟真实用户操作。测试时不要假设“点击按钮直接生成正文”，必须按当前前端真实流程观察 UI、API、SSE 和文件落盘。

## 0. 测试记录

每次测试先填写：

```md
- Date:
- Tester:
- Branch:
- Commit:
- Backend URL:
- Frontend URL:
- Browser:
- LLM provider/model:
- Workspace:
```

## 1. 启动检查

步骤：

1. 启动后端。
2. 启动前端。
3. 打开 `/`。
4. 打开浏览器 devtools。

期望：

- 页面不白屏。
- 控制台无阻塞错误。
- SSE 连接状态可见。
- 后端日志无 API Key。

记录：

- Backend started: pass/fail
- Frontend started: pass/fail
- SSE connected: pass/fail
- Console error:

## 2. 专业模式：创建项目到推进初始化链

步骤：

1. 在 `/` 点击“新建”。
2. 填写项目名、题材、风格、背景。
3. 点击创建。
4. 等待跳转 `/project/:projectId`。
5. 观察当前打开文件，通常应是 `书名与创意.md` 或 pending generation 目标。
6. 等待初始生成完成。
7. 查看右侧 Prompt / Workflow / Execution 状态。
8. 点击“写下一场景”，推进到 `style-guide.md`。
9. 继续按 L1 手动推进，或切换 L2 观察自动推进。

期望：

- 项目创建成功。
- 文件树加载。
- editor 显示当前链路文件内容，而不是默认直接进入正文场景。
- URL 与当前项目一致。
- 选中文件路径不带重复 projectId。
- 专业链路顺序应为：`书名与创意.md -> style-guide.md -> blueprint.md -> outline.md -> materials/worldbuilding.md -> characters/main.md -> sec-001.md`。
- L1 模式下每步完成后应等待用户继续。
- L2 模式下可自动推进，停止按钮能中断。

检查文件：

- `workspace/projects/{projectId}/project.json`
- `workspace/projects/{projectId}/书名与创意.md`
- `workspace/projects/{projectId}/style-guide.md`
- `workspace/projects/{projectId}/blueprint.md`

## 3. 专业模式：保存与冲突

步骤：

1. 打开任意已生成的专业链路文件，例如 `style-guide.md` 或 `sec-001.md`。
2. 输入一行测试正文。
3. 点击保存。
4. 通过 API 或后台修改同一文件。
5. 回到前端继续编辑并保存。

期望：

- 第一次保存成功。
- 保存请求携带 `expected_mtime` / `expected_hash`。
- 第二次保存遇到冲突时显示提示。
- 不静默覆盖服务器版本。
- dirty 状态不被错误清除。

记录：

- Save API body:
- Conflict UI:
- Server file after conflict:

## 4. 专业模式：从初始化链进入第一场景

步骤：

1. 当前文件推进到 `characters/main.md`。
2. 确认 `chapters/vol-01/ch-001/sec-001.md` 不存在或为空。
3. 点击“写下一场景”。
4. 观察右侧任务状态、Prompt、Workflow 和编辑器流式输出。
5. 等待完成。

期望：

- 前端目标路径是 `sec-001.md`。
- pipeline 请求使用安全输出模式。
- editor 有流式内容。
- 完成后从后端重新读取。
- `sec-001.md` 落盘。

失败判定：

- 没有任何状态提示超过 12 秒。
- 生成到错误文件。
- 输出是大纲或说明书，不是正文。
- 覆盖已有 `sec-001.md`。

## 5. 专业模式：正文场景继续推进

步骤：

1. 打开 `chapters/vol-01/ch-001/sec-001.md`。
2. 确认 `sec-002.md` 不存在或为空。
3. 点击“写下一场景”。

期望：

- 只有当前文件已经是 `sec-*.md` 时，才把“写下一场景”理解为写后续正文场景。
- 前端目标路径是 `sec-002.md`。
- 空目标可直接写入。
- 已有内容目标不得静默覆盖。

## 6. 专业模式：已有目标不能静默覆盖

步骤：

1. 手动让 `sec-002.md` 存在并有正文。
2. 打开 `sec-001.md`。
3. 点击“写下一场景”。

期望：

- 不直接覆盖 `sec-002.md`。
- 系统生成 candidate 或提示确认。
- 如果生成 candidate，Candidate 面板可见。

检查文件：

- `sec-002.md` 原文是否不变。
- `.candidates/` 是否生成新候选稿。

## 7. 专业模式：polish / rewrite candidate 闭环

步骤：

1. 打开有正文的 `sec-001.md`。
2. 记录原文 hash 或前 50 字。
3. 点击 polish。
4. 等待完成。
5. 打开 Candidate 面板。
6. 预览候选稿。
7. 点击采用。

期望：

- polish 后原文不变。
- candidate 出现。
- 采用前 candidate 有 `source_path`、`base_hash`、`base_mtime`。
- 采用后原文才改变。
- revision-log 有记录。

重复同样步骤测试 rewrite。

## 8. 专业模式：右侧栏逐项测试

逐个测试：

| 面板 | 动作 | 期望 |
|---|---|---|
| Candidate | 刷新列表 | 候选稿列表不报错 |
| Candidate | 预览 | 内容显示，不误写正文 |
| Candidate | 采用 | 覆盖 source_path，并写 revision-log |
| Candidate | 删除 | 候选稿移除，原文不变 |
| Workflow | 运行 | 当前节点和状态显示 |
| Workflow | 暂停/等待 | 等待对象和动作明确 |
| Prompt | 查看 | Prompt 内容可见 |
| Prompt | 保存 | 保存成功或明确失败 |
| Memory | 刷新 | recent-context/story-state 可读 |
| Quick Panel | 重写 | 生成 candidate |

每个失败都记录截图、API、控制台日志。

## 9. Lite：从 `/lite` 创建项目

步骤：

1. 打开 `/lite`。
2. 等待开局卡。
3. 点击“换一批”。
4. 调整参数。
5. 选择一张开局卡。

期望：

- 5 张开局卡出现。
- 换一批能变化。
- 参数不丢。
- 创建项目后跳转 `/project/:projectId/lite`。
- 不跳回专业模式。

## 10. Lite：选爽点卡自动写场景

步骤：

1. 在 `/project/:projectId/lite` 打开第一场景。
2. 观察右侧爽点卡。
3. 点击一张卡。
4. 不再点击任何“生成”按钮。
5. 观察 editor 流式输出。

期望：

- 卡片点击即开始生成。
- 8-12 秒内有状态提示或首 token。
- 内容写入正确 `sec` 文件。
- 标题显示“第 X 场景”，不是“第 X 节”。
- 输出是正文，不是说明书。

## 11. Lite：连续写三场景

步骤：

1. 完成第 1 场景。
2. 点击下一张爽点卡写第 2 场景。
3. 正在流式时切换回第 1 场景查看。
4. 再切回第 2 场景。
5. 完成后继续写第 3 场景。

期望：

- 流式输出不因切换场景停止。
- 正在生成的内容不会写错 textarea。
- 第 2 场景标题不变成第 3 场景。
- 右侧爽点卡根据前文更新，不固定复用同三张。

## 12. Lite：改稿 candidate

步骤：

1. 打开已有正文的当前场景。
2. 点击“重写当前场景”。
3. 点击“让当前场景更爽”。
4. 点击“让当前场景更合理”。
5. 使用聊天改稿。

期望：

- 每个动作生成 candidate。
- 原文不变。
- 用户采用后才替换。
- 放弃 candidate 后原文不变。

## 13. 生成质量人工检查

每个生成场景打分：

| 维度 | 分数 1-5 | 备注 |
|---|---:|---|
| 正文感 | | |
| 连续性 | | |
| 冲突推进 | | |
| 爽点兑现 | | |
| 人物一致性 | | |
| 结尾钩子 | | |

自动失败：

- 输出是大纲。
- 输出包含“写作偏好参考”“本节围绕”等说明书话术。
- 少于 400 中文字。
- 明显重复上一场景。
- 与前文人物/事件冲突。

## 14. Memory 检查

每完成一个场景后检查：

- `recent-context.md` 是否追加近期摘要。
- `story-state.md` 是否只记录长期状态，不变成流水账。
- `ch-meta.json` 是否更新场景记忆。
- 待回收伏笔是否合理。
- 没有写入未发生剧情。

每完成一章最后一个场景后检查：

- 下一章 `ch-plan.md` 是否生成或更新。
- 章规划只规划接下来一章或一小段，不强迫用户先写大纲。

## 15. SSE / 状态提示检查

观察：

- 连接状态。
- Thinking / running 状态。
- 首 token 时间。
- 阶段提示。
- 失败提示。
- 重连提示。

失败判定：

- 用户点击后超过 12 秒无任何反馈。
- 生成失败只在控制台报错，UI 无提示。
- 刷新后任务状态混乱。

## 16. 测试结束报告

复制以下模板：

```md
# E2E Human Flow Report

## Environment
- Branch:
- Commit:
- LLM:

## Pass
- ...

## Fail
- ...

## Blockers
- ...

## Quality Notes
- ...

## Files Checked
- ...

## Next Actions
- P0:
- P1:
- P2:
```
