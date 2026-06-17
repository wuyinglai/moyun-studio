# T9.4 Writing Quality Enhancement Plan

**Stage**: T9.4a — Planning + MVP Contract  
**Risk Level**: Risk C / Product Planning  
**Mode**: Design + Roadmap + Acceptance Contract, No Product Code Changes  
**Base Commit**: `86187a4` (test: stabilize continuity anchors contracts + graceful degradation)  
**Date**: 2026-06-17  

---

## 1. 背景

墨韵 Studio 的写作质量保障体系经历了两个重要阶段的建设：

- **T8（写作质量闭环）**：建立了 candidate-only 安全工作流、required/forbidden beats、beat validator warning、feedback revision child candidate、multi-round revision lineage、polish conservative rules。核心安全边界——AI 不自动覆盖正文——贯穿始终。
- **T9.3（Continuity Anchors）**：实现了用户维护的连续性锚点系统，active anchors 自动注入 prompt，metadata 记录 anchor 使用情况，candidate-only 边界不变。

T9.4 的目标是在这两个阶段的基础上，进一步增强写作质量的**可观测性**和**可控性**，同时保持 candidate-only 安全边界不被突破。

本设计文档基于对现有代码的完整调查，明确当前已解决什么、还缺什么、哪些值得做、哪些必须暂缓。

---

## 2. 当前能力基线

### 2.1 已完成的能力

| 能力 | 实现位置 | 状态 |
|------|---------|------|
| Candidate-only 安全工作流 | `candidate_service.py` + 全栈 | ✅ 稳定 |
| Required / Forbidden Beats | `beat_validator.py` + prompt blocks | ✅ 稳定 |
| Beat Validator (LLM-backed) | `RequiredBeatValidator` | ✅ 稳定 |
| Feedback Revision Child Candidate | `candidate_service.py` + `candidates.py` | ✅ 稳定 |
| Multi-round Revision Lineage | `CandidateInfo` parent/revision fields | ✅ 稳定 |
| Polish Conservative Rules | `blocks/polish-conservative-rules.md` | ✅ 稳定 |
| Continuity Anchors MVP | `continuity_anchor_service.py` + prompt injection | ✅ 稳定 |
| CandidatePanel quality check UI | `CandidatePanel.vue` | ✅ 稳定 |
| 98 backend tests | `backend/tests/` | ✅ 全通过 |
| 77 full mock E2E / 93 skipped / 0 failed | `frontend/tests/e2e/` | ✅ 全通过 |
| Real LLM dogfood (3 scenarios) | T9.3-final 验证 | ✅ 全通过 |

### 2.2 现有的质量相关基础设施

**Beat Validator** (`backend/core/beat_validator.py`)：
- LLM-backed，对 candidate 检查 required beats 是否被满足、forbidden beats 是否被违反
- 输出结构化 metadata：每个 beat 有 alignment tier (ID match → exact text → SequenceMatcher ≥0.62)
- 结果存入 `CandidateInfo.beat_validation`

**Continuity Anchors** (`backend/core/continuity_anchor_service.py`)：
- 5 种 anchor type：character_state, plot_clue, object_location, relationship, world_rule
- 3 种 status：active, resolved, archived
- Only active anchors inject into prompts
- Metadata 存入 `CandidateInfo.continuity_anchors`

**QualityService** (`backend/core/quality_service.py`)：
- Post-hoc LLM review，对已 adopt 的章节做 6 维评分
- 6 维度：coherence, character_consistency, setting_consistency, writing_quality, logic, style_compliance
- 结果存入 `materials/reviews/`，与 candidate metadata **完全断开**
- 只在用户主动触发"质量审查"时运行，不在 candidate 创建时自动运行

**Polish Pipeline** (`backend/core/pipeline.py`)：
- 5 步线性链：depai → prose → logic → rhythm → diff
- 每步包含 beat-constraints + conservative-rules
- 7 个 quality prompt blocks 通过 Jinja2 `{% include %}` 注入

