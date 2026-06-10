# T6.6 Professional 主流程安全 E2E 总验收清单

## 版本记录

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v1.0 | 2026-06-10 | E2E | 初始版本 |

---

## 一、已完成模块列表

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

### 已验证的安全边界

- ✅ dry-run 不调用真实 LLM
- ✅ dry-run 不覆盖正文
- ✅ dry-run 不生成正式 candidate
- ✅ SSE 事件正常流转
- ✅ 任务状态轮询正常
- ✅ 测试项目正确隔离清理

---

## 二、当前未覆盖模块

### 待完成能力

| 能力 | 状态 | 说明 | 建议优先级 |
|------|------|------|------------|
| Batch dry-run | ⚠️ | Batch Generate 的 dry-run 支持 | 中 |
| Pipeline dry-run UI 入口 | ⚠️ | 前端触发 Pipeline dry-run 的按钮 | 低 |
| Real LLM generation | ⚠️ | 真实 LLM 调用的完整生成链路 | 高（隔离环境） |
| Full Professional generation adopt path | ⚠️ | 从生成到采纳的完整路径 | 高（隔离环境） |

### 风险说明

1. **Batch dry-run**：当前 Batch API 未接入 Task Queue，需单独实现
2. **Pipeline dry-run UI**：当前已支持 API 调用，UI 入口可延后
3. **真实 LLM 测试**：需要隔离环境，避免产生正式业务数据

---

## 三、T6.6 分阶段建议

### T6.6.0 当前：总验收清单 + 最小 dry-run 串联
- 建立总验收文档
- 最小 Professional 主流程 dry-run 串联测试
- 验证安全边界闭环

### T6.6.1 Professional 主流程 dry-run E2E
- 从项目列表进入 → 打开文件 → 触发 dry-run → 查看结果
- 覆盖完整用户路径

### T6.6.2 Candidate adopt + conflict + SSE 串联
- 验证候选稿采纳流程
- 验证冲突检测机制
- 验证 SSE 事件联动

### T6.6.3 Pipeline dry-run UI 入口（如需要）
- 在 ExecutionPanel 添加 Pipeline dry-run 按钮
- 验证 Pipeline SSE 事件可见

### T6.6.4 Batch dry-run（如需要）
- 实现 Batch dry-run 后端能力
- 添加前端入口和测试

### T6.6.5 真实 LLM 隔离环境冒烟测试
- 在隔离环境中验证真实生成
- 验证完整生成→采纳→更新链路

---

## 四、安全边界规范

### 通用规则

1. **不调用真实 LLM**：除非明确进入真实 LLM 测试阶段
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

### 清理要求

- 测试完成后必须删除测试项目
- 工作区必须保持 clean
- 不得遗留临时文件或数据

---

## 五、验收标准

### 通过条件

| 项目 | 通过标准 |
|------|----------|
| 文档 | 总验收清单完整，已完成/未覆盖模块清晰 |
| 最小串联测试 | Playwright 通过，安全边界全部验证 |
| 后端测试 | pytest 相关测试全部通过 |
| 前端构建 | npm run build 成功 |
| 代码质量 | git diff --check 无问题 |

### 阻断条件

- dry-run 调用真实 LLM
- dry-run 覆盖正式正文
- dry-run 生成正式 candidate
- 测试项目未清理
- 工作区不干净

---

## 六、参考链接

| 文档/文件 | 路径 |
|-----------|------|
| T6.5.5 SSE 测试 | `frontend/tests/e2e/20-sse-real-event-flow.spec.ts` |
| T6.5.7 dry-run 契约测试 | `backend/tests/contracts/test_t6_5_7_dry_run_contract.py` |
| T6.5.9 dry-run UI 入口 | `frontend/src/components/right-panel/ExecutionPanel.vue` |
| Task Store | `frontend/src/stores/task.ts` |
| ExecutionPanel | `frontend/src/components/right-panel/ExecutionPanel.vue` |

---

*文档结束*
