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

## 编码原则（精简版）

**后端**：
- 所有 API 端点用 FastAPI + `async def`
- Prompt 必须从 `workspace/prompts/` 加载（Jinja2 语法），禁止硬编码
- 所有 LLM 调用通过 LiteLLM，禁止直接用 `openai` 库
- 文件读写用 aiofiles，禁止同步 `open()`
- 配置用 pydantic-settings，禁止 `os.getenv()`
- 异常使用 `backend/core/exceptions.py` 中定义的统一异常类

**前端**：
- 所有组件用 Vue 3 Composition API + `<script setup>` + TypeScript
- 全局状态用 Pinia store，避免 props 多层透传
- API 请求用 Axios（`src/services/api.ts`），SSE 用 `useSSE.ts`
- Markdown 编辑器用 CodeMirror 6

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
