# T7.4-RC1 Stability Checklist

> RC 发布前稳定性加固项，覆盖后端 token 预算、SSE 警告展示、连续性锚点噪声、LLM 错误翻译。
>
> 基线：T7.4-C (commit `a1f64fa`)
> 创建日期：2026-06-12

---

## Fix 1: Token 预算软保护

- [ ] 后端：prompt token 数 > context_window 75% 时发出 `context_warning` (severity: soft) 事件
- [ ] 后端：prompt token 数 > context_window 95% 时发出 `context_warning` (severity: hard) 事件
- [ ] 后端：prompt token 数 > max_prompt_tokens 时保留原有 error + warning:true 事件
- [ ] 测试：`test_soft_warning_at_75pct_context` 通过
- [ ] 测试：`test_no_warning_at_low_usage` 通过

## Fix 2: SSE 警告前端持久提示

- [ ] 前端：`context_warning` 事件显示为 warning 通知（不中断生成流）
- [ ] 前端：`quality_warning` 事件显示为 warning 通知
- [ ] 前端：`error` 事件带 `warning: true` 时不中断流，显示为 warning 通知
- [ ] 前端：`error` 事件带 `error_code` 时优先使用 ERROR_CODE_MAP 翻译
- [ ] 前端：新增 `LLM_ERROR`, `LLM_CIRCUIT_OPEN`, `LLM_API_ERROR`, `CONTEXT_LENGTH_ERROR` 错误码翻译
- [ ] 前端：`npm run build` 通过

## Fix 3: Continuity Anchor 噪声过滤

- [ ] 后端："余温" 不出现在锚点中（_NAME_NOISE_WORDS 过滤）
- [ ] 后端："经逼近" 不出现在锚点中（function-word prefix 过滤）
- [ ] 后端："林澈" 仍出现在锚点中（合法名称不受影响）
- [ ] 后端："沈知夏" 仍出现在锚点中
- [ ] 后端："追踪者"、"档案室"、"灰塔实验室" 仍出现在锚点中
- [ ] 测试：`test_extract_continuity_anchors_name_noise_filter` 通过
- [ ] 测试：全部 8 个现有 ContinuityAnchors/Gate 测试仍通过

## Fix 4: 真实 LLM 失败/过慢提示

- [ ] 后端：LLM APIError (503/502) 显示"模型服务暂时不可用"
- [ ] 后端：LLM APIError (500) 显示"模型服务端内部错误"
- [ ] 后端：LLM APIError (4xx) 显示"模型 API 请求错误"
- [ ] 后端：ConnectionError 显示"无法连接到模型服务"
- [ ] 后端：SSLError 显示"SSL 连接失败"
- [ ] 后端：通用未知错误显示"模型调用遇到未知错误"
- [ ] 后端：pipeline 步骤失败使用 MoyunException.message 而非 str(e)
- [ ] 后端：pipeline 错误事件包含 `error_code` 字段

## Fix 5: 文档

- [ ] 本 checklist 已创建
- [ ] 修改文件列表已确认

---

## 修改文件清单

| 文件 | 改动说明 |
|------|---------|
| `backend/core/pipeline.py` | Fix 1 token budget 软/硬警告；Fix 3 锚点噪声过滤；Fix 4 错误消息结构化 |
| `backend/core/llm.py` | Fix 4 APIError/通用异常友好消息 |
| `backend/tests/test_pipeline.py` | Fix 1 token budget 测试；Fix 3 噪声过滤测试 |
| `frontend/src/composables/useSSE.ts` | Fix 2 警告事件监听+翻译 |
| `frontend/src/composables/useFileGeneration.ts` | Fix 2 error+warning 不中断流 |
| `frontend/src/modules/sse/types.ts` | Fix 2 新增 SSEEventType |
| `frontend/src/utils/errorMessages.ts` | Fix 4 新增 LLM 错误码翻译 |
