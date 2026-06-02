# Lite Generation Orchestration 拆分设计

> **Task**: Phase 3.4D — Lite API 剩余职责盘点与 Generation Orchestration 拆分设计
> **Status**: 设计文档（不修改业务代码）
> **Date**: 2026-06-02
> **Author**: Solo (based on code analysis)

---

## 1. 当前背景

经过 Phase 1 / 2 / 3.x 几轮拆分，`backend/api/lite.py` 已从最初约 1100 行的单体路由文件瘦身到 **974 行**。但仍保留较多耦合度高的 orchestration 逻辑。下一步如果直接进入 generation orchestration 拆分，**风险极高**——里面的 prompt 调用、质量修复、候选稿创建、文件写入、SSE 事件等逻辑相互缠绕。

本设计的核心目标：
1. 明确 `lite.py` 当前剩余职责
2. 梳理 sync / stream 两条主流程的数据流
3. 划清 Candidate / SSE / File 写入的边界
4. 提出后续可拆分点的风险评级
5. 推荐 **下一步最小安全改造**，避免一次拆分失控

---

## 2. 已完成的拆分总结

| Phase | 模块 | 状态 | 文件 |
|-------|------|------|------|
| 3.1 | 项目初始化 | ✅ | `backend/application/lite_project_service.py` |
| 3.2 | 场景路径与卷章场导航 | ✅ | `backend/application/lite_scene_service.py` |
| 3.3A | Story metadata / memory 读写 | ✅ | `backend/application/lite_story_metadata_service.py` |
| 3.3B | Option cards / next-options 解析 | ✅ | `backend/application/lite_option_cards_service.py` |
| 3.4A | LLM 调用基础（complete / stream） | ✅ | `backend/application/lite_llm_service.py` |
| 3.4B | Prompt builder（chapter / ideas / next） | ✅ | `backend/application/lite_prompt_builder.py` |
| 3.4C | Quality gate（判断 + 触发） | ✅ | `backend/application/lite_quality_service.py` |

经过这一系列拆分，`lite.py` 路由层已经能 **直接调用** 这些 service，逻辑职责明显清晰。

---

## 3. 当前 `backend/api/lite.py` 剩余职责

### 3.1 路由层职责（合理保留）

| 行号 | 函数 / 路由 | 性质 |
|------|------------|------|
| 488 | `POST /lite/ideas` | 路由 |
| 500 | `POST /lite/projects` | 路由 |
| 512 | `POST /lite/next-options` | 路由 |
| 573 | `POST /lite/write-next` | 路由 |
| 784 | `POST /lite/write-next-stream` | 路由 |

### 3.2 仍然耦合在路由文件中的纯逻辑（候选拆分点）

| 类别 | 函数 | 行号 | 行数 | 风险 | 备注 |
|------|------|------|------|------|------|
| Action 映射 | `_lite_action_to_candidate_action` | 75-85 | 11 | P2 | 简单映射函数 |
| Candidate glue | `_create_lite_candidate` | 88-104 | 17 | P2 | 包装 CandidateService |
| Candidate 策略 | `_should_use_candidate` | 107-121 | 15 | P2 | 与策略文件重复，可删 |
| 偏好文本化 | `_prefs_to_text` | 124-134 | 11 | P2 | 纯字符串 |
| 故事引擎模板 | `_story_engine_template` | 137-180 | 44 | P1 | 模板字符串 |
| 路径异常 | `LitePathError` | 191-193 | 3 | P2 | 简单异常类 |
| 路径校验 | `_validate_project_id` | 195-227 | 33 | P2 | 与 PathService 重复 |
| 路径构造 | `_safe_project_path` | 228-269 | 42 | P2 | 同上 |
| 文件写入 | `_write_json` / `_write_text` | 271-279 | 9 | P2 | 同步 IO 包装 |
| 章节头 | `_ensure_section_heading` | 281-288 | 8 | P2 | 字符串 |
| 章节初始化 | `_ensure_chapter` | 291-324 | 34 | P1 | 流程串联 |
| Fallback 内容 | `_fallback_section_content` | 333-359 | 27 | P1 | 模板字符串 |
| SSE event | `_lite_stream_event` | 362-363 | 2 | P1 | SSE 序列化 |
| 下一场景推导 | `_next_writable_section_path` | 370-383 | 14 | P2 | 已基本由 SceneService 提供 |

### 3.3 高耦合 orchestration（**不建议马上拆**）

