# T6.6 Professional 主流程 dry-run 总验收报告

> **阶段结论**：T6.6 Professional 主流程 dry-run 总验收 — **✅ 阶段性通过**
>
> 本阶段已完成 Professional 主流程 dry-run 完整覆盖，包括 TaskQueue / Pipeline / Batch 三条生成链路、Candidate preview/adopt/conflict、文件树/编辑器/File API、安全边界。真实 LLM 尚未执行，仅完成隔离冒烟测试方案。

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-10 | 初始版本 |

---

## 一、任务完成表

| 任务 | 结论 | 精确 commit | 说明 |
|------|------|-----------|------|
| T6.6.0 | ✅ | `37e56225595674a85c2cc191a773d537f1fd7182` | 总验收清单 + 最小安全串联 |
| T6.6.1 | ✅ | `99f75fd6396d3f35a125a25470b435a3863cdbb3` | Professional dry-run 主流程 |
| T6.6.2 | ✅ | `0ad23d3434268c4bf2fa3b0656e68de778a42c04` | Candidate adopt/conflict/file.updated SSE |
| T6.6.3 | ✅ | `2d97430451e4e9416670e106faca6ddde65b9903` | Pipeline dry-run UI + stream |
| T6.6.4 | ✅ | `00a32c42c3ebcab462c1fd17a18ce2f3c5ed66db` | Batch dry-run 后端 + schema + API |
| T6.6.4-fix | ✅ | `b71166a2881dfae7fb72ea9e3e68dbc89e76d449` | Batch dry-run UI click（切换"执行"tab + 真实 click） |
| T6.6.5-plan | ✅ | `0c68a540655c1821caf45651a00f6820c27e2d10` | 真实 LLM 隔离冒烟测试方案 |

> **注**：所有 commit 来自 `git log --format="%H %s"`，以实际为准，未做人工调整。

---

## 二、已覆盖能力

### 2.1 前端用户路径

| 能力 | 覆盖任务 | 测试文件 |
|------|---------|---------|
| 项目创建 / 打开 | T6.5.4 / T6.6.1 | `19-project-create-open.spec.ts`, `25-professional-main-flow-dry-run.spec.ts` |
| 文件树打开场景文件 | T6.5.3 / T6.6.1 | `18-file-tree-editor.spec.ts`, `25-professional-main-flow-dry-run.spec.ts` |
| 编辑器显示正文 | T6.5.3 / T6.6.1 | `18-file-tree-editor.spec.ts` |
| 右侧面板切换（切换到"执行"tab） | T6.6.4-fix | `29-batch-dry-run-flow.spec.ts` |
| dev/test UI 按钮真实 click（TaskQueue） | T6.6.0 / T6.6.1 | `25-professional-main-flow-dry-run.spec.ts` |
| dev/test UI 按钮真实 click（Pipeline） | T6.6.3 | `28-pipeline-dry-run-ui-sse-flow.spec.ts` |
| dev/test UI 按钮真实 click（Batch） | T6.6.4-fix | `29-batch-dry-run-flow.spec.ts` |

### 2.2 后端能力

| 能力 | 覆盖任务 | 测试文件 |
|------|---------|---------|
| TaskQueue dry-run | T6.5.6 / T6.5.7 / T6.6.0 | `21-task-queue-pipeline-dry-run.spec.ts`, `test_t6_5_7_dry_run_contract.py` |
| Pipeline dry-run | T6.5.6 / T6.5.7 / T6.6.3 | `21-task-queue-pipeline-dry-run.spec.ts`, `test_t6_5_7_dry_run_contract.py` |
| Batch dry-run | T6.6.4 | `test_t6_6_4_batch_dry_run_contract.py` |
| Candidate adopt（HTTP + API） | T6.5.1 / T6.6.2 | `14-candidate-workflow.spec.ts`, `26-candidate-adopt-conflict-sse.spec.ts` |
| 冲突检测 409 / FILE_CONFLICT | T6.6.2 | `26-candidate-adopt-conflict-sse.spec.ts` |
| File API 读写安全 | T6.5.3 / T6.6.4 | `test_file_api_contract.py`, `29-batch-dry-run-flow.spec.ts` |

### 2.3 SSE / 事件

| 能力 | 覆盖任务 | 测试文件 |
|------|---------|---------|
| SSE / file.updated 跨进程事件 | T6.5.5 | `20-sse-real-event-flow.spec.ts` |
| Pipeline stream done / dry_run 标记 | T6.6.3 | `28-pipeline-dry-run-ui-sse-flow.spec.ts` |
| Batch dry-run SSE（无独立 SSE，API 返回） | T6.6.4 | `29-batch-dry-run-flow.spec.ts` |
| Task 状态轮询（API + store） | T6.6.1 | `25-professional-main-flow-dry-run.spec.ts` |

### 2.4 安全边界（全部验证通过）

- ✅ 不调用真实 LLM（dry-run 路径）
- ✅ 不覆盖正文（所有 dry-run 测试覆盖）
- ✅ 不生成非预期 candidate（dry-run 测试覆盖）
- ✅ adopt 前冲突检测 / hash / mtime 保护
- ✅ adopt 成功后正文更新
- ✅ 测试项目使用 `__e2e_*` 前缀
- ✅ 测试后清理
- ✅ 工作区 clean

