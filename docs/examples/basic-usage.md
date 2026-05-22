# Basic Usage / 最小使用流程

This guide walks you through the minimum steps to get Moyun Studio running and verify it works.

## Prerequisites

- Python 3.10+
- Node.js 18+
- An LLM API key (OpenAI, DeepSeek, or Ollama)

## Step 1: Configure

```bash
# From project root
cp .env.example .env
```

Edit `.env` and set your API key:

```env
LLM_API_KEY=sk-your-key-here
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

> **Using Ollama?** Set `LLM_PROVIDER=ollama`, `LLM_API_BASE=http://localhost:11434`, `LLM_MODEL=your-model-name`.

## Step 2: Start Backend

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

**Expected result**: You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Verify: Open `http://localhost:8000/docs` in your browser — you should see the Swagger API documentation.

## Step 3: Start Frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

**Expected result**:

```
VITE v8.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

## Step 4: Verify

1. Open `http://localhost:5173` in your browser.
2. You should see the Moyun Studio landing page.
3. Click the **Settings** (gear) icon and verify your LLM provider is configured.

## Step 5: Write Your First Scene

### Option A: Lite Mode (Quick Start)

1. Navigate to `/lite` (or click "Lite" in the navigation).
2. Pick an opening hook from the list.
3. Click **"写下一场景"** (Write Next Scene).
4. A candidate draft will appear — review it, then click **Adopt** to apply.

### Option B: Professional Mode

1. Click **"新建项目"** (New Project) on the home page.
2. Enter a project name and basic info.
3. Navigate the file tree to `chapters/vol-01/ch-001/sec-001.md`.
4. Click **"写下一场景"** to generate the first scene.
5. Review the candidate draft before adopting.

## What to Expect

- Each generated scene is approximately 600-1000 Chinese characters.
- High-risk operations (polish, rewrite) always generate a **candidate draft** first — your original text is never overwritten without your approval.
- Story memory files are automatically maintained in the background.

## Troubleshooting

| Problem | Check |
|---------|-------|
| Backend won't start | Virtual environment activated? `.env` file exists? |
| "API Key not configured" | Set `LLM_API_KEY` in `.env` or Settings UI |
| Frontend blank page | Backend running? Check browser console for errors |
| Generation fails | Verify API key is valid and has credits; check backend logs |
| SSL errors on Windows | Add `MOYUN_DISABLE_PROXY_DETECTION=true` to `.env` |

For more details, see [docs/KNOWN_ISSUES.md](../KNOWN_ISSUES.md).