| 块 | 行号 | 描述 |
|----|------|------|
| `_generate_chapter_plan` | 386-441 | LLM + 文件读取 + 文件写入混合 |
| `_generate_ideas_via_llm` | 444-485 | LLM + JSON 解析 + LiteOptionCardsService |
| `write_lite_next()` 整体 | 573-781 | 完整 generation orchestration |
| `write_lite_next_stream()` 整体 | 784-995 | 完整 generation orchestration + SSE |

---

## 4. 同步 `write_lite_next` 数据流

```text
1. 路由接收 LiteWriteNextRequest
2. 路径校验: _validate_project_id / _validate_rel_path
3. 解析 project_dir, file_service, metadata_svc
4. 读取 requested_content, is_blank_requested
5. effective_action: LITE_ACTION_ALIAS 转换
6. 计算 target_file: rewrite 类 or blank 走 target_file, 否则走 _next_writable_section_path
7. is_candidate: _should_use_candidate
8. _ensure_chapter: 确保 ch-meta / vol-meta / sec-001~005 存在
9. 读取上下文:
   - prev_content (章内前序场景)
   - target_content (当前场景)
   - current_content = prev_content + target_content
   - story_engine, story_state, style_guide, recent_context
   - chapter_plan (可选)
   - chapter_memory, pending_foreshadowing (ch-meta.json)
10. 构造 goal 字符串 (拼接爽点卡信息 + 偏好 + 章规划 + 故事引擎)
11. 渲染主 prompt: prompt_engine.render("generate/continuation", {...})
12. 调用 LLM: lite_llm.complete_with_deadline(...)
13. fallback: 失败时使用 _fallback_section_content, used_fallback=True
14. _ensure_section_heading: 添加章节标题
15. Candidate 分支:
    - is_candidate=True: _create_lite_candidate → output_file = candidate_path → 发送 candidate.created 事件
    - is_candidate=False: file_service.write_file(...)
16. 更新章节记忆: metadata_svc.update_ch_meta (仅非 candidate)
17. 质量审查:
    - candidate / fallback: 设置 quality_summary 占位
    - 正常: quality.perform_review → save_review_result
      - quality_one_line
      - needs_quality_repair 为 True 时: 构建 repair_goal → 渲染 repair_prompt → 调 LLM → 替换 content → 重新写文件
18. 更新故事引擎:
    - is_candidate=False: build_story_engine_update → 写 story-engine.md / recent-context.md
19. 整章写完 (sec == SECTIONS_PER_CHAPTER): _generate_chapter_plan
20. 组装 LiteWriteNextResponse
```

**关键耦合点**:
- step 11 与 step 17 重复使用 `prompt_engine.render("generate/continuation", ...)`，参数重叠
- step 13 与 step 17 的 fallback 行为不同
- step 18 仅非 candidate 才更新故事引擎

---

## 5. 流式 `write_lite_next_stream` 数据流

```text
1. 路由接收 LiteWriteNextRequest
2. 内部 _stream() async generator:
   a. 路径校验 (LitePathError → yield error event)
   b. project_dir 存在性 (否则 yield error event)
   c. 与 sync 相同: 读取上下文, _ensure_chapter, etc.
   d. yield _lite_stream_event("meta", {file_path, source_file, is_candidate, label})
   e. 渲染主 prompt
   f. yield _lite_stream_event("status", {message: "AI 正在写正文..."})
   g. 流式调用 LLM: async for chunk in lite_llm.stream_llm_content(...):
      - 检查 request.is_disconnected()
      - content_parts.append(chunk)
      - yield _lite_stream_event("delta", {delta: chunk})
   h. 失败: fallback → used_fallback=True
   i. 拼接 generated_text, 处理 continue 拼接逻辑
   j. yield _lite_stream_event("replace", {content})  # 注意: 这是 streaming event, 不是 file.updated
   k. _ensure_section_heading
   l. Candidate 分支 (同 sync, 发送 candidate.created 事件)
   m. file_service.write_file 或 candidate 创建
   n. metadata_svc.update_ch_meta (非 candidate)
   o. quality_summary 决定
   p. _review_in_background: 后台 quality 任务 (仅当非 fallback + 非 candidate)
   q. 更新 story-engine / recent-context (非 candidate, yield status)
   r. 整章完成: _generate_chapter_plan
   s. yield _lite_stream_event("done", {file_path, content, quality_summary, story_engine_summary, chapter_plan, candidate_id, source_file})
3. 整体异常: yield _lite_stream_event("error", {message})
4. return EventSourceResponse(_stream())
```

