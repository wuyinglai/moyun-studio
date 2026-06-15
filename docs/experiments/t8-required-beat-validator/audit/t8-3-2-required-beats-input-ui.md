# T8.3.2 Required Beats Input UI

## Background

T8.3-mini introduced opt-in required beat validation metadata for candidates, and T8.3.1 verified the CandidatePanel warning UI in a real browser. T8.3.2 adds the smallest user-facing input path so Professional users can provide required and forbidden beats before generation.

This is not a Scene Plan system, outline editor, automatic repair flow, or validator prompt change.

## UI Implementation

The Professional quick panel now includes a collapsible `本场信息点` section near the generation actions.

It contains two multiline inputs:

- `本场必须出现`: one required beat per line.
- `本场禁止出现 / 禁止揭晓`: one forbidden beat per line.

The section stays lightweight and collapsed by default. When either input has content, the summary displays `已启用检查`.

## Data Conversion

Frontend input is parsed line by line:

```json
{
  "_enable_beat_validation": true,
  "required_beats": [
    {
      "id": "beat-1",
      "text": "正文必须提到第七层协议"
    }
  ],
  "forbidden_beats": [
    {
      "id": "forbid-1",
      "text": "不能揭晓第七层协议完整真相"
    }
  ]
}
```

Rules:

- Empty lines are ignored.
- Required IDs are `beat-1`, `beat-2`, ...
- Forbidden IDs are `forbid-1`, `forbid-2`, ...
- Empty arrays are not sent.
- `_enable_beat_validation` is only sent when at least one required or forbidden beat exists.

## Default Behavior

If both inputs are blank:

- `_enable_beat_validation` is not sent.
- `required_beats` is not sent.
- `forbidden_beats` is not sent.
- Generation behavior remains unchanged.

## Validator Trigger

The shared Professional scene generation path merges the beat validation extra vars into pipeline requests. This covers:

- Professional quick panel `生成当前场景`
- Professional quick panel `重写当前场景`
- Professional quick panel `补强爽点`
- Editor toolbar `写下一场景`
- Editor toolbar `润色`
- Editor toolbar `精修`

The backend validator remains opt-in and uses the existing `_enable_beat_validation` contract.

## Browser E2E

Browser E2E used a temporary workspace and a local frontend/backend pair. Real LLM calls were not made; `/api/pipeline/run` was intercepted after the browser assembled the request.

Scenarios verified:

1. Blank input:
   - Clicked Professional quick panel generation.
   - Captured pipeline request did not include `_enable_beat_validation`.

2. Required beat:
   - Filled `正文必须提到第七层协议`.
   - Captured pipeline request included `_enable_beat_validation=true`.
   - Captured `required_beats[0]` was `{ id: "beat-1", text: "正文必须提到第七层协议" }`.
   - `forbidden_beats` was omitted.

3. Forbidden beat:
   - Filled `不能揭晓第七层协议完整真相`.
   - Captured pipeline request included `_enable_beat_validation=true`.
   - Captured `forbidden_beats[0]` was `{ id: "forbid-1", text: "不能揭晓第七层协议完整真相" }`.
   - `required_beats` was omitted.

CandidatePanel follow-up:

- A legacy candidate without beat metadata rendered normally.
- Warning candidates displayed `信息点警告`.
- Preview opened normally.
- Warning adopt confirm included the missing beat.
- Adopt succeeded after confirmation.
- Delete confirmation and discard worked.

Final browser result:

```text
T8.3.2 browser E2E passed: 18 checks
```

## Test Commands

```powershell
cd frontend
npm run build
cd ..
git diff --check
git status --short
```

Backend tests were not required because no backend code changed.

## Risks

- The input state is intentionally minimal and shared in-memory through a composable. It is not persisted across browser reloads.
- The UI lives in the Professional quick panel. Users who only use the top toolbar can still benefit after filling it once, because the toolbar uses the same shared generation state.
- This does not guarantee the model will obey beats; it only supplies the validator input and surfaces resulting candidate warnings.

## Next Step

Proceed to T8.3.3 if the next goal is to refine prompt assembly so required/forbidden beats influence generation quality before validation. Keep automatic repair and repair candidates out of scope until the warning-only loop is stable.