**Prompt Blocks** (`prompts/blocks/`)：
- `beat-constraints.md` — beat 约束注入
- `polish-conservative-rules.md` — 保守润色规则
- `depai-rules.md` — 去 AI 味规则
- `prose-rules.md` — 散文/叙事规则
- `logic-rules.md` — 逻辑一致性规则
- `rhythm-rules.md` — 节奏/韵律规则
- `continuity-anchors.md` — 连续性锚点注入

### 2.3 当前 Candidate Metadata 结构

```python
class CandidateInfo(BaseModel):
    id: str
    action: CandidateAction          # rewrite/polish/feedback_revision/etc.
    status: CandidateStatus          # pending/adopted/rejected/discarded
    beat_validation: Dict[str, Any]  # required beat validation results
    continuity_anchors: Dict[str, Any]  # anchor metadata
    continuity: Dict[str, Any]       # continuity check (has_warning/severity/message)
    generation_context: Dict[str, Any]  # generation context (schema not formalized)
    parent_candidate_id: str | None  # feedback revision parent
    revision_group_id: str | None    # lineage group
    revision_index: int              # revision index in lineage
    warning_message: str | None      # user-facing warning summary
    # ... other fields
```

### 2.4 当前 CandidatePanel UI 展示

`CandidatePanel.vue` 已展示：
- Beat validation status（满足/违反数量）
- Continuity warnings（severity + message）
- Anchor count（used anchors）
- Revision lineage info（parent link, revision index）

未展示：
- 质量评分
- 改动摘要 / diff summary
- 改动幅度
- prompt 使用了哪些 blocks

---

## 3. T8 / T9.3 已解决的问题

### T8 解决的核心问题

1. **AI 安全边界**：建立了 candidate-only 工作流，AI 永远不自动覆盖正文。
2. **Beat 约束**：用户可以指定 required beats（必须包含）和 forbidden beats（不能包含），LLM-backed validator 在 candidate 创建后自动检查。
3. **Feedback Revision**：用户可以用自然语言反馈，系统生成 child candidate，保留 lineage。
4. **Polish 保守规则**：润色 pipeline 遵循"不改情节、不改人物、不改设定"的保守原则。
5. **Multi-round Lineage**：revision chain 可追溯，parent→child 关系清晰。

### T9.3 解决的核心问题

1. **连续性锚点**：用户可以主动维护一组"写作时不能遗忘"的锚点（人物状态、情节线索、物品位置、关系变化、世界规则）。
2. **Prompt 注入**：active anchors 自动注入到 rewrite/polish/feedback revision 的 prompt 中。
3. **Metadata 追踪**：candidate 记录使用了哪些 anchors、用了几个、什么类型。
4. **Graceful Degradation**：anchors 文件不存在或损坏时，pipeline 不报错，降级为空文档。

---

## 4. T9.4 仍要解决的问题

尽管 T8 和 T9.3 建立了扎实的基础，以下能力仍然缺失或不完善：

### 4.1 Candidate 缺乏质量评分

当前 `QualityService` 是 post-hoc 的，只对已 adopt 的章节评分。用户在 candidate 卡片上看不到任何质量指标，必须 adopt 后再手动触发质量审查。这导致：
- 用户无法在 adopt 前比较多个 candidate 的质量
- 质量反馈循环断裂——生成时不知道质量如何

### 4.2 generation_context Schema 未正式化

`CandidateInfo.generation_context` 是 `Dict[str, Any]`，schema 未定义。目前可能包含 pipeline_id、beats、anchors 等信息，但没有统一的 contract。这让前端解析困难、测试脆弱。

### 4.3 无 Repair Candidate 机制

当 beat validator 报 warning 或 continuity check 发现不一致时，用户只能：
- 手动给 feedback 做 revision（需要自己想 feedback 内容）
- 放弃 candidate 重新生成

缺少一个"基于结构化 warning 自动生成 repair candidate"的快捷路径。

### 4.4 缺少改动摘要

用户面对一个 candidate，不知道它相对原文做了什么改动。当前 pipeline 有 `diff_summary` 事件，但没有结构化存入 metadata。CandidatePanel 没有展示改动范围。

### 4.5 Polish Pipeline 质量无反馈