**关键耦合点**:
- 步骤 e + g + j: 渲染 prompt → 流式 LLM → yield delta/replace，这是 stream 的"主信号"
- 步骤 p: 后台 review 任务与主流程解耦（不影响响应）
- 步骤 n: 在流式场景下不等待 review 完成，但同步场景下要等

---

## 6. Candidate 安全边界

### 6.1 当前边界

```text
Lite action (rewrite / more_exciting / more_reasonable / continue / polish / chat_edit)
    ↓ _lite_action_to_candidate_action
CandidateAction enum (REWRITE / POLISH / CHAT)
    ↓ _should_use_candidate
should_create_candidate (策略) + HIGH_RISK_LITE_ACTIONS
    ↓ _create_lite_candidate
CandidateService.create_candidate(source_mode="lite")
    ↓
.candidates/ 目录 + metadata.json + revision-log
```

### 6.2 后续拆分的安全要求

- **绝不能跳过 CandidateService 直接覆盖原文**。
- **必须保留 `source_mode="lite"`** 让 CandidateService 知道是 Lite 模式。
- **必须保留 `candidate.created` 事件发布**。
- **`_should_use_candidate` 与 `should_create_candidate` 策略重复**——未来应只保留策略文件，路由直接调用。
- **`_lite_action_to_candidate_action` 是简单映射表**——可保留在路由层，或下沉到 `LiteGenerationService`。

### 6.3 候选稿粘合层（`_create_lite_candidate`）

这个 17 行的小函数是路由层与 CandidateService 之间的 glue code。如果未来抽出 `LiteGenerationService`，这个函数应整体迁移到 service，路由层不再直接 import CandidateService。

---

## 7. SSE 安全边界

### 7.1 当前事件类型

| Event | data 字段 | 触发位置 | 前端依赖 |
|-------|-----------|----------|----------|
| `meta` | `file_path`, `source_file`, `is_candidate`, `label` | sync 路由前 | ✅ |
| `status` | `message` | stream 主流程中 | ✅ |
| `delta` | `delta` | stream 每次 chunk | ✅ |
| `replace` | `content` | stream 完整内容（不含 file.updated） | ✅ |
| `done` | `file_path`, `content`, `quality_summary`, `story_engine_summary`, `chapter_plan`, `candidate_id`, `source_file` | stream 收尾 | ✅ |
| `error` | `message` | 任何异常 | ✅ |
| `candidate.created` | via `event_bus.publish` | candidate 创建后 | ✅ |

### 7.2 安全要求

- **`_lite_stream_event` 是基础序列化函数**，应保留在路由层（或下沉到 `LiteSSEService`，但目前看收益不大）。
- **不要把 SSE event 抽象成 FlowEvent/ExecutionStep 抽象**——目前 5 个事件 + 1 个 candidate.created，已经够清晰，强行抽象会增加复杂度。
- **stream 收尾的 `done` 事件中 `content` 字段是必要的**——前端 Lite 编辑器依赖它来显示最终正文（这是 `AI_GUARDRAIL_ALLOW` 注释中明确允许的"lite generation result"，与 `file.updated` 不同）。
- **后台 review 任务** (`_review_in_background`) 是 Lite 特有的 UX 优化，**不发送 SSE**——前端只通过 quality summary 占位 + 后续 user 主动查询看到 review 结果。

### 7.3 不建议抽 SSE 抽象

- 5 个事件足够稳定
- 抽象收益小
- 增加未来维护成本

---

## 8. 文件写入与正文覆盖边界

### 8.1 写文件的所有位置

| 位置 | 条件 | 路径 |
|------|------|------|
| `_ensure_chapter` | 章节初始化 | `chapters/vol-XX/ch-XXX/` |
| 主写入 (`file_service.write_file`) | 非 candidate | `target_file` |
| 修复写入 (`file_service.write_file`) | quality repair 成功 | `output_file` |
| `update_ch_meta` | 非 candidate | `ch-meta.json` |
| `_generate_chapter_plan` 内部 | 整章写完 | `ch-plan.md` |
| `story-engine.md` 更新 | 非 candidate | `story-engine.md` |
| `recent-context.md` 更新 | 非 candidate | `recent-context.md` |
| `_write_json` / `_write_text` | 章节初始化 | vol-meta / ch-meta / sec-XXX |

### 8.2 安全要求

