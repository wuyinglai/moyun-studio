# Release Checklist / 发版检查清单

Use this checklist before creating a new release.

## Pre-Release Checks

### Git Status

- [ ] `git status --short` is clean (no uncommitted changes)
- [ ] `git rev-parse HEAD` matches `git rev-parse origin/main`
- [ ] No stale local branches that should be merged

### Backend

- [ ] `pip install -r requirements.txt` succeeds
- [ ] `pytest` passes (all backend tests)
- [ ] `ruff check .` passes (no lint errors)
- [ ] `uvicorn backend.main:app --reload` starts without errors

### Frontend

- [ ] `npm install` succeeds
- [ ] `npm run dev` starts without errors
- [ ] `npm run build` succeeds (0 errors)
- [ ] `npm run lint` passes (0 errors; warnings acceptable)

### Integration

- [ ] Backend + Frontend start together
- [ ] Can create a new project from the UI
- [ ] Can generate a scene (with mock or real LLM)
- [ ] SSE events are received (check browser console)
- [ ] Lite mode loads and functions

### Documentation

- [ ] `README.md` is up to date
- [ ] `CHANGELOG.md` is updated with this version's changes
- [ ] `docs/known-issues.md` is updated
- [ ] Release notes file exists at `docs/releases/vX.Y.Z.md`
- [ ] `docs/RELEASE_CHECKLIST.md` itself is current

### Configuration

- [ ] `.env.example` reflects all current configuration options
- [ ] No API keys or secrets in tracked files
- [ ] `.gitignore` is up to date

## Release Process

### Tag & Push

- [ ] `git tag -a vX.Y.Z -m "Moyun Studio vX.Y.Z"`
- [ ] `git push origin vX.Y.Z`
- [ ] Verify: `git ls-remote --tags origin vX.Y.Z`

### GitHub Release

- [ ] Create GitHub Release from tag `vX.Y.Z`
- [ ] Release title: `Moyun Studio vX.Y.Z`
- [ ] Release body: paste content from `docs/releases/vX.Y.Z.md`
- [ ] Verify Release page is accessible and content is complete

### Post-Release

- [ ] Verify `git status --short` is still clean
- [ ] Verify tag points to correct commit
- [ ] Verify GitHub Release page returns 200
- [ ] Verify Release body contains key sections (Highlights, Known Limitations, etc.)

## Automated Check

Run the release check script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release-check.ps1
```

This script covers: whitespace check, guardrails, backend safety tests (A-E), full backend tests, frontend lint/build, and mock E2E.

**Real LLM E2E** is a separate optional step requiring `MOYUN_E2E_REAL_LLM=true`.
