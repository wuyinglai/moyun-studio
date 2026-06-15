# Moyun Studio Release Checklist

Use this checklist before creating a release candidate, tag, or GitHub release.

Current target: `v0.2.0` Writing Quality Loop Developer Preview.

## Baseline

Latest stable T8 baseline:

- Backend tests: 85 passed
- Frontend build: passed
- Focused E2E: 16 passed
- Full E2E: 62 passed / 93 skipped / 0 failed
- Real LLM smoke: 3/3 passed
- Git status: clean

## Preflight

- [ ] Confirm version positioning: `v0.2.0` developer preview.
- [ ] Confirm this is not described as a commercial production release.
- [ ] `git status --short` is clean.
- [ ] `git diff --check` passes.
- [ ] `git rev-parse HEAD` matches the intended release commit.
- [ ] `git rev-parse origin/main` matches the intended release commit before tagging.
- [ ] No `.env`, API key, token, cookie, screenshot with secrets, or raw private prompt is staged.

## Required Checks

- [ ] Backend tests pass.
- [ ] Frontend build passes.
- [ ] Focused candidate workflow E2E passes.
- [ ] Full E2E completes with no blocking failures.
- [ ] Real LLM smoke passes in an isolated smoke project.
- [ ] Chinese prompt encoding smoke passes.
- [ ] API key leak check passes.

## Writing Quality Loop Smoke

- [ ] Required beats input can be submitted.
- [ ] Forbidden beats input can be submitted.
- [ ] Beats enter prompt assembly.
- [ ] Candidate metadata includes beat validation when enabled.
- [ ] CandidatePanel shows pass / warning / unknown.
- [ ] Warning is advisory and adopt requires confirmation.
- [ ] Feedback revision creates a child candidate.
- [ ] Multi-round revision lineage is preserved.

## Candidate Safety Smoke

- [ ] Candidate preview works.
- [ ] Candidate adopt works.
- [ ] Candidate delete/discard works.
- [ ] Candidate delete/discard does not affect official text.
- [ ] High-risk rewrite/polish creates a candidate instead of overwriting official text.
- [ ] Child candidate does not modify parent candidate.
- [ ] Formal writes do not bypass hash / mtime / FILE_CONFLICT.

## Release Documentation

- [ ] README.md reflects current product capabilities.
- [ ] CHANGELOG.md includes the target version section.
- [ ] KNOWN_ISSUES.md includes P2/P3 remaining issues.
- [ ] RELEASE_CHECKLIST.md is current.
- [ ] Release notes draft exists.
- [ ] T9.1 release docs report exists.

## Tag and GitHub Release

- [ ] Confirm tag does not already exist locally.
- [ ] Confirm tag does not already exist on origin.
- [ ] Create tag only after preflight passes.
- [ ] Push tag.
- [ ] Create GitHub prerelease or release according to the chosen release plan.
- [ ] Verify release page and tag after creation.

## Post-release Smoke

- [ ] Checkout release tag.
- [ ] Run frontend build.
- [ ] Run focused backend tests.
- [ ] Start backend.
- [ ] Start frontend.
- [ ] Open UI and verify the main workbench loads.
- [ ] Return to `main`.
- [ ] Confirm `git status --short` is clean.
