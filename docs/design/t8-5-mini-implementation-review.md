# T8.5-mini Feedback Revision Candidate Implementation Review

## 1. Background

T8.5 design has defined the next writing-quality loop:

```text
pending candidate -> user feedback -> child revision candidate -> manual preview / adopt / delete
```

This review checks the current codebase and proposes the smallest implementation plan. It does not change product code.

Baseline commit reviewed:

```text
286fad0 docs: design T8.5 feedback-driven revision
```

## 2. Current Capabilities

The codebase already has the key safety pieces needed by T8.5-mini:

- `backend/core/candidate_service.py`
  - Creates candidates under `.candidates/`.
  - Stores `base_hash` and `base_mtime`.
  - Stores `generation_context`, `continuity`, `source_type`, `scene_plan_hash`, `scene_plan_path`, and `beat_validation`.
  - Adopts only pending candidates.
  - Checks source hash / mtime before adopt.
  - Writes revision-log before replacing the source file.

- `backend/api/candidates.py`
  - Lists candidates.
  - Gets candidate detail and content.
  - Creates candidates.
  - Adopts candidates.
  - Deletes candidates.
  - Emits candidate created / adopted events.

- `backend/core/pipeline.py`
  - Creates candidates for high-risk scene output.
  - Normalizes legacy overwrite behavior.
  - Runs beat validation when `_enable_beat_validation=true`.
  - Emits `candidate_created` stream events.

- `frontend/src/components/right-panel/CandidatePanel.vue`
  - Lists candidate cards.
  - Shows action/status badges.
  - Shows beat validation pass / warning / unknown.
  - Supports preview / adopt / delete.
  - Shows adopt warning confirmation.

- `frontend/src/composables/useRequiredBeatsInput.ts`
  - Converts Professional right-panel multiline beats into `extra_vars.required_beats`, `extra_vars.forbidden_beats`, and `_enable_beat_validation=true`.

## 3. MVP Scope

T8.5-mini should only support:

```text
pending candidate -> feedback -> child revision candidate
```

It should not support:

- adopted candidate -> revision;
- discarded candidate -> revision;
- automatic repair;
- automatic adopt;
- direct official scene overwrite;
- selected-range rewrite;
- complex revision tree UI;
- Scene Plan;
- Lite integration.

## 4. Pending-only Decision

The MVP should expose "按反馈再生成" only when:

```text
candidate.status === "pending"
```

Reason:

- Adopted candidates may already have been written into the official scene.
- The official scene may have changed after adoption.
- The parent candidate may no longer represent the current source file.
- Supporting adopted candidates would require extra source/candidate diff semantics.
- Pending-only keeps the hash / mtime safety model simple.

Frontend behavior:

- Pending: show enabled action.
- Adopted / discarded / rejected: hide the action in T8.5-mini.
- Later versions may show disabled help text such as "已采用或已放弃的候选稿暂不支持反馈再生成".

Backend must also enforce this rule. UI-only restriction is insufficient.

## 5. Backend Implementation Plan

### 5.1 Files to Modify

Recommended backend files:

- `backend/schemas/candidate.py`
- `backend/core/candidate_service.py`
- `backend/api/candidates.py`
- `backend/core/beat_validator.py` only if helper extraction is needed
- New prompt file, recommended:
  - `prompts/pipeline/candidate-feedback/revise.md`

Tests:

- `backend/tests/test_candidate_service.py`
- New or extended API tests, for example:
  - `backend/tests/test_candidate_revision_api.py`

### 5.2 New Schema

Add request / response schema:

```python
class CandidateRevisionRequest(BaseModel):
    feedback_text: str
    quick_actions: list[str] = Field(default_factory=list)
    repair_scope: str = "full_candidate"
    inherit_required_beats: bool = True
    inherit_forbidden_beats: bool = True
    run_beat_validation: bool = True
```

Validation:

- `feedback_text` required after trimming.
- Max feedback length: 1000 characters.
- `quick_actions` allowlist:
  - `fix_missing_beats`
  - `preserve_mystery`
  - `avoid_new_entities`
  - `keep_style`
  - `increase_conflict`
  - `reduce_exposition`
