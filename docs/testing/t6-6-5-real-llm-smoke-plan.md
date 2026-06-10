# T6.6.5 真实 LLM 隔离环境冒烟测试方案

> **重要**：本方案是一份 **plan 文档**，不是执行指令。
> 只有在满足所有前置条件、显式开启开关并人工确认后，才能进入真实执行。
> 本任务 **不调用真实 LLM**。

---

## 一、测试目标

T6.6.5 **不是**完整质量评估，只是 **最小真实 LLM 冒烟测试**，用来验证：

1. API Key / provider 配置可用
2. 单次真实生成可完成
3. 不覆盖正文（生成 candidate 而非直接写入）
4. candidate 生成路径安全
5. adopt 前有人工确认
6. adopt 前记录 `expected_hash` / `expected_mtime`
7. adopt 后正文更新
8. 错误能被前端 / 后端识别

本阶段不评估文本质量，只验证链路完整性。

---

## 二、测试范围

### 2.1 建议测试路径（只测一条最小路径）

**路径**：Professional 单场景 continue/rewrite

```
项目创建
  → 打开文件
  → Professional 面板
  → 选择生成类型（continue / rewrite）
  → 点击生成
  → 生成 candidate（不覆盖正文）
  → candidate preview 展示
  → 人工 review
  → 可选 adopt
  → 正文更新
  → file.updated / 轮询可见
```

### 2.2 不建议本阶段测试

| 不建议测试项 | 原因 |
|------------|------|
| Batch 真实 LLM | 多文件多请求，不可控 token 消耗 |
| 多文件批量真实生成 | 难以控制测试范围 |
| 长上下文真实生成 | token 消耗大 + 耗时久 |
| 多轮复杂 Pipeline | 稳定性无法在单次验证中保障 |
| 自动写入正文 | 与安全原则冲突 |
| 大量 token 输出 | 成本 + 时间不可控 |

---

## 三、测试项目隔离

### 3.1 项目命名

```
__llm_smoke_t6_6_5
```

**必须使用此前缀，不与真实用户项目混用。**

### 3.2 测试文件

```
chapters/vol-01/ch-001/sec-001.md
```

### 3.3 初始正文

```
T6.6.5 真实 LLM 冒烟测试初始正文。
请生成一小段不超过 100 字的续写。
```

### 3.4 预期 candidate 内容

- 非空
- 非 mock 字符串（不是 `[DRY-RUN]` 前缀）
- 长度 <= 300 tokens

---

## 四、环境开关

### 4.1 显式开关要求

必须同时满足 **以下两项之一** 才允许调用真实 LLM：

1. **环境变量**：
   ```
   MOYUN_ALLOW_REAL_LLM_SMOKE=1
   ```

2. **命令行参数**：
   ```
   npx playwright test tests/e2e/30-real-llm-smoke.spec.ts --project=chromium --grep @real-llm
   # 或自定义参数（由测试实现时决定）
   ```

### 4.2 未开开关时的行为

- **测试必须 skip**
- **不得调用真实 LLM**
- Playwright 输出 `@real-llm skipped` 标记

### 4.3 建议的测试文件骨架

```
frontend/tests/e2e/30-real-llm-smoke.spec.ts
```

```ts
// 默认 skip，除非 MOYUN_ALLOW_REAL_LLM_SMOKE=1
const ALLOW_REAL_LLM = process.env.MOYUN_ALLOW_REAL_LLM_SMOKE === '1'

test.describe('T6.6.5 Real LLM Smoke', () => {
  test.use({})

  if (!ALLOW_REAL_LLM) {
    test('@real-llm skipped (MOYUN_ALLOW_REAL_LLM_SMOKE not set)', async () => {
      console.log('[t6.6.5] skipped — 未开启真实 LLM 开关')
    })
    return
  }

  // 真实 LLM 测试用例（需额外实现）
  // test('1. 最小真实 LLM 生成 → candidate → adopt', ...)
})
```

> 本任务 **不** 实现上述骨架，只做规划。

---

## 五、安全边界

### 5.1 必须遵守

