# Roadmap / 发展路线

## v0.1.x — Stabilization & Documentation

- [x] **T6.6 — Professional 主流程 dry-run 总验收**（TaskQueue / Pipeline / Batch 三条 dry-run 链路 + Candidate + 安全边界）
- [x] **T6.6.5-plan — 真实 LLM 隔离冒烟测试方案**
- [x] **T6.7 — 产品化修复 / UI 清理**（路线图见 [docs/roadmap/t6-7-productization-roadmap.md](docs/roadmap/t6-7-productization-roadmap.md)）

- [x] v0.1.0 — Initial release with core features
- [x] v0.1.1 — Documentation and onboarding improvements
- [ ] Improve demo novel project with richer content
- [ ] Stabilize release check script across platforms
- [ ] Address non-core raw I/O files as needed
- [ ] Add more example projects (different genres)

## v0.2 — Reliability & Configuration

- Conflict detection (`expected_mtime` / `expected_hash`) for memory and material endpoints
- ConfigService for workspace-level configuration (replacing raw `.config.json` I/O)
- Route remaining raw I/O through FileService
- Deeper real LLM E2E and quality reports
- Improved error messages and user-facing diagnostics

## v0.3 — Enhanced Writing Experience

- Character relationship graph visualization
- Timeline view for story events
- Batch scene generation with progress tracking
- Custom prompt template editor in UI
- Export to standard formats (EPUB, DOCX)

## v0.4 — Collaboration & Extensibility

- Plugin system for custom pipeline nodes
- Multi-language support for UI
- Writing statistics and analytics dashboard
- Version control integration hints
- Community prompt template sharing

## Long-term Vision

Moyun Studio aims to be the best local-first AI fiction writing tool, where:

- **Writers own their data** — All files stay on your machine
- **AI assists, never replaces** — Candidate-based workflow ensures human control
- **Scenes are the unit** — Scene-level granularity matches how writers think
- **Memory persists** — Story state and context carry across sessions
- **Pipelines are customizable** — Writers can define their own AI workflows

---

Have a feature request? Open an issue on [GitHub](https://github.com/wuyinglai/moyun-studio/issues).
