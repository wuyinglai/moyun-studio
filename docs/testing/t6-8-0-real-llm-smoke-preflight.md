# T6.8.0 真实 LLM 隔离冒烟测试执行前确认

> **任务性质**：**执行前确认文档，**不执行真实 LLM**，不使用 API Key，不执行真实生成。
>
> **前置基线**：T6.7.6a / 6b / 6c 已全部收口。

---

## 一、当前前置状态

- **当前 HEAD**：`e02114d2aef8597f16876394512e726729a590a8
- **分支**：`main`
- **HEAD == origin/main == ls-remote**
- **工作区**：clean
- **真实 LLM smoke gate**：已完成
- **smoke max_tokens**：已强制限制（`llm_smoke_max_tokens=300）
- **Pipeline diff summary**：已透传 `llm_extra_kwargs`
- **Batch 真实 smoke**：已禁止（`check_batch_real_llm_smoke_gate()` 永久拒绝）
- **Playwright smoke skeleton**：默认 `3 skipped`（未设置开关时不会跑）

---

## 二、执行前必须满足

### 2.1 环境变量

```text
MOYUN_ALLOW_REAL_LLM_SMOKE=1
MOYUN_LLM_SMOKE_MAX_TOKENS=300
```

### 2.2 执行前必须由用户明确确认

```text
我确认执行 T6.8.1 真实 LLM 隔离冒烟测试。
```

---

## 三、测试范围（T6.8.1

```text
只测一个隔离 smoke 项目
只测一个场景文件
只生成 candidate
不自动 adopt
不覆盖正文
不测试 Batch
max_tokens <= 300
```

### 3.1 隔离项目建议

```text
project_id = __llm_smoke_t6_8_1
file = chapters/vol-01/ch-001/sec-001.md
```

### 3.2 调用入口

- **POST /api/generate`（单场景，candidate 模式）
- **POST /api/pipeline/run`（pipeline 模式）

---

## 四、禁止事项

```text
禁止 Batch 真实 LLM
禁止自动覆盖正文
禁止默认启用真实 LLM
禁止记录 API Key
禁止未确认就 adopt
禁止未清理测试项目
```

---

## 五、执行前逐项检查清单

| # | 项目 | 状态 | 说明 |
|---|------|------|------|
| 1 | `MOYUN_ALLOW_REAL_LLM_SMOKE` 默认 false | ✅ | `backend/config.py` `allow_real_llm_smoke: bool = Field(default=False, ...)` |
| 2 | `MOYUN_LLM_SMOKE_MAX_TOKENS` 默认 300 | ✅ | `backend/config.py` `llm_smoke_max_tokens: int = Field(default=300, ge=1, le=1024, ...)` |
| 3 | smoke skeleton 未设置开关时 skipped | ✅ | `tests/e2e/30-real-llm-smoke.spec.ts` 3 skipped |
| 4 | Batch 真实 smoke 被禁止 | ✅ | `backend/core/smoke_gate.py` `check_batch_real_llm_smoke_gate()` 永久拒绝 |
| 5 | `/api/generate` 有 smoke gate | ✅ | `backend/api/generate.py` `check_real_llm_smoke_gate(settings, project_id, dry_run)` |
| 6 | `/api/chat` 有 smoke gate | ✅ | `backend/api/generate.py` 同 gate |
| 7 | `/api/pipeline/run` 有 smoke gate | ✅ | `backend/api/pipeline.py` 同 gate |
| 8 | Pipeline diff summary 透传 max_tokens | ✅ | `backend/core/pipeline.py` `_generate_diff_summary(llm_extra_kwargs=...)` → `complete(messages, timeout=60, **extra)` |
| 9 | smoke 项目通过真实 project_id 前缀识别 | ✅ | `/api/projects` 返回 `uuid[:8]`，**不**保留 `__llm_smoke_` 前缀；name 保存在 meta.json；必须直接创建 `projects/__llm_smoke_t6_8_1/` 目录 |
| 10 | API Key 不写日志 | ✅ | `backend/core/llm.py` 日志消息不含明文 key |
| 11 | 测试项目清理 | ✅ | `30-real-llm-smoke.spec.ts` afterAll 删除项目；本文档明确要求清理 |
| 12 | adopt 前冲突保护 | ✅ | `backend/api/candidates.py` `expected_mtime/expected_hash` 校验；不一致返回 `CONFLICT / FILE_MODIFIED` |
| 13 | 只测单场景 candidate | ✅ | 本文档明确限定范围 |
| 14 | 不测 Batch | ✅ | Batch gate 永久拒绝；本文档明确禁止 |
| 15 | 不自动覆盖正文 | ✅ | candidate 写入 `.candidates/`；adopt 需显式调用带冲突保护 |

---

## 六、清理方案

```text
测试完成后删除 __llm_smoke_t6_8_1 项目目录
确认 git status clean
确认无测试产物进入版本库
```

---

## 七、Contract 测试覆盖

- `test_t6_7_6a_real_llm_smoke_gate_contract.py` — gate / 批处理（20 passed
- `test_t6_7_6b_smoke_max_tokens_contract.py` — max_tokens 强制（19 passed）
- `test_t6_7_6c_pipeline_smoke_max_tokens_contract.py` — pipeline 透传 + project_id 策略（6 passed）

---

*本文档仅做执行前确认。**T6.8.1 前需用户明确确认后才能执行真实 LLM 隔离冒烟测试。**
