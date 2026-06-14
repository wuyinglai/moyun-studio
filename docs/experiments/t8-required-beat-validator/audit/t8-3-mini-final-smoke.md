# T8.3-mini Final Smoke Report

## Background

T8.3-mini added optional required-beat validation metadata for candidates. The validator is enabled only by `_enable_beat_validation=true`, stores warning metadata on the candidate, and must not change candidate adopt/delete/hash/file-save safety behavior.

Baseline commit:

```text
67a0bbf9dceac4c2e599e5d8b10f2836ad865c02
```

## Default Flow Smoke

Smoke path:

1. Created a temporary project outside repository `workspace/`.
2. Ran the professional pipeline in `output_mode=candidate` without `_enable_beat_validation`.
3. Read the generated candidate metadata.
4. Previewed candidate content through `CandidateService.get_candidate_content`.
5. Adopted the candidate.

Result:

```json
{
  "default_metadata_empty": true,
  "default_preview_content": true,
  "default_adopt": "success"
}
```

Conclusion: default candidate generation is unchanged. The candidate either has no `beat_validation` field in older metadata or an empty object for newly created metadata.

## Validator Enabled Smoke

Smoke input:

```json
{
  "extra_vars": {
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
}
```

Result:

```json
{
  "enabled_status": "pass",
  "enabled_event_status": "pass",
  "enabled_adopt": "success"
}
```

Conclusion: opt-in validator metadata is written to candidate metadata, included in the `candidate_created` event as `beat_validation_status`, remains available through candidate reload, and does not block adopt.

## Unknown Fallback Smoke

Smoke method:

1. Used a fake validator LLM response with invalid JSON.
2. Kept `_enable_beat_validation=true`.
3. Generated a candidate.
4. Adopted the candidate.

Result:

```json
{
  "unknown_status": "unknown",
  "unknown_adopt": "success"
}
```

Conclusion: JSON parse failure does not fail candidate creation. Metadata falls back to `status=unknown`; adopt remains non-blocking.

## Old Candidate Compatibility

Smoke method:

1. Created a valid candidate.
2. Removed `beat_validation` from its stored metadata to simulate an old candidate.
3. Reloaded it through `CandidateService.get_candidate`.
4. Previewed content and adopted it.

Result:

```json
{
  "old_candidate_default": true,
  "old_candidate_content": true,
  "old_candidate_adopt": "success"
}
```

Conclusion: old candidates without `beat_validation` remain compatible. The schema defaults missing metadata to `{}` and does not break preview/adopt.

## Adopt/Delete Verification

Delete smoke result:

```json
{
  "delete_candidate": true
}
```

Conclusion: delete still works. Adopt smoke was covered by default, enabled, unknown, and old-candidate cases. No evidence of regression in base hash / mtime safety behavior was found; the existing candidate service test suite also passed.

## Frontend Display Verification

Frontend verification was limited to build/type/template validation in this smoke round:

- `npm run build` passed.
- CandidatePanel supports `pass`, `warning`, and `unknown` labels.
- CandidatePanel treats missing `beat_validation` as no warning.
- Adopt confirmation includes beat warning text only when a warning exists.

No browser-click E2E was added in this task because the requested scope was post-implementation smoke only and no code bug was found.

## Test Commands

```powershell
git status --short
git log -1 --oneline
python -m pytest backend/tests/test_beat_validator.py backend/tests/test_candidate_service.py backend/tests/test_pipeline.py -q --tb=short
cd frontend
npm run build
cd ..
git diff --check
```

Results:

- Backend tests: `73 passed`
- Frontend build: passed
- Diff check: passed, with the existing CRLF/LF warning for `backend/core/pipeline.py`

## Bugs Found

None.

Notes:

- The temporary pipeline smoke emitted non-blocking logs about missing `pipeline/diff-summary/analyze.md` because the smoke used a minimal temporary prompt directory. Candidate creation, metadata persistence, preview, adopt, and delete all completed successfully.

## Recommendation

T8.3-mini is stable enough to keep as an opt-in warning layer.

## Should Enter T8.3.1

Yes. Recommended T8.3.1 scope:

1. Add a real browser E2E for CandidatePanel badge display and adopt confirmation.
2. Tune validator prompt only if warning quality is too noisy.
3. Keep automatic repair out of the flow until warning precision is measured.