Polish 5 步链每步都有 fallback，但没有质量校验环节。如果 depai-rules 导致过度去 AI 味、或 prose-rules 导致风格偏移，当前没有机制检测和修正。

### 4.6 角色声音 Prompt Block 缺失

当前 7 个 quality prompt blocks 中没有"角色声音/对话风格"专用 block。角色一致性靠 `characters/` 目录的 JSON 文件，但没有注入到 rewrite/polish prompt 中（只在 QualityService review 时读取）。

---

## 5. 明确不做事项

以下在 T9.4 阶段明确**不做**：

```text
不做自动修文（AI 不自动改已 adopt 的正文）
不做 automatic repair（不自动触发 repair，必须用户点击）
不做自动 adopt（repair candidate 仍然是 candidate）
不做 Scene Plan
不做复杂评分系统（不做总分排名、不做加权评分）
不做多模型裁判（不用多个 LLM 投票）
不大改 UI（CandidatePanel 可小幅扩展，不做全新面板）
不新增 prompt blocks（T9.4 不改变 prompt 本身）
不改 validator 逻辑（beat validator 保持稳定）
不改 release tag（T9.4 不触发新 release）
不创建 release
```

---

## 6. 质量维度设计

### 6.1 推荐维度

基于当前 `QualityService` 的 6 维评分和 T8/T9.3 已建立的能力，T9.4 推荐以下 **5 个轻量质量维度**，用于 candidate metadata 标注：

| 维度 | 英文 key | 含义 | 数据来源 |
|------|---------|------|---------|
| 指令遵守 | `instruction_following` | candidate 是否遵循了 required beats、action type 的预期 | Beat Validator 结果 |
| 连续性 | `continuity` | candidate 是否与 continuity anchors 一致 | Continuity anchor check |
| 风格保持 | `style_preservation` | 润色/改写是否保持了原文风格 | Polish conservative rules check（规则级） |
| 改动幅度 | `change_scope` | 改动是局部还是全局 | Diff stats（增/删/改段落数） |
| 禁止泄露 | `forbidden_check` | 是否违反了 forbidden beats | Beat Validator 结果 |

### 6.2 不做的事情

- **不做总分排名**：不给 candidate 打"总分"，不做加权聚合，不排序。
- **不做 AI 评分**：T9.4 不调用 LLM 做质量评分（避免额外 LLM 开销和不确定性）。
- **不做自动决策**：所有维度只是 advisory metadata，warning 不阻断 adopt。

### 6.3 维度评估方式

所有 5 个维度的评估都基于**已有结构化数据**，不需要额外 LLM 调用：

```python
def compute_quality_metadata(candidate_info, beat_validation, continuity_anchors, diff_stats):
    quality = {}

    # 1. instruction_following: 从 beat_validation 提取
    beats = beat_validation.get("beats", [])
    required_met = all(b.get("met", False) for b in beats if b.get("type") == "required")
    quality["instruction_following"] = "pass" if required_met else "warning"

    # 2. continuity: 从 continuity check 提取
    has_warning = candidate_info.continuity.get("has_warning", False)
    quality["continuity"] = "warning" if has_warning else "pass"

    # 3. style_preservation: 基于 action type 的规则判断
    if candidate_info.action == CandidateAction.POLISH:
        # polish 应该保守，如果 diff 太大则 warning
        quality["style_preservation"] = "warning" if diff_stats.change_ratio > 0.4 else "pass"
    else:
        quality["style_preservation"] = "n/a"

    # 4. change_scope: 从 diff stats 计算
    if diff_stats.change_ratio < 0.1:
        quality["change_scope"] = "minimal"
    elif diff_stats.change_ratio < 0.4:
        quality["change_scope"] = "medium"
    else:
        quality["change_scope"] = "substantial"

    # 5. forbidden_check: 从 beat_validation 提取
    forbidden_violated = any(
        not b.get("met", True) for b in beats if b.get("type") == "forbidden"
    )
    quality["forbidden_check"] = "warning" if forbidden_violated else "pass"

    return quality
```

### 6.4 与 QualityService 的关系

