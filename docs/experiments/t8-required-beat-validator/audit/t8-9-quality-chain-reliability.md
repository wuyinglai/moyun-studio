# T8.9 Quality Chain Reliability Report

## Background

T8.8 dogfood concluded that the T8 writing quality loop is viable:

```text
required / forbidden beats -> generation prompt -> candidate -> validator -> CandidatePanel warning -> preview/adopt/delete
```

The remaining reliability issues were narrower:

1. Rewrite / polish prompts did not render required or forbidden beats.
2. The required beat validator aligned model results by array order.
3. Validator failures went straight to `unknown` without retry.

This task is a targeted reliability fix. It does not add automatic repair, auto-adopt, Scene Plan behavior, or any save/adopt/hash changes.

## Prior T8 State

Qoder-completed milestones reviewed before this task:

- T8.6: feedback revision safety and UX stabilization.
- T8.6-final: comprehensive regression and API retry verification.
- T8.6.1: full E2E mock suite stabilization.
- T8.7: CandidatePanel quality panel organization.
- T8.8: writing quality dogfood, score 4.1/5, quality loop judged viable.

Current baseline:

```text
2a1fa9d docs: add T8.8 writing quality dogfood report
```

## Rewrite / Polish Beats Integration

Added a shared prompt block:

```text
prompts/blocks/beat-constraints.md
```

It renders only when non-empty beat inputs exist:

```text
## 本次必须保留 / 补上的信息点
- ...

## 本次禁止新增 / 禁止揭晓
- ...
```

Integrated the block into rewrite and polish transformation steps:

- `prompts/pipeline/rewrite/draft.md`
- `prompts/pipeline/rewrite/depai.md`
- `prompts/pipeline/rewrite/logic.md`
- `prompts/pipeline/rewrite/rhythm.md`
- `prompts/pipeline/polish/depai.md`
- `prompts/pipeline/polish/prose.md`
- `prompts/pipeline/polish/logic.md`
- `prompts/pipeline/polish/rhythm.md`

Rationale:

- Rewrite / polish are multi-step pipelines.
- Adding beats only to the first step would not protect later transformations.
- The wording is action-neutral: it says "preserve / fill in" rather than "next scene must include".

## Validator Alignment Strategy

`backend/core/beat_validator.py` now aligns each expected beat to model output by:

1. `id` match, e.g. `beat-1`, `forbid-1`.
2. Normalized text exact match.
3. `difflib.SequenceMatcher` similarity fallback.
4. `unknown` when similarity is too low.

The validator no longer silently attaches a low-similarity or unrelated model result to an expected beat.

Metadata now records alignment details:

```json
{
  "alignment": "id | text_exact | similarity | index_unlabeled | unknown",
  "alignment_score": 1.0,
  "model_text": "..."
}
```

Forbidden beats receive the same protection. When alignment is unknown, `violated` is set to `null` and the candidate remains advisory-warning/unknown rather than falsely passing.

## Validator Retry

`RequiredBeatValidator.validate()` now attempts the LLM validator call up to two times total:

- First failure can be retried once.
- JSON parse failure is also retried once.
- If both attempts fail, status is `unknown`.
- Metadata records:
  - `retry_count`
  - `last_error_type`

No infinite retry was added.

## Tests Added / Updated

Backend coverage now includes:

- rewrite prompt includes required beats;
- rewrite prompt includes forbidden beats;
- polish prompt includes required beats;
- polish prompt includes forbidden beats;
- empty beats omit prompt sections;
- validator id alignment;
- shuffled model result order;
- text exact fallback;
- similarity fallback;
- low similarity -> unknown;
- first validator failure then success;
- two validator failures -> unknown;
- retry metadata;
- feedback revision still inherits beats and validates.

## Commands Run

```powershell
python -m pytest backend/tests/test_beat_validator.py -v
python -m pytest backend/tests/test_pipeline.py backend/tests/test_candidate_feedback_revision.py -q --tb=short
python -m pytest backend/tests/test_candidate_service.py -q --tb=short
cd frontend
npm run build
npm run test:e2e:mock -- tests/e2e/14-candidate-workflow.spec.ts --reporter=line
npm run test:e2e:mock -- --reporter=line
cd ..
```

## Results

- Beat validator tests: 12 passed.
- Pipeline + feedback revision tests: 71 passed.
- Candidate service tests: 9 passed.
- Frontend build: passed.
- Focused candidate E2E: 16 passed.
- Full mock E2E: 62 passed, 93 skipped, 0 failed.

## Bugs Found

1. Rewrite / polish prompts did not carry user-entered beat constraints.
2. Validator result normalization could misalign shuffled model output by index.
3. Validator had no retry for transient LLM or JSON parse failures.

## Remaining Issues

None blocking for T8.9.

## Recommendation

T8.9 can be considered closed after review. The quality chain now consistently carries beats through write, rewrite, polish, and feedback revision paths, and validator metadata is less likely to produce false confidence from shuffled or malformed model output.

## Next Step

Recommended next step:

```text
T8.10: real LLM rewrite/polish dogfood with required / forbidden beats
```

That should verify that the newly injected rewrite/polish beat constraints improve actual revision quality without making prose worse.
