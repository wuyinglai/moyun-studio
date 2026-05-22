# Quick Start Guide / 快速开始

This guide walks you through setting up Moyun Studio from a fresh clone to writing your first scene.

## Prerequisites

| Dependency | Minimum Version | Check |
|------------|----------------|-------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 2.x | `git --version` |

## Step 1: Clone the Repository

```bash
git clone https://github.com/wuyinglai/moyun-studio.git
cd moyun-studio
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your LLM API key:

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4
LLM_API_BASE=https://api.openai.com/v1
```

### Using DeepSeek

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-deepseek-key
LLM_MODEL=deepseek-chat
LLM_API_BASE=https://api.deepseek.com/v1
```

### Using Ollama (local, no API key needed)

```env
LLM_PROVIDER=ollama
LLM_API_KEY=ollama
LLM_MODEL=llama3
LLM_API_BASE=http://localhost:11434
```

> **Windows SSL issue?** If you encounter SSL connection errors, add `MOYUN_DISABLE_PROXY_DETECTION=true` to your `.env`.

## Step 3: Start Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn backend.main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Verify: Open `http://localhost:8000/docs` in your browser — you should see the Swagger API documentation.

## Step 4: Start Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Expected output:
```
VITE v8.x.x  ready in xxxx ms

➜  Local:   http://localhost:5173/
```

## Step 5: Write Your First Scene

### Lite Mode (recommended for first-time users)

1. Open `http://localhost:5173/lite` in your browser.
2. Click **Settings** (gear icon) and verify your LLM provider is configured.
3. Enter an opening hook or select a preset.
4. Click **写下一场景** (Write Next Scene).
5. A candidate draft appears — review it, then **Adopt** to apply.

### Professional Mode

1. Open `http://localhost:5173` in your browser.
2. Click **New Project** to create a project.
3. Navigate the file tree to your chapter.
4. Use the toolbar to generate, polish, or rewrite scenes.
5. All high-risk operations generate candidates — adopt only after review.

## Using the Example Project

Copy the demo novel into your workspace:

```bash
# Windows PowerShell
Copy-Item -Recurse examples/demo-novel workspace/projects/demo-novel

# macOS / Linux
cp -r examples/demo-novel workspace/projects/demo-novel
```

Then open it from the Professional mode project list.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Activate venv: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux) |
| `LLM_API_KEY not configured` | Copy `.env.example` to `.env` and fill in your API key |
| SSL errors on Windows | Add `MOYUN_DISABLE_PROXY_DETECTION=true` to `.env` |
| Frontend can't connect to backend | Ensure backend is running on port 8000 |
| `npm install` fails | Check Node.js version (18+), try `npm cache clean --force` |
| Port already in use | Kill existing process or change port in `.env` |

## Next Steps

- Read [Known Issues](known-issues.md) for current limitations
- See [Roadmap](roadmap.md) for planned features
- Check [Changelog](changelog.md) for release history
