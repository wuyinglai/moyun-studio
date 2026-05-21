# 墨韵 (Moyun) - AI小说创作助手

墨韵是一个AI辅助小说创作平台，帮助作者管理小说项目的结构、角色、情节，并使用AI生成高质量的小说内容。

## 核心目录（AI 主要工作区）

- `backend/` — FastAPI 后端（核心，频繁修改）
- `frontend/` — Vue3 + TypeScript 前端（核心，频繁修改）
- `tests/` — 测试脚本（AI 写测试时用到）

## 辅助目录（AI 一般不需修改）

- `docs/` — 项目文档，参考用，非代码
- `_misc/` — 杂项归档和工具脚本，见下方说明

`_misc/` 子目录说明：
- `_misc/archive/` — 历史归档文件（截图、原型、备份），**禁止修改**
- `_misc/scripts/` — 工具脚本（初始化、文档生成等），按需使用
- `_misc/plans/` — 技术方案和计划文档（RFC 风格），参考用

## 禁止规则

- **禁止修改 `workspace/` 目录**（用户数据）
- **禁止修改 `_misc/archive/` 目录**（归档文件）
- **禁止修改 `.env` 文件**（敏感配置，除非用户明确要求）
- **修改 `backend/` 或 `frontend/` 前，必须先读对应目录下的 README 或上下文**
- **不要猜测文件路径，所有路径必须基于本文件声明的目录结构**
- **修改代码后检查 `docs/技术选型速查.md` 的禁止清单，确保未引入违规依赖**

## 技术栈

- **后端**: Python 3.10+, FastAPI, LiteLLM, aiofiles, Pydantic, Jinja2
- **前端**: Vue 3, TypeScript, Vite, Pinia, Vue Router, Ant Design Vue, CodeMirror 6
- **AI**: OpenAI GPT-4 / Claude / DeepSeek / Ollama（通过 LiteLLM 统一调用）
- **存储**: 本地文件系统（`workspace/projects/`），无数据库

## 分层架构规则（必须遵守）

### 后端分层

```
api/ (路由层) → core/ (服务层) → core/infra (基础设施)
```

**禁止规则：**
- **`api/` 中的路由文件禁止包含业务逻辑。** 只做三件事：参数校验、调 service、格式化响应
- **业务逻辑必须放在 `core/` 下对应的 Service 类中。** 已存在的 Service：
  - `ProjectService` → 项目 CRUD、统计计算
  - `CharacterService` → 角色 CRUD
  - `QualityService` → 质量审查
  - `GenerationService` → 生成编排
  - `FileService` → 文件 I/O
  - `LLMService` → LLM 调用
- **文件 I/O 强制走 `FileService`**，禁止 `Path.read_text()` + `json.loads()` 的同步调用
- **LLM 调用强制走 `LLMService`**，禁止直接 `litellm.acompletion()`
- 新增功能时，先判断是新建 Service 还是扩展现有 Service，**不得将逻辑塞入路由层**

### 前端分层

```
components (UI) → stores/composables (状态+逻辑) → services (通信) → API
```

**Store 职责边界（已拆分明细）：**

| Store | 只允许管 | 禁止管 |
|-------|---------|--------|
| `fileStore` | 文件 CRUD + 快照 | 任务队列、生成、审查 |
| `taskStore` | 任务生命周期 + 轮询 | 文件操作、生成 |
| `generationStore` | 生成、续写、重写、批量生成 | 文件 CRUD、聊天 |
| `reviewStore` | 质量审查 | 文件操作、生成 |
| `chatStore` | 聊天消息 + 流式传输 | 文件生成（续写/重写） |

**禁止规则：**
- **`stores/file.ts` 禁止包含任务/生成/审查相关代码**（上述表格为准）
- **`stores/chat.ts` 禁止包含 `continueWriting`/`rewriteContent`**（在 `generationStore` 中）
- **`App.vue` 禁止包含编排 watcher**（应抽取到 `composables/`）
- **禁止在组件或 store 中用 `fetch()` 调后端 API**（改用 `services/api.ts`，SSE 流除外）

### 新增功能时的分支选择

```
要加功能 → 属于哪个领域？
  ├─ 文件管理 → fileStore + FileService
  ├─ 角色设定 → characterStore(如有) + CharacterService
  ├─ 生成/续写/重写 → generationStore + GenerationService
  ├─ 质量审查 → reviewStore + QualityService
  ├─ 项目管理 → projectStore + ProjectService
  ├─ 聊天 → chatStore + PipelineRunner(后端 chat 管线)
  └─ 新领域 → 新建 store + 新建 core/*Service
```

详细编码规范见 `docs/编码规范.md`。

## 关键文档索引

| 文档 | 用途 | 必须先读 |
|------|------|----------|
| `docs/功能清单.md` | 功能定义和执行逻辑，AI 编码的核心依据 | ✅ |
| `docs/Prompt模板说明.md` | Prompt 模板系统规范 | 修改 prompt 时 |
| `docs/技术选型速查.md` | 技术栈和禁止清单 | ✅ |
| `docs/编码规范.md` | 详细编码规范 | 写代码前 |
| `docs/文件系统设计.md` | 文件存储结构和命名规则 | 涉及文件操作时 |
| `docs/后端架构设计.md` | 后端架构概览 | 了解整体设计时 |
| `docs/开发步骤.md` | 迭代开发流程 | 了解项目流程时 |
| `CONTEXT.md` | 领域术语定义 | ✅ |
| `docs/agents/` | Agent skills 说明 | 使用 agent 时 |

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

## Agent skills

### Issue tracker

本地 markdown 文件追踪，位于 `_misc/archive/scratch/` 目录。见 `docs/agents/issue-tracker.md`。

### Triage labels

使用标准的5种状态标签：needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix。见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文布局，CONTEXT.md 在根目录，ADR 在 `docs/adr/`。见 `docs/agents/domain.md`。

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
