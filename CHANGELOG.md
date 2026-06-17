# Changelog

All notable changes to Moyun Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows semantic versioning in spirit while still in developer preview.

## v0.2.1 - Writing Quality Enhancement Release

**Released**: 2026-06-17
**Tag**: `v0.2.1`
**Release commit**: `fa99483`
**Archive commit**: `51741e5`

### Added

- Candidate Quality Metadata MVP — 5 quality dimensions (instruction_following, continuity, style_preservation, change_scope, forbidden_check) computed automatically for generation candidates.
- Repair Candidate MVP — `CandidateAction.REPAIR` creates child candidates for warning recovery without modifying parent or source.
- Continuity Anchors metadata — active anchors auto-extracted for quality computation and prompt injection.
- Real LLM dogfood coverage — Agnes AI real model smoke across 8 writing scenarios (rewrite, polish, forbidden checks, relationship jump, feedback revision, repair, continuity anchors).
- Safety boundary verification — adopted/discarded parent cannot be revised or repaired; repair creates new child candidate only.
- v0.2.1 release documentation — `docs/releases/v0.2.1-rc-notes.md`, `docs/releases/v0.2.1-rc-checklist.md`, `docs/releases/v0.2.1-release-final-report.md`.

### Changed

- `create_candidate()` now auto-fetches continuity anchors from `ContinuityAnchorService.list_active()` when not explicitly provided.
- Quality metadata is now available to `CandidatePanel` for advisory display alongside beat validation.
- Pipeline prompt rendering cleanup — archive issues resolved; prompt templates use consistent pattern.

### Fixed

- `test_continuity_anchors.py` fixture — absolute path resolution instead of relative path lookup.
- Repair prompt template — properly preserves source context without introducing new plot elements.
- Continuity anchor count accuracy — `used_count >= 3` reliably detected for quality continuity scoring.

### Known Issues

- Guardrails allowlist still contains low-frequency noise; targeted cleanup recommended for v0.2.2.
- T9.4 stage implementation docs remain scattered across `docs/design/`; consolidation recommended.

### Test Results

- **Backend tests**: 52 passed (release gate) / 115 passed (full set)
- **Frontend build**: passed
- **Focused E2E**: 23 passed
- **Full mock E2E**: 77 passed, 93 skipped
- **Real LLM dogfood**: 8 cases passed

[v0.2.1]: https://github.com/wuyinglai/moyun-studio/releases/tag/v0.2.1

## v0.2.0 - Writing Quality Loop Developer Preview

This is an internal developer preview, not a commercial production release.

### Added

- Required / forbidden beats input for generation constraints.
- Beat validation metadata on candidate drafts.
- CandidatePanel quality checks with pass / warning / unknown states.
- Feedback revision child candidates for pending candidates.
- Multi-round revision lineage through parent candidate metadata.
- Polish conservative rules for safer small revisions.
- Real UI + real LLM smoke coverage for the writing quality loop.
- Release documentation set for T9.1.

### Changed

- Generate / rewrite / polish / revise prompt assembly now carries beats when provided.
- CandidatePanel is organized around quality, revision information, and actions.
- LLM slow-response and error UX is clearer.
- High-risk rewrite / polish / existing-scene generation remains candidate-first.
- `write_next_scene` remains a continuation action and must not silently overwrite existing scene text.

### Fixed

- Validator alignment no longer relies only on array order.
- Validator retry was added for more stable beat checks.
- Full E2E mock suite was stabilized enough to complete without blocking failures.
- Feedback revision failure no longer creates a bad child candidate.
- Chinese prompt / candidate / metadata chain was dogfooded for encoding safety.

### Known Issues

- See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for P2/P3 issues that do not block the developer preview.

## v0.2.0-alpha - 2026-06-13

### Added

- Professional real LLM generation path validation for scene-level writing.
- Candidate preview / adopt / delete lifecycle verification.
- Real LLM status visibility and smoke validation coverage.
- User-facing error message mapping for LLM and generation failures.
- Persistent generation warning visibility for context and quality warnings.
- Release smoke checklist and T7.4 RC1 validation reports.

### Changed

- `write_next_scene` is treated as a continuation action and surfaces as `continue` / `续写`.
- High-risk rewrite / polish / existing-scene generation flows remain candidate-first instead of silently overwriting formal scene text.
- Continuity anchor extraction was reduced in noise and hardened for real LLM smoke scenarios.
- Project list and create-project experience were validated as part of the pre-alpha frontend flow checks.
- LLM errors are reported with friendlier messages instead of raw provider exceptions where possible.

### Fixed

- Unsaved-edit warnings before adopting candidate drafts.
- FILE_CONFLICT protection verification for file save/adopt flows.
- Incorrect `write_next_scene` action labeling.
- Overly noisy continuity warning anchors.
- SSE warning events that were easy to miss before generation completion.

### Known Issues

- Small-context models may still require stricter token truncation.
- Long-context generation can still weaken or omit individual character details.
- Continuity anchor extraction may still contain low-frequency noise.
- Slow real LLM responses still need a more complete cancel / retry experience.
- This is an alpha release and is not recommended for important long-form production drafts without backups.

## [0.1.1] - 2026-05-22

### Documentation

- Rewrote README.md for first-time users with Quick Start, commands table, and configuration reference.
- Added `docs/quick-start.md` for setup and troubleshooting.
- Added `docs/known-issues.md` for limitations and workarounds.
- Added `docs/roadmap.md` for planned features.
- Added `examples/basic-novel-project/` as a minimal example project.
- Added release readiness scripts and docs.

### Changed

- README.md now includes project structure and setup guidance.
- README.md links updated to point to docs pages.

## [0.1.0] - 2025-05-21

### Added

- Local-first AI fiction writing studio.
- Scene-level writing model (`sec-*.md` = single scene, 600-1000 Chinese characters).
- Candidate-based safe revision flow for high-risk operations.
- Lite mode and Professional mode.
- Story memory files.
- Customizable pipeline workflows through YAML.
- Demo novel project.

### Changed

- Pipeline `output_mode=overwrite` normalized to safe modes (`write_scene`, `candidate`, `append`).

### Fixed

- Pipeline overwrite/rewrite protection.
- Lite path safety.
- FileService routing for core project files.
- Materials API security hardening.
- API key leakage prevention.

[0.1.1]: https://github.com/wuyinglai/moyun-studio/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/wuyinglai/moyun-studio/releases/tag/v0.1.0
