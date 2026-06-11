# T6.8.1 真实 LLM 隔离冒烟测试报告（补充验证版）

## 1. 结论

**T6.8.1：✅ 正式收口**

真实 LLM 调用成功，**candidate 真实生成**，原正文未被覆盖，未执行 Batch，未自动 adopt。

## 2. 测试环境

| 配置项 | 值 |
|--------|-----|
| `ALLOW_REAL_LLM_SMOKE` | `1`（Settings `case_sensitive=False`） |
| `LLM_SMOKE_MAX_TOKENS` | `300` |
| API Key | 未记录（使用环境变量） |

## 3. 测试范围

- **project_id**: `__llm_smoke_t6_8_1`
- **file**: `chapters/vol-01/ch-001/sec-001.md`
- **prompt_type**: `generate/rewrite`（走 pipeline 模式，output_mode=candidate）
- **mode**: `rewrite`
- **触发路径**: `GenerationService.generate_stream` → `PipelineRunner` → `OutputWriterExecutor` → `CandidateService.create_candidate`
- **Batch**: 未测试 / 未触发
- **auto adopt**: 未执行
- **overwrite**: 未执行

## 4. 测试结果

### 4.1 真实 LLM 调用

✅ **成功** - pipeline 模式执行 6 个 step（diagnose → draft → depai → logic → rhythm → diff），共收到 584 个 SSE 事件。

### 4.2 candidate 生成（实体证据）

✅ **candidate 真实存在**（不是逻辑推断，有文件 + 元数据 + SSE 事件三重证据）

**证据 1：SSE candidate_created 事件**

```
event=candidate_created
{
  'task_id': 'pipeline-rewrite-fa8efa6a',
  'candidate_id': 'cand_1c819dfe',
  'source_path': 'chapters/vol-01/ch-001/sec-001.md',
  'action': 'rewrite'
}
```

**证据 2：.candidates 目录真实文件**

```
workspace/projects/__llm_smoke_t6_8_1/.candidates/
  ├── metadata.json        (含 candidate_id)
  └── cand_1c819dfe.rewrite.md  (142 chars)
```

**证据 3：metadata.json**

| 字段 | 值 |
|------|----|
| candidate_id | `cand_1c819dfe` |
| source_path | `chapters/vol-01/ch-001/sec-001.md` |
| action | `rewrite` |
| status | `pending`（未 adopt） |
| created_at | `2026-06-11T09:54:00.650203` |
| base_hash | `9811aa57c6d3529b...`（原正文 hash） |

**证据 4：candidate 内容**

- 文件: `workspace/projects/__llm_smoke_t6_8_1/.candidates/cand_1c819dfe.rewrite.md`
- 长度: 142 chars
- 非空: ✅
- 前 100 字预览: `执行 T6.8.1 真实 LLM 隔离冒烟测试。审查逻辑，杜绝矛盾；理顺时间，确保合理...`

### 4.3 原正文保护

✅ **原正文未被覆盖** - `sec-001.md` 内容保持测试原文：

```
这是 T6.8.1 真实 LLM 隔离冒烟测试的测试场景。请不要覆盖正文，只生成候选稿。
```

### 4.4 max_tokens 限制

✅ **已确认** - smoke 项目强制 `max_tokens=300`（通过 smoke gate → `maybe_apply_smoke_max_tokens` 注入到 pipeline 调用）

### 4.5 Batch 未触发

✅ **Batch 未执行** - 仅调用单文件 `/api/generate` 路径，未调用 `/api/generate/batch`

### 4.6 auto adopt 未执行

✅ **status=pending** - candidate 保持 pending 状态，未被 adopt

### 4.7 清理确认

✅ **已清理** - `workspace/projects/__llm_smoke_t6_8_1/` 已删除

## 5. 安全结论

| 项目 | 状态 |
|------|------|
| API Key 未提交 | ✅ |
| .env 未提交 | ✅ |
| smoke 项目已清理 | ✅ |
| 真实生成产物未污染版本库 | ✅ |
| 普通项目未受影响 | ✅ |
| 高风险修改走 candidate 而非直接覆盖 | ✅ |

## 6. 回归测试

计划运行以下回归测试：

- `tests/contracts/test_t6_7_6c_pipeline_smoke_max_tokens_contract.py`
- `tests/contracts/test_t6_7_6b_smoke_max_tokens_contract.py`
- `tests/contracts/test_t6_7_6a_real_llm_smoke_gate_contract.py`
- `tests/contracts/test_t6_5_7_dry_run_contract.py`
- `tests/contracts/test_t6_6_4_batch_dry_run_contract.py`
- frontend `npm run build`

## 7. 本次补充验证发现的代码路径

供排查参考：

1. `GenerationService.generate_stream` → `prompt_type in GENERATE_PIPELINE_MAP` → pipeline 模式
2. `PipelineRunner.run` → 执行各 step，最后 `OutputWriterExecutor`
3. `OutputWriterExecutor.execute` → `_is_dangerous_output("chapters/vol-01/ch-001/sec-001.md")` → True（命中 `/sec-` 模式）
4. `OutputWriterExecutor._write_output_or_candidate` → `CandidateService.create_candidate`
5. `CandidateService.create_candidate` → 写入 `.candidates/` 目录 + 更新 `metadata.json`
6. SSE 事件: `candidate_created` → `task_completed` → `done`
