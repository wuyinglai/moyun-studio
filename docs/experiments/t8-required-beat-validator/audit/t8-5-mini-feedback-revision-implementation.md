# T8.5-mini Feedback Revision Candidate Implementation

## 1. Background

T8.4 completed the writing-quality loop for required / forbidden beats:
generation prompt injection, candidate metadata, warning display, preview,
adopt, delete, and slow/error UX. T8.5-mini adds the smallest next loop:

```text
pending candidate -> user feedback -> child revision candidate
```

This is not automatic repair and does not adopt or overwrite official scene
files.

## 2. Implementation Scope

Implemented:

- Dedicated candidate revision API.
- Pending-only backend enforcement.
- Parent candidate content and current source scene loading.
- User feedback and quick actions passed into a revision prompt.
- Child candidate creation with lineage metadata.
- Required / forbidden beat inheritance from parent metadata.
- Optional beat validation rerun for the child candidate.
- CandidatePanel entry and feedback modal for pending candidates.
- Candidate list refresh after child candidate creation.

Not implemented:

- Adopted / discarded / rejected candidate revision.
- Automatic repair.
- Automatic adopt.
- Scene Plan integration.
- Revision tree UI.
- Lite-specific feedback revision entry.

## 3. API

```http
POST /api/candidates/{project_id}/{candidate_id}/revise
```

Request:

```json
{
  "feedback_text": "加强冲突，不要新增人物",
  "quick_actions": ["increase_conflict", "avoid_new_entities"],
  "repair_scope": "full_candidate",
  "inherit_required_beats": true,
  "inherit_forbidden_beats": true,
  "run_beat_validation": true
}
```

Rules:

- Empty `feedback_text` plus empty `quick_actions` returns `400`.
- Missing parent returns `404`.
- Non-pending parent returns `409`.
- LLM empty output returns `502`.
- Success returns the child `CandidateInfo`.

## 4. Candidate Metadata

Child candidates use:

```text
action = feedback_revision
source_type = llm
parent_candidate_id = cand_xxx
revision_group_id = revgrp_xxx
revision_index = 1..n
```

`generation_context` records:

- `revision_type: feedback_revision`
- `parent_candidate_id`
- `feedback_text`
- `quick_actions`
- `repair_scope`
- `source_candidate_action`
- `source_candidate_status_at_revision`
- `source_candidate_beat_validation_status`
- `required_beats_input`
- `forbidden_beats_input`

The parent candidate is not modified.

## 5. Prompt Strategy

New prompt:

```text
prompts/pipeline/candidate-feedback/revise.md
```

The prompt treats the current official scene as the factual anchor and the
parent candidate as the draft to revise. It instructs the model to output only
the complete revised candidate body, with no explanation, scoring, or metadata.

## 6. Required Beats Inheritance

Inheritance priority:

1. `parent.generation_context.required_beats_input`
2. `parent.generation_context.inherited_required_beats`
3. `parent.beat_validation.required_beats`
4. Equivalent forbidden beat fields

The child candidate stores inherited beat inputs back into `generation_context`.
If beats are present and validation is enabled, the child candidate runs the
required beat validator again.

## 7. Frontend UI

`CandidatePanel` now shows "按反馈再生成" only for `pending` candidates.

The modal contains:

- Parent candidate identifier and action label.
- Parent beat warning summary if present.
- Quick feedback buttons.
- Free-text feedback textarea.
- Repair scope selector.
- Submit button that creates a child candidate.

On success, the modal closes, the candidate list refreshes, and the new child
candidate is selected. The official scene remains unchanged until the user
uses the existing adopt flow.

## 8. Backend Tests

Added:

```text
backend/tests/test_candidate_feedback_revision.py
```

Coverage:

- Pending parent creates a child candidate.
- Parent candidate remains pending and unchanged.
- Official source scene is not overwritten.
- Child metadata includes parent lineage and feedback fields.
- Required / forbidden beats are inherited.
- Non-pending parent is rejected.
- API rejects empty feedback.
- API rejects adopted parent with `409`.

## 9. Browser E2E

Mock browser E2E was added to:

```text
frontend/tests/e2e/14-candidate-workflow.spec.ts
```

Covered:

- pending candidate shows the "按反馈再生成" action;
- clicking the action opens the feedback modal;
- empty direct overwrite is not involved;
- submitting feedback calls the revision API;
- child `feedback_revision` candidate appears in the CandidatePanel;
- existing preview / adopt / delete candidate tests still pass.

Command result:

```text
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
7 passed
```

The full Playwright suite was attempted once and timed out after 3 minutes
without useful failure output, so the focused candidate workflow spec was used
for this T8.5-mini validation pass.

## 10. Risks

- The revision model may satisfy user feedback but introduce new continuity
  errors. The official source is included as factual anchor, and adoption
  remains manual.
- CandidatePanel continues to grow; if later revisions add more controls,
  extract a dedicated modal component.
- Existing old candidates may not contain original beat inputs; fallback to
  `beat_validation` preserves best-effort inheritance.

## 11. Next Step Recommendation

Proceed to browser E2E for T8.5-mini, then consider a small UI polish pass if
the modal feels crowded. Do not implement automatic repair until feedback
revision has been validated with real users and real LLM output.