- **`output_mode=overwrite` 是旧兼容值**——主写入仍是 `file_service.write_file`，但 Lite 不应使用 `overwrite` 模式。
- **修复写入必须走 `file_service.write_file`**，不走 `output_mode=overwrite`。
- **candidate 流程不更新 `story-engine.md` / `recent-context.md`**——必须 adopt 后才更新。
- **adopt 流程仍走 CandidateService.adopt_candidate**——不要在路由层手写 adopt 逻辑。

---

## 9. 后续可拆分服务候选

### 9.1 候选服务列表

| 候选服务 | 职责 | 来源函数 | 风险 |
|----------|------|----------|------|
| `lite_section_service` | 章节初始化、章节头、sec 文件创建 | `_ensure_chapter`, `_ensure_section_heading`, `_write_json`, `_write_text` | P1 |
| `lite_validation_service` | 路径校验、project_id 校验、rel_path 校验 | `_validate_project_id`, `_validate_rel_path`, `_safe_project_path`, `LitePathError` | P1 |
| `lite_sse_service` | SSE event 序列化 | `_lite_stream_event` | P2 |
| `lite_generation_service` | sync + stream 主 orchestration | `write_lite_next`, `write_lite_next_stream` | P0 |
| `lite_idea_service` | ideas 生成 + 兜底 | `_generate_ideas_via_llm` | P1 |
| `lite_chapter_plan_service` | 章规划生成 | `_generate_chapter_plan` | P1 |
| `lite_fallback_service` | fallback 内容生成 | `_fallback_section_content` | P1 |

### 9.2 已存在 / 重复的函数（应清理）

| 函数 | 来源 | 建议 |
|------|------|------|
| `_should_use_candidate` | `backend/api/lite.py` | 与 `should_create_candidate` (策略文件) 重复，**应直接删除并调用策略** |
| `_safe_project_path` | `backend/api/lite.py` | 与 FileService 重复，**应删除** |
| `_prefs_to_text` | `backend/api/lite.py` | 纯字符串函数，**应保留或下沉** |
| `_validate_project_id` | `backend/api/lite.py` | 已被 PathService 替代，**应检查是否仍需要** |

---

## 10. 风险等级 P0/P1/P2

| 等级 | 含义 | 候选操作 |
|------|------|----------|
| **P0** | 高风险，不建议本季度拆 | 同步 / 流式 generation orchestration 整体抽取 |
| **P1** | 中风险，可小步拆，但要补足测试 | 章节初始化服务、ideas 服务、章规划服务、validation 服务 |
| **P2** | 低风险，可优先拆 | SSE 序列化、prefs 文本化、candidate action 映射 |

---

## 11. 推荐下一步最小改造

### 11.1 Phase 3.4E：清理重复函数（低风险，1-2 小时）

1. **删除 `_should_use_candidate`**，路由层直接调用 `should_create_candidate` 策略
2. **删除 `_safe_project_path`**，路由层直接调用 FileService 内的方法
3. **下沉 `_prefs_to_text`** 到 `lite_prompt_builder.py`（作为 `format_preferences` 静态方法）
4. **下沉 `_lite_action_to_candidate_action`** 到 `LiteGenerationService` 或保留在路由（视未来是否抽 generation service 而定）

预期收益：lite.py 减少约 70 行，重复逻辑归位
风险：P2（几乎无风险）
测试：现有测试应继续通过

### 11.2 Phase 3.4F：抽取 Lite Section Service（中风险，半天）

1. 新增 `backend/application/lite_section_service.py`
2. 迁移：
   - `_ensure_chapter` → `ensure_chapter`
   - `_ensure_section_heading` → `ensure_section_heading`
   - `_write_json` / `_write_text` → 内部 helper
3. 路由层调用 service
4. 新增 `test_lite_section_service.py` 覆盖章节初始化、文件创建、metadata 默认值

预期收益：lite.py 减少约 60 行
风险：P1（与文件 IO 紧密相关，但每个函数行为都很清晰）
测试：可大量复用现有 E2E 测试

### 11.3 Phase 3.4G：抽取 Lite Validation Service（低风险，2 小时）

1. 新增 `backend/application/lite_validation_service.py`
2. 迁移：
   - `_validate_project_id` → `validate_project_id`
   - `_validate_rel_path` → `validate_rel_path`
   - `LitePathError` → 重新导出
3. 路由层改为抛 `LiteValidationError`

预期收益：lite.py 减少约 50 行
风险：P2（纯字符串 / 路径校验，无副作用）
测试：可补 `test_lite_validation_service.py`

