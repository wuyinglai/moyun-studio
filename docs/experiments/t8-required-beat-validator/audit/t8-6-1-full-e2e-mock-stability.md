# T8.6.1 Full E2E Mock 稳定性专项报告

> 日期：2026-06-15
> 基线 commit：`f6a3a02 docs: add T8.6 final regression report`
> 分支：`main`

---

## 1. 背景

T8.6-final 验收时，full E2E suite 跑到 128/151 后超过 5 分钟被手动终止，大量 spec 因 mock 后端 30s 超时级联失败。该问题是既有技术债，影响后续阶段验收效率。

T8.6.1 目标：定位 root cause、修复可低风险修复的问题、让 full E2E 可靠运行。

---

## 2. 当前 Commit

```
f6a3a02 docs: add T8.6 final regression report
```

工作区状态：干净（初始检查）。

---

## 3. Full E2E Timeout 复现情况

### 修复前（T8.6-final 阶段）

```
命令：npm run test:e2e:mock -- --reporter=line
结果：> 5 分钟后手动终止（128/151），大量 30s Axios 超时级联
失败 spec：01, 10, 12, 13, 14, 15, 17 等（跨多个不相关 spec）
```

### 修复后

```
命令：npm run test:e2e:mock -- --reporter=line
结果：58 passed, 0 failed, 93 skipped (3.5m)
```

---

## 4. 定位过程

### Step 1：基础设施探索

阅读了 `playwright.config.ts`、`package.json`、`helpers/mockApi.ts` 和全部 31 个 spec 文件头部。

**关键发现：**

| 配置项 | 值 | 影响 |
|--------|-----|------|
| `fullyParallel` | `false` | spec 间不并行，但 worker 内顺序执行 |
| `workers` | 未设置 | 默认 half CPU cores = 11 workers |
| `webServer` | Vite dev only (port 5173) | **无后端启动** |
| `test:e2e:mock` | `playwright test` | **与 test:e2e 完全相同，无过滤** |
| spec 总数 | 31 个 | 其中 14 个需要真实后端 (port 8000) |

### Step 2：Spec 分类

| 类型 | 数量 | spec 编号 |
|------|------|-----------|
| Mock-based (page.route) | 14 | 01, 02, 06, 09, 10, 11, 12, 13, 14, 15, 16, 17, 30-real-llm-smoke, 99 |
| Real-backend (port 8000) | 13 | 18-30 (不含 30-real-llm-smoke) |
| Real-LLM (env-gated) | 3 | 03, 04, 05 |
| 混合 (real-LLM + 已 gated) | 1 | 30-real-llm-smoke |

### Step 3：Root Cause 分析

发现 **三个叠加的 root cause**：

**Root Cause 1：13 个 real-backend spec 无 skip guard**

Spec 18-30 直接调用 `http://127.0.0.1:8000/api`，但 Playwright `webServer` 只启动 Vite dev (port 5173)，不启动后端。每个 spec 的 `beforeAll` 中 fetch 连接失败 → 每个 test 等 120s 超时 → 13 个 spec × ~6 tests = ~78 个 test × 120s = 大量无效等待。

**Root Cause 2：Pinia persisted state 通过 localStorage 在 spec 间泄漏**

应用使用 `pinia-plugin-persistedstate`，9 个 Pinia store 持久化到 localStorage（`currentProject`、`perProjectData`、`fileMetaMap`、`messages` 等）。当 spec A 创建项目后，spec B 启动时 app 从 localStorage 恢复了一个不存在的 project，但 mock 返回空数据，导致 UI 进入不一致状态。

这解释了为什么所有 mock spec 单独运行通过、full suite 失败：单独运行时 localStorage 干净，full suite 运行时前面的 spec 污染了后面的。

**Root Cause 3：11 workers 并行导致 Vite dev server 资源争用**

`workers` 未设置，默认 half CPU = 11 workers。11 个浏览器上下文同时向 Vite dev server 发请求，导致大量 30s Axios 超时。

---

## 5. Root Cause

总结：

1. **13 real-backend spec 无 skip guard** → 每个 test 等 120s 超时，耗尽时间预算
2. **Pinia localStorage 状态泄漏** → mock spec 在全 suite 上下文中失败
3. **11 workers 并行** → Vite dev server 过载，加剧超时

---

## 6. 修复内容

### 6.1 Skip Guard：16 个 spec 加环境变量门控

| 环境变量 | 适用 spec | 数量 |
|----------|-----------|------|
| `MOYUN_E2E_REAL_BACKEND=1` | 18-30 (13 个 real-backend spec) | 13 |
| `MOYUN_ALLOW_REAL_LLM_SMOKE=1` | 03, 04, 05 (3 个 real-LLM spec) | 3 |
| `MOYUN_E2E_ALLOW_PHASE_SMOKE=1` | 99 (Phase T3-A 冒烟) | 1 |

模式与 `30-real-llm-smoke.spec.ts` 已有的 env-gated skip 一致：

```typescript
const REAL_BACKEND_AVAILABLE = process.env.MOYUN_E2E_REAL_BACKEND === '1'
test.describe('...', () => {
  test.skip(!REAL_BACKEND_AVAILABLE, 'MOYUN_E2E_REAL_BACKEND=1 未设置，跳过需要真实后端的测试')
  // ...
})
```

### 6.2 localStorage 清理：10 个 mock spec 加 addInitScript

在 10 个 mock-based spec 的 `beforeEach` 中添加：

```typescript
await page.addInitScript(() => {
  localStorage.clear()
  sessionStorage.clear()
})
```

受影响的 spec：01, 02, 09, 10, 11, 12, 13, 14, 16, 17

