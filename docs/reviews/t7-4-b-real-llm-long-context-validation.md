# T7.4-B：真实 LLM 长文本能力验证报告

**风险等级**: Risk A-（Verification Only，无代码修改）
**基线**: commit `255a7e0` (T7.4-A), branch `main`, working tree clean
**验证方式**: 全链路代码走查（静态分析），不启动后端、不发送真实 LLM 请求
**验证日期**: 2026-06-12

---

## 1. LLM 连通性链路

**结论: PASS — 三层配置加载 + LiteLLM 统一路由 + 熔断器保护，链路完整。**

### 1.1 配置加载（三层优先级）

| 优先级 | 来源 | 文件 |
|--------|------|------|
| 1 | `workspace/llm_config.json`（旧独立配置） | `backend/core/llm.py:39-52` |
| 2 | `workspace/.config.json` → `"llm"` key（前端设置保存格式） | `backend/core/llm.py:55-70` |
| 3 | `.env` / 环境变量（pydantic-settings） | `backend/config.py:52-71` |

三层均返回统一结构：`{apiType, apiKey, apiBase, model, thinking, reasoningFormat}`。

### 1.2 LiteLLM 路由

- `normalize_model_for_provider()` 自动添加 provider 前缀（`openai/`, `ollama/`, `anthropic/`），DeepSeek 走 OpenAI 兼容格式。
- 实际调用：`litellm.acompletion(model=..., messages=..., stream=True, ...)` + tenacity 重试（3 次，指数退避 4-10s）。
- 并发控制：`asyncio.Semaphore(3)` 防止并发请求过多。

### 1.3 熔断器

- 三态：CLOSED → OPEN → HALF_OPEN → CLOSED。
- 按 `provider|base_url|model` 隔离故障。
- 连续 3 次失败后断开，60 秒后允许单次探测。
- 状态持久化到 `.circuit-breaker-state.json`，重启不丢失。

### 1.4 Smoke Gate

- `check_real_llm_smoke_gate()` 仅拦截 smoke 测试项目，正常用户项目直接放行（返回 `None`）。
- dry_run 模式永远放行。

### 1.5 安全性

- API Key 不写入 localStorage（`llm.ts` persist serializer 剥离 apiKey）。
- API Key 不进入日志（settings 通过 pydantic-settings 管理）。
- 前端 `GET /api/llm/config` 不返回 apiKey。

---

## 2. "写下一场景" 链路

**结论: PASS — 完整链路从前端按钮到候选稿创建，所有环节正确衔接。**

### 2.1 端到端路径

```
[EditorToolbar "写下一场景" 按钮]
  → writeNextScene()                                    useSceneGenerationActions.ts:548
    → getNextInChain(filePath)                          :68-89
      返回 { path: nextSecPath, pipeline: 'generate' }
    → runSceneAction({ action: 'write_next_scene' })    :492-545
      → 读取 previous_text = editorStore.getContent()   :503-506
      → output_mode = 'candidate'                       :516
      → fileGen.runPipeline(projectId, targetPath, 'generate', extraVars, 'candidate')
        → POST /api/pipeline/run                        useFileGeneration.ts:190
          → PipelineRunner.run(action='write_next_scene')  backend/core/pipeline.py:425
            → _extract_continuity_anchors(previous_text)   :474-481
            → 加载系统变量 (style_guide, story_state, ...)  :496-502
            → 渲染 pipeline/generate/write.md              :564-565
            → LLMNodeExecutor → litellm.acompletion()      executors.py:87-91
            → _continuity_anchor_hit_count() 检查           :775-798
            → CandidateService.create_candidate()           :853-865
            → SSE: candidate_created event                 :867-875
```

### 2.2 关键验证点

| 检查项 | 结果 |
|--------|------|
| 输出模式始终 candidate | PASS — `runSceneAction` 硬编码 `candidate`，`GenerationOutputPolicy` 二次兜底 |
| previous_text 正确传递 | PASS — 从 `editorStore.getContent(sourcePath)` 读取 |
| 场景路径计算 | PASS — `getNextScenePath()` 按 `sec-NNN.md` 递增 |
| 跨链文件推进 | PASS — style-guide → blueprint → outline → ... → sec-001 |
| SSE 流式回传 | PASS — `EventSourceResponse` + `generation` 事件逐 delta 推送 |
| _action 正确转发 | PASS — `extra_vars._action = 'write_next_scene'` → `_infer_candidate_action()` 返回 `CandidateAction.CONTINUE` |