### 11.4 Phase 3.5A：评估 Generation Orchestration 抽取（**不建议马上做**）

`write_lite_next` 和 `write_lite_next_stream` 之间共享大量 orchestration 代码，但 stream 多了 SSE 事件、后台 review、is_disconnected 检查等。

抽取策略候选：
- **方案 A**：抽 `LiteGenerationService.execute_sync()` 和 `LiteGenerationService.execute_stream()` 两个方法，路由层只负责 SSE 序列化
- **方案 B**：抽 `LiteGenerationContext` 数据类承载所有上下文，sync / stream 各自只编排 context → call service
- **方案 C**：保留现状，**只把同步流程的 SSE 拼装和后台 review 抽到 service**

推荐：**方案 C**——边界最小、收益最大（同步和流式可以共用 review 在后台执行）。但仍需先完成 3.4E / 3.4F / 3.4G 三轮清理。

---

## 12. 不建议马上做的事情

| 行为 | 不建议原因 |
|------|------------|
| 一次拆 sync + stream 完整 orchestration | 两个流程细节差异大（流式多了 SSE / is_disconnected / 后台 review），耦合深，测试难以补足 |
| 把 Lite 接入 Pipeline | 风险极高，与 Pipeline 解耦是 Phase 1 的既定目标 |
| 抽象 FlowEvent / ExecutionStep | 当前 5 个 SSE event 已足够清晰，抽象收益小 |
| 重构 _generate_chapter_plan | 与 LLM + 文件 IO + 元数据耦合，且与 next-options 流程有共享 |
| 把 review 改成强制等 review 完成再返回 | 同步场景下 review 是 IO 密集，强制等会显著增加响应时间；后台 review 是合理 UX 优化 |

---

## 13. 对未来数据流可视化的启发

完成 3.4E / 3.4F / 3.4G 后，Lite 数据流可以表达为：

```text
┌─────────────────────────────────────────────────────────────────┐
│ 路由层 (lite.py)                                                  │
│   /lite/next-options / /lite/write-next / /lite/write-next-stream│
└────┬─────────────────────────┬─────────────────────────┬─────────┘
     │                         │                         │
     ▼                         ▼                         ▼
┌──────────────┐  ┌───────────────────────┐  ┌────────────────────┐
│ Validation   │  │ Generation            │  │ SSE Service        │
│ Service      │  │ Service (future)      │  │                    │
└──────────────┘  └─────┬─────────────────┘  └────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌──────────┐   ┌──────────┐   ┌─────────────┐
  │Scene     │   │Story     │   │Option Cards │
  │Service   │   │Metadata  │   │Service      │
  └──────────┘   │Service   │   └─────────────┘
                 └──────────┘
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  ┌──────────┐   ┌──────────┐   ┌─────────────┐
  │Prompt    │   │Quality   │   │LLM          │
  │Builder   │   │Service   │   │Service      │
  └──────────┘   └──────────┘   └─────────────┘
                       │
                       ▼
              ┌────────────────┐
              │Candidate       │
              │Service         │
              └────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │FileService     │
              └────────────────┘
```

每条边都是明确的数据 / 函数调用，无循环依赖。

---

## 14. 结论

- **本季度 Phase 3.4E / 3.4F / 3.4G 完成后**，lite.py 应从 974 行降到约 **800 行**。
- **Phase 3.5A 之前**，应先补足相关 E2E 测试（特别是 stream + repair + candidate 组合场景）。
- **不要在本季度抽 generation orchestration**——风险高、收益小、测试覆盖不足。
- **不要修改业务代码**——本轮只输出设计文档。

---

## 附录 A：lite.py 行数变化

| 阶段 | 行数 | 备注 |
|------|------|------|
| Phase 1 之前 | ~1100 | 原始 |
| Phase 3.1 之后 | ~1050 | -50 |
| Phase 3.2 之后 | ~1020 | -30 |
| Phase 3.3A 之后 | ~990 | -30 |
| Phase 3.3B 之后 | ~990 | -10（option cards 简化） |
| Phase 3.4A 之后 | ~960 | -30 |
| Phase 3.4B 之后 | ~960 | -20（prompt builder） |
| Phase 3.4C 之后 | 974 | -21（quality service） |
| **Phase 3.4D 当前** | **974** | 本轮无代码变更 |
| Phase 3.4E 之后（预估） | ~910 | -60（清理重复） |
| Phase 3.4F 之后（预估） | ~850 | -60（section service） |
| Phase 3.4G 之后（预估） | ~800 | -50（validation service） |
