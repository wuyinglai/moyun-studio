# T6.6 Professional 主流程安全 E2E 总验收清单

## 版本记录

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v1.0 | 2026-06-10 | E2E | 初始版本 |
| v1.1 | 2026-06-10 | E2E | T6.6.1 ~ T6.6.4 完成状态更新，T6.6.5-plan 补充 |

---

## 一、T6.6 子任务状态总览

| 任务 | 标题 | 状态 | 核心验证内容 |
|------|------|------|--------------|
| T6.6.0 | 总验收清单 + 最小安全串联 | ✅ | 总验收文档建立，Professional 主流程 dry-run 串联 |
| T6.6.1 | Professional 主流程 dry-run E2E | ✅ | 完整用户路径 dry-run |
| T6.6.2 | Candidate adopt + conflict + SSE 串联 | ✅ | 候选稿采纳/冲突/SSE 事件 |
| T6.6.3 | Pipeline dry-run UI 入口 + SSE 流 | ✅ | Pipeline 执行面板 + SSE 事件可见 |
| T6.6.4 | Batch dry-run 能力 + UI click E2E | ✅ | Batch dry-run 后端 + UI 入口 + 真实 click |
| T6.6.5-plan | 真实 LLM 隔离环境冒烟测试方案 | ✅ | 方案文档 + 环境开关 + 验收标准 |
| T6.6.5 | 真实 LLM 隔离环境冒烟测试（执行） | ⚠️ 待执行 | 需要人工确认，显式开启开关 |

---

## 二、已完成模块详细说明

### T6.5.x 阶段已验证能力

| 任务 | 状态 | 核心验证内容 | 测试文件 |
|------|------|--------------|----------|
| T6.5.1 | ✅ | Candidate 工作流（创建/采纳/拒绝） | `14-candidate-workflow.spec.ts` |
| T6.5.2 | ✅ | Scene Plan 面板 + Lite 视图 UI | `16-scene-plan-panel.spec.ts`, `99-phase-t3a-flowpanel-smoke.spec.ts` |
| T6.5.3 | ✅ | 文件树 + 编辑器 + File API 真实联调 | `18-file-tree-editor.spec.ts` |
| T6.5.4 | ✅ | 项目创建 / 打开 / 项目列表真实 E2E | `19-project-create-open.spec.ts` |
| T6.5.5 | ✅ | SSE / file.updated 真实跨进程事件 | `20-sse-real-event-flow.spec.ts` |
| T6.5.6 | ✅ | Task Queue / Pipeline API dry-run 能力 | `21-task-queue-pipeline-dry-run.spec.ts` |
| T6.5.7 | ✅ | Pipeline + TaskQueue dry-run 后端实现 | `test_t6_5_7_dry_run_contract.py` |
| T6.5.8 | ✅ | 前端可见性 E2E（API + store） | `23-task-queue-pipeline-ui-dry-run.spec.ts` |
| T6.5.9 | ✅ | 前端 dry-run dev/test UI 入口 | `24-dry-run-ui-entry.spec.ts` |

### T6.6 新增已验证能力

| 任务 | 状态 | 核心验证内容 | 测试文件 |
|------|------|--------------|----------|
| T6.6.1 | ✅ | Professional 主流程 dry-run E2E | `25-professional-main-flow-dry-run.spec.ts` |
| T6.6.2 | ✅ | Candidate adopt + conflict + SSE | `26-candidate-adopt-conflict-sse.spec.ts` |
| T6.6.3 | ✅ | Pipeline dry-run UI 入口 + stream | `28-pipeline-dry-run-ui-sse-flow.spec.ts` |
| T6.6.4 | ✅ | Batch dry-run 能力 + UI click | `29-batch-dry-run-flow.spec.ts`, `test_t6_6_4_batch_dry_run_contract.py` |

### 已验证的安全边界

- ✅ dry-run 不调用真实 LLM
- ✅ dry-run 不覆盖正文
- ✅ dry-run 不生成正式 candidate
- ✅ SSE 事件正常流转
- ✅ Task Queue / Pipeline / Batch 三条 dry-run 链路全部覆盖
- ✅ dev/test UI 入口全部可点击（仅在 dev 模式渲染）
- ✅ 任务状态轮询正常
- ✅ 测试项目正确隔离清理
- ✅ 测试项目命名规范（`__e2e_t6_6_*` / `__llm_smoke_*`）