`QualityService` 保持不变——它仍然是 post-hoc 的、LLM-backed 的深度审查工具。T9.4 的 quality metadata 是轻量的、实时的、基于规则的，两者互补：

- **T9.4 quality metadata**：candidate 创建时自动计算，0 LLM 开销，快速 advisory
- **QualityService review**：用户主动触发，1 次 LLM 调用，深度分析

---

## 7. Candidate Quality Metadata 方案

### 7.1 Schema 设计

在 `CandidateInfo` 中新增 `quality` 字段：

```python
# backend/schemas/candidate.py

class CandidateQualityMetadata(BaseModel):
    """Candidate 质量 metadata — 轻量 advisory，不影响 adopt"""
    instruction_following: str = "n/a"  # pass / warning / n/a
    continuity: str = "n/a"             # pass / warning / n/a
    style_preservation: str = "n/a"     # pass / warning / n/a
    change_scope: str = "n/a"           # minimal / medium / substantial / n/a
    forbidden_check: str = "n/a"        # pass / warning / n/a
    notes: list[str] = Field(default_factory=list)  # 可解释性备注

class CandidateInfo(BaseModel):
    # ... existing fields ...
    quality: CandidateQualityMetadata = Field(
        default_factory=CandidateQualityMetadata,
        description="Quality metadata (advisory, does not block adopt)"
    )
```

### 7.2 计算时机

Quality metadata 在 **candidate 创建时**自动计算，不需要额外 LLM 调用：

1. Pipeline 生成 candidate content
2. Beat validator 运行（如果 beats 存在）
3. Continuity anchor check（如果 anchors 存在）
4. Diff stats 计算（已有 `diff_summary` 事件）
5. **Quality metadata 计算**（纯规则，0 LLM 开销）
6. 写入 `CandidateInfo`

### 7.3 存储

与现有 metadata 一起存储在 candidate JSON 文件中：

```json
{
  "id": "cand-abc123",
  "action": "polish",
  "status": "pending",
  "beat_validation": { "beats": [...], "summary": "..." },
  "continuity_anchors": { "used_count": 3, "anchor_ids": [...], "types": [...] },
  "quality": {
    "instruction_following": "pass",
    "continuity": "warning",
    "style_preservation": "pass",
    "change_scope": "medium",
    "forbidden_check": "pass",
    "notes": ["continuity: anchor 'a-001' flagged inconsistency"]
  }
}
```

### 7.4 UI 展示（最小变更）

`CandidatePanel.vue` 在现有的 beat/continuity 展示区域下方，增加一行 quality summary：

```text
Quality: instruction ✅ | continuity ⚠️ | style ✅ | scope: medium | forbidden ✅
```

- `pass` → 绿色 ✅
- `warning` → 黄色 ⚠️
- `n/a` → 灰色 —

不弹窗，不阻断，纯 advisory。

### 7.5 安全约束

```text
quality warning 不阻断 adopt
quality warning 不触发自动修复
quality metadata 不包含 API key
quality notes 不泄露 prompt 全文
quality metadata 字段可选，缺失时显示 n/a
```

---

## 8. Repair Candidate 方案

### 8.1 定位

Repair Candidate 是一个**新的 candidate action type**，基于结构化 warning（而非用户自然语言反馈）生成修复候选稿。

**与 Feedback Revision 的区别：**

| 维度 | Feedback Revision | Repair Candidate |
|------|-------------------|-----------------|
| 触发方式 | 用户自然语言反馈 | 基于 beat/continuity/quality warning |
| 输入 | `feedback_text` (自由文本) | `repair_targets` (结构化 warning list) |
| Prompt | `revise.md` (包含用户文本) | `repair.md` (包含结构化 repair 指令) |
| 目标 | 按用户意图修改 | 修复具体的 validator/anchor warning |
| Lineage | parent→child | parent→child |
| 安全边界 | candidate-only | candidate-only |

### 8.2 Repair Targets 来源

Repair targets 来自已有的 warning 系统：

1. **Beat validation warnings**：required beat 未满足、forbidden beat 被违反
2. **Continuity anchor warnings**：anchor 一致性检查 flag
3. **Quality metadata warnings**：`instruction_following: warning`、`continuity: warning` 等

