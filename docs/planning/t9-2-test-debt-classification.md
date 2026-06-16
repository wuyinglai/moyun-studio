# T9.2 Test Debt Classification

Date: 2026-06-16

Risk: Risk B

Mode: Planning / Test Debt Classification / Roadmap

Scope:

- Documentation planning only.
- No product code changes.
- No test implementation changes.
- No release tag or GitHub Release changes.
- No real LLM execution.

## 1. Baseline

Current release baseline:

| Item | Status |
| --- | --- |
| Release tag | `v0.2.0` |
| Tag commit | `6ef7d7893e22a93141ac5c23eb2053bd1d7877b4` |
| Post-release smoke commit | `2acb4f2 docs: add v0.2.0 post-release smoke report` |
| Backend smoke | `75 passed` |
| Frontend build | passed |
| Focused candidate E2E | `16 passed` |
| Full mock E2E from T9.1-final | `62 passed / 93 skipped / 0 failed` |
| Current recommendation | Keep `v0.2.0` as the developer preview baseline and continue T9 stabilization planning. |

Release notes and known issues call out four active debt areas:

- `93` full E2E tests remain skipped and need classification.
- The validator is limited for subtle narrative quality and terminal hooks.
- Real LLM latency depends on the selected model service and network path.
- Candidate/file writes still need future atomic-write hardening.

## 2. Skipped E2E Classification

The observed full mock E2E result is:

```text
62 passed / 93 skipped / 0 failed
```

Static inspection of `frontend/tests/e2e/*.spec.ts` shows the skipped tests are mostly produced by file-level gates. The static gated count is larger than the observed skipped count because some files include runtime skips, helper gates, or tests that are not counted the same way in the latest full mock run. The operational classification should therefore use the observed `93 skipped` as the release metric, and use the file-level mapping below as the triage guide.

### 2.1 Real LLM Gated Tests

Files:

- `03-main-entry-real-llm.spec.ts`
- `04-lite-entry-real-llm.spec.ts`
- `05-candidate-batch-real-llm.spec.ts`
- `06-quality-report.spec.ts`
- `30-real-llm-smoke.spec.ts`

Gate examples:

- `MOYUN_ALLOW_REAL_LLM_SMOKE=1`
- `MOYUN_E2E_REAL_LLM=true`

Classification:

- Real LLM type.
- Should not run in the default mock suite.
- Should become a small, explicit manual or opt-in smoke lane.
- Must redact API keys and avoid committing generated workspace data.

Recommended handling:

- Keep skipped in default CI/mock runs.
- Select 2-3 high-value scenarios for an opt-in `real-llm-smoke` lane.
- Prefer direct backend smoke for polish / rewrite / feedback revision over fragile full-browser LLM tests.
- Keep browser real LLM tests only for release-candidate dogfood.

### 2.2 Real Backend / Real API Gated Tests

Files:

- `18-file-tree-editor.spec.ts`
- `19-project-create-open-real-api.spec.ts`
- `20-sse-real-event-flow.spec.ts`
- `21-task-queue-pipeline-dry-run.spec.ts`
- `22-task-queue-pipeline-real-dry-run.spec.ts`
- `23-task-queue-pipeline-ui-dry-run.spec.ts`
- `24-dry-run-ui-entry.spec.ts`
- `25-professional-minimal-safe-flow.spec.ts`
- `26-professional-dry-run-main-flow.spec.ts`
- `27-candidate-adopt-conflict-sse-flow.spec.ts`
- `28-pipeline-dry-run-ui-sse-flow.spec.ts`
- `29-batch-dry-run-flow.spec.ts`
- `30-candidate-adopted-sse-flow.spec.ts`

Gate example:

- `MOYUN_E2E_REAL_BACKEND=1`

Classification:

- Environment-dependent.
- Many scenarios are still valuable but should be separated from the default mock suite.
- Some overlap with backend unit tests and the focused candidate E2E suite.

Recommended handling:

- Split into two groups:
  - recoverable mock E2E tests that can be rewritten to use `installMockApi`;
  - true integration tests that should stay opt-in with an isolated backend workspace.