- `repair_scope` allowlist:
  - `full_candidate`
  - `keep_opening`
  - `ending_only`

### 5.3 Candidate Action / Source Type

Recommended action:

```python
CandidateAction.FEEDBACK_REVISION = "feedback_revision"
```

Alternative:

- Reuse `CandidateAction.MODIFY`.
- Store `generation_context.revision_type = "feedback_revision"`.

Recommendation:

- Add `feedback_revision`.
- It makes CandidatePanel, tests, and future analytics clearer.
- `source_type` should remain `"llm"` or `"dry-run"` and should not encode revision type.

### 5.4 Candidate Metadata Fields

Add optional top-level fields to `CandidateInfo`:

```python
parent_candidate_id: str | None = None
revision_group_id: str | None = None
revision_index: int = 0
```

Keep detailed provenance inside `generation_context`:

```json
{
  "revision_type": "feedback_revision",
  "parent_candidate_id": "cand_parent",
  "feedback_text": "加强冲突，不要新增人物",
  "quick_actions": ["increase_conflict", "avoid_new_entities"],
  "repair_scope": "full_candidate",
  "source_candidate_action": "rewrite",
  "source_candidate_status_at_revision": "pending",
  "source_candidate_beat_validation_status": "warning",
  "inherited_required_beats": [
    { "id": "beat-1", "text": "第七层协议必须被提及" }
  ],
  "inherited_forbidden_beats": [
    { "id": "forbid-1", "text": "不能提前揭晓第七层协议完整真相" }
  ]
}
```

Why both top-level and `generation_context`:

- Top-level `parent_candidate_id` is easy for UI and future filtering.
- `generation_context` keeps the full revision provenance without expanding the main schema too much.

### 5.5 CandidateService Method

Add a focused service method:

```python
async def create_feedback_revision_candidate(
    self,
    project_id: str,
    parent_candidate_id: str,
    feedback_text: str,
    quick_actions: list[str],
    repair_scope: str,
    llm_service: LLMService,
    inherit_required_beats: bool = True,
    inherit_forbidden_beats: bool = True,
    run_beat_validation: bool = True,
) -> CandidateInfo:
```

Responsibilities:

1. Load parent candidate.
2. Reject if parent is missing.
3. Reject if parent status is not pending.
4. Load parent candidate content.
5. Load official source scene content from `parent.source_path`.
6. Extract inherited required / forbidden beats.
7. Render revision prompt.
8. Call LLM.
9. Run beat validator when enabled.
10. Create child candidate with `CandidateAction.FEEDBACK_REVISION`.
11. Preserve parent candidate unchanged.

Important:

- This method must not call `adopt_candidate`.
- This method must not write to the source scene file.
- This method should call existing `create_candidate()` so base hash / mtime are captured from current source.

## 6. Frontend Implementation Plan

### 6.1 Files to Modify

Recommended frontend files:

- `frontend/src/components/right-panel/CandidatePanel.vue`
- `frontend/src/shared/api/types.ts`
- `frontend/src/shared/api/routes.ts`
- `frontend/src/modules/candidate/api.ts` if the module path is used consistently

Optional extraction if CandidatePanel becomes too large:

- New component:
  - `frontend/src/components/right-panel/CandidateFeedbackRevisionModal.vue`
- Or composable:
  - `frontend/src/modules/candidate/useCandidateRevision.ts`

MVP recommendation:

- Add a small modal component if the edit in `CandidatePanel.vue` grows beyond roughly 100 lines.
- Keep API call centralized in `frontend/src/modules/candidate/api.ts` or `API_ROUTES`.

### 6.2 CandidatePanel UI

Add an action button for pending candidates:

```text
按反馈再生成
```

Minimal modal:

```text
基于当前候选稿再生成

快捷反馈:
[补上缺失信息点] [不要新增人物] [保持原文风格] [加强冲突] [减少解释]

修改范围:
[整个候选稿] [保留开头] [只改结尾]

告诉 AI 你想怎么改:
[textarea]

[生成新的候选稿] [取消]
```

Submit behavior:

- Disable submit while request is running.
- Require either feedback text or at least one quick action.
- On success:
  - close modal;
  - refresh candidate list;
  - show success notice;
  - keep original candidate unchanged.
