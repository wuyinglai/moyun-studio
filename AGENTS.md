# Moyun Studio / 墨韵

Moyun Studio is a local-first AI fiction writing studio with scene-level writing, story memory, safe candidate revisions, and customizable workflows.

墨韵是一个本地优先的 AI 小说创作工作台，支持场景级写作、故事记忆、安全候选稿、Prompt/Pipeline 工作流和人机协同创作。

---

## AI Reading Order

Before editing code, read:

1. **AGENTS.md** (this file) — Product rules, forbidden zones, code map
2. **docs/code-map.md** — 12 feature areas mapped to files
3. **docs/frontend-user-flow.md** — User flows for all routes
4. **docs/contracts/scene-path-contract.md** — Scene path rules (sec = scene)
5. **Relevant contract under docs/contracts/** — api-contract, event-contract, candidate-contract

Do not rely on archived documents unless explicitly asked.

---

## Non-negotiable Product Rules / 不可违反的产品规则

These rules are enforced at the product level. Violating any of them will break user data or core workflows.

1. **`sec-*.md` 永远表示单场景，不是传统章节。** 场景是写作和生成的最小单位。
2. **默认场景长度约 800 中文字，允许范围 600-1000 字。**
3. **默认每章 5 个场景，每卷 12 章。**
4. **`chapters/vol-01/ch-001/sec-001.md` 是标准场景路径。**
5. **polish / rewrite / chat edit / more exciting / more reasonable 等高风险修改默认必须生成 candidate，不直接覆盖正式正文。**
6. **写下一部分只应写入新场景或空场景；如果目标场景已有内容，应生成 candidate 或要求确认。**
7. **Candidate adopt 前必须检查 `base_hash` / `base_mtime`，采用前必须写 revision-log。**
8. **`candidate.source_path` 必须是项目内相对路径，不能带重复 project_id。**
9. **`file.updated` / SSE 事件不得携带完整正文 content。**
10. **API 层不得直接使用 `project_dir / req.path` 拼接文件路径，所有文件操作必须走 FileService。**
11. **前端保存文件必须携带 `expected_mtime` / `expected_hash`，并处理 `FILE_CONFLICT`。**
12. **API Key 不得写入 localStorage、日志、截图、测试报告、E2E 质量报告。**
13. **Lite 入口和 Professional 主工作台入口都必须同时考虑，不要只改其中一个。**
14. **修改用户流程时必须同步 `docs/frontend-user-flow.md` 和 Wiki。**

---

## 禁止规则

- **禁止修改 `workspace/` 目录**（用户数据）
- **禁止修改 `_misc/archive/` 目录**（归档文件）
- **禁止修改 `.env` 文件**（敏感配置，除非用户明确要求）
- **修改 `backend/` 或 `frontend/` 前，必须先读对应目录下的 README 或上下文**
- **不要猜测文件路径，所有路径必须基于本文件声明的目录结构**
- **修改代码后检查 `docs/技术选型速查.md` 的禁止清单，确保未引入违规依赖**

---

## 核心目录（AI 主要工作区）

- `backend/` — FastAPI 后端（核心，频繁修改）
- `frontend/` — Vue3 + TypeScript 前端（核心，频繁修改）
- `prompts/` — Prompt 模板和 Pipeline YAML（系统级，修改需谨慎）
- `tests/` — 测试脚本（AI 写测试时用到）

## 辅助目录（AI 一般不需修改）

- `docs/` — 项目文档，参考用，非代码
- `_misc/` — 杂项归档和工具脚本，见下方说明

`_misc/` 子目录说明：
- `_misc/archive/` — 历史归档文件（截图、原型、备份），**禁止修改**
- `_misc/scripts/` — 工具脚本（初始化、文档生成等），按需使用
- `_misc/plans/` — 技术方案和计划文档（RFC 风格），参考用

---

## 技术栈

- **后端**: Python 3.10+, FastAPI, LiteLLM, aiofiles, Pydantic, Jinja2
- **前端**: Vue 3, TypeScript, Vite, Pinia, Vue Router, Ant Design Vue, CodeMirror 6
- **AI**: OpenAI GPT-4 / Codex / DeepSeek / Ollama（通过 LiteLLM 统一调用）
- **存储**: 本地文件系统（`workspace/projects/`），无数据库

---

## 编码原则

**后端**：
- 所有 API 端点用 FastAPI + `async def`
- Prompt 必须从 `prompts/` 目录加载（Jinja2 语法），禁止硬编码
- 所有 LLM 调用通过 LiteLLM，禁止直接用 `openai` 库
- 文件读写用 aiofiles，禁止同步 `open()`
- 配置用 pydantic-settings，禁止 `os.getenv()`
- 异常使用 `backend/core/exceptions.py` 中定义的统一异常类
- Pipeline YAML 启动时校验（`backend/core/pipeline_validator.py`）
- LLM 熔断器防止连续失败拖慢系统（`backend/core/llm_circuit_breaker.py`）

**前端**：
- 所有组件用 Vue 3 Composition API + `<script setup>` + TypeScript
- 全局状态用 Pinia store，避免 props 多层透传
- API 请求用 Axios（`src/services/api.ts`），SSE 用 `useSSE.ts`
- Markdown 编辑器用 CodeMirror 6
- ErrorBoundary 包裹高风险区域（编辑器、右侧面板、Lite 编辑区），防止单组件崩溃导致白屏
- SSE 心跳 15 秒间隔，45 秒超时自动重连

详细编码规范见 `docs/编码规范.md`。

---

## Where to Modify / 常见任务改哪里

### Project management
- Frontend: `frontend/src/stores/project.ts`, `frontend/src/modules/project/`
- Backend: `backend/api/projects.py`, `backend/core/project_service.py`

### File editing
- Frontend: `frontend/src/stores/file.ts`, `frontend/src/components/editor/`
- Backend: `backend/api/files.py`, `backend/core/file_ops.py`

### Scene path
- Frontend: `frontend/src/modules/scene/scenePath.ts`
- Backend: `backend/application/scene_service.py`

### Candidate / safe revisions
- Frontend: `frontend/src/components/right-panel/CandidatePanel.vue`, `frontend/src/modules/candidate/`
- Backend: `backend/core/candidate_service.py`, `backend/api/candidates.py`

### Pipeline
- Backend: `backend/core/pipeline.py`, `backend/application/pipeline/`, `prompts/pipeline/`
- Frontend: `frontend/src/stores/pipeline.ts`, `frontend/src/components/editor/EditorToolbar.vue`

### Lite writing
- Frontend: `frontend/src/views/LiteWritingView.vue`
- Backend: `backend/api/lite.py`

### Story memory
- Backend: `backend/application/memory_service.py`
- Files: `recent-context.md`, `story-state.md`, `ch-meta.json`

### SSE
- Frontend: `frontend/src/composables/useSSE.ts`, `frontend/src/modules/sse/`
- Backend: `backend/core/event_bus.py`, `backend/api/sse.py`, `backend/main.py` (bridge)

### LLM
- Backend: `backend/core/llm.py`, `backend/core/llm_circuit_breaker.py`
- Frontend: `frontend/src/stores/llm.ts`, settings UI

---

## Before Editing Checklist

### Before editing backend
- Read related service and API file
- Run GitNexus impact analysis if available
- Do not bypass FileService
- Do not introduce direct synchronous file IO
- Run `py_compile` and `pytest`

### Before editing frontend
- Check both Lite and Professional entry
- Do not hardcode API paths in components
- Do not duplicate scene path logic
- Run `lint`, `build`, and relevant E2E

### Before editing prompts
- Keep `sec` = scene (not section, not chapter)
- Do not ask model to generate whole chapter body directly
- Keep scene output around 600-1000 Chinese characters
- High-risk rewrite/polish should preserve candidate workflow

---

## 关键文档索引

| 文档 | 用途 | 必须先读 |
|------|------|----------|
| `docs/功能清单.md` | 功能定义和执行逻辑，AI 编码的核心依据 | Yes |
| `docs/Prompt模板说明.md` | Prompt 模板系统规范 | 修改 prompt 时 |
| `docs/技术选型速查.md` | 技术栈和禁止清单 | Yes |
| `docs/编码规范.md` | 详细编码规范 | 写代码前 |
| `docs/文件系统设计.md` | 文件存储结构和命名规则 | 涉及文件操作时 |
| `docs/后端架构设计.md` | 后端架构概览 | 了解整体设计时 |
| `docs/frontend-user-flow.md` | 前端用户流程 | 修改用户流程时 |
| `docs/contracts/scene-path-contract.md` | 场景路径契约 | 涉及场景路径时 |
| `docs/contracts/api-contract.md` | API 契约（文件读写、冲突检测） | 涉及 API 时 |
| `docs/contracts/event-contract.md` | SSE 事件契约 | 涉及事件时 |
| `docs/contracts/candidate-contract.md` | 候选稿契约 | 涉及候选稿时 |
| `docs/document-index.md` | 文档总索引 | 查找文档时 |
| `CONTEXT.md` | 领域术语定义 | Yes |
| `docs/agents/` | Agent skills 说明 | 使用 agent 时 |

---

## 快速开始

```bash
# 后端启动
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # 填入 API Key
uvicorn backend.main:app --reload

# 前端启动
cd frontend
npm install
npm run dev
```

API 文档：启动后端后访问 `/docs`（Swagger）或 `/redoc`

---

## Agent skills

### Issue tracker

本地 markdown 文件追踪，位于 `_misc/archive/scratch/` 目录。见 `docs/agents/issue-tracker.md`。

### Triage labels

使用标准的5种状态标签：needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix。见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文布局，CONTEXT.md 在根目录，ADR 在 `docs/adr/`。见 `docs/agents/domain.md`。

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **moyun-studio** (11043 symbols, 19251 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/moyun-studio/context` | Codebase overview, check index freshness |
| `gitnexus://repo/moyun-studio/clusters` | All functional areas |
| `gitnexus://repo/moyun-studio/processes` | All execution flows |
| `gitnexus://repo/moyun-studio/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