---

## 三、当前已知限制（未覆盖）

| 限制项 | 说明 |
|--------|------|
| candidate-adopted SSE | 未完整端到端验证（API 层已验证，UI 层事件未做完整断言） |
| Pipeline stream 消息格式 | 当前使用 JSON 消息，不是标准 `event:` / `data:` 字段 |
| 真实 LLM 调用 | 尚未执行（需进入 T6.6.5 隔离环境） |
| 真实生成后的文本质量 / 速度 / 异常恢复 | 尚未验收 |
| 真实 LLM 测试隔离 | 必须隔离项目、可清理、可回滚 |

---

## 四、安全边界规范

### 通用规则

1. **不调用真实 LLM**：除非进入 T6.6.5 并显式开启开关
2. **不覆盖正文**：dry-run 模式禁止写入正式文件
3. **不生成正式 candidate**：测试 candidate 需标记为测试用途
4. **不污染真实项目**：测试项目使用专用前缀

### 测试项目命名规范

```
__e2e_t6_6_<功能>_<描述>
```

示例：
- `__e2e_t6_6_professional_safe_flow`
- `__e2e_t6_6_candidate_adopt`

真实 LLM 测试项目：

```
__llm_smoke_t6_6_5
```

### 清理要求

- 测试完成后必须删除测试项目
- 工作区必须保持 clean
- 不得遗留临时文件或数据

### 真实 LLM 额外规则（T6.6.5 起适用）

- 必须显式开关：`MOYUN_ALLOW_REAL_LLM_SMOKE=1`
- 默认 skip，不自动执行
- 单次调用，避免大规模 token 消耗
- 生成内容长度限制（max_tokens <= 300）
- 不允许 Batch 真实 LLM
- 不允许自动覆盖正文
- 失败时不得继续 adopt
- API Key 不得写入日志

---

## 五、T6.6 分阶段建议

### T6.6.0 ~ T6.6.4 ✅ 已完成

三条 dry-run 链路全部覆盖：
- **Task Queue**：`dry-run-task-button`（dev-only）
- **Pipeline**：`dry-run-pipeline-button`（dev-only）
- **Batch**：`dry-run-batch-button`（dev-only）

每条链路均已在 Playwright 中通过真实 UI click 验证安全边界。

### T6.6.5-plan ✅ 已完成

详细方案见：[t6-6-5-real-llm-smoke-plan.md](./t6-6-5-real-llm-smoke-plan.md)

### T6.6.5 真实 LLM 隔离环境冒烟测试（待执行）

- 仅测试最小路径：Professional 单场景 continue/rewrite
- 必须显式开关，默认 skip
- 只测一次或极少次真实 LLM
- 不建议本阶段测试 Batch / 长上下文 / 多轮复杂 Pipeline

---

## 六、参考链接

| 文档/文件 | 路径 |
|-----------|------|
| T6.6.5 真实 LLM 冒烟测试方案 | `docs/testing/t6-6-5-real-llm-smoke-plan.md` |
| T6.5.5 SSE 测试 | `frontend/tests/e2e/20-sse-real-event-flow.spec.ts` |
| T6.5.7 dry-run 契约测试 | `backend/tests/contracts/test_t6_5_7_dry_run_contract.py` |
| T6.6.4 Batch dry-run 后端测试 | `backend/tests/contracts/test_t6_6_4_batch_dry_run_contract.py` |
| T6.6.4 Batch dry-run E2E | `frontend/tests/e2e/29-batch-dry-run-flow.spec.ts` |
| ExecutionPanel（dev/test UI 入口） | `frontend/src/components/right-panel/ExecutionPanel.vue` |
| Task Store | `frontend/src/stores/task.ts` |

---

## 七、下一步可选路径

| 路径 | 说明 | 风险 |
|------|------|------|
| 1. 执行 T6.6.5 真实 LLM 隔离冒烟测试 | 验证真实生成链路，需显式开关 | 中（token 消耗，API Key 配置） |
| 2. 先做 T6.6-final 总结报告 | 收束当前阶段，延后真实 LLM | 低 |

---

*文档结束*
