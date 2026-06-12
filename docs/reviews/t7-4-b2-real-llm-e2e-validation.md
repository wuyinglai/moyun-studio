# T7.4-B2：真实 LLM 实机 E2E 验证报告

**风险等级**: Risk A-（E2E Verification Only，无代码修改）
**基线**: commit `5b8f004` (T7.4-B1), branch `main`, working tree clean
**验证方式**: 真实启动后端 + 前端，真实调用 LLM，通过 API 执行完整工作流
**验证日期**: 2026-06-12
**验证类型**: 实机 E2E 验证（非静态走查）

---

## 环境信息

| 项目 | 状态 | 详情 |
|------|------|------|
| 后端 | 已启动 | Python 3.14, uvicorn, 端口 8000, PID 30044 |
| 前端 | 已启动 | Vite dev server, 端口 5173, PID 42728 |
| LLM | 已连通 | apiType=custom, model=openai/agnes-2.0-flash, endpoint=apihub.agnes-ai.com |
| API Key | 已配置 | 存在且有效（不在报告中暴露） |
| 测试项目 | 已创建 | project_id=`00621f53`, name="T7.4-B2 Real LLM Test" |

---

## 测试 A：写下一场景（Write Next Scene）

**结论: PASS — 真实 LLM 调用成功，candidate 正确创建，正文未被覆盖。**

| 指标 | 值 |
|------|-----|
| API 端点 | `POST /api/pipeline/run` |
| Pipeline | `generate` |
| action | `write_next_scene` |
| output_mode | `candidate` |
| 上文长度 | 691 字 |
| 生成正文长度 | 1099 字 |
| SSE 事件数 | 711（generation: 698, thinking: 1, prompt: 1, step_done: 1, candidate_created: 1, ping: 6, diff_summary: 1, done: 1） |
| 响应时间 | 93.2s |
| HTTP 状态 | 200 |

### 关键词命中

| 关键词 | 命中 |
|--------|------|
| 林澈 | YES |
| 沈知夏 | YES |
| 旧港站 | YES |
| 银色芯片 | YES |
| 芯片 | YES |
| 追踪 | YES |

### Candidate 信息

| 字段 | 值 |
|------|-----|
| candidate_id | `cand_e48b93ef` |
| action | `rewrite` |
| source_type | `llm` |
| status | `pending` |
| source_path | `chapters/vol-01/ch-001/sec-002.md` |
| base_hash | 有值 |
| continuity severity | `medium` |
| continuity_ratio | 0.12 |
| anchors_preserved | ["旧港站"] |

### 安全性验证

- sec-002 原始内容未被覆盖（保持 1405 字）：YES
- 输出进入 candidate 而非直接写入：YES
- candidate_created SSE 事件触发：YES

### 质量观察

生成内容自然衔接上文：林澈和沈知夏在值班室内的对话，围绕茶杯中的可疑粉末展开紧张对峙。节奏紧凑，对话有潜台词，符合设定。字数略超 1000 字上限但在可接受范围。

---

## 测试 B：续写当前场景（Continue Writing）

**结论: PASS — legacy `/api/generate` 端点正常工作，内容正确追加到文件。**

| 指标 | 值 |
|------|-----|
| API 端点 | `POST /api/generate` |
| prompt_type | `generate/continuation` |
| mode | `append` |
| 续写前长度 | 691 字 |
| 生成正文长度 | 1499 字 |
| 续写后文件长度 | 2192 字 |
| SSE 事件数 | 941 |
| 响应时间 | 61.5s |

### 验证点

| 检查项 | 结果 |
|--------|------|
| 内容追加到文件末尾 | YES（691 → 2192） |
| 原文保留 | YES |
| 真实调用 LLM | YES |
| 生成内容衔接上文 | YES（延续旧港站场景，林澈收起黑伞进入站内） |
| 是否创建 candidate | NO（append 模式直接写入，设计预期） |

---

## 测试 C：润色当前场景（Polish）

**结论: PASS — 5 步 pipeline 全部执行，candidate 创建，原文未被覆盖。**

| 指标 | 值 |
|------|-----|
| API 端点 | `POST /api/pipeline/run` |
| Pipeline | `polish` |
| action | `polish_current_scene` |
| output_mode | `candidate` |
| Pipeline 步骤 | depai → prose → logic → rhythm → diff（5 步） |
| SSE 事件数 | 1700 |
| 响应时间 | 59.1s |
| candidate_id | `cand_63de0954` |

### Pipeline 步骤执行记录

| 步骤 | 标签 | 状态 |
|------|------|------|
| depai | 去AI味 | STEP_DONE |
| prose | 提升文笔 | STEP_DONE |
| logic | 修正逻辑 | STEP_DONE |
| rhythm | 优化节奏 | STEP_DONE |
| diff | 修改摘要 | STEP_DONE |

### Candidate 信息

| 字段 | 值 |
|------|-----|
| action | `polish` |
| source_type | `llm` |
| continuity severity | `none` |
| source_path | `chapters/vol-01/ch-001/sec-001.md` |

### 安全性验证

