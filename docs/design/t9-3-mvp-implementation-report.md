# T9.3 Continuity Anchors MVP Implementation Report

## 1. Current Commit

Base commit before implementation:

```text
a8befb0 docs: design T9.3 continuity anchors
```

This report documents the T9.3 MVP implementation of user-controlled Continuity Anchors.

## 2. Implementation Scope

T9.3 adds a minimal closed loop for long-form continuity constraints:

- A project-level `continuity-anchors.json` document.
- Backend schema, service, and GET/PUT API.
- Active-anchor filtering for generation-time prompt assembly.
- Prompt block injection for generate, rewrite, polish, Lite continuation, and feedback revision.
- Candidate metadata recording which anchors were used.
- A minimal Professional right-panel UI for adding and archiving anchors.
- CandidatePanel display of the number of anchors used.
- Backend and focused E2E coverage.

The implementation keeps the existing candidate-first safety boundary: anchors guide generation, but do not automatically modify official scene files, adopt candidates, repair drafts, or update story state.

## 3. Data Structure

The MVP anchor document is:

```json
{
  "version": 1,
  "anchors": [
    {
      "id": "anchor-character-001",
      "type": "character_state",
      "title": "Heroine right shoulder injury",
      "content": "The heroine's right shoulder is injured and she cannot use her right hand to wield a sword.",
      "scope": "global",
      "status": "active",
      "priority": "high",
      "source": "user",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

Supported MVP fields:

- `type`: `character_state`, `plot_clue`, `object_location`, `relationship`, `world_rule`.
- `scope`: `global`, `chapter`, `scene`, `character`.
- `status`: `active`, `resolved`, `archived`.
- `priority`: `high`, `normal`, `low`.
- `source`: currently `user`.

Only `active` anchors are injected into prompts and counted in candidate metadata.

## 4. Storage

Continuity anchors are stored at the project root:

```text
continuity-anchors.json
```

The file is intentionally placed beside `story-state.md` and `recent-context.md`, because it is project-level writing memory rather than a single scene artifact.

Missing files return:

```json
{
  "version": 1,
  "anchors": []
}
```

All reads and writes go through `FileService`; no direct path concatenation is introduced.

## 5. Service / API

Backend additions:

- `backend/schemas/continuity_anchor.py`
- `backend/core/continuity_anchor_service.py`
- `backend/api/continuity_anchors.py`

New API endpoints:

```text
GET /api/projects/{project_id}/continuity-anchors
PUT /api/projects/{project_id}/continuity-anchors
```

The service supports:

- `read_document`
- `write_document`
- `list_active`
- `prompt_items`
- `metadata`

Invalid anchor documents raise a validation error. Archived and resolved anchors are filtered out before prompt assembly.

## 6. Prompt Assembly

New prompt block:

```text
prompts/blocks/continuity-anchors.md
```

It is conditionally rendered only when `continuity_anchor_items` exists. Empty anchor sets do not pollute the final prompt.

Injected prompt locations:

- `prompts/pipeline/generate/write.md`
- `prompts/pipeline/generate/write_facts_first.md`
- `prompts/pipeline/rewrite/draft.md`
- `prompts/pipeline/polish/prose.md`
- `prompts/pipeline/candidate-feedback/revise.md`
- `prompts/generate/continuation/main.md`

Anchors are treated as long-term continuity constraints. They are separate from required beats, which remain the current-scene task requirements.

## 7. Candidate Metadata

Candidate metadata now supports:

```json
{
  "continuity_anchors": {
    "enabled": true,
    "used_count": 2,
    "anchor_ids": ["anchor-1", "anchor-2"],
    "types": {
      "character_state": 1,
      "object_location": 1
    }
  }
}
```

Only IDs, counts, and type counts are stored. Full anchor content is not duplicated into candidate metadata.

Coverage includes:

- Pipeline-generated candidates.
- High-risk overwrite fallback candidates.
- Feedback revision child candidates.
- Lite candidate fallback / streaming candidate paths.

Official scene files are not changed by anchor metadata.

## 8. UI MVP

The Professional right panel now has a minimal Continuity Anchors area near the required / forbidden beats inputs.

The MVP UI supports:

- Loading anchors for the current project.
- Showing active anchor count.
- Adding a user anchor.
- Selecting type and priority.
- Archiving an anchor.
- Safe empty state for old projects without anchors.

Defaults:

- `scope = global`
- `source = user`
- `status = active`

The UI copy states that anchors enter generation constraints and do not automatically modify official prose.

## 9. CandidatePanel Display

CandidatePanel shows the count when a candidate records anchor usage:

```text
连续性锚点：已使用 N 条
```

Old candidates without `continuity_anchors` metadata remain compatible and do not crash the panel.

## 10. Tests

Backend tests added:

```text
backend/tests/test_continuity_anchors.py
```

Focused coverage includes:

- Missing anchors file returns an empty document.
- Valid read/write and active filtering.
- Invalid document rejection.
- GET/PUT API behavior.
- Prompt block conditional rendering.
- Pipeline candidate metadata.
- Feedback revision child metadata.
- Source scene content is not overwritten by anchor flow.

Frontend / E2E coverage added:

- `frontend/tests/e2e/32-continuity-anchors.spec.ts`
- CandidatePanel anchor-count assertion in `frontend/tests/e2e/14-candidate-workflow.spec.ts`

Focused UI coverage includes:

- Old project without anchors opens the quick panel safely.
- User can add and archive an active continuity anchor.
- CandidatePanel displays `continuity_anchors.used_count`.

## 11. Not Implemented

T9.3 intentionally does not implement:

- Automatic anchor extraction from prose.
- Automatic story-state updates.
- Automatic repair.
- Automatic adopt.
- Scene Plan integration.
- Relationship graphs.
- Complex knowledge-base editing.
- Multi-model arbitration.
- Anchor validator.

These remain future work and should not be inferred from this MVP.

## 12. Test Results

Commands run during implementation:

```text
python -m py_compile backend/main.py backend/api/continuity_anchors.py backend/core/continuity_anchor_service.py backend/core/pipeline.py backend/core/candidate_service.py backend/schemas/continuity_anchor.py backend/schemas/candidate.py
```

Result: passed.

```text
python -m pytest backend/tests/test_beat_validator.py backend/tests/test_candidate_feedback_revision.py backend/tests/test_pipeline.py backend/tests/test_continuity_anchors.py -q --tb=short
```

Result: `92 passed`.

```text
cd frontend
npm run build
```

Result: passed.

```text
npm run test:e2e:mock -- tests/e2e/32-continuity-anchors.spec.ts --reporter=line
```

Result: `2 passed`.

```text
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

Result: `23 passed`.

```text
npm run test:e2e:mock -- --reporter=line
```

First run: one unrelated Scene Plan panel mount flake. The same spec passed when run directly.

Second run: `77 passed / 93 skipped / 0 failed`.

## 13. Remaining Issues

- The Continuity Anchors UI is intentionally minimal. It supports add/archive, but not rich editing, search, grouping, or conflict analysis.
- Anchor scope is stored, but MVP prompt injection treats active anchors as project-level constraints.
- No automatic extraction exists; users must explicitly add anchors.
- No anchor validator exists; the current implementation records usage, not whether the model obeyed each anchor.

## 14. Recommendation

T9.3 MVP can be accepted as the base closed loop.

Recommended next step:

```text
T9.3-final: focused regression and UX polish
```

Potential follow-up polish items:

- Add edit-in-place for existing anchors.
- Add scope-aware filtering.
- Add a small prompt debug smoke showing anchors in final prompt.
- Add manual dogfood with real LLM to evaluate whether anchors improve continuity.