- Prioritize safety-critical tests for recovery first: file conflict, candidate adopt, delete, SSE candidate events, and dry-run non-overwrite behavior.

### 2.3 Phase Smoke / Historical Flow Tests

File:

- `99-phase-t3a-flowpanel-smoke.spec.ts`

Gate example:

- `MOYUN_E2E_ALLOW_PHASE_SMOKE=1`

Classification:

- Historical phase smoke.
- Likely replaced by newer workflow / right-panel / candidate tests.
- Should not block the current developer preview.

Recommended handling:

- Archive or rewrite only if the FlowPanel path remains product-critical.
- Do not restore wholesale.
- Extract any still-relevant assertions into smaller mock E2E tests.

### 2.4 Old UI Flow Tests

Likely sources:

- Early main/lite/professional flows.
- Dry-run UI flows from T6.5/T6.6.
- Phase smoke paths that predate the T8 candidate-first writing quality loop.

Classification:

- UI old-flow type.
- Some assumptions may no longer match the real product flow documented in `docs/frontend-user-flow.md`.

Recommended handling:

- Rewrite instead of unskipping.
- Test current flows:
  - open project;
  - open scene;
  - generate candidate;
  - preview/adopt/delete;
  - feedback revision;
  - required/forbidden beats visibility.

### 2.5 Timing / Flakiness Debt

Observed pattern:

- Many E2E files still use `page.waitForTimeout(...)`.
- This appears in both skipped and passing tests.

Classification:

- Unstable timing type.
- It does not necessarily explain all skips, but it increases false failure risk when tests are restored.

Recommended handling:

- Replace sleeps with condition-based waits during recovery work.
- Prioritize waits around:
  - candidate creation;
  - SSE event visibility;
  - modal open/close;
  - editor content load;
  - file tree refresh.

### 2.6 Tests Already Covered By New Flows

Current strong baseline:

- `14-candidate-workflow.spec.ts` focused E2E passes with 16 scenarios.

Covered areas:

- CandidatePanel list.
- Candidate safety notice.
- Feedback revision from pending candidate.
- Empty feedback rejection.
- Adopted candidate revision disabled.
- Revision metadata display.
- Revision LLM failure retry behavior.
- Required beat inheritance display.
- Beat warning / unknown visibility.
- Preview / adopt / delete.
- Old candidate compatibility.

Recommended handling:

- Do not duplicate these with older real-backend tests unless they add a distinct integration guarantee.
- When restoring skipped tests, avoid re-testing the same CandidatePanel UI assertions at a higher cost.

## 3. Priority

### P0: Candidate-first and File Safety

These are release-critical because they protect user prose.

Scope:

- Candidate-only rewrite / polish / feedback revision.
- No direct overwrite of existing `sec-*.md`.
- Candidate adopt hash / mtime / FILE_CONFLICT behavior.
- Delete/discard does not change official text.
- Existing scene write safety.
- SSE event payload safety for candidate/file updates.

Recommended tests:

- Restore or rewrite `27-candidate-adopt-conflict-sse-flow.spec.ts` as a mock-first focused E2E.
- Keep backend unit/contract tests around candidate adopt and file conflict as the source of truth.
- Add only small UI assertions where user-visible behavior matters.

### P1: Main Writing Flow and Revision Loop

These are high-value user workflows.

Scope:

- Professional open scene -> generate candidate -> preview -> adopt/delete.
- Feedback revision child candidate.
- Required/forbidden beats input.
- Lite write/save/rewrite candidate flow.
- Right-panel generation status recovery.

Recommended tests:

- Keep `14-candidate-workflow.spec.ts` as the focused safety baseline.
- Recover one Professional flow test and one Lite flow test in mock mode.
- Keep real LLM variants opt-in only.

### P2: UI Visibility, Warning, and Test Stability

These improve user trust but do not directly decide file safety.

Scope:

- Beat validation pass/warning/unknown display.
- Long-wait / error UX.
- Candidate source/revision metadata display.
- Scene Plan panel visibility if still product-active.
- Replacement of brittle `waitForTimeout` sleeps.