| 规则 | 说明 |
|------|------|
| 不允许 Batch 真实 LLM | 仅测单场景生成 |
| 不允许自动覆盖正文 | 必须走 candidate 路径 |
| 不允许写 scoring/final | 不修改任何 scoring / final 字段 |
| 不允许污染 story_state / materials / recent_context | 不写任何 context / meta 文件 |
| 不允许使用真实用户项目 | 仅用 `__llm_smoke_*` 项目 |
| 生成内容长度限制 | max_tokens <= 300 |
| 测试项目必须可删除 | 测试完成后调用 delete project API |
| API Key 不得写入日志 | 日志中严禁出现 key |
| 测试输出不得包含完整密钥 | 日志脱敏 |
| 失败时不得继续 adopt | 生成失败后禁止走 adopt 流程 |

### 5.2 异常回滚

如果测试过程中发现异常：

1. **立即停止**后续 adopt / 写入操作
2. **删除**测试项目（通过 delete API）
3. **记录**完整错误日志（脱敏后）
4. **输出**失败报告（不包含 key）
5. **不改** commit / push

---

## 六、验收标准

### 6.1 成功标准

| 项目 | 标准 |
|------|------|
| 开关 | 真实 LLM 请求被显式开关允许 |
| LLM 调用次数 | 只调用一次或极少次数 |
| candidate 生成 | 成功生成 candidate |
| 正文保护 | 原正文不自动覆盖 |
| candidate 内容 | 非空、非 mock |
| preview | candidate preview 可见 |
| adopt 保护 | adopt 前检查冲突 / hash / mtime |
| adopt 后更新 | 正文更新，file.updated / 轮询可见 |
| 清理 | 测试项目可清理成功 |
| 工作区 | clean |

### 6.2 失败标准（命中任一项即失败）

| 项 | 说明 |
|---|------|
| 未开开关却调用真实 LLM | 严重阻断 |
| 自动覆盖正文 | 严重阻断 |
| 生成内容写入 final/scoring | 严重阻断 |
| API Key 泄露到日志 | 严重阻断 |
| Batch 真实调用 | 严重阻断 |
| 失败后继续 adopt | 阻断 |
| 测试项目未清理 | 需手动修复 |

---

## 七、建议测试步骤（执行版）

> 本步骤为 **T6.6.5 执行阶段** 的参考步骤，不是本任务的操作。

1. 确认代码在最新 commit，工作区 clean
2. 确认 API Key 已配置（`.env` 或对应 provider 配置）
3. 设置 `MOYUN_ALLOW_REAL_LLM_SMOKE=1`
4. 启动后端 `uvicorn backend.main:app`
5. 启动前端 `npm run dev`
6. 执行 `npx playwright test tests/e2e/30-real-llm-smoke.spec.ts --project=chromium`
7. 观察首次真实生成是否成功
8. 在 candidate preview 中人工 review
9. 选择 adopt，观察正文更新 + file.updated 可见
10. 清理测试项目，确认工作区 clean
11. 记录结果

---

## 八、建议的执行 checklist

```
□ 代码在最新 commit
□ 工作区 clean
□ API Key 已配置
□ MOYUN_ALLOW_REAL_LLM_SMOKE=1
□ 后端启动成功
□ 前端启动成功
□ 测试项目使用 __llm_smoke_t6_6_5
□ 单次真实 LLM 调用
□ 生成 candidate 成功
□ 正文未自动覆盖
□ candidate preview 可见
□ adopt 前冲突检查通过
□ adopt 后正文更新
□ 测试项目删除成功
□ 工作区 clean
□ 日志中无 API Key
```

---

## 九、何时不执行 T6.6.5

建议在以下任一情况发生时 **不执行** 真实 LLM 测试：

1. API Key 配置不完整或不可用
2. 对生成路径做过重大修改但未通过 dry-run
3. 网络不稳定（可能导致 token 浪费 / 超时）
4. 只想快速确认整体流程（改用 dry-run 即可）

---

## 十、参考链接

| 文件 | 说明 |
|------|------|
| [t6-6-professional-e2e-acceptance.md](./t6-6-professional-e2e-acceptance.md) | T6.6 总验收清单 |
| `frontend/src/components/right-panel/ExecutionPanel.vue` | ExecutionPanel（含 dev-only dry-run 按钮） |
| `frontend/src/stores/task.ts` | Task Store |
| `backend/core/generation_service.py` | 生成服务（dry-run / 真实路径） |
| `backend/api/generate.py` | 生成 API 入口 |

---

*文档结束*
