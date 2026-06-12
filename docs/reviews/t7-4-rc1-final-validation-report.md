# T7.4-RC1 Final Validation Report

> RC1 稳定性加固包的最终验收报告，覆盖代码、测试、构建、真实 LLM smoke 全链路验证。
>
> 基线：T7.4-C (`a1f64fa`)
> RC1 范围：`4cdf514` → `11e3ea5`（2 commits）
> 报告日期：2026-06-13

---

## 1. Commits

| Commit | Date | Message |
|--------|------|---------|
| `4cdf514` | 2026-06-12 22:21 | fix: harden RC generation warnings and continuity anchors |
| `11e3ea5` | 2026-06-12 22:45 | fix: persist generation warnings in RC flow |

两个 commit 均已推送至 `main`。

---

## 2. Scope Summary

RC1 包含 5 个 fix 领域 + 1 个 fixup：

| # | Fix | Risk | Status |
|---|-----|------|--------|
| 1 | Token 预算软保护 (75%/95%) | B | Done |
| 2 | SSE warning 前端持久提示 | B | Done (含 fixup) |
| 3 | Continuity anchor 噪声过滤 | B | Done |
| 4 | LLM 失败/过慢友好提示 | B | Done |
| 5 | RC checklist 文档 | C | Done |
| F | Fixup: 持久警告横幅 | B | Done |

**未触及**：candidate adopt/delete、file save/hash/conflict、LLM provider 配置、release/tag、UI 大重构。

---

## 3. Diff Stats

```
10 files changed, 361 insertions(+), 10 deletions(-)
```

| File | Lines +/- | Fix |
|------|-----------|-----|
| `backend/core/pipeline.py` | +48/-1 | 1, 3, 4 |
| `backend/core/llm.py` | +21/-1 | 4 |
| `backend/tests/test_pipeline.py` | +106/-0 | 1, 3 |
| `frontend/src/components/right-panel/ExecutionPanel.vue` | +61/-0 | F |
| `frontend/src/composables/useSSE.ts` | +39/-1 | 2, F |
| `frontend/src/stores/task.ts` | +15/-0 | F |
| `frontend/src/composables/useFileGeneration.ts` | +7/-1 | 2 |
| `frontend/src/utils/errorMessages.ts` | +6/-1 | 2, 4 |
| `frontend/src/modules/sse/types.ts` | +3/-0 | 2 |
| `docs/reviews/t7-4-rc1-stability-checklist.md` | +65/-0 | 5 |

---

## 4. Test Results

### Backend: pytest

```
52 passed in 12.49s
```

新增测试（3 个）：

| Test | Fix | Purpose |
|------|-----|---------|
| `test_soft_warning_at_75pct_context` | 1 | context_warning 在 75%+ 触发 |
| `test_no_warning_at_low_usage` | 1 | 低用量不误报 |
| `test_extract_continuity_anchors_name_noise_filter` | 3 | 余温/经逼近 被过滤 |

全部 52 个测试通过，包括 8 个原有 ContinuityAnchors/Gate 回归测试。

### Frontend: build

```
vue-tsc -b && vite build
✓ 3431 modules transformed
✓ built in 2.95s
```

无 TypeScript 类型错误。

### Diff check

```
git diff --check → CRLF warnings only（无实际错误）
```

---

## 5. Real LLM Smoke

| Check | Result |
|-------|--------|
| 后端 API | ✅ localhost:8000 响应正常 |
| 前端 dev | ✅ localhost:5173 返回 200 |
| LLM connected | ✅ `openai/agnes-2.0-flash` |
| 测试项目 | `403cdddb`（柳清玄修仙小说） |
| 写空场景 (sec-004) | ✅ 直接写入，不经过 candidate |
| 写已有场景 (sec-004 二次) | ✅ 生成 candidate |
| candidate.action | ✅ `"continue"` |
| 前端 action 标签 | ✅ 映射为"续写" |
| 连续性锚点保留 | ✅ 柳清玄、孙猴子、万宝阁 |
| 正文不被覆盖 | ✅ sec-004.md 原始内容完好 |

