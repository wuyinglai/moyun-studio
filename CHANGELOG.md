# Changelog

All notable changes to Moyun Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Rewrote README.md for first-time users with Quick Start, commands table, and configuration reference
- Added `docs/quick-start.md` — step-by-step setup walkthrough with troubleshooting
- Added `docs/known-issues.md` — known limitations, common startup failures, and workarounds
- Added `docs/roadmap.md` — planned features and milestones through v0.4
- Added `docs/changelog.md` — changelog following Keep a Changelog format
- Added `examples/basic-novel-project/` — minimal example project for quick reference
- Added `scripts/verify-release.ps1` — verification script for release readiness
- Enhanced `.env.example` with section comments and proxy workaround
- Added `docs/known-issues.md` — known limitations, common startup failures, and workarounds
- Added `docs/RELEASE_CHECKLIST.md` — pre-release verification steps
- Added `docs/examples/basic-usage.md` — minimal usage walkthrough

### Changed
- README.md now includes project structure section and version badge
- README.md links updated to point to `docs/known-issues.md` and `docs/changelog.md`

## [0.1.0] - 2025-05-21

### Added
- Local-first AI fiction writing studio — all data stays on your machine
- Scene-level writing model (`sec-*.md` = single scene, 600-1000 Chinese characters)
- Candidate-based safe revision flow for high-risk operations (polish, rewrite, chat edit)
- Lite mode (`/lite`) for quick writing and Professional mode (`/project/:id`) for full workbench
- Story memory system (`recent-context.md`, `story-state.md`, `ch-meta.json`)
- Customizable pipeline workflows via YAML configuration
- Demo novel project at `examples/demo-novel/`
- Release check script at `scripts/release-check.ps1`

### Changed
- Pipeline `output_mode=overwrite` normalized to safe modes (`write_scene`, `candidate`, `append`)

### Fixed
- **Package A**: Pipeline overwrite/rewrite protection — legacy modes can no longer directly write existing scene files
- **Package B**: Lite path safety — path traversal validation for `project_id`, `current_file`, `target_file`, `output_file`
- **Package C**: FileService routing for core project files (`story-state.md`, `style-guide.md`, `meta.json`, `recent-context.md`, `.chapters-meta.json`)
- **Package D**: Materials API security — FileService routing, TrashService for deletion, path traversal validation
- **Package E**: API Key leakage prevention — redact `sk-*` patterns from logs, gitignore test artifacts

[0.1.1]: https://github.com/wuyinglai/moyun-studio/compare/v0.1.0...v0.1.1
[Unreleased]: https://github.com/wuyinglai/moyun-studio/compare/v0.1.1...HEAD
[0.1.0]: https://github.com/wuyinglai/moyun-studio/releases/tag/v0.1.0