- sec-001 原文未被润色操作覆盖：YES
- 润色后正文保留原意（林澈、旧港站、银色芯片、沈知夏均在）：YES
- 未大幅改剧情：YES

### 质量观察

润色版本文笔更凝练："夜雨砸在旧港站生锈的铁皮屋顶上，噪杂如鼓" 比原文 "夜雨打在旧港站的铁皮屋顶上，发出密集的鼓点声" 更有力度。句式更短促，节奏更紧凑。

---

## 测试 D：Preview / Adopt / Delete 生命周期

**结论: PASS — 三种操作均正确执行，安全机制有效触发。**

### D1: Preview

| 检查项 | 结果 |
|--------|------|
| API | `GET /candidates/{pid}/{cid}` |
| 返回内容 | 528 字，action=polish |
| 是否修改正文 | NO |
| continuity 信息 | severity=none |

### D2: Adopt（FILE_CONFLICT 安全触发）

首次尝试 adopt `cand_63de0954`（polish, sec-001）：

| 检查项 | 结果 |
|--------|------|
| 请求 | `POST /candidates/00621f53/cand_63de0954/adopt` |
| HTTP 状态 | 200（success=false） |
| 错误码 | `FILE_CONFLICT` |
| 用户文案 | "源文件已被其他操作修改，请重新生成候选稿后再采用。" |
| 是否命中 T7.3.7 错误翻译层 | YES |
| 正文是否变更 | NO |

**分析**：sec-001 在 Test B 中被续写追加（691 → 2192 字），导致文件的 hash 与 candidate 创建时记录的 base_hash 不一致。base_hash/mtime 安全校验正确拦截了过期 candidate 的采用。

### D3: Adopt（成功路径）

第二次 adopt `cand_e48b93ef`（rewrite, sec-002）：

| 检查项 | 结果 |
|--------|------|
| 请求 | `POST /candidates/00621f53/cand_e48b93ef/adopt` |
| 结果 | `success=true, conflict=false` |
| sec-002 之前 | 1405 字（原始 medium 测试内容） |
| sec-002 之后 | 1099 字（Test A 生成的 candidate 内容） |
| 内容正确 | YES（林澈 + 沈知夏 + 旧港站值班室场景） |

### D4: Delete

| 检查项 | 结果 |
|--------|------|
| 目标 | `cand_46d97974`（sec-010） |
| 请求 | `DELETE /candidates/00621f53/cand_46d97974` |
| 结果 | `success=true` |
| 状态变化 | `pending` → `discarded` |
| 是否影响正文 | NO |

---

## 测试 E：长上下文三档测试

**结论: CONDITIONAL PASS — 三档均成功生成，但连续性锚点提取存在精度问题。**

### Tier 1: 短上下文（~691 字）

| 指标 | 值 |
|------|-----|
| 输入 | 691 字 |
| 输出 | 1192 字 |
| 时间 | 7.3s |
| 候选 ID | `cand_14a68c06` |
| 关键词命中 | 林澈, 沈知夏, 芯片 |
| 连续性 severity | medium |
| quality | OK |

### Tier 2: 中上下文（~1902 字）

| 指标 | 值 |
|------|-----|
| 输入 | 1902 字 |
| 输出 | 1296 字 |
| 时间 | 47.5s |
| 候选 ID | `cand_e28cf03f` |
| 关键词命中 | 林澈, 芯片, 老赵, 晨星 |
| 关键词缺失 | 沈知夏 |
| 连续性 severity | high |
| quality | OK |

### Tier 3: 长上下文（~2595 字，拼接 sec-001 + sec-003）

| 指标 | 值 |
|------|-----|
| 输入 | 2595 字 |
| 输出 | 1175 字 |
| 时间 | 14.5s |
| 候选 ID | `cand_b6b93f01` |
| 关键词命中 | 林澈, 芯片, 老赵, 晨星 |
| 关键词缺失 | 沈知夏 |
| 连续性 severity | medium |
| quality | OK |

### 三档对比

| 维度 | Tier 1 | Tier 2 | Tier 3 |
|------|--------|--------|--------|
| 成功 | YES | YES | YES |
| 超时 | NO | NO | NO |
| token 超限 | NO | NO | NO |
| 进入 candidate | YES | YES | YES |
| 丢人物 | NO | 沈知夏 | 沈知夏 |
| 丢地点 | NO | NO | NO |
| 丢道具 | NO | NO | NO |
| 重复 | NO | NO | NO |
| 突然总结 | NO | NO | NO |
| 过短 | NO | NO | NO |
| 格式异常 | NO | NO | NO |

---

## 错误场景验证

### FILE_CONFLICT 错误（Test D adopt 失败路径）

| 项目 | 值 |
|------|-----|
| 原始错误类别 | `FILE_CONFLICT` (HTTP 409-equivalent) |
| 前端用户文案 | "源文件已被其他操作修改，请重新生成候选稿后再采用。" |
| 是否命中 T7.3.7 翻译层 | YES（`ERROR_CODE_MAP["FILE_CONFLICT"]` 匹配） |
| 是否可指导用户 | YES（明确提示"重新生成候选稿后再采用"） |

---

## 发现的问题

### P2 — 连续性锚点提取精度不足

