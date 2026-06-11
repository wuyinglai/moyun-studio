# Moyun Studio / 墨韵

**Local-first AI fiction writing studio** — 本地优先的 AI 小说创作工作台，支持场景级写作、故事记忆、安全候选稿与人机协同创作。

所有数据留在你的机器上，无需云数据库、无需注册账号。

> **Current version: v0.1.1** — Maintenance release. See [Release Notes](docs/releases/v0.1.1.md) and [Changelog](docs/changelog.md).

## Core Features

- **Scene-level writing** — `sec-*.md` = 单场景（600-1000 字），写作和生成的最小单位
- **Candidate-based safe revision** — 润色/重写等高风险操作生成候选稿，审核后才覆盖正文
- **Story memory** — 自动维护 `recent-context.md`、`story-state.md` 等记忆文件
- **Two entry points** — Lite 快写模式 + Professional 全功能工作台
- **Customizable pipelines** — YAML 定义 Prompt 工作流，支持多步生成
- **Local file storage** — 零数据库，所有项目文件都在本地 `workspace/` 目录

## Requirements

| Dependency | Version |
|------------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

## Default Safety Behavior

> ⚠️ **These defaults protect your data and API credits. Please read before starting.**
>
> - **默认不调用真实 LLM** — AI 功能需显式配置 `LLM_API_KEY` 才生效；未配置时所有生成操作使用 dry-run（模拟）。
> - **高风险操作默认生成 candidate，不覆盖正文** — polish / rewrite / chat-edit 等高风险修改仅生成候选稿，需人工审核后才覆盖正文。
> - **dry-run 不写入任何文件** — 模拟生成仅在内存中运行，不读写 `workspace/`。
> - **真实 LLM smoke 默认关闭** — `ALLOW_REAL_LLM_SMOKE` 默认为 `false`；即使开启，也仅限 `project_id` 以 `__llm_smoke_` 为前缀的隔离项目。
> - **Batch 真实 smoke 永久禁止** — 批量生成链路不参与真实 LLM 冒烟。
> - **`.env` 不提交** — 已加入 `.gitignore`，请勿把 API Key 放入版本控制。

## Quick Start

> Detailed guide: [docs/quick-start.md](docs/quick-start.md)

### 1. Clone & Install

```bash
git clone https://github.com/wuyinglai/moyun-studio.git
cd moyun-studio
```

### 2. Configure Environment

```bash
# Windows PowerShell
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Edit `.env` and fill in your LLM API Key:

```env
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

**本地 LLM 示例（Ollama 等 OpenAI-compatible 服务）：**

```env
LLM_PROVIDER=ollama
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5
LLM_API_BASE=http://localhost:11434/v1
```

Supports DeepSeek, Ollama, and other LiteLLM-compatible providers.

> 🛡️ **安全提示**：`.env` 包含 API Key，已加入 `.gitignore`，**请勿提交**到版本控制。

### 3. Start Backend

```bash
cd backend
python -m venv venv

# Windows PowerShell
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Backend API starts at `http://localhost:8000`. API docs at `/docs` (Swagger) or `/redoc`.

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend starts at `http://localhost:5173`.

### 5. Write Your First Scene

1. Open `http://localhost:5173` in your browser.
2. Configure your LLM provider in **Settings** (gear icon).
3. Choose an entry point:
   - **Lite Mode** (`/lite`) — Pick an opening hook, click "写下一场景"
   - **Professional Mode** — Create a project, navigate the file tree
4. Review the generated candidate draft before applying changes.

## Available Commands

### Frontend (`cd frontend`)

| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies |
| `npm run dev` | Start dev server (port 5173) |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Run ESLint with auto-fix |

### Backend (`cd backend`, with venv activated)

| Command | Description |
|---------|-------------|
| `pip install -r requirements.txt` | Install dependencies |
| `uvicorn backend.main:app --reload` | Start dev server (port 8000) |
| `pytest` | Run tests |
| `ruff check .` | Lint |

## Project Structure

```
moyun-studio/
├── backend/               # FastAPI backend
│   ├── api/               # API endpoints
│   ├── application/       # Application services (scene, memory, pipeline)
│   ├── core/              # Core services (LLM, file ops, candidates, events)
│   ├── domain/            # Domain models and events
│   ├── models/            # Pydantic models
│   ├── schemas/           # Request/response schemas
│   ├── policies/          # Business policies (candidate, generation output)
│   ├── tests/             # Backend tests
│   └── config.py          # Configuration (pydantic-settings)
├── frontend/              # Vue 3 + TypeScript frontend
│   ├── src/
│   │   ├── components/    # Vue components (editor, chat, modals, panels)
│   │   ├── composables/   # Composables (SSE, auto-save, keyboard shortcuts)
│   │   ├── modules/       # Feature modules (candidate, scene, pipeline, SSE)
│   │   ├── stores/        # Pinia stores
│   │   ├── views/         # Page views (LiteWritingView)
│   │   └── services/      # API service layer
│   └── tests/             # E2E tests (Playwright)
├── prompts/               # Prompt templates and pipeline YAML
│   ├── blocks/            # Reusable prompt blocks
│   ├── generate/          # Generation prompts
│   ├── pipeline/          # Pipeline definitions (YAML + prompts)
│   ├── extract/           # Extraction prompts
│   ├── review/            # Quality review prompts
│   ├── transform/         # Transform prompts (polish, shorten, expand)
│   └── templates/         # File templates (ch-meta, story-state, etc.)
├── examples/              # Example projects
│   └── demo-novel/        # Demo: "黑塔信号" (near-future suspense)
├── docs/                  # Documentation
├── scripts/               # Utility scripts (release check, guardrails)
└── workspace/             # User data (gitignored, created at runtime)
```

