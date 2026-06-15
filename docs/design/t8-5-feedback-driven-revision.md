# T8.5 Feedback-driven Revision Candidate Design

## 1. Background

T8.4 closed the first writing-quality loop for small-model generation:

- Professional generation can accept required beats and forbidden beats.
- Required / forbidden beats are conditionally assembled into the generation prompt.
- Candidate metadata can carry `beat_validation` with `pass`, `warning`, or `unknown`.
- CandidatePanel displays beat validation status.
- Warning candidates can still be adopted after user confirmation.
- Preview, adopt, and delete flows remain advisory and candidate-based.
- Slow LLM response, timeout, and `LLM_ERROR` states have clearer UI feedback.

The remaining gap is not automatic repair. The product needs a human-controlled way for the author to say what is wrong with a candidate and generate another candidate from that feedback.

## 2. T8.4 Completed Capabilities

The current system already has the correct safety base:

- High-risk writing operations create candidates instead of overwriting official scene files.
- Candidate adoption is explicit.
- Required beat warnings are advisory, not blocking.
- Candidate metadata can preserve generation context.
- The right panel can show candidate quality signals.
- The generation flow can pass extra variables into the prompt.

T8.5 should build on those capabilities rather than introducing a separate repair workflow.

## 3. Current Gap

When a candidate is weak, the user can currently preview, adopt, or delete it. They cannot directly say:

- "补上缺失的信息点。"
- "不要提前揭晓真相。"
- "保留开头，只改结尾。"
- "增强冲突，但不要新增人物。"

The system also has no candidate lineage for "this candidate was revised from that candidate because of this user feedback".

## 4. User Feedback Types

T8.5 should support three feedback categories.

### 4.1 Fix Warning

Used when beat validation or the author identifies concrete missing or forbidden content:

- 补上缺失的信息点
- 不要提前揭晓真相
- 不要新增人物或组织
- 保持结尾悬念
- 修复道具归属错误
- 修复人物状态错误

### 4.2 Improve Quality

Used when the draft is usable but not satisfying:

- 增强冲突
- 增加对白
- 减少解释
- 更有画面感
- 更像原文风格
- 节奏更快
- 情绪更克制

### 4.3 Local Constraint

Used when the user wants partial preservation:

- 保留开头
- 只改结尾
- 保留这段对白
- 不要改人物关系
- 不要改核心事实
- 不改变场景地点

## 5. Frontend Interaction Draft

### 5.1 Minimal Entry

Add one action to each candidate card:

```text
按反馈再生成
```

Recommended placement:

- In CandidatePanel action row, near preview / adopt / delete.
- Available for pending candidates in T8.5-mini.
- Later versions can allow adopted candidates or historical candidates to start a new revision chain.

### 5.2 Feedback Drawer / Modal

Clicking the action opens a lightweight panel:

```text
基于当前候选稿再生成

快捷反馈:
[补上缺失信息点] [不要提前揭晓] [增强冲突] [减少解释] [更像原文风格]

修改范围:
( ) 整个候选稿
( ) 保留开头
( ) 只改结尾

我的反馈:
[多行输入框]

选项:
[x] 继承本场必须出现的信息点
[x] 继承本场禁止出现/禁止揭晓的内容
[x] 生成后再次检查信息点

[生成新的候选稿]
```

The panel should also show the parent candidate warning summary when available:

```text
当前候选稿提示：发现 1 个可能缺失的信息点：第七层协议必须被提及。
```

### 5.3 Result Behavior

After submission:

1. The original candidate remains unchanged.
2. A new candidate is created.
3. The candidate list refreshes.
4. The new candidate is marked as "反馈再生成".
5. If beat validation ran, CandidatePanel shows pass / warning / unknown as today.
6. The user can preview, adopt, or delete the new candidate through the existing flow.

No official scene file is changed until the user adopts a candidate.

## 6. Backend Data Structure

### 6.1 Minimal API

Recommended endpoint:

```http
POST /api/candidates/{project_id}/{candidate_id}/revise
```

Request:

```json
{
  "feedback_text": "补上第七层协议，但不要揭晓完整真相。",
  "quick_actions": ["fix_missing_beats", "preserve_mystery"],
  "repair_scope": "full_candidate",
  "inherit_required_beats": true,
  "inherit_forbidden_beats": true,
  "run_beat_validation": true
}
```

Response:

```json
{
  "candidate_id": "cand_xxx",
  "source_path": "chapters/vol-01/ch-001/sec-001.md",
  "action": "feedback_revision",
  "status": "pending",
  "metadata": {
    "parent_candidate_id": "cand_parent",
    "generation_context": {
      "revision_type": "feedback_revision"
    }
  }
}
```

### 6.2 Backend Service Flow

```text
Load parent candidate
-> Load official source scene
-> Validate source_path and base hash / mtime
-> Build revision prompt from source, parent candidate, warnings, feedback, inherited beats
-> Generate revised draft
-> Run beat validator if enabled
-> Create new candidate with parent metadata
-> Emit candidate-created event
-> Return new candidate info
```

The service should reuse CandidateService and GenerationOutputPolicy. It must not write the official scene file directly.

## 7. Candidate Metadata Design

T8.5-mini should add provenance metadata without breaking existing candidate readers.

Recommended fields:

```json
{
  "parent_candidate_id": "cand_parent",
  "revision_group_id": "revgrp_20260615_xxx",
  "revision_index": 1,
  "generation_context": {
    "revision_type": "feedback_revision",
    "feedback_text": "补上第七层协议，但不要揭晓完整真相。",
    "quick_actions": ["fix_missing_beats", "preserve_mystery"],
    "repair_scope": "full_candidate",
    "inherited_required_beats": [
      {
        "id": "beat-1",
        "text": "第七层协议必须被提及"
      }
    ],
    "inherited_forbidden_beats": [
      {
        "id": "forbid-1",
        "text": "不能提前揭晓第七层协议完整真相"
      }
    ],
    "parent_beat_validation_status": "warning",
    "parent_beat_validation_summary": "发现 1 个可能缺失的信息点",
    "source_hash_at_revision": "sha256:...",
    "source_mtime_at_revision": 1234567890
  },
  "beat_validation": {
    "enabled": true,
    "status": "pass",
    "summary": "本场信息点检查通过"
  }
}
```

Notes:

- `parent_candidate_id` should be easy to query.
- `revision_group_id` allows future grouping of multiple attempts.
- `feedback_text` is user-authored provenance. Limit length, for example 1000 characters.
- Do not store raw prompts, API keys, or full provider responses in metadata.
- `beat_validation` remains advisory.

## 8. Prompt Assembly Strategy

The revision prompt should be facts-first and candidate-safe.

Recommended input blocks:

1. Official source scene: the current accepted text.
2. Parent candidate: the draft being revised.
3. Parent warning summary: missing beats or forbidden risks.
4. User feedback: free text and quick actions.
5. Required beats: inherited or newly supplied.
6. Forbidden beats: inherited or newly supplied.
7. Repair scope: full candidate, keep opening, ending only.
8. Output rule: only output revised scene text, not analysis.

Core instruction:

```text
You are revising a candidate draft, not editing the official scene directly.
Preserve all established facts unless the user explicitly asks to change them.
Fix the user's feedback without introducing new characters, organizations, items, locations, or timeline changes.
If required beats are provided, include them naturally.
If forbidden beats are provided, do not reveal or write them as facts.
Output only the revised candidate scene text.
```

To avoid fixing one error while introducing another, the prompt should explicitly include:

- immutable facts from the official scene;
- source path and scene identity;
- current character state;
- item ownership;
- location and time constraints;
- warning details from the parent candidate;
- a prohibition against inventing new explanations to satisfy a beat.

## 9. Risk Analysis

### High Risk

- A revision candidate may fix the warning but introduce a new continuity error.
- User feedback may contradict required beats or existing story facts.
- Parent candidate content may already contain wrong facts that the model repeats.

Mitigation:

- Use official source scene as the factual anchor.
- Re-run beat validation after generation.
- Keep candidate adoption manual.
- Preserve base hash / mtime checks at adopt time.

### Medium Risk

- Candidate list may become noisy if every feedback attempt creates another card.
- Users may confuse parent and child candidates.
- Feedback text can become too broad or vague.

Mitigation:

- Add a compact "来自 cand_xxx" badge.
- Sort child revisions near the parent candidate or show a small lineage label.
- Limit feedback length and provide quick feedback buttons.

### Low Risk

- Old candidates have no parent metadata.
- Unknown beat validation can still occur.

Mitigation:

- CandidatePanel should treat missing parent metadata as normal.
- Unknown validation remains advisory and should not block preview, adopt, or delete.

## 10. Minimal Implementation Order

### T8.5-mini

1. Add CandidatePanel action: "按反馈再生成".
2. Add feedback modal / drawer with quick actions, repair scope, and feedback textarea.
3. Add request type and API client call.
4. Add backend revise endpoint.
5. Add CandidateService helper to create a child revision candidate.
6. Assemble revision prompt from official source, parent candidate, feedback, and inherited beats.
7. Re-run beat validator when inherited beats exist or user chooses validation.
8. Refresh CandidatePanel after the new candidate is created.
9. Add E2E:
   - warning candidate -> feedback revision -> new candidate created;
   - parent candidate preserved;
   - new candidate preview / adopt / delete works;
   - official scene unchanged before adopt.

### T8.5.1

- Add side-by-side parent / child preview.
- Add revision grouping in CandidatePanel.
- Add selected-range repair support.
- Add better conflict messaging if source changed after parent candidate creation.

### Later

- Automatic repair suggestion, still not auto-adopt.
- Multi-candidate comparison.
- Human score node integration.
- Lite mode feedback revision entry.
- Memory update review after adopting revised candidate.

## 11. Acceptance Criteria

T8.5-mini is complete when:

1. A user can choose a candidate and enter feedback.
2. The system creates a new candidate instead of overwriting the official scene.
3. The original candidate remains visible and unchanged.
4. The new candidate records `parent_candidate_id`.
5. The new candidate records `feedback_text` and `repair_scope`.
6. Required / forbidden beats can be inherited into the revision prompt.
7. Beat validation runs again when enabled.
8. CandidatePanel can show the new candidate's beat validation status.
9. Preview / adopt / delete continue to use existing candidate safety rules.
10. Adoption still checks source base hash / mtime and writes revision log.

## 12. Out of Scope

T8.5-mini should not include:

- automatic repair;
- automatic adopt;
- direct official scene overwrite;
- Scene Plan;
- complex outline editor;
- required beats management UI beyond candidate feedback inheritance;
- full revision tree visualization;
- multi-model validation;
- memory auto-write after revision;
- changing LLM provider configuration.

## 13. Recommendation

Proceed with T8.5-mini as a small productization step.

The most valuable first version is not an automatic repair system. It is a safe, author-controlled loop:

```text
candidate warning
-> user feedback
-> new child candidate
-> validator advisory result
-> manual preview / adopt / delete
```

This keeps the current candidate safety model intact while giving users a practical way to improve weak drafts without losing earlier options.