---

## 三、仍有限制

以下为**当前阶段已知限制**，如实记录，不回避：

| 限制项 | 说明 | 建议处理 |
|--------|------|---------|
| candidate-adopted SSE | 未完整端到端验证（API adopt 层已覆盖，UI 层 file.updated 事件断言不完整） | 后续补测或明确由 T6.6.5 覆盖 |
| Pipeline stream 消息格式 | 当前使用 JSON 消息，不是标准 `event:` / `data:` 字段（类似 SSE 但非标准） | 后续规范化 |
| Task 状态验证方式 | 部分场景主要通过 API 轮询 + store 验证，非 SSE 实时推送 | 后续统一验证层 |
| 真实 LLM 调用 | 尚未执行 | 进入 T6.6.5 需显式开关 |
| 真实生成质量 / 速度 / 异常恢复 | 尚未验收 | 进入 T6.6.5 隔离环境 |
| Batch 真实 LLM | 明确不在当前阶段测试 | 方案文档已明确排除 |
| T6.6.4 与 TaskQueue 的集成 | Batch 当前独立于 TaskQueue 运行，未通过 SSE / TaskQueue 调度 | 架构割裂问题，后续评估 |

---

## 四、安全结论

**当前 dry-run 阶段安全边界通过：**

- ✅ 未调用真实 LLM
- ✅ 未使用 API Key
- ✅ 未覆盖正文
- ✅ 未污染真实项目
- ✅ 未写 scoring / final
- ✅ 未污染 story_state / materials / recent_context
- ✅ 测试项目使用 `__e2e_t6_6_*` 或 `__llm_smoke_*` 前缀
- ✅ 测试后全部清理
- ✅ API Key 未出现在日志、截图、测试报告中
- ✅ 工作区 clean

---

## 五、T6.6 交付物清单

| 类别 | 交付物 | 路径 |
|------|--------|------|
| 总验收清单 | T6.6 主流程 E2E 总验收 | `docs/testing/t6-6-professional-e2e-acceptance.md` |
| 阶段报告 | T6.6 final 总验收报告 | `docs/testing/t6-6-final-acceptance-report.md` |
| 测试方案 | 真实 LLM 冒烟测试方案 | `docs/testing/t6-6-5-real-llm-smoke-plan.md` |
| 后端 contract 测试 | TaskQueue/Pipeline dry-run | `backend/tests/contracts/test_t6_5_7_dry_run_contract.py` |
| 后端 contract 测试 | Batch dry-run | `backend/tests/contracts/test_t6_6_4_batch_dry_run_contract.py` |
| 后端 contract 测试 | File API 安全 | `backend/tests/contracts/test_file_api_contract.py` |
| Playwright E2E | TaskQueue / Pipeline / Batch dry-run（dev-only UI 入口） | `frontend/tests/e2e/25~29-*.spec.ts` |
| 后端实现 | TaskQueue / Pipeline dry-run | `backend/core/task_queue.py`, `backend/application/pipeline/` |
| 后端实现 | Batch dry-run | `backend/core/generation_service.py`, `backend/api/generate.py` |
| 前端 UI | dev-only dry-run 按钮（ExecutionPanel） | `frontend/src/components/right-panel/ExecutionPanel.vue` |

---

## 六、下一步建议

### 选项 A：执行 T6.6.5 真实 LLM 隔离冒烟测试

**适用场景**：需要验证真实生成链路、API Key 配置、candidate adopt 全链路。

条件：
- 显式开启 `MOYUN_ALLOW_REAL_LLM_SMOKE=1`
- 仅测试单场景 continue/rewrite（**禁止 Batch 真实 LLM**）
- 只生成 candidate，不自动覆盖正文
- 长度限制 max_tokens <= 300
- 失败不得继续 adopt
- 按 [t6-6-5-real-llm-smoke-plan.md](./t6-6-5-real-llm-smoke-plan.md) checklist 执行

风险：token 消耗、API Key 配置、生成不稳定。

### 选项 B：进入 T6.7 产品化修复 / UI 清理

**适用场景**：先完善产品细节，延后真实 LLM 测试。

建议范围：
1. dev/test 按钮布局整理（`ExecutionPanel`）
2. candidate-adopted SSE 补测（`26-candidate-adopt-conflict-sse.spec.ts` 增强断言）
3. Pipeline stream 消息格式标准化（JSON → `event:` / `data:`）
4. Task 状态 UI / 验证层统一
5. Batch 与 TaskQueue 架构割裂问题评估
6. E2E 测试 selector 稳定性整理
7. 文档与已知限制同步更新

---

## 七、最终声明

**T6.6 Professional 主流程 dry-run 总验收 — 阶段性通过。**

本阶段覆盖了三条 dry-run 生成链路、完整 Candidate 采纳流程、文件树/编辑器/File API 链路、SSE 跨进程事件、安全边界闭环、dev-only UI 入口。所有测试均通过 Playwright 真实 UI click 验证，工作区干净，commit 历史可查。

真实 LLM 调用需显式开启，需人工确认，需隔离环境。

---

*文档结束*
