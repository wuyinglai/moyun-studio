# T6.7 产品化修复 / UI 清理路线图

> **阶段性质**：本路线图是 T6.6 dry-run 验收完成后的产品化收口阶段，**不是新增大功能**，而是把现有功能中的体验问题、架构问题和测试覆盖缺口逐步收口。

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-10 | 初始版本 |
| v1.1 | 2026-06-10 | 标记 T6.7.5 完成，补充 Batch 架构评估交付物 |
| v1.2 | 2026-06-11 | 标记 T6.7.6 完成，补充真实 LLM 冒烟准备检查文档和骨架 |

---

## 一、阶段目标

T6.7 目标不是新增大功能，而是把 T6.6 dry-run 验收暴露出的产品化问题收口，让 Professional 主流程更稳定、更清晰、更接近可真实使用状态。

具体而言：
- 整理 dev/test UI，降低误操作风险
- 补齐 SSE 事件覆盖缺口
- 标准化流式消息格式认知
- 评估 Batch 与 TaskQueue / Pipeline 的架构关系
- 为真实 LLM 冒烟测试做最后准备

---

## 二、T6.6 遗留限制清单

以下限制来自 [T6.6 final 总验收报告](../testing/t6-6-final-acceptance-report.md)，如实转录：

| 限制项 | 说明 | 紧迫度 |
|--------|------|--------|
| candidate-adopted SSE | 未完整端到端验证（API adopt 层已覆盖，UI 层 file.updated 事件断言不完整） | 高 |
| Pipeline stream 消息格式 | 当前使用 JSON 消息，不是标准 `event:` / `data:` 字段（类似 SSE 但非标准） | 中 |
| Task 状态 UI | 部分场景主要通过 API 轮询 + store 验证，非 SSE 实时推送 | 中 |
| dev/test dry-run 按钮布局 | 散落在 ExecutionPanel，布局和产品语义需要整理 | 低 |
| Batch 与 TaskQueue/Pipeline 架构割裂 | Batch 独立运行，未接入 TaskQueue，未发布任务事件 | 低 |
| 真实 LLM 尚未执行 | — | — |
| 真实生成质量 / 速度 / 异常恢复 | 尚未验收 | — |

---

## 三、T6.7 建议任务拆分

### T6.7.1：dev/test dry-run 按钮布局整理

**优先级**：P0
**目标**：把 TaskQueue / Pipeline / Batch 三个 dry-run 按钮放入清晰的开发测试区块，不影响生产 UI。

具体：
- 在 ExecutionPanel 中新增 `.dev-actions` 区块（或类似语义分区）
- 三个按钮统一放在该区块内，`v-if="isDevMode"` 不变
- 按钮可折叠或收起，避免占用主界面空间
- Playwright 验证：切换到"执行"tab 后按钮可见 + 真实 click

**不改动**：
- 后端 dry-run 逻辑
- 生产 UI 行为
- API 契约

---

### T6.7.2：candidate-adopted SSE 补测

**优先级**：P0
**目标**：补齐 adopt 成功后的 candidate-adopted SSE 或确认真实事件名，与 file.updated 区分。

具体：
- 阅读 `backend/api/candidates.py` 和 `backend/core/event_bus.py`
- 确认 adopt 后实际发布的事件类型（`candidate.adopted` / `file.updated` / 其他）
- 补写 Playwright 测试断言，确保 adopt 后 SSE 事件可被观测
- 如果当前无 candidate-adopted 事件，文档化现状，不要强行添加

**不改动**：不调用真实 LLM，不改 adopt 逻辑

---

### T6.7.3：Pipeline stream 格式标准化评估

**优先级**：P1
**目标**：评估是否统一为标准 SSE event/data 格式，若暂不改至少文档化当前 JSON stream 结构。

具体：
- 阅读 `backend/api/pipeline.py` 和 `frontend/src/composables/useSSE.ts`
- 确认当前 Pipeline stream 消息的完整结构（是否类似 `event: done\ndata: {...}`）
- 评估是否可改为标准 SSE 格式（后端改 event_bus，前端改 useSSE）
- 如需改，写评估报告，不在本阶段直接大改
- 如不改，文档化当前 JSON stream 格式供后续参考

**风险**：改动 stream 格式可能破坏已有 dry-run E2E，谨慎评估

---

### T6.7.4：Task 状态 UI 统一

**优先级**：P0
**目标**：减少 API/store/轮询降级验证，统一 TaskQueue / Pipeline / Batch dry-run 的前端状态展示。

具体：
- 梳理 TaskQueue / Pipeline / Batch 三条链路的 task 状态模型
- 确认 `pending / running / completed / failed / cancelled / dry_run` 状态映射是否一致
- 评估 ExecutionPanel 中任务状态展示是否统一
- 如有不一致，整理 store 或 UI，不改后端逻辑

---

### T6.7.5：Batch 与 TaskQueue/Pipeline 架构关系评估 ✅

**优先级**：P1
**状态**：已完成

**目标**：评估 Batch 是否应接入 TaskQueue，是否应发布任务事件，是否应统一 candidate 策略。

**完成内容**：
- 梳理 Batch 当前架构（同步执行，不经过 TaskQueue，不发布 SSE 事件）
- 对比 TaskQueue / Pipeline 的任务调度模型
- 输出完整架构评估报告，明确不做本轮接入
- 推荐分 6 Phase 演进（A 现状文档化 → F 真实 LLM 冒烟）

**交付物**：
- [docs/architecture/t6-7-5-batch-architecture-assessment.md](../architecture/t6-7-5-batch-architecture-assessment.md)

