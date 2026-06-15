# T8.6 Feedback Revision Stabilization Report

## Background

T8.5-mini introduced feedback-driven revision candidates:

```text
pending parent candidate -> user feedback -> child revision candidate
```

T8.6 focuses on UX and safety hardening for that flow. The goal is not to add automatic repair or auto-adopt. A feedback revision must remain a safe child candidate until the user previews and adopts it.

Baseline commit:

```text
fcff072 docs: add T8.5 mini final regression report
```

## Scope

Validated and hardened:

- LLM failure safety for revision generation.
- Multi-round revision lineage.
- CandidatePanel revision source display.
- Feedback modal UX and validation.
- Required / forbidden beats inheritance visibility.
- Old candidate compatibility.
- Focused browser E2E coverage for candidate workflow.

Out of scope:

- Automatic repair.
- Repair candidate background jobs.
- Auto-adopt.
- Adopted candidate revision.
- Scene Plan changes.
- Core save/hash/FILE_CONFLICT changes.

## Fixes

### LLM Failure Safety

`CandidateService.create_feedback_revision_candidate()` now catches revision LLM exceptions before creating the child candidate and raises `REVISION_LLM_FAILED`.

The API maps that failure to HTTP 502 with a clear revision-specific message.

Verified:

- No child metadata is created on LLM failure.
- Parent candidate status and metadata remain unchanged.
- Official source scene remains unchanged.
- Retrying after failure can create a normal child candidate.

### Multi-round Revision Lineage

Revision index calculation now uses the whole `revision_group_id` lineage instead of only direct children of the current parent.

Verified:

```text
A -> B -> C
B.parent_candidate_id = A
C.parent_candidate_id = B
B.revision_group_id = C.revision_group_id
B.revision_index = 1
C.revision_index = 2
```

### API Retry Safety

The frontend API request interceptor no longer resets `__retryCount` on each retry. This prevents persistent 5xx errors from keeping UI actions in an indefinite loading state.

Verified with focused E2E:

- Revision request receives repeated 502 responses.
- Modal remains open.
- Controls recover after retry exhaustion.
- User can retry and generate a child candidate.

### CandidatePanel UX

CandidatePanel now shows feedback revision provenance for child candidates:

- Feedback revision badge.
- Revision index.
- Parent candidate id.
- Feedback summary.

The feedback modal now includes:

- More specific placeholder.
- Disabled submit when feedback and quick actions are empty.
- 1000-character feedback limit and hint.
- Extra quick action: enhance imagery.
- Loading state preserved.
- Failed generation keeps the modal open.
- Successful generation closes the modal and selects the new child.

### Required Beats Inheritance Visibility

When a parent candidate has required or forbidden beats, the revision modal shows the count of inherited checks. Child candidate metadata continues to store inherited beats and rerun beat validation when enabled.

## Browser E2E Coverage

Focused candidate workflow E2E now covers 12 scenarios:

1. Open CandidatePanel and list candidates.
2. Safety notice: candidates do not auto-overwrite official text.
3. Pending parent can generate a child revision candidate.
4. CandidatePanel load does not emit user-visible list errors.
5. Preview remains safe.
6. Adopt remains available.
7. Delete/discard remains available.
8. Empty feedback with no quick action disables revision submit.
9. Adopted candidate does not expose feedback revision action.
10. Feedback revision displays source, revision index, and feedback summary.
11. LLM failure keeps modal open and allows retry.
12. Parent required/forbidden beats show inheritance count.

## Backend Regression Coverage

`backend/tests/test_candidate_feedback_revision.py` now covers:

- Pending parent creates child without touching parent/source.
- Adopted, discarded, and rejected parents reject revision.
- LLM failure does not create child.
- Retry after LLM failure succeeds.
- Multi-round A -> B -> C lineage.
- Required/forbidden beats inheritance and validator rerun.
- Empty feedback API rejection.
- Adopted parent API rejection.

## Commands Run

```powershell
python -m pytest backend/tests/test_candidate_feedback_revision.py -v
python -m pytest backend/tests/test_candidate_service.py backend/tests/test_beat_validator.py backend/tests/test_pipeline.py -q --tb=short
cd frontend
npm run build
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
cd ..
```

## Results

- `backend/tests/test_candidate_feedback_revision.py`: 10 passed.
- Candidate / beat validator / pipeline regression tests: 73 passed.
- Frontend build: passed.
- Focused candidate workflow E2E: 12 passed.

The E2E suite intentionally emits three 502 responses in the failure recovery scenario to validate retry exhaustion and UI recovery. Those expected network errors are filtered only inside that specific negative-path test.

## Bugs Found

1. Revision LLM exceptions could propagate without a stable API error mapping.
2. Multi-round revision indexing counted direct children instead of the full revision group.
3. Frontend API retry count was reset on every retry, risking indefinite loading for persistent 5xx responses.
4. CandidatePanel did not clearly show child revision provenance or inherited beat count.

## Remaining Issues

None blocking for T8.6.

## Recommendation

T8.6 can be considered closed after review. Feedback revision now has a safer failure path, clearer lineage, better user-facing context, and stronger E2E regression coverage.

Recommended next step:

```text
T8.7: real LLM feedback revision quality smoke
```

That should validate whether user feedback materially improves candidate quality without weakening candidate safety.
