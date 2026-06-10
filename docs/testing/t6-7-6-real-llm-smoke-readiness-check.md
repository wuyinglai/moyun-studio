# T6.7.6 真实 LLM 冒烟测试准备检查

> **任务性质**：准备检查文档，**不执行真实 LLM 调用**。不调用真实 LLM，不使用 API Key，不执行真实生成。
>
> **前置基线**：T6.6（完整 dry-run 验收 + T6.6.5 方案文档）、T6.7.5a（Batch result schema contract 加固）已完成。

---

## 一、当前结论

**T6.7.6 只做准备检查，不执行真实 LLM。**

本任务完成了对以下内容的静态分析：
- 当前真实 LLM 调用入口（generate / batch）
- 当前 dry-run 路径（完全隔离，不触发 LLM）
- 当前 `MOYUN_ALLOW_REAL_LLM_SMOKE` 开关状态
- 当前 max_tokens 限制
- 当前日志脱敏情况
- 当前项目隔离规则
- 当前 adopt 安全策略

---

## 二、准备检查清单

以下清单基于 T6.6.5 方案文档，逐一对照当前代码现状。

| # | 规则 | 当前状态 | 说明 |
|---|------|---------|------|
| 1 | 显式开关 `MOYUN_ALLOW_REAL_LLM_SMOKE=1` | ⚠️ **仅存在于文档** | 代码中无任何读取逻辑；后端 `config.py` 无此字段；需在 T6.7.6a 新增 |
| 2 | 默认跳过（未开开关时测试 skip） | ⚠️ **无测试骨架** | `frontend/tests/e2e/30-real-llm-smoke.spec.ts` 不存在；需在 T6.7.6a 新增 |
| 3 | 测试项目命名 `__llm_smoke_t6_6_5` | ✅ **已约定在文档中** | E2E 测试用 `__e2e_*` 前缀；`__llm_smoke_*` 仅为方案约定，无代码强制 |
| 4 | 测试文件 `chapters/vol-01/ch-001/sec-001.md` | ✅ **已约定在方案中** | 需在 T6.7.6a 测试骨架中显式创建 |
| 5 | max_tokens <= 300 | ⚠️ **无 smoke 专用限制** | 后端默认 `llm_max_tokens=16000`；Batch 生成硬编码 2500；无 smoke <=300 限制 |
| 6 | 只允许单场景生成 | ✅ **方案已明确** | T6.6.5 方案限制只测单场景 |
| 7 | 不允许 Batch 真实 LLM | ✅ **已明确** | T6.6.5/T6.7.5 方案均明确禁止；`generation_service.py` 中 dry_run=True 时跳过 LLM |
| 8 | 不允许自动覆盖正文 | ⚠️ **有条件保护** | 当 `should_create_candidate()` 返回 False 时会直接写文件（无冲突保护）；需确保测试文件有内容 |
| 9 | 只允许生成 candidate | ✅ **有条件保护** | `should_create_candidate()` 对 rewrite/continue 等模式返回 True；需确保测试文件非空 |
| 10 | adopt 必须人工或测试显式确认 | ✅ **已有 adopt API** | adopt 有 expected_mtime/expected_hash 冲突检测；失败时 candidate.adopted 不更新 |
| 11 | adopt 前带冲突保护 | ✅ **已实现** | candidate adopt API 层检查冲突，返回 409 |
| 12 | API Key 不写日志 | ⚠️ **部分风险** | litellm 内部可能打印请求；`llm.py` 中 `logger.error(f"LLM 未知错误 [{error_type}]: {e}")` 若异常含 Key 上下文则泄露 |
| 13 | 失败后不得继续 adopt | ✅ **API 层保证** | adopt 失败时 HTTP 状态非 200，前端不应继续 |
| 14 | 测试后必须清理 | ⚠️ **需在骨架中实现** | E2E 测试骨架需在 `afterAll` 中调用 delete project API |

---

## 三、当前代码差距

### 3.1 已具备

| 能力 | 位置 |
|------|------|
| dry-run 路径完全不调 LLM | `generation_service.py` L395-404 |
| Batch 真实 LLM 有 dry_run 参数控制 | `BatchGenerateRequest.dry_run` |
| should_create_candidate 策略 | `backend/policies/candidate_policy.py` |
| candidate adopt 冲突保护 | `backend/api/candidates.py` |
| LLM 熔断器 | `backend/core/llm_circuit_breaker.py` |
| API Key 从配置文件读取（非硬编码） | `llm.py` `load_llm_config_from_workspace()` |
| 日志规范（error 中不含明文 key） | `llm.py` 中异常消息不含 api_key |
| 测试项目命名约定（`__e2e_*`） | 现有 E2E 测试惯例 |

