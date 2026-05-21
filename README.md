# Moyun Studio / 墨韵

Local-first AI fiction studio with story memory, safe revisions, and customizable workflows.

墨韵是一个本地优先的 AI 小说创作工作台，面向长篇小说创作，支持故事记忆、安全候选稿、可配置工作流与人机协同创作。

## Quick Start

### Backend

```bat
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

After starting, access the frontend at `http://localhost:5173`. Backend API docs at `/docs` or `/redoc`.

## Two Entry Points

- **Lite Mode** (`/lite`) — Casual writing page with opening hooks, satisfying plot points, streaming generation, and candidate drafts.
- **Professional Mode** (`/project/:id`) — Full workbench with file tree, prompts, pipelines, workflows, snapshots, and comparison.

## LLM Configuration

Copy `.env.example` to `.env` and fill in your API Key:

```env
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

Supports DeepSeek, Ollama, and other LiteLLM-compatible models.

## Example Project

A complete demo novel project is available at [`examples/demo-novel/`](examples/demo-novel/). It demonstrates the standard project structure, scene-level writing model, story memory files, and character profiles.

### Quick Start

1. Start backend and frontend.
2. Open the web UI.
3. Configure your LLM provider in Settings.
4. Create a new project or use Lite mode to pick an opening hook.
5. Click "写下一场景" to generate a scene.
6. Review the candidate draft before applying changes.

## Documentation

- [Document Index](docs/document-index.md) — Complete documentation navigation
- [AGENTS.md](AGENTS.md) — AI collaboration rules and code map
- [GitHub Wiki](https://github.com/wuyinglai/moyun-studio/wiki) — User-facing documentation

## Release Check

Run before release:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release-check.ps1
```

This script runs guardrails, backend safety tests (A-E), full backend tests, and frontend lint/build. It does **not** run real LLM E2E or require API Keys. Real LLM E2E is a separate optional check requiring `MOYUN_E2E_REAL_LLM=true`.

## Tech Stack

- **Backend**: FastAPI, LiteLLM, aiofiles, Pydantic, Jinja2
- **Frontend**: Vue 3, TypeScript, Vite, Pinia, Ant Design Vue, CodeMirror 6
- **Storage**: Local file system (no database)

## License

MIT License