- On failure:
  - show friendly error;
  - keep modal open if possible.

### 6.3 Candidate Labels

Add label mapping:

```ts
feedback_revision: '反馈再生成'
```

Add optional parent badge:

```text
来自 cand_xxx
```

For MVP, showing the parent badge is useful but not required for correctness.

## 7. API Decision

### Option A: Reuse `POST /api/pipeline/run`

Pros:

- No new endpoint.
- Existing SSE streaming path already works.
- Existing candidate creation path can be reused.

Cons:

- Pipeline request has no natural parent candidate identity.
- Pending-only validation belongs to candidate domain, not pipeline domain.
- Parent candidate content loading would have to be smuggled through `extra_vars`.
- `parent_candidate_id`, `feedback_text`, and revision lineage metadata would be awkward.
- Inheriting beats from parent candidate metadata would require pipeline to understand candidate internals.
- Harder to keep official source and parent candidate as separate prompt inputs.

### Option B: Add `POST /api/candidates/{project_id}/{candidate_id}/revise`

Pros:

- Clear candidate-domain semantics.
- Enforces pending-only at backend.
- Can load parent candidate and source scene safely.
- Can create child candidate with first-class lineage metadata.
- Avoids overloading `pipeline/run`.
- Easier to test without streaming complexity.

Cons:

- New API contract.
- New request / response types.
- Need one new prompt template or service prompt renderer.

### Recommendation

Use Option B for T8.5-mini:

```http
POST /api/candidates/{project_id}/{candidate_id}/revise
```

The endpoint can internally reuse:

- `CandidateService`;
- `LLMService`;
- `FileService`;
- `RequiredBeatValidator`;
- existing candidate-created event.

It should not reuse the generic pipeline entry for MVP.

## 8. Prompt Assembly Plan

Recommended new prompt:

```text
prompts/pipeline/candidate-feedback/revise.md
```

Inputs:

- `official_source_text`
- `parent_candidate_text`
- `feedback_text`
- `quick_actions`
- `repair_scope`
- `required_beats`
- `forbidden_beats`
- `parent_beat_validation_summary`
- `parent_beat_validation_details`

Prompt rules:

```text
基于父候选稿修改，而不是直接改正式正文。
以正式正文作为事实锚点。
遵守用户反馈。
保留已经满足的信息点。
不要新增人物、组织、道具、地点或时间线设定。
不要提前揭晓 forbidden beats。
输出完整修订候选稿正文，不输出解释、评分或 Markdown 元信息。
```

Repair scope handling:

- `full_candidate`: revise the full parent candidate.
- `keep_opening`: preserve the opening paragraph unless it directly violates feedback.
- `ending_only`: keep most of the parent candidate, only rewrite the ending section.

## 9. Required Beats Inheritance

### What Exists Today

Current pipeline creates `beat_validation` from `extra_vars` when validation is enabled. The stored `beat_validation` contains normalized required / forbidden items with text and status.

Current `generation_context` records Scene Plan provenance, but it does not reliably store the original `required_beats` / `forbidden_beats` request inputs.

### MVP Inheritance Strategy

Use this priority:

1. Prefer `parent.generation_context.required_beats_input` and `parent.generation_context.forbidden_beats_input` if present.
2. Fall back to `parent.beat_validation.required_beats[].text`.
3. Fall back to `parent.beat_validation.forbidden_beats[].text`.
4. If no beats exist, revision still works but does not enable validator unless the request provides beats later.

### Recommended Small Schema Enhancement

When any future candidate is created with beat validation enabled, store original beat inputs in `generation_context`:

```json
{
  "required_beats_input": [
    { "id": "beat-1", "text": "第七层协议必须被提及" }
  ],
  "forbidden_beats_input": [
    { "id": "forbid-1", "text": "不能提前揭晓第七层协议完整真相" }
  ]
}
```

This should be added alongside T8.5-mini if the implementation touches candidate creation metadata. It improves inheritance without changing validator behavior.

## 10. Risks

### High Risk

- Revision fixes a warning but introduces a new story continuity error.
- Parent candidate already contains wrong facts and the model copies them.
- User feedback contradicts established facts or inherited beats.