### 3.2 缺什么

| 缺口 | 严重度 | 说明 |
|------|--------|------|
| 后端无 `MOYUN_ALLOW_REAL_LLM_SMOKE` 环境变量读取 | **高** | 无法在 API 层 gate 真实 LLM 调用；建议在 `config.py` 新增字段并在 API 层检查 |
| 无 E2E test skeleton | **高** | `frontend/tests/e2e/30-real-llm-smoke.spec.ts` 不存在；需新增并默认 skip |
| 无 smoke 专用 max_tokens 限制 | **中** | 当前无 <=300 冒烟限制；可在 `config.py` 新增 `llm_smoke_max_tokens=300` |
| 日志脱敏未验证 | **低** | litellm 内部日志无法控制；`llm.py` 自己的日志不含明文 key |

### 3.3 需要改什么

| 需改动位置 | 改动内容 |
|-----------|---------|
| `backend/config.py` | 新增 `allow_real_llm_smoke: bool` 字段（默认 False） |
| `backend/api/generate.py` | 在 `batch_generate` 和 `generate` 中，若 `allow_real_llm_smoke=False` 且 `dry_run=False`，返回错误或强制 dry_run |
| `frontend/tests/e2e/30-real-llm-smoke.spec.ts` | 新增测试骨架，未设置 `MOYUN_ALLOW_REAL_LLM_SMOKE=1` 时 skip |

---

## 四、推荐下一步

### 选项 A：T6.7.6a — 新增默认 skip 的真实 LLM smoke test skeleton

**目标**：不调用真实 LLM，只建立骨架 + 断言。未开开关时 Playwright 测试直接 skip。

范围：
- 在 `backend/config.py` 新增 `allow_real_llm_smoke: bool = False`
- 在 `backend/api/generate.py` 新增 gate：若 `allow_real_llm_smoke=False` 且请求 `dry_run=False`，拒绝或强制 dry_run
- 新增 `frontend/tests/e2e/30-real-llm-smoke.spec.ts`，默认 skip
- 在骨架中建立项目创建 → dry_run=True 验证 → 项目清理的最小路径

不改动：
- 不改 dry-run 逻辑
- 不改 candidate 策略
- 不改文件写入策略
- 不实际调用真实 LLM

### 选项 B：T6.8.0 — 在用户显式确认后执行真实 LLM 隔离冒烟测试

**目标**：在 T6.7.6a 完成 + 用户配置 API Key + 设置 `MOYUN_ALLOW_REAL_LLM_SMOKE=1` 后，执行最小冒烟。

必须满足：
- 用户显式确认（不接受自动触发）
- `MOYUN_ALLOW_REAL_LLM_SMOKE=1` 已设置
- API Key 已配置
- 只测单场景 candidate
- 不测 Batch
- max_tokens <= 300
- adopt 前人工确认
- 测试后清理

---

## 五、真实 LLM 调用入口总结

```
真实 LLM 入口：
1. POST /api/generate
   → GenerationService.generate_stream()
   → svc.complete()  [stream=True]
   → litellm.acompletion()

2. POST /api/generate/batch
   → GenerationService.batch_generate()
   → svc.complete_sync()  [stream=False]
   → litellm.acompletion()

Dry-run 路径（完全不调 LLM）：
1. POST /api/generate + dry_run=True → GenerationService 中 dry_run 分支
2. POST /api/generate/batch + dry_run=True → L395-404 模拟分支

Gate 控制点：
- 当前：dry_run=True 参数（前端传入）
- 缺失：后端环境变量 gate（MOYUN_ALLOW_REAL_LLM_SMOKE）
```

---

## 六、T6.6.5 方案回顾

T6.6.5 方案（`docs/testing/t6-6-5-real-llm-smoke-plan.md`）定义了：
- 测试路径：Professional 单场景 continue/rewrite
- 禁止项：Batch 真实 LLM / 自动覆盖正文 / 污染 context
- 开关机制：`MOYUN_ALLOW_REAL_LLM_SMOKE=1`
- 安全边界：max_tokens <= 300 / 失败不 adopt / 日志脱敏

**本任务确认 T6.6.5 方案设计完整，但代码实现存在缺口（无后端 gate，无测试骨架）。**

---

## 七、本轮明确不做的事

| 事项 | 原因 |
|------|------|
| 执行真实 LLM 调用 | 本任务只做准备检查 |
| 配置 API Key | 不需要 |
| 修改 dry-run 逻辑 | 现有 dry-run 已完全隔离 |
| 修改 candidate 策略 | 现有策略已工作 |
| 修改文件写入策略 | 现有策略已工作 |
| 新增真实 LLM E2E 用例 | 留给 T6.7.6a 或 T6.8.0 |

---

*文档结束*
