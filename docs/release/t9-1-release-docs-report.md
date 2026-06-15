# T9.1 Release Documentation Closure Report

## Current Commit

Base commit before this documentation update: `58b8698 docs: fix T9 stage plan encoding`.

## Version Decision

Decision: use `v0.2.0` for the next developer preview.

Reason:

T8 was not only a bug-fix phase. It added a complete writing quality loop:

- required / forbidden beats input;
- prompt injection for generate / rewrite / polish / revise;
- beat validator metadata;
- CandidatePanel pass / warning / unknown;
- adopt warning confirmation;
- feedback revision child candidates;
- multi-round revision lineage;
- polish conservative rules;
- real Chinese backend chain dogfood;
- real UI + real LLM smoke;
- candidate-only safety boundaries.

This scope is larger than a `v0.1.3` maintenance patch, so `v0.2.0` is the clearer version signal.

This version must still be described as an internal developer preview, not a commercial production release.

## Updated Files

- `README.md`
- `CHANGELOG.md`
- `KNOWN_ISSUES.md`
- `RELEASE_CHECKLIST.md`
- `docs/release/v0.2.0-release-notes-draft.md`
- `docs/release/t9-1-release-docs-report.md`

## README Summary

README now states:

- current target is `v0.2.0` Writing Quality Loop Developer Preview;
- Moyun Studio is a local-first long-form fiction writing studio;
- candidate-only workflow protects formal prose;
- T8 writing quality loop capabilities are visible;
- OpenAI-compatible and local endpoint configuration are supported;
- current limitations are linked to known issues.

## CHANGELOG Summary

CHANGELOG now includes:

- `v0.2.0 - Writing Quality Loop Developer Preview`;
- Added section for beats input, validator metadata, CandidatePanel quality checks, feedback revision, lineage, polish conservative rules, and real LLM smoke coverage;
- Changed section for beat-aware prompt assembly, CandidatePanel organization, and LLM UX;
- Fixed section for validator alignment, retry, E2E mock stabilization, feedback revision failure safety, and Chinese chain dogfood.

## KNOWN_ISSUES Summary

KNOWN_ISSUES now separates:

- P2 issues: skipped E2E, validator limits, TOCTOU/atomic write hardening, real LLM latency;
- P3 issues: MCP Unicode transport, polish awkward phrasing, mock duplication, `waitForTimeout`, non-atomic candidate writes.

It explicitly states that these issues do not block the developer preview release.

## RELEASE_CHECKLIST Summary

The release checklist now includes:

- backend tests;
- frontend build;
- focused E2E;
- full E2E;
- real LLM smoke;
- candidate preview/adopt/delete;
- feedback revision;
- required beats warning;
- Chinese prompt encoding smoke;
- API key leak check;
- `git diff --check`;
- clean git status.

## Release Notes Draft Summary

`docs/release/v0.2.0-release-notes-draft.md` includes:

- version positioning;
- highlights;
- Writing Quality Loop;
- Candidate Safety;
- Feedback Revision;
- Real LLM Smoke;
- Known Issues;
- Upgrade / Testing Notes;
- developer preview disclaimer.

## Release Blockers

No documentation blocker found for entering T9.1-final.

## Non-blocking Issues

- Full E2E still has 93 skipped tests.
- Validator is limited for subtle narrative judgment.
- TOCTOU / atomic write hardening remains future work.
- Real LLM latency depends on external or local model service.
- MCP Unicode transport issue remains outside the core product path.

## Recommendation

Proceed to T9.1-final: Preflight + Smoke + Release Readiness.

## T9.1-final Suggested Verification

Run at minimum:

```powershell
git status --short
git diff --check
```

Then perform release readiness checks:

- backend tests;
- frontend build;
- focused candidate E2E;
- full E2E with skipped count recorded;
- real LLM smoke in an isolated smoke project;
- API key leak check;
- candidate preview/adopt/delete smoke;
- feedback revision smoke;
- Chinese prompt encoding smoke.
