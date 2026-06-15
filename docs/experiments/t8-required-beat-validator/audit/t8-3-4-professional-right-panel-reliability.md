# T8.3.4 Professional Right Panel Reliability

## Background

T8.3.3 confirmed that required / forbidden beats enter the final generation prompt and that candidate metadata is persisted. The browser smoke also exposed reliability concerns in the Professional right panel:

- Clicking `重写当前场景` did not complete candidate creation.
- The page showed existing `404` noise from prompt/workflow loading.
- After preview, the browser test session appeared unable to delete the candidate.

This audit focused on reproducing the actual browser flow, identifying whether the failures came from the right panel, pipeline request shape, LLM execution, or CandidatePanel behavior, and applying only the minimum fix needed.

## Reproduction Setup

- Branch: `main`
- Base commit: `93ac146 feat: include required beats in generation prompt`
- Backend: local FastAPI on `127.0.0.1:8000`
- Frontend: Vite on `127.0.0.1:5184`
- Workspace: isolated temp workspace outside the repository
- Project: temporary E2E project with `chapters/vol-01/ch-001/sec-001.md`
- Browser automation: Playwright against the local Vite app

## Findings

### 1. Right panel request path

The right panel did send `/api/pipeline/run`, but when entering through `/project/:projectId/file/*`, the frontend `filePath` could include a leading slash:

```json
{
  "target_file": "/chapters/vol-01/ch-001/sec-001.md",
  "output_mode": "candidate"
}
```

`FileStore.readFile()` and `saveFile()` already normalize this form, but `useFileGeneration.runPipeline()` did not. This violates the project-relative path contract and can push backend pipeline execution onto an invalid target path.

Fix: normalize generation request paths at the `useFileGeneration` boundary before sending `file_path` / `target_file`, before Scene Plan matching, and before emitted file-path metadata.

### 2. Candidate creation still depends on real LLM success

After path normalization, the request became:

```json
{
  "target_file": "chapters/vol-01/ch-001/sec-001.md",
  "output_mode": "candidate",
  "extra_vars": {
    "_action": "rewrite_current_scene",
    "_enable_beat_validation": true,
    "required_beats": [
      {
        "id": "beat-1",
        "text": "正文必须提到第七层协议"
      }
    ]
  }
}
```

However, the Professional `重写当前场景` action uses the full `rewrite` pipeline. In the current environment, the first LLM step (`diagnose`) emitted only heartbeats for about 200 seconds and then returned `LLM_ERROR`. Because the LLM step failed before any final content existed, no candidate was created. This is not a CandidatePanel failure.

Failure recovery was verified in browser: the rewrite button became enabled again after the backend error, and the right panel status showed:

```text
步骤 诊断问题 失败: 模型调用遇到未知错误，请稍后重试或联系支持
```

### 3. 404 source

The observed 404s were reproduced and traced to side-panel initialization paths:

- `GET /api/prompts/generate/chapter?project_id=...`
  - Triggered by legacy prompt-type fallback for scene files.
  - Not the cause of candidate creation failure.
- `GET /api/workflows/full-novel`
  - Triggered by workflow guide initialization.
  - Also not the cause of candidate creation failure.

These remain lower-priority cleanup items. They pollute browser logs but do not block the candidate panel or rewrite request after the path fix.

### 4. Preview / delete behavior

CandidatePanel preview and delete were verified with API-created candidates containing `pass`, `warning`, `unknown`, and legacy empty beat metadata.

The earlier delete failure was caused by the E2E script looking for an obsolete preview selector (`.candidate-preview-overlay`). The actual component uses `.preview-modal`, so the preview modal was not closed and intercepted the delete button. With the correct selector:

- Preview modal opened.
- Preview modal closed.
- Delete confirmation appeared.
- Confirming delete changed the candidate status to `discarded`.
- The page did not become unresponsive.

## Fix

Changed `frontend/src/composables/useFileGeneration.ts`:

- Added `normalizeProjectPath(filePath)`.
- `generateToFile()` now sends normalized `file_path`.
- `runPipeline()` now sends normalized `target_file`.
- Scene Plan matching now uses the normalized path.
- Generation emitter metadata and file meta persistence use the normalized project-relative path.

No backend code, prompt template, candidate adopt/delete logic, validator logic, or pipeline structure was changed.

## Browser E2E Results

### Right panel generation

- Clicked Professional right panel `重写当前场景`.
- Verified `/api/pipeline/run` was sent.
- Verified request includes `output_mode: candidate`.
- Verified request includes required beat extra vars when the input is filled.
- Verified `target_file` is now project-relative with no leading slash.
- Candidate was not created because the real LLM step failed with `LLM_ERROR`.

### Required beats

- Filled `required_beats` in the right panel input.
- Verified request includes `_enable_beat_validation: true`.
- Verified request includes `required_beats`.
- Since LLM did not return final content, beat validation metadata was not produced in this generation run.

### Failure recovery

- Waited for the backend LLM failure.
- The right panel rewrite button became enabled again.
- The status line showed the backend error.
- The UI did not remain permanently generating.

### CandidatePanel preview/delete

- Created candidates through the Candidate API for `pass`, `warning`, `unknown`, and legacy metadata.
- CandidatePanel displayed the expected beat validation labels.
- Preview opened and closed normally.
- Delete confirmation appeared.
- Confirming delete marked the candidate as `discarded`.

## Bugs Found

1. **Fixed:** Pipeline generation requests could send a leading-slash project path from `/project/:projectId/file/*`.
2. **Confirmed, not fixed in this task:** Prompt/workflow side panels still emit 404 log noise for `generate/chapter` and `full-novel`.
3. **Confirmed environment/runtime issue:** Real LLM pipeline calls can wait a long time for the first model step and fail with `LLM_ERROR`, preventing candidate creation.
4. **Not a product bug:** Preview/delete failure in the previous smoke was due to the test script using an obsolete modal selector.

## Tests / Commands

```powershell
git status --short
git log -1 --oneline
npx gitnexus impact --repo moyun-studio runSceneAction --direction upstream
npx gitnexus impact --repo moyun-studio "Function:frontend/src/composables/useFileGeneration.ts:runPipeline" --direction upstream
npx gitnexus impact --repo moyun-studio "Function:frontend/src/composables/useFileGeneration.ts:generateToFile" --direction upstream
node %TEMP%\t834-right-panel-e2e.js
node %TEMP%\t834-failure-recovery.js
node %TEMP%\t834-preview-delete-e2e.js
```

Pending final validation:

```powershell
cd frontend
npm run build
cd ..
git diff --check
npx gitnexus detect-changes --repo moyun-studio
```

## Recommendation

T8.3.5 can continue after this fix, but it should explicitly separate:

1. UI reliability and request-contract checks.
2. CandidatePanel metadata display and adopt/delete checks.
3. Real LLM first-token latency / timeout behavior.

For the next stability pass, consider improving user-facing progress while the pipeline is waiting for the first LLM token, and cleaning up the `generate/chapter` / `full-novel` 404 log noise.
