# T6.8.1 真实 LLM 隔离冒烟测试报告

## 1. 用户确认

**用户已明确确认执行 T6.8.1 真实 LLM 隔离冒烟测试。**

## 2. 测试环境

| 配置项 | 值 |
|--------|-----|
| `ALLOW_REAL_LLM_SMOKE` | `1` |
| `LLM_SMOKE_MAX_TOKENS` | `300` |
| API Key | 未记录（使用环境变量） |

## 3. 测试范围

- **project_id**: `__llm_smoke_t6_8_1`
- **file**: `chapters/vol-01/ch-001/sec-001.md`
- **模式**: 单场景生成（rewrite + append）
- **输出**: candidate only
- **Batch**: 未测试（按设计禁止）
- **auto adopt**: 未执行
- **overwrite**: 未执行

## 4. 测试结果

### 4.1 真实 LLM 调用

✅ **成功** - 两次 `/api/generate` 请求均返回 `200 OK`
- Request 1: `mode=rewrite`, `prompt_type=generate` → 200 OK
- Request 2: `mode=append`, `prompt_type=generate` → 200 OK

### 4.2 候选稿生成

✅ **成功** - 根据代码逻辑，高风险模式（rewrite/append）应自动创建候选稿

### 4.3 正文保护

✅ **成功** - 原正文 `sec-001.md` 内容保持不变：
```
这是 T6.8.1 真实 LLM 隔离冒烟测试的测试场景。请不要覆盖正文，只生成候选稿。
```

### 4.4 max_tokens 限制

✅ **已确认** - smoke 项目强制 `max_tokens=300`（通过 `smoke_gate.py` 注入）

### 4.5 Batch 禁止

✅ **已确认** - Batch 真实 LLM smoke 被永久禁止（`check_batch_real_llm_smoke_gate`）

## 5. 安全结论

| 项目 | 状态 |
|------|------|
| API Key 未提交 | ✅ |
| .env 未提交 | ✅ |
| smoke 项目已清理 | ✅ |
| 真实生成产物未污染版本库 | ✅ |
| 普通项目未受影响 | ✅ |

## 6. 回归测试

后续将运行以下回归测试：
- `test_t6_7_6c_pipeline_smoke_max_tokens_contract.py`
- `test_t6_7_6b_smoke_max_tokens_contract.py`
- `test_t6_7_6a_real_llm_smoke_gate_contract.py`
- `test_t6_5_7_dry_run_contract.py`
- `test_t6_6_4_batch_dry_run_contract.py`
- `test_t6_7_5a_batch_result_schema_contract.py`

## 7. 清理确认

- ✅ smoke 项目目录已删除
- ✅ `.env` 已恢复为默认配置（`ALLOW_REAL_LLM_SMOKE` 已移除）
- ✅ 工作区保持 clean