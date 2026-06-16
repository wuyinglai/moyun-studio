# T9.1-final Release Readiness Report

> Target: `v0.2.0` Writing Quality Loop Developer Preview  
> Mode: Preflight + Smoke + Release Readiness  
> Base commit: `1d24687 docs: prepare release docs for T9.1`  
> Date: 2026-06-16

## 1. Current Commit

Preflight was run on:

```text
1d24687 docs: prepare release docs for T9.1
```

## 2. Release Target

Release target remains:

```text
v0.2.0 - Writing Quality Loop Developer Preview
```

This is an internal developer preview, not a commercial production release.

## 3. Preflight Summary

| Check | Result |
| --- | --- |
| `git status --short` before checks | clean |
| `git log -1 --oneline` | `1d24687 docs: prepare release docs for T9.1` |
| `git diff --check` | passed |
| Product code changed | no |
| Prompt changed | no |
| Test code changed | no |
| Tag / GitHub Release created | no |

## 4. Backend Tests

Commands:

```powershell
python -m pytest backend/tests/test_pipeline.py backend/tests/test_beat_validator.py -q --tb=short
python -m pytest backend/tests/test_candidate_feedback_revision.py -q --tb=short
```

Results:

```text
75 passed in 9.01s
10 passed in 7.43s
```

Backend readiness result: passed.

## 5. Frontend Build

Command:

```powershell
cd frontend
npm run build
```

Result:

```text
vue-tsc -b && vite build
build passed
```

Frontend build readiness result: passed.

## 6. Focused E2E

Command:

```powershell
cd frontend
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
```

Result:

```text
16 passed
```

Focused candidate workflow result: passed.

Covered safety behaviors:

- CandidatePanel list opens.
- Candidate preview works.
- Candidate adopt works.
- Candidate delete/discard works.
- Feedback revision modal works.
- Empty feedback is rejected.
- Adopted candidates do not show feedback revision.
- Required beat warning / unknown UI states render.
- Candidates without `beat_validation` remain compatible.

## 7. Full E2E Mock

Command:

```powershell
cd frontend
npm run test:e2e:mock -- --reporter=line
```

Result:

```text
62 passed
93 skipped
0 failed
```

This matches the T8 baseline and has no blocking failure.

## 8. Real LLM Smoke

Real LLM smoke was attempted with a temporary runner outside the repository.

Runner properties:

- Location: system temp directory, deleted after execution.
- Workspace: system temp directory, deleted after execution.
- Product path: real `PipelineRunner`, `FileService`, `CandidateService`, `LLMService`.
- Model configured by current `.env`: `gemma-4-12b-it-uncensored-Q4_K_M`.
- API base: configured, not printed with secrets.
- API key: not printed, not written to repo.

Target scenarios:

1. Polish current scene.
2. Rewrite current scene.
3. Feedback revision child candidate.

Result:

```text
polish: failed before candidate creation
rewrite: failed before candidate creation
feedback revision: not reached because polish parent candidate was not created
```

Failure detail:

```text
LLM_ERROR
OpenAI-compatible model service returned HTTP 502 BadGatewayError.
```

Safety observations:

- Source scene remained unchanged after polish failure.
- Source scene remained unchanged after rewrite failure.
- No bad candidate was created.
- Temporary smoke workspace was removed.

Readiness judgment:

The real LLM smoke did not pass in the current environment. The failure appears to be an environment/model-service issue from the configured local OpenAI-compatible endpoint, not a product code regression. However, because the release gate explicitly asks for real LLM smoke coverage, this should be treated as a release readiness blocker until the model endpoint is fixed, switched, or explicitly waived.

## 9. Candidate Safety Smoke

Candidate safety is covered by the focused E2E, full E2E, and failed real-smoke safety observations.

Confirmed:

- AI output enters candidate flow in tested candidate scenarios.
- Preview does not overwrite official text.
- Adopt changes official text only after explicit user action.
- Delete/discard does not affect official text.
- Feedback revision creates child candidates in E2E.
- Parent candidate remains unchanged in feedback revision E2E.
- Warning is advisory and does not hard-block adopt.
- Adopted candidates do not support feedback revision.
- Failed real LLM generation did not overwrite source text or create bad candidates.

Candidate safety result: passed for mock/E2E coverage; real LLM success path blocked by model service 502.

## 10. API Key / Secret Check

Commands:

```powershell
git grep -n "sk-" .
git grep -n "OPENAI_API_KEY" .
git grep -n "api_key" .
git grep -n "Authorization: Bearer" .
```

Additional exact-prefix check:

```text
tracked files containing sk-vn prefix: 0
```

Assessment:

- No unredacted real API key was found in tracked files.
- `sk-` hits are placeholders, tests, redaction tests, examples, or historical archived notes.
- `api_key` / `Authorization: Bearer` hits are code paths, tests, examples, or redaction logic.
- No API key was printed in the real LLM smoke output.

Secret check result: passed.

## 11. Release Docs Consistency

Checked files:

- `README.md`
- `CHANGELOG.md`
- `KNOWN_ISSUES.md`
- `RELEASE_CHECKLIST.md`
- `docs/release/v0.2.0-release-notes-draft.md`
- `docs/release/t9-1-release-docs-report.md`
- `docs/roadmaps/t9-stage-plan.md`
- `docs/archives/t8-writing-quality-closure.md`

Result:

- Current release-facing docs consistently identify `v0.2.0` as a developer preview.
- Candidate-only safety is consistently documented.
- Known issues are documented as non-blocking except for the current real LLM smoke environment failure.
- T8 archive is historical and not expected to carry the final T9.1 release target wording.

Docs consistency result: passed.

## 12. Release Blockers

Current blocker:

```text
Real LLM smoke did not pass because the configured OpenAI-compatible model service returned HTTP 502.
```

Why it blocks readiness:

- The T9.1-final gate asks for real LLM smoke with polish, rewrite, and feedback revision.
- Current run did not create polish/rewrite candidates.
- Feedback revision could not run because there was no parent candidate.

Why it is likely environmental:

- Backend tests passed.
- Frontend build passed.
- Focused E2E passed.
- Full E2E had 0 failed.
- The real smoke reached the LLM boundary and failed with provider HTTP 502.
- Source text remained unchanged and no bad candidate was left behind.

## 13. Non-blocking Issues

These remain non-blocking but should stay visible:

- Full E2E has 93 skipped tests.
- Validator remains limited for subtle narrative / terminal hook judgment.
- Real LLM latency depends on the selected model service.
- TOCTOU / atomic write hardening remains future work.
- MCP Unicode transport issue remains outside the core product path.
- Mock helpers still have duplication.
- Some `waitForTimeout` hard sleeps remain in tests.

## 14. Recommendation

Do not create the `v0.2.0` tag yet.

Recommended next step:

1. Fix or switch the configured real LLM endpoint.
2. Re-run only the T9.1-final real LLM smoke.
3. If polish / rewrite / feedback revision pass 3/3, proceed to tag / GitHub Release preparation.

## 15. Next Step

Run a focused follow-up:

```text
T9.1-final-fixup: real LLM smoke rerun
```

Scope:

- no code changes unless a product bug is found;
- use a working real LLM endpoint;
- verify polish, rewrite, feedback revision;
- update this readiness report or add a short fixup report;
- then decide whether `v0.2.0` can proceed to tag / GitHub Release preparation.
