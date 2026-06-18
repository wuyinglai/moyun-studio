# v0.2.2a Guardrails Allowlist Cleanup Report

## 基本信息

| 字段 | 值 |
|------|-----|
| Task Title | v0.2.2a — Guardrails Allowlist Cleanup |
| Risk Level | Risk B / Safety Tooling + Test Noise Cleanup |
| Mode | Guardrails Audit + Allowlist Cleanup + No Product Feature |
| Branch | main |
| Base Commit | f0284c2 |
| Date | 2026-06-17 |

---

## 1. 当前 commit

```text
f0284c2 docs: decide v0.2.2 and T10 scope
```

---

## 2. 原始 guardrails 结果

运行 `powershell -ExecutionPolicy Bypass -File scripts/ai-guardrails.ps1` 后，发现以下 violation：

### Rule 1: file.updated content leak

| 文件 | 行号 | 原始代码 |
|------|------|----------|
| `backend/api/materials.py` | 130, 160 | HTTP API response 包含 `content` 字段 |
| `backend/tests/test_pipeline.py` | 1008, 1047, 1086, 1157, 1225 | 测试 mock 数据 `write_calls.append({"path": ..., "content": ...})` |
| `backend/tests/test_pipeline_scaffold_placeholders.py` | 75 | 测试 mock 数据 |

### Rule 2: output_mode overwrite

| 文件 | 行号 | 原始代码 |
|------|------|----------|
| `backend/application/pipeline/context.py` | 23 | Schema 定义 + LEGACY_COMPAT 说明 |
| `backend/policies/generation_output_policy.py` | 111 | Policy 文档说明 |
| `backend/schemas/pipeline.py` | 32 | Schema 定义 |
| `backend/schemas/pipeline_config.py` | 26 | DEPRECATED_OUTPUT_MODES 常量 |
| `backend/schemas/workflow.py` | 15 | Schema 定义 |
| `backend/tests/test_generation_output_policy.py` | 多处 | 测试 legacy overwrite 安全处理 |
| `backend/tests/test_pipeline.py` | 多处 | 测试 overwrite 安全处理 |

---

## 3. violation 分类

### Rule 1: file.updated content leak

| 文件 | 分类 | 原因 |
|------|------|------|
| `backend/api/materials.py` | C. 文档说明 | HTTP API response，不是 SSE event，guardrails 误判 |
| `backend/tests/test_pipeline.py` | B. 测试噪声 | 测试 mock 数据，不是真实 SSE |
| `backend/tests/test_pipeline_scaffold_placeholders.py` | B. 测试噪声 | 测试 mock 数据 |

**结论**：无真实风险。Guardrails 规则过于宽泛，误将 HTTP API response 识别为 SSE file.updated。

### Rule 2: output_mode overwrite

| 文件 | 分类 | 原因 |
|------|------|------|
| `backend/application/pipeline/context.py` | D. 历史兼容 | Schema 定义 + LEGACY_COMPAT 说明，已明确 deprecated |
| `backend/policies/generation_output_policy.py` | D. 历史兼容 | Policy 文档说明，已明确 deprecated |
| `backend/schemas/pipeline.py` | D. 历史兼容 | Schema 定义，已明确 deprecated |
| `backend/schemas/pipeline_config.py` | D. 历史兼容 | DEPRECATED_OUTPUT_MODES 常量 |
| `backend/schemas/workflow.py` | D. 历史兼容 | Schema 定义，已明确 deprecated |
| `backend/tests/test_generation_output_policy.py` | B. 测试噪声 | 测试 legacy overwrite 安全处理 |
| `backend/tests/test_pipeline.py` | B. 测试噪声 | 测试 overwrite 安全处理 |

**结论**：无真实风险。所有 `overwrite` 出现均为：
1. Schema 定义 + LEGACY_COMPAT 说明（明确 deprecated）
2. 测试代码验证 overwrite → candidate 安全转换

---

## 4. 修复/allowlist 内容

采用 `AI_GUARDRAIL_ALLOW` 注释机制，在每处 violation 行尾添加注释说明原因。

### 修改文件列表