## Configuration

All configuration is managed via `.env` file (copy from `.env.example`). Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | (empty) | Your LLM API key — **required for AI features** |
| `LLM_API_BASE` | (empty) | API base URL (e.g. `https://api.openai.com/v1`) |
| `LLM_MODEL` | `gpt-4` | Default model name |
| `LLM_PROVIDER` | `openai` | Provider: `openai`, `anthropic`, `ollama`, `custom` |
| `DEBUG` | `false` | Enable debug logging |
| `WORKSPACE_PATH` | `./workspace` | Project data directory |
| `ALLOW_REAL_LLM_SMOKE` | `false` | 允许真实 LLM 冒烟测试（需 `__llm_smoke_*` 前缀项目，普通用户请勿开启） |
| `LLM_SMOKE_MAX_TOKENS` | `300` | 真实 LLM 冒烟测试 max_tokens 上限（1-1024） |

> 📌 **变量名说明**：`backend/config.py` 中的 Settings **未设置 `env_prefix`**，因此环境变量直接使用 `ALLOW_REAL_LLM_SMOKE`（非 `MOYUN_*` 前缀）。部分历史文档提及 `MOYUN_ALLOW_REAL_LLM_SMOKE` 已过时。
>
> 例外：`MOYUN_DISABLE_PROXY_DETECTION` 由 `backend/main.py` 直接读取 `os.environ`，使用 `MOYUN_` 前缀。

Full configuration reference: [backend/config.py](backend/config.py)

## Example Project

A complete demo novel is at [`examples/demo-novel/`](examples/demo-novel/):

- **Genre**: Near-future suspense (近未来悬疑)
- **Title**: 黑塔信号 (Black Tower Signal)
- Demonstrates standard project structure and scene-level writing model

A minimal example project is at [`examples/basic-novel-project/`](examples/basic-novel-project/):

- Minimal project structure for quick reference
- Includes `meta.json`, `outline.md`, and one scene file

To use either, copy into your workspace:

```powershell
Copy-Item -Recurse examples/demo-novel workspace/projects/demo-novel
```

## FAQ / 常见问题

### Q1: 端口占用（Port 8000 / 5173 被占用）

Windows:
```powershell
# 查看占用端口的进程
netstat -ano | findstr :8000
# 杀进程
taskkill /PID <PID> /F
```

macOS / Linux:
```bash
lsof -i :8000
kill -9 <PID>
```

### Q2: 代理影响 git push / LLM 连接问题

Windows 下如果遇到 `git push 或 LLM 调用报 SSL 错误，可临时禁用系统代理检测：

```env
MOYUN_DISABLE_PROXY_DETECTION=true
```

### Q3: 真实 LLM smoke 变量名到底是哪个？

主配置变量名：`ALLOW_REAL_LLM_SMOKE`（**非** `MOYUN_ALLOW_REAL_LLM_SMOKE`）。`backend/config.py` 中的 Settings 未设置 `env_prefix`，直接读取。

> 前端 E2E 测试用 `process.env.MOYUN_ALLOW_REAL_LLM_SMOKE`（前端自有命名空间，独立于后端）。

### Q4: project_id 和 project name 有什么区别？

- **project_id**：UUID[:8] — 系统内部使用，由前端自动生成。
- **project name**：用户可读名称，在创建项目时自定义。
- 真实 LLM smoke 需要 project_id 以 `__llm_smoke_` 为前缀的隔离项目，并非普通创建的项目。

### Q5: 生成按钮点了没反应？

1. 检查 `.env` 是否有 `LLM_API_KEY` 了吗？没有配置 API Key 时使用 dry-run（模拟）。
2. 检查浏览器 Console 控制台，可能有错误提示。
3. 检查 `workspace/` 是否存在。

## Known Issues

See [docs/known-issues.md](docs/known-issues.md) for current limitations and workarounds.

## Changelog

See [docs/changelog.md](docs/changelog.md) for release history.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for planned features and milestones.

## Documentation

- [Quick Start Guide](docs/quick-start.md) — Step-by-step setup walkthrough
- [Known Issues](docs/known-issues.md) — Current limitations and workarounds
- [Changelog](docs/changelog.md) — Release history
- [Roadmap](docs/roadmap.md) — Planned features
- [Document Index](docs/document-index.md) — Complete documentation navigation
- [Release Checklist](docs/RELEASE_CHECKLIST.md) — Pre-release verification steps
- [Release Preflight](docs/release-preflight.md) — Pre-release tag and CLI checks
- [v0.1.1 Release Notes](docs/releases/v0.1.1.md)
- [v0.1.0 Release Notes](docs/releases/v0.1.0.md)

## Tech Stack

- **Backend**: FastAPI, LiteLLM, aiofiles, Pydantic, Jinja2
- **Frontend**: Vue 3, TypeScript, Vite, Pinia, Ant Design Vue, CodeMirror 6
- **Storage**: Local file system (no database)

## License

MIT License