### 8.3 用户交互流程

```text
1. 用户看到 candidate 卡片上的 warning (beat/continuity/quality)
2. 用户点击 "修复" 按钮
3. 系统收集该 candidate 的所有 warning 作为 repair_targets
4. 系统生成 repair candidate (action=repair, parent=current candidate)
5. 用户预览 repair candidate
6. 用户决定 adopt 或 discard
```

**关键：用户必须主动点击"修复"，系统不自动触发。**

### 8.4 Data Model

```python
# backend/schemas/candidate.py

class CandidateAction(str, Enum):
    # ... existing actions ...
    REPAIR = "repair"  # 基于 warning 的结构化修复

class CandidateRepairRequest(BaseModel):
    """Repair candidate request"""
    repair_targets: list[dict] = Field(
        default_factory=list,
        description="List of warnings to repair, each with type/source/message"
    )
    repair_scope: str = Field(
        "full_candidate",
        description="full_candidate | targeted_section"
    )
    inherit_required_beats: bool = True
    inherit_forbidden_beats: bool = True
```

### 8.5 Repair Prompt Template

新增 `prompts/pipeline/candidate-repair/repair.md`：

```markdown
你是一个专业的小说修改助手。请根据以下修复目标，修改候选稿内容。

## 修复目标
{% for target in repair_targets %}
- **{{ target.type }}**: {{ target.message }}
{% endfor %}

## 原候选稿
{{ parent_candidate_text }}

## 正文
{{ official_source_text }}

{% include 'blocks/beat-constraints.md' %}
{% include 'blocks/continuity-anchors.md' %}

## 规则
1. 只修改与修复目标相关的部分
2. 保持其他内容不变
3. 不要添加新情节
4. 不要改变人物性格
5. 输出完整修改后的文本
```

### 8.6 安全约束

```text
repair 只能生成新的 candidate
不能自动覆盖正文
不能自动修改 parent candidate
不能自动 adopt
必须保留 lineage (parent_candidate_id + revision_group_id)
repair_targets 不包含 API key
repair prompt 不泄露完整 prompt 配置
```

### 8.7 Lineage 兼容

Repair candidate 复用现有的 lineage 机制：

- `parent_candidate_id` = 被修复的 candidate
- `revision_group_id` = 与 feedback revision 共享同一个 lineage group
- `revision_index` = group 内自增
- `action` = `CandidateAction.REPAIR`

这意味着一个 candidate 可以有多个 child：既有 feedback revision child，也有 repair child。用户在 CandidatePanel 中看到完整的 revision tree。

---

## 9. Candidate Compare / Explainability 评估

### 9.1 Candidate Compare（候选稿对比）

**当前状态**：前端没有 candidate 对比功能。用户只能一个一个预览 candidate。

**T9.4 评估**：

实现完整的 diff UI 需要较大的前端工作量（side-by-side diff、highlight changes、scroll sync），且收益在 MVP 阶段有限。T9.4 建议：

- **MVP 阶段不做**完整 diff UI
- 但可以做**改动摘要**（change summary）存入 metadata，为后续 diff UI 做数据准备
- 改动摘要可以从 pipeline 的 `diff_summary` 事件提取，不需要额外计算

**改动摘要 schema**（存入 `generation_context` 或新增 `change_summary` 字段）：

```python
class ChangeSummary(BaseModel):
    paragraphs_added: int = 0
    paragraphs_removed: int = 0
    paragraphs_modified: int = 0
    change_ratio: float = 0.0  # 0-1, 改动字数 / 原文字数
    summary_text: str = ""     # pipeline diff_summary 事件的文本
```

### 9.2 Prompt Debug / Explainability

**当前状态**：用户不知道 pipeline 用了哪些 prompt blocks、beats、anchors。

**T9.4 评估**：

可解释性对用户调试很有价值，但需要在信息量和复杂度之间平衡。建议：