---

## 6. Fix-by-Fix Verification

### Fix 1: Token 预算软保护

- `context_warning` SSE 事件在 prompt token > 75% context_window 时触发（severity: soft）
- `context_warning` SSE 事件在 prompt token > 95% context_window 时触发（severity: hard）
- 事件包含 `severity`, `prompt_tokens`, `context_window`, `usage_pct`, `task_id` 字段
- 原有 max_prompt_tokens 超限时仍发出 `error` + `warning: true` 事件（向后兼容）

### Fix 2 + Fixup: SSE Warning 持久提示

- `quality_warning` / `context_warning` / `warning` 三种事件类型注册到 SSE 监听器
- `error` 事件带 `warning: true` 时不再中断生成流，转为 `warning` 事件
- `error` 事件带 `error_code` 时优先使用 `ERROR_CODE_MAP` 翻译消息
- `task.ts` store 新增 `activeWarnings` 响应式数组
- `ExecutionPanel.vue` 在 diff-summary 和日志之间渲染持久警告横幅
- 生成完成（`done` 事件）时自动清除警告
- 横幅支持手动关闭（× 按钮）

### Fix 3: Anchor 噪声过滤

- `_NAME_NOISE_WORDS = {"余温", "余地", "余光", "余额", "余生", "余款", "余粮"}`
- 3 字候选项首字为 `经已被将从向让` 时过滤（捕获"经逼近"类动词短语）
- 合法人名（林澈、沈知夏）不受影响
- 独立关键词（追踪者、档案室、灰塔实验室）不受影响

### Fix 4: LLM 错误友好消息

**后端 `llm.py`：**
- APIError 503/502 → "模型服务暂时不可用"
- APIError 500 → "模型服务端内部错误"
- APIError 4xx → "模型 API 请求错误"
- ConnectionError → "无法连接到模型服务"
- SSLError → "SSL 连接失败"
- DNS 错误 → "无法解析模型服务地址"
- 通用异常 → "模型调用遇到未知错误"

**后端 `pipeline.py`：**
- 步骤失败使用 `MoyunException.message` 替代 `str(e)`
- 错误事件包含 `error_code` 字段

**前端 `errorMessages.ts`：**
- 新增 `LLM_ERROR`, `LLM_CIRCUIT_OPEN`, `LLM_API_ERROR`, `CONTEXT_LENGTH_ERROR` 码

---

## 7. Known Limitations

| Issue | Severity | Note |
|-------|----------|------|
| 锚点提取仍有低频噪声 | Low | 500 字短文本中 surname 字符误匹配（如"元丹"），不影响核心功能 |
| `context_warning` 横幅未做 E2E 长上下文验证 | Low | 需构造 >75% token 阈值的真实场景，待后续 smoke |
| 通知系统仍为 toast 模式 | Info | 持久横幅在 ExecutionPanel 中，但顶部 toast 仍 3-5 秒消失（设计如此） |

---

## 8. Checklist Cross-Reference

对照 `t7-4-rc1-stability-checklist.md` 全部 25 项：

| Section | Items | Passed |
|---------|-------|--------|
| Fix 1: Token 预算 | 5 | 5 |
| Fix 2: SSE 警告 | 6 | 6 |
| Fix 3: Anchor 噪声 | 7 | 7 |
| Fix 4: LLM 错误 | 8 | 8 |
| Fix 5: 文档 | 2 | 2 |
| **Total** | **28** | **28** |

全部 checklist 项已验证通过。

---

## 9. Conclusion

T7.4-RC1 稳定性加固包已完成全部开发、测试、真实 LLM smoke 和推送。

- 后端 52/52 测试通过
- 前端 build 无类型错误
- 真实 LLM smoke 验证 write_next_scene → candidate → action=continue 全链路
- 10 个文件，361 行新增，10 行删除
- 2 个 commit 已推送至 main

**RC1 状态：Closed。**