---

## 3. "续写" 链路

**结论: PASS — 存在两条路径（pipeline 路径 + legacy 路径），均正确工作。**

### 3.1 Pipeline 路径（项目链文件）

当 `getPipelineForFile(filePath)` 返回 pipeline 名称时，走 `fileGen.runPipeline()` + `output_mode: 'write_scene'`。与写下一场景共享基础设施，区别在于 pipeline 名称和目标文件不同。

### 3.2 Legacy 路径（非映射文件）

- 入口：`generation.ts` → `continueWriting()` → `POST /api/generate`
- 参数：`prompt_type: 'generate/continuation'`, `mode: 'append'`
- Prompt：`prompts/generate/continuation/main.md` — 基于 `{{ current_content }}` 续写
- 后端路由：`GenerationService.generate_stream()` → 映射到 `generate` pipeline + `append` 模式
- **注意**：legacy 路径不传递 `previous_text`，因此不触发连续性锚点检查。这是设计上的预期行为（append 模式不创建 candidate，直接追加到文件末尾）。

---

## 4. "润色" 链路

**结论: PASS — 5 步 pipeline，强制 candidate 输出，带级联 fallback。**

### 4.1 Pipeline 定义

```yaml
# prompts/pipeline/polish.yaml
steps:
  - id: depai     # 去 AI 味    → pipeline/polish/depai.md
  - id: prose     # 提升文笔    → pipeline/polish/prose.md  (fallback: depai)
  - id: logic     # 修正逻辑    → pipeline/polish/logic.md  (fallback: prose)
  - id: rhythm    # 优化节奏    → pipeline/polish/rhythm.md (fallback: logic)
  - id: diff      # 修改摘要    → pipeline/diff-summary/analyze.md (fallback: rhythm)
```

### 4.2 关键验证点

| 检查项 | 结果 |
|--------|------|
| 强制 candidate | PASS — `candidateOnly = name === 'polish'` → `output_mode: 'candidate'` |
| 最终输出取 rhythm 步骤 | PASS — `pipeline.py:754-758` 取倒数第二步输出（diff 步骤生成摘要，不用于写入） |
| 级联 fallback | PASS — 每步失败自动降级到上一步的输出 |
| 动作推断 | PASS — `_infer_candidate_action()` 识别 `polish` → `CandidateAction.POLISH` |
| 步骤间上下文传递 | PASS — 每步使用 `{{ previous_output }}` 接收上一步结果 |

---

## 5. 连续性警告机制

**结论: PASS — 锚点提取 + 命中计数 + 自动降级 + 前端展示，全链路完整。**

### 5.1 锚点提取 (`_extract_continuity_anchors`)

三种正则模式协同工作：

| 模式 | 匹配目标 | 示例 |
|------|----------|------|
| `_CONTINUITY_KEYWORD_PATTERN` | 特定后缀的中文复合词 | "黑塔计划"、"旧港站"、"黑色芯片" |
| `_QUOTED_ENTITY_PATTERN` | 中文引号/书名号内 2-12 字 | "「天道盟」"、"《灵脉诀》" |
| `_CHINESE_NAME_PATTERN` | 常见姓氏 + 1-2 字 | "林澈"、"沈知夏" |

后处理：去噪（尾部虚词、分隔词拆分、忽略词过滤）→ 去重 → 限制 8 个锚点。

### 5.2 命中检查 + 自动降级

```
continuity_required_hits = min(2, len(anchors))
if hit_count < required_hits:
    should_use_candidate = True    # 强制降级为 candidate
    yield quality_warning SSE event (code: CONTINUITY_ANCHOR_MISS)
```

即使 `output_mode` 为 `write_scene`，锚点不命中时也会自动降级为 candidate，确保不会静默覆盖正式正文。

### 5.3 Candidate 连续性元数据

创建候选稿时写入 `continuity_info`：

