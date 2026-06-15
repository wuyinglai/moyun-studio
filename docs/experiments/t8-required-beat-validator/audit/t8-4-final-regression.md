# T8.4 Final Regression

## Background

T8.4 stabilized the small-model writing quality loop after the required beat validator work:

- Professional right-panel generation status;
- long-wait and LLM error UX;
- required / forbidden beats input;
- prompt assembly carrying beats;
- beat validation metadata;
- CandidatePanel warning display;
- preview / adopt / delete;
- 404 noise cleanup.

This final regression is verification-only. No product code was changed.

## Current Commit

```text
f385bce fix: stabilize writing quality generation flow
```

## Test Environment

- Branch: `main`
- Backend: local FastAPI on `127.0.0.1:8000`
- Frontend: Vite on `127.0.0.1:5184`
- Workspace: isolated temp workspace outside the repository
- Browser: Playwright Chromium

Pipeline SSE was mocked at the browser route layer for deterministic fast / slow / error flows. Candidate creation, candidate metadata, preview, adopt, and delete used the real backend Candidate API.

## Regression Results

| # | Scenario | Result |
|---:|---|---|
| 1 | Default empty input generation | Pass: validator not enabled, candidate panel works, preview/adopt works |
| 2 | Required beat generation | Pass: `extra_vars` and final prompt include `第七层协议必须被提及`; candidate metadata status `pass`; panel shows validation status |
| 3 | Forbidden beat generation | Pass: final prompt includes `不能提前揭晓第七层协议完整真相`; candidate metadata status `warning`; warning detail visible |
| 4 | Right panel rewrite current scene | Pass: `pipeline=rewrite`, `output_mode=candidate`, normalized target path, clear status, button recovers |
| 5 | Toolbar write next scene | Pass: `pipeline=generate`, `output_mode=candidate`, target `sec-002.md`, source content not polluted before adopt |
| 6 | LLM_ERROR / timeout recovery | Pass: friendly error appears, button recovers, no bad candidate is created |
| 7 | Preview then delete | Pass: preview modal opens/closes, delete dialog appears, candidate becomes `discarded` |
| 8 | Old candidate compatibility | Pass: candidate without `beat_validation` does not crash; preview works |

## LLM Slow / Error Recovery

Slow response regression:

- Mocked pipeline waited past 15 seconds.
- UI showed `模型响应较慢，仍在等待生成结果……`.
- Button recovered after stream completion.

Error recovery regression:

- Mocked pipeline returned `LLM_ERROR timeout`.
- UI showed the friendly model failure message.
- The generation button became clickable again.
- Candidate count did not increase, confirming no broken candidate was created.

## Required Beats Input

Verified:

- Empty input does not set `_enable_beat_validation`.
- Required beat input sets `_enable_beat_validation=true` and `required_beats`.
- Forbidden beat input sets `_enable_beat_validation=true` and `forbidden_beats`.
- Prompt payload contains the submitted required / forbidden text.

## CandidatePanel Warning

Verified:

- `pass` status is visible.
- `warning` status is visible.
- Warning details are visible for missing / forbidden-risk metadata.
- Legacy candidate with no `beat_validation` remains compatible.
- Warning remains advisory and does not become a hard adopt blocker.

## Preview / Adopt / Delete

Verified:

- Preview opens and closes.
- Adopt confirm appears and succeeds for a pending candidate.
- Delete confirm appears and changes the candidate status to `discarded`.
- Page remains responsive after preview and delete.

## 404 Noise

The final browser regression recorded no `404` / `[API Error]` console noise in the stabilized writing flow.

## Commands Run

```powershell
git status --short
git log -1 --oneline
cd frontend
npm run build
cd ..
node %TEMP%\t84-final-regression.js
node %TEMP%\t84-final-slow.js
git diff --check
```

## Bugs Found

None in this final regression.

## Remaining Issues

- Real LLM/provider latency is still outside this frontend regression.
- The full Professional rewrite pipeline may still be slow with small models.
- Some historical mojibake remains in older source comments/UI strings and was not part of this verification.

## Recommendation

T8.4 can be formally closed.

## Next Step

Recommended T8.5 focus:

1. backend first-token timeout / retry policy;
2. shorter quick-rewrite candidate pipeline for small models;
3. optional committed E2E smoke script for repeatable release-gate checks.
