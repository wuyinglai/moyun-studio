# T8.5-mini Final Regression Report

## 1. Background

Baseline commit:

```text
b6088bd feat: add feedback revision candidates
```

This verification checks the T8.5-mini feedback revision candidate flow:

```text
pending parent candidate -> user feedback -> child revision candidate
```

The flow must not auto-adopt, must not overwrite official scene text, and must
preserve the existing candidate safety model.

## 2. Pending Parent Revision

Status: passed.

Verified by:

```text
backend/tests/test_candidate_feedback_revision.py::test_feedback_revision_creates_child_candidate_without_touching_parent
```

The test creates a pending parent candidate, calls the feedback revision service,
and verifies that a new child candidate is created with:

- `action=feedback_revision`
- `status=pending`
- same `source_path` as the parent
- a different candidate id
- persisted child content

## 3. Non-pending Parent Rejection

Status: passed.

Verified by:

```text
backend/tests/test_candidate_feedback_revision.py::test_feedback_revision_rejects_non_pending_parent
backend/tests/test_candidate_feedback_revision.py::test_candidate_revision_api_rejects_adopted_parent
```

The service rejects non-pending parents with `PARENT_NOT_PENDING`; the API maps
an adopted parent to HTTP `409`.

The MVP intentionally does not support adopted, discarded, or rejected parent
candidate revision.

## 4. Empty Feedback Rejection

Status: passed.

Verified by:

```text
backend/tests/test_candidate_feedback_revision.py::test_candidate_revision_api_rejects_empty_feedback
```

When both `feedback_text` and `quick_actions` are empty, the API returns `400`
and no child candidate is created.

## 5. Parent Preservation

Status: passed.

The regression test verifies that after child creation:

- parent candidate status remains `pending`;
- parent candidate content is not modified;
- official source scene content remains unchanged.

## 6. Child Candidate Safety

Status: passed.

Child candidates:

- default to `pending`;
- do not auto-adopt;
- do not overwrite `source_path`;
- must still go through existing preview / adopt / delete paths.

Adoption remains protected by the existing candidate adopt checks.

## 7. Child Metadata

Status: passed.

The regression test verifies child metadata includes:

- `parent_candidate_id`
- `revision_group_id`
- `revision_index`
- `generation_context.revision_type=feedback_revision`
- `generation_context.feedback_text`
- `generation_context.quick_actions`
- `generation_context.repair_scope`

## 8. Required / Forbidden Beats Inheritance

Status: passed.

The regression test creates a parent candidate with:

- `generation_context.required_beats_input`
- `generation_context.forbidden_beats_input`

The child candidate inherits these into its own `generation_context`, preserving
the information needed for subsequent validation and audits.

## 9. Beat Validator Re-run

Status: covered by implementation and related regression set.

The service reruns the required beat validator when inherited beats exist and
`run_beat_validation=true`. Validator failures are handled by
`RequiredBeatValidator` as `status=unknown`, so candidate creation is not blocked
by validator parse or LLM failures.

Related tests:

```text
backend/tests/test_beat_validator.py
```

## 10. LLM Failure Recovery

Status: partially covered.

The implementation rejects empty LLM output with `EMPTY_REVISION_CONTENT`, which
the API maps to HTTP `502`. The current focused regression suite does not add a
separate LLM exception test, but the service does not write a child candidate
until after the LLM returns non-empty content.

Recommended follow-up: add a service/API test where `complete_sync` raises an
exception and confirm no child metadata entry is created.

## 11. Frontend E2E

Status: passed.

Command:

```text
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

Result:

```text
7 passed
```

Covered:

- CandidatePanel loads existing candidates.
- Safety notice remains visible.
- Pending candidate shows "按反馈再生成".
- Feedback modal opens.
- Feedback submission calls the revision API.
- New child `feedback_revision` candidate appears.
- Existing preview, adopt, and delete tests still pass.

## 12. Preview / Adopt / Delete

Status: passed.

Focused E2E confirms existing candidate preview, adopt, and delete workflows
still work after adding the feedback revision entry.

## 13. Old Candidate Compatibility

Status: passed through focused E2E and existing candidate service regression.

Existing candidates without feedback revision metadata remain visible and usable.
The new action is only rendered for `pending` candidates.

## 14. Commands Run

```text
python -m pytest backend/tests/test_candidate_feedback_revision.py -v
```

Result:

```text
4 passed
```

```text
python -m pytest backend/tests/test_candidate_service.py backend/tests/test_beat_validator.py backend/tests/test_pipeline.py -q --tb=short
```

Result:

```text
73 passed
```

```text
cd frontend
npm run build
```

Result:

```text
passed
```

```text
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

Result:

```text
7 passed
```

## 15. Bugs Found

None in this final regression pass.

## 16. Remaining Issues

- Full Playwright suite was not rerun in this pass. The previous implementation
  pass observed a full-suite timeout; the focused candidate workflow E2E is the
  required gate for this task and passed.
- LLM exception recovery should get one explicit no-child-created unit test in a
  future hardening pass.

## 17. Recommendation

T8.5-mini can be formally closed.

The implemented loop preserves the candidate safety model:

```text
feedback creates a new candidate; only adopt can update official scene text.
```

Recommended next step: T8.5.1 browser polish and additional failure-path unit
tests, without changing the core product behavior.
