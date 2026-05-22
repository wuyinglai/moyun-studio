# Changelog

All notable changes to Moyun Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-05-22

### Documentation

- Rewrote README.md with project structure, version status, roadmap link, and improved navigation
- Added `docs/quick-start.md` — step-by-step setup walkthrough with troubleshooting
- Added `docs/known-issues.md` — known limitations, common startup failures, and workarounds
- Added `docs/roadmap.md` — planned features and milestones through v0.4
- Added `docs/changelog.md` — this file, replacing root-level CHANGELOG.md reference
- Added `examples/basic-novel-project/` — minimal example project for quick reference
- Updated `docs/releases/v0.1.1.md` — release notes for v0.1.1
- Added `_misc/scripts/verify-release.ps1` — verification script for release readiness

### Changed

- README.md now links to `docs/known-issues.md` instead of `docs/KNOWN_ISSUES.md`
- README.md now links to `docs/changelog.md` instead of root `CHANGELOG.md`
- Added project structure section to README.md
- Added version badge to README.md

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
[0.1.0]: https://github.com/wuyinglai/moyun-studio/releases/tag/v0.1.0
