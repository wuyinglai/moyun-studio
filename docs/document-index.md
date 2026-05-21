# Document Index

> Last updated: 2026-05-21

This index categorizes all documentation for AI agents and maintainers.

## AI Must Read

Read these before editing any code:

- [AGENTS.md](../AGENTS.md) — Product rules, forbidden zones, code map, editing checklist
- [CONTEXT.md](../CONTEXT.md) — Domain terminology
- [code-map.md](code-map.md) — 12 feature areas mapped to frontend/backend files
- [frontend-user-flow.md](frontend-user-flow.md) — User flows for all 4 routes
- [功能清单.md](功能清单.md) — Feature definitions and execution logic
- [技术选型速查.md](技术选型速查.md) — Tech stack and prohibited dependencies
- [编码规范.md](编码规范.md) — Coding standards
- [文件系统设计.md](文件系统设计.md) — File storage structure and naming rules
- [后端架构设计.md](后端架构设计.md) — Backend architecture overview
- [Prompt模板说明.md](Prompt模板说明.md) — Prompt template system
- [产品架构-人机协同工作流.md](产品架构-人机协同工作流.md) — New architecture direction
- [专业版节点化改造计划.md](专业版节点化改造计划.md) — Professional edition migration plan
- [agents/domain.md](agents/domain.md) — Domain doc consumption pattern

## Contracts

Formal interface contracts that must be checked before cross-system changes:

- [contracts/scene-path-contract.md](contracts/scene-path-contract.md) — Scene path rules (sec = scene, path format, defaults)
- [contracts/api-contract.md](contracts/api-contract.md) — File API, conflict detection, safety rules
- [contracts/event-contract.md](contracts/event-contract.md) — SSE event format, file.updated rules, heartbeat
- [contracts/candidate-contract.md](contracts/candidate-contract.md) — Candidate lifecycle, adopt safety, source_path rules
- [adr/0001-架构优化-服务解耦与职责分离.md](adr/0001-架构优化-服务解耦与职责分离.md) — Service decoupling ADR
- [adr/2026-05-20-人机协同节点架构.md](adr/2026-05-20-人机协同节点架构.md) — Node-based architecture ADR

## Developer Docs

- [开发步骤.md](开发步骤.md) — Iterative development model and phases
- [产品说明.md](产品说明.md) — Product overview and UI layout
- [代码分析与改进建议.md](代码分析与改进建议.md) — Known issues and improvement priorities
- [前端功能清单_完整版V2.md](前端功能清单_完整版V2.md) — Detailed frontend feature checklist
- [agents/issue-tracker.md](agents/issue-tracker.md) — Local issue tracking system
- [agents/triage-labels.md](agents/triage-labels.md) — Issue triage labels
- [superpowers/plans/2026-05-14-code-improvements-plan.md](superpowers/plans/2026-05-14-code-improvements-plan.md) — Code improvement tasks

## Release Docs

- [功能测试报告.md](功能测试报告.md) — Feature test report
- [手动功能测试指南.md](手动功能测试指南.md) — Manual testing guide
- [history/ux-audit-report-2026-05-14.md](history/ux-audit-report-2026-05-14.md) — UX audit report

## Archive

Moved to [archive/](archive/). Do not rely on archived documents unless explicitly asked.

| Archived File | Reason |
|---|---|
| [archive/API契约.md](archive/API契约.md) | Superseded by FastAPI OpenAPI docs |
| [archive/技术选型与依赖.md](archive/技术选型与依赖.md) | Superseded by 技术选型速查.md |
| [archive/工作流引擎设计.md](archive/工作流引擎设计.md) | Superseded by 产品架构-人机协同工作流.md |
| [archive/项目完整文档.html](archive/项目完整文档.html) | Generated snapshot, inherently outdated |
| [archive/项目概览.html](archive/项目概览.html) | Generated snapshot, inherently outdated |
| [archive/api-README.md](archive/api-README.md) | Empty placeholder |
| [archive/features-README.md](archive/features-README.md) | Empty placeholder |

## History

Historical materials in [history/](history/) — not authoritative, kept for reference only.
