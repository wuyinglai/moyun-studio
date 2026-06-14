# T8.3-mini Required Beat Warning Candidate Metadata

## Scope

This change productizes required-beat validation only as candidate metadata and UI warning. It does not repair text, block adopt, auto adopt, or overwrite formal scene files.

## Trigger

Validation is opt-in only:

```json
{
  "_enable_beat_validation": true,
  "required_beats": ["第七层协议", "银色芯片显示残缺坐标"],
  "forbidden_beats": ["直接揭晓完整真相"]
}
```

If `_enable_beat_validation` is absent or false, candidate generation behaves as before and no validator call is made.

## Metadata

Candidate metadata may include:

```json
{
  "beat_validation": {
    "enabled": true,
    "status": "pass | warning | unknown",
    "summary": "一句面向作者的检查结论",
    "required_beats": [
      {"text": "第七层协议", "status": "satisfied | partial | missing | unknown", "evidence": "..."}
    ],
    "forbidden_beats": [
      {"text": "提前揭晓真相", "violated": false, "evidence": "..."}
    ],
    "logic_risks": [],
    "validator": {"type": "llm-json", "version": "required-beat-validator-v1"}
  }
}
```

When the validator fails or the model does not return valid JSON, candidate creation still succeeds and metadata status becomes `unknown`.

## Frontend Behavior

`CandidatePanel` displays a small status badge:

- `信息点通过`
- `信息点警告`
- `信息点未知`

Warnings are also shown in candidate cards and preview warnings. Adopt remains available. If a warning exists, the confirm dialog includes the warning so the author can decide whether to continue.

## Safety Boundaries

- Candidate adopt/delete/hash/file-save safety logic is unchanged.
- Required-beat validation does not become a hard gate.
- No automatic repair is attempted.
- No formal scene file is overwritten by the validator.
- No raw prompt, raw model output, API key, or user workspace content is stored in metadata.

## Smoke Result

Smoke used the configured `openai/agnes-2.0-flash` model through the product LLM service against a temporary directory outside the repository workspace.

Result:

```json
{
  "status": "ok",
  "validator_status": "warning",
  "metadata_status": "warning",
  "model": "openai/agnes-2.0-flash"
}
```

The warning result is acceptable: the smoke verifies validator execution, metadata persistence, and non-blocking behavior rather than literary quality.

## Recommendation

This is safe to keep as an opt-in warning layer. The next step should be UI/E2E coverage for a real pipeline request with `_enable_beat_validation=true`, followed by prompt tuning only if warning quality is too noisy.
