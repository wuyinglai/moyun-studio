# T9.2 Final Test Debt Closure

Date: 2026-06-17

Risk: Risk C

Mode: Final Regression + Stage Archive

Current commit at verification start:

```text
3ddba06 test: recover second focused E2E batch for T9.2
```

## 1. Background

T9.2 was the post-v0.2.0 test debt phase. Its purpose was not to chase raw skip count, but to classify existing E2E debt and recover the highest-value safety coverage around candidate-first writing, file conflict handling, and user-visible generation recovery.

Completed T9.2 work:

- T9.2a: skipped E2E classification and P0/P1/P2/P3 prioritization.
- T9.2b: focused candidate workflow recovery batch 1.
- T9.2c: focused Professional / Lite / FILE_CONFLICT recovery batch 2.

This final pass reran the release-gate-style mock frontend checks and archives the remaining skipped test strategy.

## 2. T9.2a / T9.2b / T9.2c Summary

### T9.2a

Document:

- `docs/planning/t9-2-test-debt-classification.md`

Outcome:

- Classified the `93` skipped full E2E tests by risk and test type.
- Defined P0/P1/P2/P3 priorities.
- Recommended focused recovery rather than wholesale unskip.
- Kept real LLM and real backend flows opt-in.

### T9.2b

Document:

- `docs/testing/t9-2b-focused-e2e-recovery.md`

Primary test file:

- `frontend/tests/e2e/14-candidate-workflow.spec.ts`

Outcome:

- Focused candidate workflow increased from `16` scenarios to `22`.
- Added coverage for candidate SSE payload safety, adopt cancel, adopt conflict, delete/discard safety, and feedback revision request metadata.

### T9.2c

Document:

- `docs/testing/t9-2c-focused-e2e-recovery.md`

Primary test file:

- `frontend/tests/e2e/31-t9-2c-focused-recovery.spec.ts`

Outcome:

- Added `6` focused mock E2E tests for Professional, Lite, file conflict, and LLM error recovery.
- Verified Professional rewrite generates a candidate instead of writing official scene content.
- Verified Lite feedback generation streams into a candidate draft without overwriting source.
- Verified frontend save conflict UI sends `expected_mtime` / `expected_hash` and does not silently overwrite content.

## 3. Final Regression Commands

Baseline checks:

```powershell
cd D:\newmoyun
git status --short
git log -1 --oneline
git diff --check
```

Frontend build:

```powershell
cd D:\newmoyun\frontend
npm run build
```

Focused candidate workflow:

```powershell
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

Focused T9.2c recovery:

```powershell
npm run test:e2e:mock -- tests/e2e/31-t9-2c-focused-recovery.spec.ts --reporter=line
```

Full mock E2E:

```powershell
npm run test:e2e:mock -- --reporter=line
```

## 4. Final Regression Results

| Check | Result |
| --- | --- |
| `git status --short` before regression | clean |
| `git log -1 --oneline` | `3ddba06 test: recover second focused E2E batch for T9.2` |
| `git diff --check` before regression | passed |
| `npm run build` | passed |
| T9.2b focused candidate E2E | `22 passed` |
| T9.2c focused recovery E2E | `6 passed` |
| Full mock E2E | `74 passed / 93 skipped / 0 failed` |

The first full mock attempts timed out at the command wrapper level because Playwright reused stale Vite processes already listening on port `5173`. Two Vite processes from the current repository were stopped, allowing Playwright to start a clean configured web server. After that environment reset, the full mock suite passed with the expected result:

```text
74 passed / 93 skipped / 0 failed
```

This is recorded as a local test environment issue, not a product code failure.

## 5. Coverage Improved

T9.2 improved the default mock regression baseline:

```text
full mock E2E: 62 passed -> 74 passed
focused candidate workflow: 16 passed -> 22 passed
new T9.2c focused spec: 6 passed
full mock E2E: 0 failed
```

## 6. P0 / P1 / P2 Coverage Lift

### P0 Safety Coverage

Strengthened:

- Candidate-first generation safety.
- Preview does not cover official text.
- Adopt cancel does not call adopt API.
- `FILE_CONFLICT` on adopt keeps candidate pending and does not save source.
- Delete/discard does not write official scene content.
- SSE payloads do not leak full `content`.
- Professional rewrite uses candidate output.
- Frontend save conflict sends `expected_mtime` / `expected_hash` and shows conflict UI.

### P1 Workflow Coverage

Strengthened:

- Feedback revision request preserves safety metadata flags.
- Quick feedback action can create a safe revision request.
- Lite feedback generation creates a candidate draft.
- Professional pipeline error restores controls and does not leave a bad candidate.
- Lite stream error restores the generate button and does not show a candidate draft.
- Candidate preview can close before delete without freezing the page.

### P2 UI / Stability Coverage

Strengthened:

- CandidatePanel warning / unknown quality sections remain covered by the focused candidate suite.
- Conflict modal visibility is covered.
- Existing stable selectors were reused.
- Selector debt was documented for CandidatePanel preview action, which still lacks a dedicated `data-testid`.

## 7. Remaining Skipped Tests

The full mock suite still reports:

```text
93 skipped
```

This does not block T9.2 closure.

Remaining skipped strategy:

- Real LLM tests remain opt-in and should not run in the default mock suite.
- Real backend tests remain opt-in unless rewritten into current-flow mock E2E.
- UI old-flow tests should be rewritten against `docs/frontend-user-flow.md` before unskip.
- Timing-heavy tests need condition-based waits before recovery.
- Historical phase smoke should be archived or mined for useful assertions rather than restored wholesale.

## 8. Why T9.2 Does Not Restore More Skipped Tests

T9.2 was scoped as test debt classification plus focused recovery, not a Playwright framework rewrite.

Restoring more skipped tests now would be low leverage because:

- Many skipped tests require real LLM, real backend, or old product assumptions.
- The highest-risk candidate/file safety flows already have focused mock coverage.
- The full mock suite now runs with `0 failed`.
- Chasing the skip count would blur the boundary between T9.2 closure and later product-quality work.

The next stage should change topic rather than keep expanding T9.2.

## 9. Release Impact

T9.2 does not change the v0.2.0 release tag or release artifacts.

Release confidence improved because the default frontend mock suite now has broader current-flow safety coverage and still finishes with `0 failed`.

## 10. Recommendation

T9.2 can be closed.

Recommended next stage:

```text
T9.3: Continuity Anchors design
```

Reason:

- Candidate-first and file conflict test debt has been classified and strengthened enough for the developer preview baseline.
- Remaining skipped tests are known and intentionally deferred.
- The next product risk is long-form continuity, not more raw E2E recovery.

## 11. Next Step

Start T9.3 as a design/planning task for Continuity Anchors.

Recommended T9.3 boundaries:

- Do not start with implementation.
- Define what continuity anchors are.
- Decide where they live in candidate metadata, story memory, prompt assembly, and UI.
- Reuse T8/T9 required-beat validator lessons.
- Keep candidate-first safety unchanged.
