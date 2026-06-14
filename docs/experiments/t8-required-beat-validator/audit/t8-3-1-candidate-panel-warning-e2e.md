# T8.3.1 CandidatePanel Warning UI Browser E2E

## Background

T8.3-mini added opt-in required beat validation metadata for candidates, with CandidatePanel badges for pass / warning / unknown and an adopt-time warning confirmation. T8.3.1 verifies that behavior in a real browser UI without changing product code.

## Test Environment

- Base commit: `8c66b64601b7a2efacea411b7bc33bce992608af`
- Backend: local FastAPI on `http://127.0.0.1:8017`
- Frontend: local Vite on `http://127.0.0.1:5177`
- Workspace: temporary directory outside the repository, `C:\Users\wuyin\AppData\Local\Temp\moyun-t831-e2e-workspace`
- Browser automation: Playwright Chromium against `http://127.0.0.1:5177/project/c779928c`
- Test data: one temporary project created through the project API, then five candidates injected through `CandidateService`

The temporary candidates covered:

| Source file | Validation metadata | Purpose |
| --- | --- | --- |
| `sec-pass.md` | `beat_validation.status = pass` | pass badge, preview, adopt |
| `sec-warning.md` | `beat_validation.status = warning` | warning badge, missing beat text, adopt warning confirm |
| `sec-unknown.md` | `beat_validation.status = unknown` | unknown badge, preview, adopt without warning block |
| `sec-old.md` | no `beat_validation` field | legacy candidate compatibility |
| `sec-delete.md` | `beat_validation.status = pass` | delete flow |

## Pass State UI

Result: passed.

- CandidatePanel displayed `信息点通过` for pass candidates.
- The pass candidate preview opened successfully.
- The preview body loaded candidate content asynchronously and did not modify the source file.
- Adopt showed the normal candidate safety confirmation and did not include required beat warning text.
- After confirmation, the card status changed to adopted.

## Warning State UI

Result: passed.

- CandidatePanel displayed `信息点警告`.
- The warning card showed the missing required beat text: `正文必须提到第七层协议`.
- Preview displayed the same warning in the preview modal.
- Adopt triggered a native confirmation dialog containing the warning heading and missing beat text.

## Unknown State UI

Result: passed.

- CandidatePanel displayed `信息点未知`.
- Preview opened and loaded the candidate content.
- Adopt showed the normal safety confirmation, not the required beat warning confirmation.
- After confirmation, the card status changed to adopted.

## Old Candidate Compatibility

Result: passed.

- A candidate with no `beat_validation` field rendered without crashing.
- It did not display a pass / warning / unknown badge.
- Preview opened normally.
- Adopt showed the normal safety confirmation and completed successfully.

## Adopt Confirm Behavior

Result: passed.

- Warning candidate cancel path: dismissing the warning confirmation left the candidate pending and did not adopt it.
- Warning candidate accept path: accepting the warning confirmation adopted the candidate.
- Pass / unknown / old candidates still showed the generic safety confirmation, but did not include the warning heading or missing beat text.

## Preview / Delete Behavior

Result: passed.

- Preview worked for pass, warning, unknown, and legacy candidates.
- Delete still asked for confirmation.
- After confirming delete, the delete candidate card changed to discarded.

## Test Commands

```powershell
git status --short
cd frontend
npm run build
```

Browser E2E was executed with an inline Playwright script from `frontend/`. The final run reported:

```text
T8.3.1 candidate panel E2E passed: 32 checks
C:\Users\wuyin\AppData\Local\Temp\moyun-t831-candidate-panel-e2e-result.json
```

## Bugs Found

No product code bug was found.

Two test setup issues were corrected during verification:

1. A hand-written temporary project metadata file was not accepted by the real project API. The final test created the project through `POST /api/projects`.
2. PowerShell stdin corrupted literal Chinese test data in an earlier setup attempt. The final test used ASCII-safe Unicode escapes for injected test content and metadata.

## Recommendation

T8.3.1 passes. The required beat warning metadata is visible in the browser UI and does not break CandidatePanel preview, adopt, delete, or legacy candidate compatibility.

Recommended next step: proceed to T8.3.2 if the next scope is productizing validator warning visibility in broader generation flows, while keeping automatic repair out of scope.
