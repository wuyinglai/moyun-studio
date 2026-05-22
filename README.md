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

## Quick Start

> Detailed guide: [docs/quick-start.md](docs/quick-start.md)

### 1. Clone & Install

```bash
git clone https://github.com/wuyinglai/moyun-studio.git
cd moyun-studio
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your LLM API Key:

```env
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

Supports DeepSeek, Ollama, and other LiteLLM-compatible providers.

### 3. Start Backend

```bash
cd backend
python -m venv venv

# Windows
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