**做（轻量）**：
- 在 `generation_context` 中记录 prompt blocks used、beats used、anchors used
- CandidatePanel 增加一个可折叠的 "Generation Info" 区域，展示这些 metadata
- 不展示 prompt 全文（避免信息过载和安全风险）

**不做（重量级）**：
- 不做 prompt 编辑器
- 不做 prompt diff
- 不暴露 API key 或完整 prompt template

**generation_context 正式化 schema**：

```python
class GenerationContext(BaseModel):
    """正式化的 generation context schema"""
    pipeline_id: str | None = None
    pipeline_steps: list[str] = Field(default_factory=list)
    prompt_blocks_used: list[str] = Field(default_factory=list)
    beats_required: list[str] = Field(default_factory=list)
    beats_forbidden: list[str] = Field(default_factory=list)
    anchors_used_ids: list[str] = Field(default_factory=list)
    anchors_used_count: int = 0
    scene_plan_used: bool = False
    model: str | None = None
    dry_run: bool = False
```

---

## 10. Real LLM Dogfood Set 设计

### 10.1 设计目标

建立一组固定的中文 dogfood cases，用于每个阶段收口时验证端到端行为。每个 case 覆盖一个核心能力，可在 10 分钟内手动完成。

### 10.2 Case 列表

| # | Case Name | 覆盖能力 | 验证重点 |
|---|-----------|---------|---------|
| 1 | Rewrite + Continuity | rewrite pipeline + anchors 注入 | anchors 出现在 prompt 中，candidate 不泄露 anchor metadata |
| 2 | Polish Conservative | polish pipeline + conservative rules | 不改情节/人物/设定，diff 幅度合理 |
| 3 | Feedback Revision | feedback → child candidate + lineage | child 创建成功，parent 不变，lineage 正确 |
| 4 | Forbidden Reveal | forbidden beat 检测 | validator 正确报告 forbidden beat 违反 |
| 5 | Relationship Jump | relationship anchor + rewrite | relationship 类型的 anchor 被正确注入 |
| 6 | Repair Candidate | repair action + warning-based | repair candidate 生成成功，lineage 正确 |

### 10.3 每个 Case 的标准输入

```json
{
  "case_id": "dogfood-01-rewrite-continuity",
  "project_id": "__dogfood__",
  "action": "rewrite",
  "source_path": "chapters/ch-001.md",
  "anchors": [
    {"id": "a-001", "type": "character_state", "title": "李默的伤", "content": "左臂骨折未愈", "status": "active"},
    {"id": "a-002", "type": "plot_clue", "title": "密信", "content": "密信藏在鞋底", "status": "active"}
  ],
  "beats": {
    "required": ["李默发现密信"],
    "forbidden": ["李默的伤已痊愈"]
  },
  "expected": {
    "candidate_created": true,
    "anchors_used_count": 2,
    "beat_validation_run": true,
    "no_source_change": true
  }
}
```

### 10.4 Case 6: Repair Candidate 特别说明

Case 6 依赖 T9.4c 实现的 repair candidate 功能。如果 T9.4c 尚未实现，Case 6 暂标记为 "blocked by T9.4c"，先跳过。

### 10.5 执行方式

```powershell
# 启动 backend
cd D:\newmoyun
set PYTHONIOENCODING=utf-8 && python -X utf8 -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000

# 重置 circuit breaker
# (手动编辑 backend/workspace/.circuit-breaker-state.json → 全部设为 closed + failure_count:0)

# 逐 case 执行
# 用 Python script 调用 API，验证 expected 条件
```

---

## 11. 风险与缓解

### 11.1 Quality Metadata 误判

**风险**：基于规则的 quality 评估可能误判（例如 diff ratio 高不一定代表风格破坏）。  
**缓解**：所有维度都是 advisory，UI 用 ⚠️ 而非 ❌，notes 字段提供可解释性。用户可以忽略。

### 11.2 Repair Candidate Prompt 质量

**风险**：repair prompt 可能不如用户手写 feedback 精准。  
**缓解**：repair candidate 仍然可以被用户 discard；repair targets 是结构化 warning，比自由文本更聚焦。

### 11.3 额外 API 开销

