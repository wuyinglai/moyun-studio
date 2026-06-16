# T9.2c Focused E2E Recovery Batch 2

Date: 2026-06-16

Risk: Risk B

Mode: Focused Test Recovery + Minimal Test Refactor

Base commit: `4611088 test: recover focused E2E batch for T9.2`

Related documents:

- `docs/planning/t9-2-test-debt-classification.md`
- `docs/testing/t9-2b-focused-e2e-recovery.md`

## Scope

This batch added a second focused mock E2E recovery layer for user-visible safety flows that were not covered by the T9.2b candidate-only suite.

No product code was changed. No real backend, real LLM, release tag, or workspace data was used.

New test file:

- `frontend/tests/e2e/31-t9-2c-focused-recovery.spec.ts`

## Recovered Tests

Added 6 mock E2E tests:

1. `Professional rewrite creates candidate and does not save official scene`
   - Opens a Professional scene route.
   - Clicks the rewrite toolbar button.
   - Verifies `/api/pipeline/run` uses `output_mode: candidate`.
   - Verifies no official file save occurs.
   - Verifies CandidatePanel receives the generated candidate.

2. `Professional pipeline error restores generation controls and leaves no bad candidate`
   - Mocks an SSE `error` event from pipeline.
   - Verifies rewrite controls become usable again.
   - Verifies no candidate or file write is produced after the failure.

3. `Lite feedback generation streams into a candidate draft without overwriting source`
   - Opens `/project/:projectId/lite`.
   - Uses the Lite feedback textarea and generate button.
   - Verifies Lite stream runs with `action: rewrite`.
   - Verifies candidate bar appears.
   - Verifies the official source content remains unchanged.

4. `Lite LLM error recovers the generate button and does not create a candidate draft`
   - Mocks a Lite stream `LLM_ERROR`.
   - Verifies the generate button recovers.
   - Verifies no candidate bar or source save is produced.

5. `File save conflict shows conflict modal and does not silently overwrite content`
   - Opens a Professional scene.
   - Edits CodeMirror content and triggers Ctrl+S.
   - Mocks `FILE_CONFLICT` / 409 from the file save endpoint.
   - Verifies the request includes `expected_mtime` and `expected_hash`.
   - Verifies the conflict modal is shown and official content is not overwritten.

6. `Candidate preview can close before delete, and delete never saves official scene`
   - Opens CandidatePanel with an existing candidate.
   - Opens and closes preview.
   - Deletes the candidate.
   - Verifies the candidate becomes discarded and official content is not saved.

## P0 / P1 / P2 Mapping

### P0 Coverage

- Candidate-first rewrite safety: Professional rewrite produces a candidate and does not save the official scene.
- File conflict safety: frontend save sends `expected_mtime` / `expected_hash` and shows conflict UI on `FILE_CONFLICT`.
- Candidate delete safety: deleting a candidate does not write the official scene.

### P1 Coverage

- Professional scene-level generation failure recovery.
- Lite feedback-to-candidate flow.
- Lite LLM failure recovery.
- Candidate preview and delete interaction stability.

### P2 Coverage

- CandidatePanel selector stability through existing `data-testid` selectors.
- Conflict modal visibility.
- No page freeze after preview close.

## Helper / Selector Changes

No shared helper files were changed.

No product `data-testid` changes were needed. The new spec reuses existing stable selectors:

- `editor-toolbar`
- `rewrite-button`
- `candidate-panel`
- `candidate-content`
- `candidate-reject-button`
- `lite-entry-root`
- `lite-prompt-input`
- `lite-generate-button`
- `lite-accept-button`

The preview action currently has no dedicated `data-testid`, so the test uses `.candidate-card .card-actions-primary button` for the existing preview button. This is acceptable for T9.2c but remains a small selector debt item.

## Why No More Skipped Tests Were Restored

This batch intentionally added current-flow mock coverage instead of unskipping legacy real-backend or real-LLM files.

Reasons:

- The remaining skipped tests are largely real LLM, real backend, old dry-run UI, or historical phase smoke lanes.
- T9.2 is classification and focused recovery, not wholesale E2E framework rewrite.
- The full mock suite already keeps `0 failed` after this batch.
- The developer preview needs safety-critical coverage more than raw skip-count reduction.

## Test Results

Commands run:

```powershell
cd frontend
npm run test:e2e:mock -- tests/e2e/31-t9-2c-focused-recovery.spec.ts --reporter=line
npm run build
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
npm run test:e2e:mock -- --reporter=line
```

Results:

| Command | Result |
| --- | --- |
| `npm run test:e2e:mock -- tests/e2e/31-t9-2c-focused-recovery.spec.ts --reporter=line` | `6 passed` |
| `npm run build` | passed |
| `npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line` | `22 passed` |
| `npm run test:e2e:mock -- --reporter=line` | `74 passed / 93 skipped / 0 failed` |

Backend tests were not run because this batch did not modify backend code.

## Remaining Skipped Tests

The full mock suite still reports:

```text
93 skipped
```

This is expected for T9.2c. Remaining skipped areas should continue to follow the T9.2 classification:

- Real LLM browser flows.
- Real backend integration flows.
- Historical phase smoke.
- Old dry-run UI routes.
- Timing-heavy tests that need rewrite before unskip.

## Bugs Found

No product bug was fixed in this batch.

During the first local run, the new spec had three test-side assumptions that were corrected before commit:

- Lite resumed the blank next scene (`sec-002`) before feedback generation, so the assertion now checks the actual current Lite target.
- File save conflict may trigger more than one save attempt while still preserving conflict safety, so the assertion now checks at least one request and no official overwrite.
- CandidatePanel card body selects the candidate; preview is triggered by the preview action button.

## Recommendation

T9.2c can be accepted as Focused E2E Recovery Batch 2.

Recommended next step:

```text
T9.2-final: consolidate T9.2 test debt classification and focused recovery results.
```

After T9.2-final, the next implementation planning task should be:

```text
T9.3: focused E2E recovery batch 3 or targeted selector debt cleanup.
```

Suggested T9.3 focus:

- Add stable `data-testid` for CandidatePanel preview action.
- Convert one more real-backend safety flow to mock-first E2E if it adds unique coverage.
- Keep real LLM tests opt-in.
