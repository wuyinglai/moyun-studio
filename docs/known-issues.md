# Known Issues / 已知问题

This document tracks current limitations, common failure modes, and workarounds.

---

## Version Status

| Version | Status | Date |
|---------|--------|------|
| v0.2.0 | Released | 2026-06-16 |
| v0.2.1 | Released | 2026-06-17 |
| v0.2.2a | Done | 2026-06-17 (Guardrails Allowlist Cleanup) |
| v0.2.2b | Done | 2026-06-17 (Docs Consolidation + Known Issues Update) |
| v0.2.2 | Released | 2026-06-18 (Maintenance release, tag v0.2.2) |

---

## Recently Resolved (v0.2.1 / v0.2.2a)

| # | Issue | Resolution | Version |
|---|-------|------------|---------|
| R1 | Guardrails existing noise | All violations classified and allowlisted (B/D/C, no real risk) | v0.2.2a |
| R2 | T9.4 continuity metadata dogfood | `create_candidate()` auto-fetches continuity anchors from service | v0.2.1 |
| R3 | T9.4 continuity prompt test path | Absolute path resolution instead of relative path lookup | v0.2.1 |
| R4 | Pipeline prompt rendering contract | Archive issues resolved; prompt templates use consistent pattern | v0.2.1 (T9.5) |

---

## Release Blockers / 阻断发布问题

以下问题出现时必须修复才能发布：

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| B1 | 前端构建失败 | Critical | `npm run build` 无法完成或有 fatal 错误 |
| B2 | 核心 E2E 失败 | Critical | `14-candidate-workflow.spec.ts` 或 `24-dry-run-ui-entry.spec.ts` 失败 |
| B3 | Git 状态不一致 | High | HEAD != origin/main 或存在未提交的代码变更 |
| B4 | 真实 LLM 环境变量误启用 | High | `ALLOW_REAL_LLM_SMOKE` 或 `MOYUN_ALLOW_REAL_LLM_SMOKE` 被设置 |
| B5 | API Key 泄露 | Critical | API Key 出现在日志、测试报告或提交的文件中 |
| B6 | .env 被提交 | High | `.env` 文件出现在 git 追踪中 |

---

## Non-blocking Issues / 不阻断发布问题

以下问题已知但不影响核心功能，可留到后续版本修复：

| # | Issue | Priority | Description | Target Version |
|---|-------|----------|-------------|----------------|
| NB1 | 内存端点无冲突检测 | P2 | `story_state`, `style_guide`, `recent_context`, `workflows`, `materials` 端点不支持 `expected_mtime` / `expected_hash` | v0.2 |
| NB2 | 部分非核心 API 使用同步 I/O | P3 | `llm.py`, `lite.py`, `prompts.py` 等仍使用 `Path.read_text()` / `Path.write_text()` | v0.2 |
| NB3 | 真实 LLM E2E 为可选 | P2 | 默认 release check 不包含真实 LLM 测试 | v0.2 |
| NB4 | 工作区 `.config.json` 明文存储 API Key | P2 | 本地优先应用有意设计，需保持 gitignored | v0.2 |
| NB5 | 多标签页编辑无冲突保护 | P3 | 同一文件在多个浏览器标签页编辑可能导致静默覆盖 | v0.2 |
| NB6 | 项目 ID 与名称语义易混淆 | P3 | `project_id` (UUID) 与项目显示名称不同，用户可能误解 | v0.1.x |
| NB7 | dry-run 工具在生产构建中可见 | P3 | dev-tools 区块在非 dev 模式下仍可见（但功能被禁用） | v0.1.x |

---

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