**结论**：Batch 与 TaskQueue 架构保持独立，T6.7 不做大改动。

**建议后续**：
- T6.7.5a：Batch result schema contract 加固（可选，P2）
- T6.7.6：真实 LLM 冒烟测试准备检查（P1）

---

### T6.7.6：真实 LLM 冒烟测试准备检查 ✅

**优先级**：P1（前置条件）
**状态**：已完成

**目标**：检查 `MOYUN_ALLOW_REAL_LLM_SMOKE=1` 开关、隔离项目、max_tokens、日志脱敏。

**完成内容**：
- 完成 12 项静态分析，识别当前真实 LLM 调用入口和护栏现状
- 确认 `MOYUN_ALLOW_REAL_LLM_SMOKE=1` 只存在于 T6.6.5 方案文档，代码中无读取逻辑（⚠️ 需在 T6.7.6a 新增后端 gate）
- 确认 Batch 真实 LLM 已明确禁止（dry_run 参数 + 文档约定）
- 确认 adopt 冲突保护已实现（expected_mtime / expected_hash）
- 新增 `docs/testing/t6-7-6-real-llm-smoke-readiness-check.md` 准备检查文档
- 新增 `frontend/tests/e2e/30-real-llm-smoke.spec.ts` 骨架，默认 skip（未开开关时跳过）

**交付物**：
- [docs/testing/t6-7-6-real-llm-smoke-readiness-check.md](../testing/t6-7-6-real-llm-smoke-readiness-check.md)
- [frontend/tests/e2e/30-real-llm-smoke.spec.ts](../../frontend/tests/e2e/30-real-llm-smoke.spec.ts)

**结论**：当前代码差距 = 后端无环境变量 gate + 无 smoke 专用 max_tokens 限制。T6.7.6a 补充后端 gate 后方可执行真实 LLM 冒烟。

**建议后续**：
- T6.7.6a：新增后端 gate（`allow_real_llm_smoke`）+ E2E 骨架完善
- T6.8.0：用户显式确认后执行真实 LLM 隔离冒烟

**不改动**：不在本任务执行真实 LLM 调用

---

## 四、优先级总结

| 优先级 | 任务 | 说明 |
|--------|------|------|
| **P0** | T6.7.1 dev/test 按钮布局整理 | 风险最低，立即提升 UI 清晰度 |
| **P0** | T6.7.2 candidate-adopted SSE 补测 | 填补事件覆盖缺口 |
| **P0** | T6.7.4 Task 状态 UI 统一 | 提升用户体验一致性 |
| **P1** | T6.7.3 Pipeline stream 格式评估 | 评估后再决定是否改 |
| **P1** | T6.7.5 Batch 架构关系评估 | 不急着大改 |
| **P1** | T6.7.6 真实 LLM 准备 | 为后续执行打基础 |

---

## 五、风险说明

| 规则 | 说明 |
|------|------|
| 不要大改 Batch 架构 | T6.7 初期不直接重构 Batch，保持稳定 |
| 不要无开关调用真实 LLM | 除非 T6.7.6 准备完成 + 显式开关 |
| 不要破坏已有 dry-run E2E | 任何改动后必须确保 T6.6 的 Playwright 测试仍通过 |
| 不要暴露 dev/test 按钮到生产 | `v-if="isDevMode"` 必须保留 |
| 不要跳过冲突保护 | adopt 前 hash / mtime 检查不能绕过 |
| 不要隐藏降级验证事实 | UI/API 降级场景要文档化，不要假装全是实时 SSE |

---

## 六、T6.8 真实 LLM 隔离冒烟阶段 ✅

**状态**：已完成（T6.8.0 + T6.8.1 + T6.8.2）

### T6.8.0：真实 LLM 冒烟前准备检查
- ✅ 确认后端 gate 已就绪（`allow_real_llm_smoke`）
- ✅ 确认 max_tokens 限制已就绪（`llm_smoke_max_tokens=300`）
- ✅ 创建隔离项目 `__llm_smoke_t6_8_1`
- ✅ 准备测试场景文件

### T6.8.1：真实 LLM 隔离冒烟验证
- ✅ 真实 LLM 调用成功（pipeline 模式，6 个 step）
- ✅ candidate 真实生成：`cand_1c819dfe`
- ✅ candidate 文件存在且非空（142 chars）
- ✅ candidate status = pending（未 adopt）
- ✅ 原正文未被覆盖
- ✅ 未执行 Batch（被 gate 禁止）
- ✅ smoke 项目已清理

**记录 commit**：`e8f3313d1e526b6d8985ccc0f863e78736d81e54`

**交付物**：
- [docs/testing/t6-8-1-real-llm-smoke-result.md](../testing/t6-8-1-real-llm-smoke-result.md)

### T6.8.2：安全回归与文档收口
- ✅ 安全污染检查（无残留）
- ✅ API Key 未提交（脱敏保护正常）
- ✅ .env 未改动
- ✅ 回归测试全部通过（45 个 contract tests）
- ✅ frontend build 成功
- ✅ Playwright smoke skeleton 默认 skipped（无开关不执行）

### 下一步建议
**T6.9.0：产品化 review / 发布前体验整理**

建议先做产品化 review，确认当前状态是否满足发布质量要求，再决定是否扩大真实 LLM 测试范围。

---

## 七、T6.6 最终验收报告

详细 T6.6 验收内容见：[../testing/t6-6-final-acceptance-report.md](../testing/t6-6-final-acceptance-report.md)

---

*文档结束*
