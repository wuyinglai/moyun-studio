# Moyun Studio / 墨韵

Moyun Studio is a local-first AI fiction writing studio for long-form web novel creation.

墨韵是一个面向长篇小说创作的本地优先 AI 写作工作台，支持场景级写作、故事记忆、安全候选稿、Prompt/Pipeline 工作流和人机协同创作。

> Current target: `v0.2.0` Writing Quality Loop Developer Preview.
> This is an internal developer preview, not a commercial production release.

Full documentation: [GitHub Wiki](https://github.com/wuyinglai/moyun-studio/wiki)

## Current Positioning

Moyun Studio focuses on helping authors write and revise fiction at the scene level.

- Local-first: project files live under the local `workspace/` directory.
- Scene-level writing: `sec-*.md` means one scene, not a traditional chapter section.
- Candidate-first safety: AI output enters a candidate draft before it can affect official prose.
- Human-in-the-loop: users preview, revise, adopt, or discard candidate drafts.
- Developer preview: useful for dogfood, testing, and local experiments; not yet a production guarantee.

## Writing Quality Loop

The current `v0.2.0` developer preview includes the T8 writing quality loop:

- required / forbidden beats input for generation constraints;
- prompt assembly that carries beats into generate / rewrite / polish / feedback revision flows;
- beat validation metadata on candidates;
- CandidatePanel quality checks with pass / warning / unknown states;
- adopt warning confirmation for advisory warnings;
- feedback revision child candidates;
- multi-round revision lineage with parent/child relationships;
- polish conservative rules for safer small edits;
- real UI + real LLM smoke coverage.

## Candidate-only Safety Workflow

Moyun Studio treats formal prose as protected user work.

- AI-generated content does not silently overwrite official scene files.
- High-risk operations such as rewrite, polish, chat edit, more exciting, and more reasonable create candidates by default.
- Users preview candidates before adopting them.
- Official text changes only after explicit user adoption.
- Deleting a candidate does not affect official text.
- Candidate adopt remains protected by hash / mtime / FILE_CONFLICT checks.

## Core Features

- **Scene-level writing**: `chapters/vol-01/ch-001/sec-001.md` is the standard scene path.
- **Lite mode**: a simpler writing entry for fast scene generation.
- **Professional mode**: full project workbench with files, candidates, workflow panels, and prompt/pipeline tools.
- **Candidate lifecycle**: preview / adopt / delete for safe revisions.
- **Feedback revision**: generate a new child candidate from user feedback without changing the parent candidate.
- **Story memory files**: `recent-context.md`, `story-state.md`, and chapter metadata support continuity.
- **OpenAI-compatible LLM support**: use OpenAI-compatible endpoints through LiteLLM, including local services.
- **Local file storage**: no database is required.

## Requirements

| Dependency | Version |
| --- | --- |
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

## Quick Start

### 1. Clone

```bash
git clone https://github.com/wuyinglai/moyun-studio.git
cd moyun-studio
```

### 2. Configure Environment

```powershell
copy .env.example .env
```

Edit `.env` and configure your LLM provider. Do not commit `.env`.

OpenAI-compatible example:

```env
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

Local OpenAI-compatible example:

```env
LLM_PROVIDER=ollama
LLM_API_KEY=ollama
LLM_API_BASE=http://localhost:11434/v1
LLM_MODEL=qwen2.5
```

Moyun Studio supports LiteLLM-compatible providers. Keep private endpoints and API keys out of logs, screenshots, docs, and commits.

### 3. Start Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Backend API starts at `http://localhost:8000`.

### 4. Start Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend starts at `http://localhost:5173`.

### 5. Write and Review a Scene

1. Open the frontend in a browser.
2. Configure your LLM settings.
3. Create or open a project.
4. Open a scene file such as `chapters/vol-01/ch-001/sec-001.md`.
5. Generate, rewrite, polish, or revise through candidate drafts.
6. Preview the candidate and adopt only when satisfied.

## Available Commands

Frontend:

```powershell
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

Backend:

```powershell
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
pytest
```

Release/document checks:

```powershell
git diff --check
git status --short
```

## Project Structure

```text
moyun-studio/
  backend/      FastAPI backend
  frontend/     Vue 3 + TypeScript frontend
  prompts/      Prompt templates and pipeline YAML
  docs/         Product, design, testing, and release docs
  scripts/      Utility and verification scripts
  examples/     Example projects
  workspace/    Local user projects, gitignored
```

## Current Limitations

This developer preview is usable for testing and dogfood, but it has known limitations:

- Some E2E tests remain skipped and require T9.2 classification.
- Validator judgment is limited for narrative quality, terminal hooks, and subtle continuity.
- Real LLM latency depends on the selected model service and local/network conditions.
- Polish may still produce awkward phrasing in some cases.
- Candidate file writes are not yet fully atomic.

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for details.

## Release Docs

- [CHANGELOG.md](CHANGELOG.md)
- [KNOWN_ISSUES.md](KNOWN_ISSUES.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
- [v0.2.0 Release Notes Draft](docs/release/v0.2.0-release-notes-draft.md)
- [T9.1 Release Docs Report](docs/release/t9-1-release-docs-report.md)

## License

MIT License
