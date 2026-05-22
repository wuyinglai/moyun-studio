# Known Issues / 已知问题

This document tracks current limitations, common failure modes, and workarounds.

## Current Limitations

### 1. No conflict detection on memory/material endpoints

`story_state`, `style_guide`, `recent_context`, `workflows`, and `materials` endpoints do not yet expose `expected_mtime` / `expected_hash` parameters. FileService supports it internally, but the API layer does not validate concurrent edits.

**Impact**: Safe for single-user local-first usage. May cause silent overwrites if the same file is edited from multiple browser tabs.

**Plan**: v0.2 will add conflict detection to these endpoints.

### 2. Some non-core API files still use raw I/O

`llm.py`, `lite.py`, `prompts.py`, `feedback.py`, `tokens.py`, `wizard.py`, `projects.py`, `revision_log.py`, `backup.py`, and `config.py` still use `Path.read_text()` / `Path.write_text()`. These handle workspace-level config, prompt templates, and initialization — not core project memory files.

**Impact**: Low risk for local-first single-user usage. These files are not subject to concurrent edit scenarios.

**Plan**: Future classification and routing through FileService as needed.

### 3. Real LLM E2E is optional

Not part of the default release check. Requires explicit environment variable `MOYUN_E2E_REAL_LLM=true` and a real API key.

**Impact**: E2E coverage for AI generation features is limited to mock tests by default.

**Plan**: v0.2 will improve real LLM E2E coverage.

### 4. Workspace `.config.json` stores API keys locally

This is intentional for a local-first application. The file must remain gitignored.

**Impact**: API keys are stored in plaintext on the local machine. Do not commit `.config.json` to version control.

**Plan**: v0.2 will introduce ConfigService for more secure configuration management.

## Common Startup Failures

### Backend fails to start: `ModuleNotFoundError`

**Cause**: Virtual environment not activated or dependencies not installed.

**Fix**:
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
pip install -r requirements.txt
```

### Backend fails to start: `LLM_API_KEY not configured`

**Cause**: `.env` file missing or API key not filled in.

**Fix**:
```bash
cp .env.example .env
# Edit .env and set LLM_API_KEY
```

Note: The backend will start without an API key, but AI generation features will not work until one is configured.

### Backend SSL/connection errors on Windows

**Cause**: Windows proxy settings interfering with aiohttp/httpx SSL connections.

**Fix**: Add to `.env`:
```env
MOYUN_DISABLE_PROXY_DETECTION=true
```

### Frontend fails: `npm install` errors

**Cause**: Node.js version too old or npm cache corrupted.

**Fix**:
```bash
# Check Node.js version (requires 18+)
node --version

# Clear npm cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Frontend fails: `vite build` type errors

**Cause**: TypeScript strict checks catching type mismatches.

**Fix**: Run `npm run build` to see specific errors. Most warnings are non-blocking. If build fails, check the error message for the specific file and line.

### Frontend cannot connect to backend

**Cause**: Backend not running, or running on a different port.

**Fix**:
1. Verify backend is running: `curl http://localhost:8000/docs`
2. Check CORS settings in `.env` if accessing from a non-default origin
3. Default backend port is 8000, frontend dev server is 5173

## Workarounds

| Issue | Workaround |
|-------|-----------|
| Multiple browser tabs editing same file | Avoid editing the same file simultaneously; refresh before editing |
| LLM generation timeout | Check API key validity and network connectivity; increase `LLM_MAX_TOKENS` if needed |
| Large project slow to load | Reduce number of scenes per chapter; split into multiple projects |
| Chinese character encoding issues | Ensure all `.md` files are UTF-8 encoded |

## Future Fix Directions (v0.2)

- Conflict detection (`expected_mtime` / `expected_hash`) for memory and material endpoints
- ConfigService for workspace-level configuration
- Route remaining raw I/O through FileService
- Deeper real LLM E2E and quality reports
