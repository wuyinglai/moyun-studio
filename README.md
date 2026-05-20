# Moyun Studio / 墨韵

Local-first AI fiction studio with story memory, safe revisions, and customizable workflows.

Moyun Studio is an AI-native long-form fiction writing studio for storytellers. It combines story memory, safe AI revisions, customizable workflows, and human-in-the-loop creation.

墨韵是一个本地优先的 AI 小说创作工作台，面向长篇小说创作，支持故事记忆、安全候选稿、可配置工作流与人机协同创作。

## Features

- **Casual Mode**: Lightweight writing page for casual users, featuring opening hooks, satisfying plot points, streaming generation, candidate drafts, quality summaries, and story engine progression.
- **Professional Mode**: Workbench for advanced authors and developers, providing file tree, Prompts, pipelines, workflows, variables, snapshots, comparison, and configurable execution flows.

The current product direction is **human-AI collaborative creation**: AI handles generation, summarization, review, and candidate rewriting; authors control direction through chat, selection, confirmation, and editing; workflows connect Prompt, human nodes, file nodes, memory nodes, and quality nodes.

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

After starting, access the frontend development server URL. Backend API documentation is available at `/docs` or `/redoc`.

## First Demo

1. Start backend and frontend as above.
2. Open the web UI (typically `http://localhost:5173`).
3. Configure your LLM provider in Settings.
4. Create a new project with your preferred genre and settings.
5. Select a section to write.
6. Click "Continue / 写下一部分" to generate content.
7. Review the candidate draft before applying changes.

## LLM Configuration

Copy `.env.example` to `.env` and fill in your API Key:

```env
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

You can also configure DeepSeek, Ollama, or other LiteLLM-compatible models.

## Tech Stack

- **Backend**: FastAPI, LiteLLM, aiofiles, Pydantic, Jinja2
- **Frontend**: Vue 3, TypeScript, Vite, Pinia, Vue Router, Ant Design Vue, CodeMirror 6
- **Storage**: Local file system (no database required)
- **AI Integration**: Unified access through LiteLLM

## Project Structure

```text
backend/       FastAPI backend
frontend/      Vue 3 frontend
prompts/       System Prompt templates
tests/         E2E and auxiliary test scripts
docs/          Product, architecture, specifications, and design documents
_misc/plans/   Migration plans and phase schemes
workspace/     User project data (not committed to Git)
```

## Documentation

Start with these files to quickly understand the project:

- [AGENTS.md](AGENTS.md): AI collaboration rules, forbidden zones, GitNexus requirements.
- [CONTEXT.md](CONTEXT.md): Domain terminology.
- [docs/文档索引.md](docs/文档索引.md): Documentation navigation.
- [docs/产品架构-人机协同工作流.md](docs/产品架构-人机协同工作流.md): New product architecture.
- [docs/专业版节点化改造计划.md](docs/专业版节点化改造计划.md): Professional edition roadmap.
- [docs/功能清单.md](docs/功能清单.md): Feature definitions and execution logic.
- [docs/技术选型速查.md](docs/技术选型速查.md): Tech stack and forbidden list.
- [docs/编码规范.md](docs/编码规范.md): Coding standards.
- [docs/文件系统设计.md](docs/文件系统设计.md): Project file structure.

For complete user documentation, visit the GitHub Wiki:

https://github.com/wuyinglai/moyun-studio/wiki

## Development Commands

```bash
# Frontend build
cd frontend
npm run build

# Backend tests
python -m pytest backend/tests -q

# Backend syntax check example
python -m py_compile backend/api/lite.py backend/schemas/lite.py
```

## Important Constraints

- Do not commit `.env`, `.config.json`, or `workspace/`.
- Do not modify `_misc/archive/` - it contains historical archives.
- Read the corresponding README or context documents before modifying `backend/` or `frontend/`.
- Check the forbidden list in [docs/技术选型速查.md](docs/技术选型速查.md) after code changes.
- Follow GitNexus requirements in `AGENTS.md` for impact analysis when modifying functions, classes, or methods.

## License

MIT License