`_extract_continuity_anchors()` 从 691 字上文提取的锚点包含大量句子片段而非命名实体：

| 提取结果 | 类型 |
|----------|------|
| "旧港站" | 命名实体（正确） |
| "夜雨打在旧港站" | 句子片段（错误） |
| "快步穿过站" | 句子片段（错误） |
| "袋里摸出那枚银色芯片" | 句子片段（错误） |
| "验室逃出来时磕在门" | 句子片段（错误） |

导致 8 个锚点中仅 1 个正确，continuity_ratio 始终 ≤ 0.12，几乎所有 candidate 都触发 medium/high 连续性警告。

**影响**：连续性警告过于频繁，可能导致用户对警告麻木（alert fatigue）。实际生成内容的人物/地点/道具保留率远高于锚点命中率所暗示的水平。

**根因推测**：`_CONTINUITY_KEYWORD_PATTERN` 的后缀匹配可能误匹配了句子中的动词 + 名词组合，或 `_CHINESE_NAME_PATTERN` 未能正确分割句子边界。

### P3 — 新文件 candidate 缺少 base_hash

以新文件为目标的 candidate（sec-006 ~ sec-010，文件不存在时创建）的 `base_hash` 为空字符串，`base_mtime` 为 null。这意味着：

- 这些 candidate 无法被 adopt（后端拒绝 base_hash 为空的 adopt）
- 虽然从安全角度这是合理的（空文件无 hash），但限制了新场景 candidate 的可用性

### P3 — candidate action 标注不够精确

所有 `write_next_scene` 操作生成的 candidate action 均为 `"rewrite"`，而非更准确的 `"continue"` 或 `"write_next"`。前端 CandidatePanel 显示的 action 文案可能不够直观。

### P3 — Tier 2/3 中沈知夏未被保留

在 Tier 2（1902 字上文）和 Tier 3（2595 字上文）的生成结果中，沈知夏未出现。虽然这不一定是 bug（LLM 可能在续写时聚焦其他角色），但值得观察是否为长上下文下的常见模式。

---

## 最终候选稿统计

| ID | Action | Status | Source Path | Severity |
|----|--------|--------|-------------|----------|
| cand_e48b93ef | rewrite | **adopted** | sec-002 | medium |
| cand_63de0954 | polish | **rejected** | sec-001 | none |
| cand_46d97974 | rewrite | **discarded** | sec-010 | medium |
| cand_5010e0ec | polish | pending | sec-001 | none |
| cand_bc4b01a5 | rewrite | pending | sec-002 | medium |
| cand_0e48cda2 | rewrite | pending | sec-002 | medium |
| cand_14a68c06 | rewrite | pending | sec-006 | medium |
| cand_f3b1220e | rewrite | pending | sec-006 | medium |
| cand_505d8820 | rewrite | pending | sec-007 | high |
| cand_e28cf03f | rewrite | pending | sec-007 | high |
| cand_720186fb | rewrite | pending | sec-008 | medium |
| cand_b6b93f01 | rewrite | pending | sec-008 | medium |
| cand_f58238fd | rewrite | pending | sec-009 | medium |

状态分布：adopted × 1, rejected × 1, discarded × 1, pending × 10

---

## 综合评定

| 测试 | 结果 | 备注 |
|------|------|------|
| A. 写下一场景 | **PASS** | 真实 LLM，6/6 关键词命中，candidate 创建 |
| B. 续写 | **PASS** | append 模式，691→2192 字，直接写入 |
| C. 润色 | **PASS** | 5 步 pipeline 全执行，candidate 创建 |
| D. Preview | **PASS** | 内容正确返回，不修改正文 |
| D. Adopt (冲突) | **PASS** | FILE_CONFLICT 正确触发，错误翻译层命中 |
| D. Adopt (成功) | **PASS** | sec-002 正确更新，1405→1099 字 |
| D. Delete | **PASS** | pending→discarded，不影响正文 |
| E. Tier 1 短 | **PASS** | 7.3s，3/3 关键词 |
| E. Tier 2 中 | **PASS** | 47.5s，4/5 关键词（缺沈知夏） |
| E. Tier 3 长 | **PASS** | 14.5s，4/5 关键词（缺沈知夏） |

**总体结论**: **CONDITIONAL PASS**

真实 LLM 链路完整可用，candidate 安全机制正确工作，FILE_CONFLICT 防护有效，错误翻译层正常命中。长上下文三档均成功生成无超时。主要减分项为连续性锚点提取精度不足导致警告过于频繁（P2）。

---

## 剩余问题

| ID | 优先级 | 描述 |
|----|--------|------|
| R7.4-B2-1 | P2 | `_extract_continuity_anchors()` 提取大量句子片段而非命名实体，导致连续性警告过于频繁 |
| R7.4-B2-2 | P3 | 新文件 candidate 的 base_hash 为空，adopt 被拒绝 |
| R7.4-B2-3 | P3 | write_next_scene 的 candidate action 标注为 "rewrite" 而非 "continue" |
| R7.4-B2-4 | P3 | 长上下文（>1900 字）生成中沈知夏角色可能丢失 |