**风险**：quality metadata 如果需要 LLM 调用，会增加延迟和成本。  
**缓解**：T9.4 的 quality metadata 完全基于规则计算，0 LLM 开销。QualityService 保持不变，只在用户主动触发时使用。

### 11.4 CandidateInfo Schema 变更兼容

**风险**：新增 `quality` 字段可能影响现有 candidate 文件的读取。  
**缓解**：`quality` 字段使用 `default_factory`，缺失时自动填充默认值。Pydantic 向后兼容。

### 11.5 Repair Prompt Template 的 `{% include %}` 依赖

**风险**：repair prompt template 使用 `{% include %}`，需要 `Environment(FileSystemLoader)` 支持。  
**缓解**：T9.3-final 已修复此问题（`candidate_service.py` 已使用 `Environment(FileSystemLoader)`），repair 代码路径复用同一机制。

---

## 12. 推荐 MVP

### T9.4 MVP = Quality Metadata + Repair Candidate Design + Dogfood Set

#### MVP 包含

1. **Quality Metadata**（T9.4b）
   - 新增 `CandidateQualityMetadata` schema
   - Candidate 创建时自动计算 5 个维度（0 LLM 开销）
   - CandidatePanel 最小展示（一行 quality summary）
   - Mock E2E + backend tests

2. **Repair Candidate**（T9.4c）
   - 新增 `CandidateAction.REPAIR` action type
   - 新增 `CandidateRepairRequest` schema
   - 新增 `repair.md` prompt template
   - `candidate_service.py` 新增 `create_repair_candidate()` 方法
   - API endpoint: `POST /api/candidates/{id}/repair`
   - Lineage 复用现有机制
   - Mock E2E + backend tests

3. **Dogfood Set**（T9.4d）
   - 6 个标准 dogfood cases
   - 自动化验证脚本
   - 覆盖 rewrite/polish/feedback/anchors/forbidden/repair

#### MVP 不包含

- Candidate Compare diff UI（推迟到 T10+）
- Generation Context 正式化 schema（可作为 quality metadata 的附属工作，但不作为独立任务）
- 角色声音 prompt block（需要 prompt engineering 投入，推迟）
- Polish pipeline 质量反馈循环（复杂度高，推迟）

#### MVP 约束

```text
不大改 UI（CandidatePanel 小幅扩展）
不破坏 candidate-only
可测试（mock E2E + backend tests）
可用真实 LLM dogfood 验证
不需要复杂评分模型
0 额外 LLM 开销（quality metadata 纯规则计算）
```

---

## 13. 后续任务拆分

### T9.4b：Quality Metadata MVP

**Risk Level**: Risk B  
**依赖**: 无

**工作内容**：
1. 新增 `CandidateQualityMetadata` schema（`backend/schemas/candidate.py`）
2. 新增 `compute_quality_metadata()` 函数（`backend/core/quality_metadata.py`）
3. Pipeline candidate 创建后自动调用（`backend/core/pipeline.py`）
4. CandidatePanel 增加 quality summary 行（`frontend/src/components/right-panel/CandidatePanel.vue`）
5. Backend tests: 覆盖 5 个维度的计算逻辑
6. Mock E2E: quality metadata 出现在 candidate list/detail 中

**验收标准**：
- quality metadata 在 candidate 创建时自动计算
- 5 个维度有正确值
- CandidatePanel 展示 quality summary
- 不阻断 adopt
- backend tests pass
- mock E2E pass

---

### T9.4c：Repair Candidate MVP

**Risk Level**: Risk A (new action type + new prompt template + new API endpoint)  
**依赖**: T9.4b（quality metadata 提供 repair targets）

**工作内容**：
1. 新增 `CandidateAction.REPAIR`（`backend/schemas/candidate.py`）
2. 新增 `CandidateRepairRequest` schema
3. 新增 `create_repair_candidate()` 方法（`backend/core/candidate_service.py`）
4. 新增 `repair.md` prompt template（`prompts/pipeline/candidate-repair/repair.md`）
5. 新增 API endpoint（`backend/api/candidates.py`）
6. Frontend: candidate 卡片增加"修复"按钮（仅有 warning 时显示）
7. Backend tests: repair candidate creation + lineage
8. Mock E2E: repair flow end-to-end