- 对于已有 `beforeEach` 的 spec (01, 02, 09)：注入到现有 `beforeEach` 开头
- 对于无 `beforeEach` 的 spec (10-17)：新增 `beforeEach` 块

### 6.3 Playwright Config：设置 `workers: 1`

```typescript
// playwright.config.ts
workers: 1,
```

防止 11 workers 并行导致 Vite dev server 过载。用户可通过 `--workers=N` CLI 参数覆盖。

---

## 7. Quarantine / Known Issue

### Spec 99：Phase T3-A FlowPanel 冒烟测试

**状态**：已 quarantine（`test.skip` 门控）。

**原因**：
- 无 mock、无 `page.route()`，所有 API 请求直接发到 Vite dev server
- 在 `beforeAll` 中创建共享 `chromium.launch()` browser/page，违反 Playwright 隔离模型
- 8 个 test 依赖顺序状态（test 2 依赖 test 1 的 UI 状态）
- 截图写入 `docs/testing/screenshots/`，有磁盘 IO 副作用
- 需要真实后端才能完整测试

**恢复方式**：设置 `MOYUN_E2E_ALLOW_PHASE_SMOKE=1` 并启动后端。

### 已知体验问题（非 T8.6.1 范围）

- Mock 实现重复：6+ 个 spec 各自维护 100-280 行的 `installMocks()` 函数，建议后续统一到 `helpers/mockApi.ts`
- `page.waitForTimeout()` 调用：137 处硬编码 sleep（500ms-16s），建议替换为 wait-for-condition

---

## 8. Focused E2E 结果

```
命令：npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
结果：12 passed (45.1s)
```

与修复前一致，无回归。

---

## 9. Full E2E 结果

### 修复前

| 指标 | 值 |
|------|-----|
| 完成度 | 128/151 (手动终止) |
| 通过 | 未知 |
| 失败 | 大量级联失败 |
| 跳过 | 0 |
| 耗时 | > 5 min |

### 修复后

| 指标 | 值 |
|------|-----|
| 完成度 | 151/151 (100%) |
| 通过 | **58** |
| 失败 | **0** |
| 跳过 | 93 |
| 耗时 | **3.5 min** |

### 93 个 skipped 分布

| 原因 | 数量 |
|------|------|
| Real-backend specs (18-30) | ~78 |
| Real-LLM specs (03-05) | ~10 |
| Phase T3-A 冒烟 (99) | 8 |
| 质量报告条件跳过 (06) | ~1 |

---

## 10. Remaining Issues

| # | 问题 | 优先级 | 阻断 T8.7？ |
|---|------|--------|-------------|
| 1 | Spec 99 (Phase T3-A) 需重构为标准 mock 模式 | P3 | 否 |
| 2 | Mock 实现重复（6+ 份 copy-paste） | P3 | 否 |
| 3 | 137 处 `waitForTimeout` 硬编码 sleep | P3 | 否 |
| 4 | 并行 workers > 1 时 Vite 资源争用 | P2 | 否（已设 workers:1） |
| 5 | 3 个 real-LLM spec 的 skip guard 与 30-real-llm-smoke 用了不同 env var | P4 | 否 |

---

## 11. 是否建议进入 T8.7

**建议进入 T8.7。**

理由：
- Full E2E suite 首次 100% 完成运行，58/58 mock 测试通过，0 失败
- Focused candidate E2E 12/12 通过，无回归
- Frontend build 通过
- 所有修改仅限测试基础设施，未改动产品代码
- Remaining issues 均为 P3+，不阻断后续开发

---

## 附录：修改文件清单

| 文件 | 改动类型 |
|------|----------|
| `frontend/playwright.config.ts` | 新增 `workers: 1` |
| `frontend/tests/e2e/01-main-entry-smoke.spec.ts` | localStorage clear |
| `frontend/tests/e2e/02-lite-entry-smoke.spec.ts` | localStorage clear |
| `frontend/tests/e2e/03-main-entry-real-llm.spec.ts` | skip guard (LLM) |
| `frontend/tests/e2e/04-lite-entry-real-llm.spec.ts` | skip guard (LLM) |
| `frontend/tests/e2e/05-candidate-batch-real-llm.spec.ts` | skip guard (LLM) |
| `frontend/tests/e2e/09-error-boundary.spec.ts` | localStorage clear |
| `frontend/tests/e2e/10-create-project-title-generation.spec.ts` | localStorage clear |
| `frontend/tests/e2e/11-right-panel-tabs.spec.ts` | localStorage clear |
| `frontend/tests/e2e/12-create-project-flow.spec.ts` | localStorage clear |
| `frontend/tests/e2e/13-file-operations.spec.ts` | localStorage clear |
| `frontend/tests/e2e/14-candidate-workflow.spec.ts` | localStorage clear |
| `frontend/tests/e2e/16-scene-plan-panel.spec.ts` | localStorage clear |
| `frontend/tests/e2e/17-lite-view.spec.ts` | localStorage clear |
| `frontend/tests/e2e/18-file-tree-editor.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/19-project-create-open-real-api.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/20-sse-real-event-flow.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/21-task-queue-pipeline-dry-run.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/22-task-queue-pipeline-real-dry-run.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/23-task-queue-pipeline-ui-dry-run.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/24-dry-run-ui-entry.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/25-professional-minimal-safe-flow.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/26-professional-dry-run-main-flow.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/27-candidate-adopt-conflict-sse-flow.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/28-pipeline-dry-run-ui-sse-flow.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/29-batch-dry-run-flow.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/30-candidate-adopted-sse-flow.spec.ts` | skip guard (backend) |
| `frontend/tests/e2e/99-phase-t3a-flowpanel-smoke.spec.ts` | skip guard (phase smoke) |