Mitigation:

- Always include official source scene as the factual anchor.
- Include parent candidate as draft, not authority.
- Re-run beat validation.
- Keep adopt manual and protected by base hash / mtime.

### Medium Risk

- CandidatePanel becomes too large.
- Candidate list becomes noisy with child revisions.
- Old candidates do not have generation lineage.

Mitigation:

- Extract modal if CandidatePanel grows too much.
- Add compact parent badge.
- Treat missing parent metadata as normal.

### Low Risk

- Validator returns unknown.
- Feedback text too vague.

Mitigation:

- Keep unknown advisory.
- Provide quick feedback buttons.

## 11. Test Plan

### Backend Unit / API Tests

Add tests for:

1. Pending parent candidate can create child revision candidate.
2. Adopted parent candidate cannot create revision candidate.
3. Discarded parent candidate cannot create revision candidate.
4. Child candidate preserves parent candidate unchanged.
5. Child candidate source_path equals parent source_path.
6. Child candidate action is `feedback_revision`.
7. Child candidate stores `parent_candidate_id`.
8. Child candidate stores `feedback_text` and `repair_scope`.
9. Child candidate records base hash / mtime from current official source.
10. Required / forbidden beats inherit from parent metadata or beat_validation.
11. Beat validator failure creates candidate with `beat_validation.status = unknown`.
12. LLM failure returns a clear error and creates no child candidate.

Recommended command:

```powershell
python -m pytest backend/tests/test_candidate_service.py backend/tests/test_candidate_revision_api.py backend/tests/test_beat_validator.py -q --tb=short
```

### Frontend / Browser E2E

Add E2E for:

1. Pending candidate shows "按反馈再生成".
2. Adopted / discarded candidates do not show the action.
3. Clicking action opens feedback modal.
4. Empty feedback and no quick action cannot submit.
5. Feedback submit calls revise API.
6. New child candidate appears in CandidatePanel.
7. Parent candidate remains visible and unchanged.
8. Child candidate preview works.
9. Child candidate adopt works through existing warning / conflict flow.
10. Child candidate delete works.
11. Required beat warning parent can generate a child that also has beat validation metadata.

Recommended commands:

```powershell
cd frontend
npm run build
npm run test:e2e:mock
```

## 12. Recommended Implementation Order

1. Add backend schemas for revision request and optional lineage fields.
2. Add `CandidateAction.FEEDBACK_REVISION`.
3. Add `CandidateService.create_feedback_revision_candidate()`.
4. Add prompt template `prompts/pipeline/candidate-feedback/revise.md`.
5. Add `POST /api/candidates/{project_id}/{candidate_id}/revise`.
6. Emit candidate-created event after child candidate creation.
7. Add backend tests.
8. Add frontend API route and types.
9. Add CandidatePanel feedback action and modal.
10. Add frontend build and browser E2E.
11. Update `docs/contracts/candidate-contract.md` and `docs/frontend-user-flow.md` after implementation.

## 13. Files Expected to Change During Implementation

Backend:

- `backend/schemas/candidate.py`
- `backend/core/candidate_service.py`
- `backend/api/candidates.py`
- `prompts/pipeline/candidate-feedback/revise.md`
- `backend/tests/test_candidate_revision_api.py`
- Possibly `backend/tests/test_candidate_service.py`

Frontend:

- `frontend/src/components/right-panel/CandidatePanel.vue`
- `frontend/src/shared/api/types.ts`
- `frontend/src/shared/api/routes.ts`
- `frontend/src/modules/candidate/api.ts`
- Possibly `frontend/src/components/right-panel/CandidateFeedbackRevisionModal.vue`

Docs after implementation:

- `docs/contracts/candidate-contract.md`
- `docs/frontend-user-flow.md`

## 14. Recommendation

T8.5-mini is ready to enter code implementation.

Recommended technical decision:

```text
Add a dedicated candidate revise API.
Create a child candidate with action=feedback_revision.
Persist parent_candidate_id and feedback metadata.
Inherit beats from generation_context first, beat_validation second.
Keep the feature pending-only.
Do not reuse generic pipeline/run for MVP.
```

This keeps the feature small, testable, and aligned with the existing candidate safety model.

