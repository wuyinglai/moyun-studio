# T9.2b Focused E2E Recovery Batch 1

Date: 2026-06-16

Risk: Risk B

Mode: Focused Test Recovery + Minimal Test Refactor

## Baseline

- Starting commit: `b460edb docs: classify T9.2 test debt`
- Branch: `main`
- Scope: frontend mock E2E and documentation only
- Product code changes: none
- Backend changes: none
- Real LLM: not used
- Release tag changes: none

## Recovery Summary

T9.2b recovered safety-focused coverage by extending the existing focused candidate workflow mock suite:

- Existing focused suite before this batch: `16` candidate workflow scenarios.
- Focused suite after this batch: `22` candidate workflow scenarios.
- New scenarios added: `6`.
- Primary file: `frontend/tests/e2e/14-candidate-workflow.spec.ts`.

The batch intentionally did not attempt to unskip the full E2E backlog wholesale. It added current-flow coverage for candidate-first safety and feedback revision behavior, which were called out as P0/P1 priorities in `docs/planning/t9-2-test-debt-classification.md`.

## Recovered Tests

Added scenarios:

1. `T9.2b: candidate SSE events do not expose full content`
   - Verifies mock `file.updated` and `candidate-created` SSE payloads carry metadata only.
   - Checks `project_id` is present.
   - Checks no payload includes a full `content` field.

2. `T9.2b: cancelling warning adopt does not call adopt API`
   - Opens CandidatePanel.
   - Clicks adopt on a warning candidate.
   - Dismisses the browser confirm.
   - Asserts no adopt API call is made and no file save occurs.

3. `T9.2b: FILE_CONFLICT on adopt keeps candidate pending and does not save source`
   - Mocks candidate adopt returning `409 FILE_CONFLICT`.
   - Asserts the candidate remains pending.
   - Asserts the official scene file save endpoint is not called.

4. `T9.2b: deleting candidate does not write official scene file`
   - Deletes/discards a pending candidate.
   - Asserts candidate delete is called.
   - Asserts official scene file save is not called.

5. `T9.2b: feedback revision request preserves safety metadata flags`
   - Submits feedback revision from a pending candidate.
   - Asserts the request includes `inherit_required_beats`, `inherit_forbidden_beats`, and `run_beat_validation`.
   - Asserts the revision scope remains `full_candidate`.

6. `T9.2b: quick feedback action alone can create a safe revision candidate`
   - Uses a quick feedback action without freeform feedback text.
   - Asserts submit becomes enabled.
   - Asserts the revision request includes quick actions.
   - Asserts no official file save occurs.

## New Helpers / Mock Enhancements

The existing `installMocks` helper in `14-candidate-workflow.spec.ts` now returns a small state object for test assertions:

- `revisionPayloads`
- `adoptCalls`
- `deleteCalls`
- `fileSaveCalls`
- `sseEvents`
- `candidates`

This keeps assertions inside the browser E2E test while avoiding real backend, real LLM, or workspace writes.

The mock API now also supports:

- Adopt conflict response via `adoptConflict`.
- SSE event fixtures for `file.updated` and `candidate-created`.
- File save call counting.
- Candidate delete call counting.
- Revision request payload capture.

The shared E2E error filter now ignores Chromium's transient `net::ERR_CERT_DATABASE_CHANGED` console noise. This was observed during the full mock suite in `17-lite-view.spec.ts` and is treated like the existing connection/404 environment filters, not as a product behavior change.

## P0 Coverage

Covered P0 items:

- Candidate adopt cancellation does not mutate state or call adopt.
- Candidate adopt `FILE_CONFLICT` does not write official scene content.
- Candidate delete/discard does not write official scene content.
- SSE candidate/file events do not include full content payloads.

Not covered in this batch:

- Real backend atomic write behavior.
- Real FileService conflict behavior.
- Cross-process candidate/file race conditions.

These remain backend/integration concerns for T9.4 or an opt-in integration lane.

## P1 Coverage

Covered P1 items:

- Feedback revision request preserves safety metadata.
- Feedback revision quick actions can generate a safe child candidate.
- Required/forbidden beat inheritance flags stay wired in the request.

Already covered by the existing focused suite:

- CandidatePanel list.
- Preview/adopt/delete.
- Pending-only feedback revision.
- Empty feedback rejection.
- Adopted candidate revision disabled.
- Revision LLM failure retry.
- Warning/unknown quality display.
- Old candidate compatibility.

## P2 Coverage

Covered or strengthened P2 items:

- Warning adopt confirm cancellation.
- Metadata-only SSE visibility.
- Quick feedback UI state transition.

Not covered in this batch:

- Long-wait UX.
- Real LLM latency UX.
- Full visual regression.

## Skipped Remaining

This batch does not remove the `93` skipped full E2E debt from the v0.2.0 baseline. The skipped tests remain classified in `docs/planning/t9-2-test-debt-classification.md`.

Recommended handling remains:

- Keep real LLM browser tests opt-in.
- Rewrite selected real-backend safety tests into mock-first focused E2E only when they add distinct current-flow coverage.
- Keep environment-dependent tests gated.
- Delete or archive historical old-flow tests only after confirming no unique coverage remains.

## Commands

Executed during recovery:

```powershell
git status --short
git log -1 --oneline
npm run build
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

Focused E2E result:

```text
22 passed
```

The first run of the expanded focused suite exposed a selector issue in newly added tests: they used a Chinese tab label and failed under the historical encoded test file. The tests were adjusted to use the stable CandidatePanel tab position instead of text matching.

## Risks

- The focused suite still uses a local mock API, so it verifies frontend behavior and request contracts rather than real backend persistence.
- CandidatePanel tab access in the new tests uses the current tab order (`candidate` is the fifth tab). A future UI tab reorder would require updating these tests or adding a stable `data-testid` to the tab.
- Existing test file text includes historical encoding artifacts; this batch avoids rewriting old titles or assertions to reduce churn.

## Recommendation

T9.2b can be considered successful if:

- Frontend build passes.
- Focused candidate workflow remains `22 passed`.
- Full mock E2E remains `0 failed`, even if skipped debt remains.
- `git diff --check` passes.

Recommended next task:

```text
T9.3: focused E2E recovery batch 2
```

Candidate scope for T9.3:

- Professional minimal safe flow mock recovery.
- Lite minimal safe flow mock recovery.
- File editor save conflict UI smoke.
- Optional stable `data-testid` for RightPanel candidate tab if product code changes are permitted.