Recommended tests:

- Rewrite selected old UI tests into condition-based waits.
- Prefer small component-like E2E scenarios with mocked API responses.

### P3: Cleanup, Historical Tests, and Low-frequency Edges

Scope:

- Phase T3-A smoke.
- Old dry-run UI paths that are no longer product entry points.
- Quality report generation files not used in the release gate.
- Legacy screenshots or visual smoke with heavy timing sleeps.

Recommended tests:

- Archive or delete after confirming no unique coverage.
- Keep as manual smoke only if useful for screenshots or demos.

## 4. Recommended Actions

### T9.3: Focused E2E Recovery Batch 1

Goal:

```text
Reduce skipped debt by recovering safety-critical mock E2E tests first.
```

Recommended scope:

1. Candidate adopt conflict and SSE visibility.
2. File tree + editor read/save conflict smoke.
3. Professional minimal safe flow.
4. Lite minimal safe flow.
5. Task queue / pipeline dry-run non-overwrite smoke if it still maps to the current product flow.

Rules:

- Do not enable real LLM by default.
- Convert recoverable tests to mock API where possible.
- Replace hard sleeps with condition waits.
- Keep each restored test narrow.

### T9.4: Candidate / File Write Hardening Planning

Goal:

```text
Plan and then implement stronger write safety where needed.
```

Planning areas:

- Atomic candidate metadata writes.
- Atomic candidate content writes.
- Atomic revision-log writes.
- FileService write temp-file + rename strategy.
- Recovery behavior after partial write failure.
- Additional backend tests for interrupted writes.

This should be planning first, not an immediate large refactor.

### T9.5: Real LLM Smoke Guardrails

Goal:

```text
Make real LLM smoke repeatable without leaking secrets or blocking normal CI.
```

Recommended scope:

- One backend smoke for polish / rewrite / feedback revision.
- Optional browser smoke for release candidates only.
- Clear env gates.
- Short max tokens.
- Isolated smoke project IDs.
- Automatic cleanup.
- Report template that records model, elapsed time, status, and safety result without content secrets.

### T10: Developer Preview Stabilization / v0.2.1 Maintenance

Recommended T10 direction:

- If T9.3/T9.4 reduce critical debt, prepare `v0.2.1` maintenance.
- Focus on stability, not major new features.
- Candidate-first safety remains the release gate.
- Real LLM dogfood remains opt-in and documented.

## 5. Delete / Keep / Rewrite Matrix

| Test Type | Action |
| --- | --- |
| Real LLM browser tests | Keep skipped by default; convert to manual or opt-in release smoke. |
| Real backend safety tests | Rewrite selected tests into mock-first E2E; keep some as opt-in integration. |
| CandidatePanel duplicate coverage | Delete or archive if already covered by `14-candidate-workflow.spec.ts`. |
| Phase T3-A historical smoke | Archive or rewrite only if the feature remains active. |
| Dry-run UI tests | Rewrite against current product flow or move to backend/API tests. |
| Timing-heavy tests | Stabilize before unskipping; replace sleeps with condition waits. |
| Quality report real LLM tests | Keep manual/opt-in; do not default-run. |

## 6. Release Stabilization Checklist

Before the next release candidate, require:

- Focused candidate E2E still passes.
- Backend candidate/file safety tests pass.
- At least one recovered mock E2E covers file conflict or adopt conflict UI.
- Real LLM smoke is run once manually or through an explicit opt-in lane.
- No test writes generated workspace data into git.
- No API key appears in logs, screenshots, reports, or localStorage.

## 7. Recommended Next Task

Recommended next task:

```text
T9.3: Focused E2E recovery batch 1.
```

Suggested T9.3 acceptance:

- Recover 3-5 high-value skipped tests or rewrite their equivalent current-flow coverage.
- Keep full mock E2E at `0 failed`.
- Reduce skipped count only where meaningful.
- Do not chase skip count as the primary metric; prioritize safety coverage.

