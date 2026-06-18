# v0.2.2b Docs Consolidation + Known Issues Update Report

## 基本信息

| 字段 | 值 |
|------|-----|
| Task Title | v0.2.2b — Docs Consolidation + Known Issues Update |
| Risk Level | Risk C / Documentation Consolidation |
| Mode | Docs Cleanup + Known Issues Update + No Product Code |
| Branch | main |
| Base Commit | e85836a |
| Date | 2026-06-17 |

---

## 1. 当前 commit

```text
e85836a chore: clean up guardrails allowlist noise
```

---

## 2. 更新了哪些文档

| 文件 | 更新内容 |
|------|----------|
| `docs/known-issues.md` | 新增 Version Status 表格 + Recently Resolved 表格（R1-R4） |
| `docs/roadmap.md` | 更新 v0.2 section，标记 v0.2.2a/v0.2.2b 为 done，v0.2.2 为 planned |
| `docs/roadmaps/t10-v0-2-2-scope-decision.md` | 补充 v0.2.2a/v0.2.2b 状态 |

---

## 3. known issues 当前状态

### Version Status

| Version | Status | Date |
|---------|--------|------|
| v0.2.0 | Released | 2026-06-16 |
| v0.2.1 | Released | 2026-06-17 |
| v0.2.2a | Done | 2026-06-17 (Guardrails Allowlist Cleanup) |
| v0.2.2b | Done | 2026-06-17 (Docs Consolidation + Known Issues Update) |
| v0.2.2 | Planned | Maintenance release candidate |

### Recently Resolved

| # | Issue | Resolution | Version |
|---|-------|------------|---------|
| R1 | Guardrails existing noise | All violations classified and allowlisted (B/D/C, no real risk) | v0.2.2a |
| R2 | T9.4 continuity metadata dogfood | `create_candidate()` auto-fetches continuity anchors from service | v0.2.1 |
| R3 | T9.4 continuity prompt test path | Absolute path resolution instead of relative path lookup | v0.2.1 |
| R4 | Pipeline prompt rendering contract | Archive issues resolved; prompt templates use consistent pattern | v0.2.1 (T9.5) |

### Still Open (Non-blocking)

| # | Issue | Priority | Target |
|---|-------|----------|--------|
| NB1 | 内存端点无冲突检测 | P2 | v0.2+ |
| NB2 | 部分非核心 API 使用同步 I/O | P3 | v0.2+ |
| NB3 | 真实 LLM E2E 为可选 | P2 | v0.2+ |
| NB4 | 工作区 `.config.json` 明文存储 API Key | P2 | v0.2+ |
| NB5 | 多标签页编辑无冲突保护 | P3 | v0.2+ |

---

## 4. v0.2.2 剩余范围

根据 `docs/roadmaps/t10-v0-2-2-scope-decision.md`，v0.2.2 原计划范围：

| # | 项目 | 状态 |
|---|------|------|
| V1 | Guardrails allowlist cleanup | ✅ Done (v0.2.2a) |
| V2 | T9.4 文档合并 | ✅ Done (v0.2.2b - known issues + roadmap 更新) |
| V3 | Release notes polish | Pending (v0.2.2 release) |
| V4 | Known issues cleanup | ✅ Done (v0.2.2b) |
| V6 | T9.4a-b-c 文档补充 | N/A - 已合并到 final closure report |

**v0.2.2 剩余工作**：
- Release notes polish（可选）
- Minor smoke test improvements（可选）
- v0.2.2 tag + GitHub Release（正式维护版发布）

---

## 5. 是否建议进入 v0.2.2 RC

**建议**：✅ 可以进入 v0.2.2 RC 准备

理由：
1. v0.2.2a guardrails cleanup 已完成
2. v0.2.2b 文档整理已完成
3. known issues 状态清晰
4. roadmap 已更新
5. 无产品代码变更
6. 剩余工作仅为 release notes polish + tag

---

## 6. 下一步建议

| 优先级 | 任务 | 风险 | 说明 |
|--------|------|------|------|
| 1 | v0.2.2 release notes polish | Risk C | 可选，更新 docs/releases/v0.2.2-rc-notes.md |
| 2 | v0.2.2 tag + GitHub Release | Risk A | 正式维护版发布 |
| 3 | T10.1 Quality Explanation UI | Risk B | T10 阶段第一个功能 |

---

## 7. 结论

v0.2.2b 任务已完成：

- ✅ 文档已更新（known issues + roadmap + scope decision）
- ✅ known issues 状态清楚
- ✅ v0.2.2a 已标记完成
- ✅ v0.2.2 剩余范围清楚
- ✅ 不改产品代码
- ✅ diff check passed
- ✅ git clean

---

## 文档归档

本报告归档于：`docs/roadmaps/v0-2-2b-docs-known-issues-update.md`