| 文件 | 修改内容 |
|------|----------|
| `backend/api/materials.py` | 第 130, 160 行添加 `# AI_GUARDRAIL_ALLOW: materials API response, not SSE` |
| `backend/application/pipeline/context.py` | 第 23 行添加 `# AI_GUARDRAIL_ALLOW: schema definition with LEGACY_COMPAT note` |
| `backend/schemas/pipeline.py` | 第 32 行添加 `# AI_GUARDRAIL_ALLOW: schema definition` |
| `backend/schemas/pipeline_config.py` | 第 26 行添加 `# AI_GUARDRAIL_ALLOW: deprecated modes constant for legacy compat` |
| `backend/schemas/workflow.py` | 第 15 行添加 `# AI_GUARDRAIL_ALLOW: schema definition` |
| `backend/policies/generation_output_policy.py` | 第 111 行添加 `# AI_GUARDRAIL_ALLOW: policy doc with LEGACY_COMPAT note` |
| `backend/tests/test_pipeline.py` | 多处添加 `# AI_GUARDRAIL_ALLOW: test mock data` 或 `# AI_GUARDRAIL_ALLOW: test param for legacy overwrite safety` |
| `backend/tests/test_pipeline_scaffold_placeholders.py` | 第 75 行添加 `# AI_GUARDRAIL_ALLOW: test mock data` |
| `backend/tests/test_generation_output_policy.py` | 多处添加 `# AI_GUARDRAIL_ALLOW: test param for legacy overwrite safety` |

---

## 5. 修复后 guardrails 结果

运行 `powershell -ExecutionPolicy Bypass -File scripts/ai-guardrails.ps1`：

```text
PASS: All guardrails checks passed.
```

**Remaining Noise**: 0

---

## 6. API key 检查

运行安全 grep：

```powershell
git grep -n "sk-" .
git grep -n "OPENAI_API_KEY" .
git grep -n "Authorization: Bearer" .
```

**结果**：

- `sk-` 仅出现在占位符和测试 mock（如 `sk-test-key`, `sk-placeholder`），无真实 API key
- `OPENAI_API_KEY` 仅出现在 `os.getenv()` 和文档说明，无硬编码 key
- `Authorization: Bearer` 仅出现在测试 mock 和 redaction test

**结论**：无真实 API key 泄露风险 ✅

---

## 7. candidate-only 安全边界

检查 candidate-only 安全边界是否被破坏：

- `output_mode=overwrite` 在产品代码中已明确 LEGACY_COMPAT + deprecated
- 测试代码验证 overwrite → candidate 安全转换
- 无代码允许 overwrite 直接写入已有 sec 文件

**结论**：candidate-only 安全边界未破坏 ✅

---

## 8. 测试结果

### Backend tests

```powershell
python -m pytest backend/tests/test_repair_candidate.py backend/tests/test_candidate_quality_metadata.py backend/tests/test_candidate_feedback_revision.py backend/tests/test_continuity_anchors.py -q --tb=short
```

**结果**：40 passed in 16.13s ✅

### Frontend build

```powershell
cd frontend; npm run build
```

**结果**：3435 modules transformed, built in 3.72s ✅

---

## 9. 是否建议进入 v0.2.2b

**建议**：✅ 可以进入 v0.2.2b — T9.4 文档合并 + known-issues 更新

理由：
1. Guardrails 全部通过，无 remaining noise
2. 无真实安全风险
3. 核心回归测试通过
4. Frontend build 通过
5. candidate-only 安全边界未破坏

---

## 10. 结论

v0.2.2a 任务已完成：

- ✅ Guardrails 输出已复现
- ✅ 所有 violation 已分类（B/D/C 类，无 A 类真实风险）
- ✅ Allowlist 不掩盖真实问题
- ✅ 无真实 API key 入库
- ✅ candidate-only 安全边界未破坏
- ✅ 核心后端测试通过
- ✅ frontend build 通过
- ✅ diff check passed
- ✅ git clean

---

## 文档归档

本报告归档于：`docs/security/v0-2-2a-guardrails-allowlist-cleanup.md`