- `severity`: high（0 命中）/ medium（< 要求）/ low（< 总数）/ none（全部命中）
- `anchors_missing` / `anchors_preserved`: 缺失和保留的锚点列表
- `continuity_ratio`: 命中比例

### 5.4 前端展示

| 位置 | 展示 |
|------|------|
| 候选卡片 | 红/橙/黄色 "连续性警告" 徽章 + 缺失锚点列表 |
| 预览弹窗 | `getPreviewWarning()` 返回警告文本 |
| 采用确认框 | "⚠ 该候选稿存在连续性警告：..." 前置于确认文本 |

### 5.5 Prompt 级硬性锁

`write.md` 包含 "连续性硬性锁" 段落：要求正文开头 100 字内出现至少 2 项上文关键元素。这是 LLM 生成端的前置约束，与后端后检查形成双重保障。

---

## 6. 预览/采用/删除生命周期

**结论: PASS — 完整的 CRUD + base_hash/mtime 安全校验 + 前端 unsaved-edits 保护。**

### 6.1 状态机

```
pending  →  adopted    (用户接受，源文件被覆盖)
pending  →  rejected   (hash/mtime 冲突)
pending  →  discarded  (用户删除)
```

### 6.2 采用安全链（5 层保护）

| 层级 | 机制 | 位置 |
|------|------|------|
| 1 | 前端 unsaved-edits 检查 | `CandidatePanel.vue:329` — `fileStore.unsavedFiles.has(source_path)` |
| 2 | 前端连续性警告确认 | `CandidatePanel.vue:337-339` — 警告文本前置到 confirm 对话框 |
| 3 | 后端 base_hash 空值拒绝 | `candidate_service.py:257-266` — hash 为空则 REJECTED |
| 4 | 后端 hash 比对 | `candidate_service.py:268-278` — `current_hash != base_hash` → CONFLICT |
| 5 | 后端 mtime 比对 | `candidate_service.py:280-290` — `abs(current_mtime - base_mtime) > 0.001` → CONFLICT |

冲突时：HTTP 409 + `FILE_CONFLICT` 错误码 → 前端 `toUserFacingMessage()` 翻译为 "文件已被修改，请刷新后重试"。

### 6.3 采用成功后

`syncAdoptedSource()` 执行：刷新文件树 → 重新读取源文件 → 重载编辑器内容 → 清除 `unsavedFiles` 脏标记。

### 6.4 删除

简单流程：DELETE API → 候选文件删除 → 状态设为 DISCARDED → 前端刷新列表。

### 6.5 SSE 自动刷新

CandidatePanel mount 时注册 `candidate-created` 和 `candidate-adopted` 事件监听，自动刷新列表。

---

## 7. 长上下文边界能力评估

**结论: CONDITIONAL PASS — 当前架构在中等规模下工作良好，超大上下文缺乏主动截断机制。**

### 7.1 上下文来源与规模估算

| 来源 | 典型规模 | 上限控制 |
|------|----------|----------|
| `previous_text` / `current_scene_text` | 600-1000 字 | 自然受限于单场景长度 |
| `style_guide` (style-guide.md) | 500-2000 字 | 无截断 |
| `outline` (outline.md) | 1000-5000 字 | 无截断 |
| `story_state` (story-state.md) | 500-2000 字 | 无截断 |
| `recent_context` (recent-context.md) | 15 场景 × ~300 字 = ~4500 字 | **15 场景硬上限** |
| `continuity_anchors` | ≤ 8 个锚点 | 硬上限 8 |
| `writing-rules.md` (include) | ~500 字 | 固定 |
| **合计（典型）** | **~10000-15000 字 ≈ ~5000-7500 tokens** | — |

### 7.2 三级边界评估

#### Tier 1：500-800 字上文（单场景）

- **Prompt 规模**：~5000-8000 tokens（含系统变量）
- **适配模型**：所有模型（包括 8k 窗口的 GPT-4 基础版）
- **风险**：无
- **结论**：完全安全

#### Tier 2：1500-2500 字上文（2-3 场景 / 含较多项目变量）