**验收标准**：
- 用户点击"修复"按钮，系统生成 repair candidate
- Repair candidate 有正确的 lineage（parent + group + index）
- Repair candidate 使用 repair prompt template
- 不自动覆盖正文
- 不自动修改 parent candidate
- backend tests pass
- mock E2E pass

---

### T9.4d：Real LLM Dogfood Set

**Risk Level**: Risk C  
**依赖**: T9.4b + T9.4c（dogfood case 6 依赖 repair）

**工作内容**：
1. 设计 6 个标准 dogfood cases（JSON 输入 + expected 输出）
2. 编写自动化验证脚本（Python，调用 API + 验证 expected）
3. 执行全部 6 cases
4. 记录结果

**验收标准**：
- 6 cases 全部 PASS（或 case 6 blocked by T9.4c 明确记录）
- 无 API key 泄露
- 无 candidate-only 违反
- 结果记录在文档中

---

### T9.4-final：Stage Closure

**Risk Level**: Risk C  
**依赖**: T9.4b + T9.4c + T9.4d

**工作内容**：
1. 回归测试（backend + mock E2E + focused E2E）
2. Real LLM dogfood 重跑
3. 阶段归档文档
4. 评估是否建议 v0.2.1

**验收标准**：
- 所有测试 pass
- Dogfood pass
- 归档文档完成
- 阶段 commit + push

---

### 任务顺序与理由

```text
T9.4b (Quality Metadata) → T9.4c (Repair Candidate) → T9.4d (Dogfood Set) → T9.4-final (Closure)
```

**理由**：
- T9.4b 是基础：quality metadata 为 repair candidate 提供 repair targets
- T9.4c 依赖 T9.4b：repair 需要知道哪些维度有 warning
- T9.4d 依赖 T9.4b + T9.4c：dogfood case 6 需要 repair 功能
- T9.4-final 收口所有

---

## 14. 是否建议 v0.2.1

**不建议在 T9.4 阶段创建 v0.2.1。**

理由：

1. **T9.4 是增量增强，不是 release 级别的功能**。Quality metadata 和 repair candidate 是在现有 candidate-only 框架内的优化，不构成新的 developer preview。
2. **v0.2.0 已在 T9.1 发布**，包含完整的 candidate workflow + beats + polish。T9.4 的增强可以在 v0.2.0 基础上作为 patch 发布，但建议等 T9 整体收口后再决定。
3. **如果 T9.4-final 验证通过**，且后续没有 T9.5，可以考虑在 T9.4-final 时打 v0.2.1 作为 T9 阶段的维护版 release。但这应该在 T9.4-final 时根据实际质量决定，不提前承诺。

**建议**：T9.4-final 时评估，如果质量稳定、dogfood pass、无阻断 bug，可以打 v0.2.1 tag。

---

## 15. 最终结论

### T9.4 的核心价值

T9.4 不引入新的 AI 能力，不改变 candidate-only 安全边界，不新增 prompt blocks。它的价值在于：

1. **让质量可观测**：用户第一次能在 adopt 前看到 candidate 的质量概况。
2. **让修复更快捷**：repair candidate 提供了"一键修复 warning"的快捷路径，与 feedback revision 互补。
3. **让验证更系统**：dogfood set 为后续每个阶段提供标准化的端到端验证基准。

### 安全边界不变

```text
AI 不自动覆盖正文
AI 不自动 adopt
AI 不自动修文（repair 是用户主动触发的）
repair 只生成 candidate
quality warning 只是 advisory
validator 不直接改文
candidate metadata 不包含 API key
SSE 不泄露完整正文 content
feedback revision child 不修改 parent
Continuity Anchors 不自动更新自身
```

### 推荐路径

```text
T9.4a (本文档) → T9.4b (Quality Metadata) → T9.4c (Repair Candidate) → T9.4d (Dogfood Set) → T9.4-final (Closure)
```

T9.4a 收口条件：本文档已提交，方向已确认，后续任务已拆分。