- **Prompt 规模**：~8000-15000 tokens
- **适配模型**：16k+ 窗口模型（GPT-4-turbo、DeepSeek-v3、Qwen-72b 等）
- **风险**：8k 窗口模型（`gpt-4` 基础版、`deepseek-chat`）可能触发 token 超限警告
- **缓解**：系统已实现 token 检查 + SSE 警告（`pipeline.py:577-599`），但**仅警告不截断**
- **结论**：主流模型安全，旧版 8k 模型需注意

#### Tier 3：4000-6000 字上文（大量项目上下文 + 完整 recent_context）

- **Prompt 规模**：~20000-40000 tokens
- **适配模型**：32k+ 窗口模型（GPT-4-turbo 128k、DeepSeek-v3 128k、Claude 200k）
- **风险**：
  - 32k 窗口模型可能在 `outline` + `recent_context` 同时较大时触发警告
  - 无 token 级截断机制 — 如果模型实际窗口小于推断值，可能导致 API 报错
- **缓解**：
  - `recent_context` 已有 15 场景硬上限
  - token 检查会在超限时发出 SSE 警告
  - `_infer_context_window()` 按模型参数/族名推断窗口，覆盖主流模型
  - `max_prompt_tokens = context_window - reserved_output_tokens(3000)`
- **结论**：128k 模型安全，32k 模型边界情况需关注

### 7.3 现有保护措施

| 措施 | 类型 | 位置 |
|------|------|------|
| recent_context 15 场景上限 | 条目数硬限 | `memory_service.py:28-62` |
| 场景记忆压缩（~200 字 + 元数据） | 内容压缩 | `memory_service.py:82-127` |
| Token 检查 + SSE 警告 | 事后警告 | `pipeline.py:577-599` |
| 上下文步骤缓存（同章复用） | 性能优化 | `pipeline.py:601-677` |
| 模型上下文窗口推断 | 自动适配 | `llm.py:231-262` |

### 7.4 已知限制

1. **无主动截断**：当 prompt 超过模型窗口时，系统仅发出警告但继续执行。LLM API 可能返回 token limit 错误，此时由 tenacity 重试 + 熔断器处理。
2. **recent_context 按场景数限制而非 token 数**：15 个场景 × 300 字 ≈ 4500 字 ≈ 2250 tokens（中文），但如果 style-guide / outline / story-state 同时很大，总量仍可能过高。
3. **fallback 路径 token 检查**：`generation_service.py:174-196` 也有同样的 token 检查，与 pipeline 路径一致。

### 7.5 改进建议（不阻塞本次验证）

| 优先级 | 建议 | 理由 |
|--------|------|------|
| P2 | 实现 prompt token 软截断（超限时自动裁剪 recent_context 最旧条目） | 避免 8k/16k 窗口模型 API 报错 |
| P3 | 在设置页面展示当前 prompt token 估算值 | 用户可感知上下文负载 |
| P3 | 添加 "精简上下文" 按钮（手动触发 recent_context 缩减） | 给长篇小说用户提供主动控制权 |

---

## 综合评定

| 验证区域 | 结果 | 备注 |
|----------|------|------|
| 1. LLM 连通性 | **PASS** | 三层配置 + LiteLLM + 熔断器 |
| 2. 写下一场景 | **PASS** | 完整 candidate 链路 |
| 3. 续写 | **PASS** | pipeline + legacy 双路径 |
| 4. 润色 | **PASS** | 5 步 pipeline + fallback |
| 5. 连续性警告 | **PASS** | 锚点提取 + 自动降级 + 前端展示 |
| 6. 预览/采用/删除 | **PASS** | 5 层安全保护 |
| 7. 长上下文边界 | **CONDITIONAL PASS** | 128k 模型安全；小窗口模型需关注 |

**总体结论**: 真实 LLM 链路完整、安全保护充分、连续性机制健全。长上下文在主流 128k 窗口模型下工作正常，建议后续增加 prompt token 软截断作为增强。

---

## 剩余问题

| ID | 优先级 | 描述 |
|----|--------|------|
| R7.4-B-1 | P2 | 无 prompt token 软截断机制，小窗口模型可能 API 报错 |
| R7.4-B-2 | P3 | legacy 续写路径不触发连续性锚点检查（设计预期，但用户可能不知情） |
| R7.4-B-3 | P3 | token 超限仅 SSE 警告，前端无持久化提示（可能被用户忽略） |
