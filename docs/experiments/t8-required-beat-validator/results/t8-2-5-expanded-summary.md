# T8.2.5 Expanded Summary

## 1. Background

T8.2.5 strengthens the T8 required-beat validator benchmark so it can be reused as a regression system for fiction-generation quality. It does not modify Moyun product code, production prompts, pipeline, frontend, backend, candidates, releases, or workspace data.

## 2. Previous T8 Summary

- T8.2.2 built the first reusable validator benchmark but had only 50.00% validator agreement and 66.67% final usable rate.
- T8.2.3 manually audited disagreements and found rule false positives, semantic ambiguity, and weak knowledge-boundary modeling.
- T8.2.4 refined schema, prompt, and rule semantics so rule precheck became weak signal only.

## 3. Runner Enhancements

- Added run-specific output directory under `results/runs/<run_id>/`.
- Added `manifest.json` with model, samples, commit, schema versions, prompt versions, and notes.
- Added run-local `raw/`, `scored/`, `summary.md`, `summary.json`, `summary.csv`, and `audit-candidates.csv`.
- Added failure taxonomy to scored JSON.
- Added audit candidate extraction.
- Added T8.2.2 baseline comparison.
- Added difficulty and beat-type grouping.
- Added repair risk breakdown.

## 4. Run Manifest

- Run ID: `t8-2-5-20260614-112700`
- Timestamp: `2026-06-14T11:27:00Z`
- Model: `agnes-2.0-flash`
- Samples: `2`
- Cases: `case-01-seventh-protocol, case-02-ending-hook, case-03-injury-limitation, case-04-item-handover, case-05-location-lock, case-06-no-new-entity`
- Commit: `487c361c35ebc8848e45bae80f13fb9afd8e5f12`
- Case schema version: `t8-required-beat-case-v2`
- Validator prompt version: `t8-validator-semantic-v2`
- Repair prompt version: `t8-repair-minimal-v1`

## 5. Samples / Cases / Model

- Model used: `agnes-2.0-flash`
- Total runs: 12
- Coverage: 6 cases x 2 samples = 12 full flows
- Average total latency: 67.94s

## 6. Baseline Comparison

| Metric | T8.2.2 | T8.2.5 | Delta |
| --- | ---: | ---: | ---: |
| Validator agreement | 50.00% | 66.67% | +16.67% |
| Repair success | 33.33% | 100.00% | +66.67% |
| Final usable | 66.67% | 100.00% | +33.33% |

## 7. Core Metrics

| Metric | Value |
| --- | ---: |
| Initial beat completion | 97.67% |
| JSON parse rate | 100.00% |
| Validator agreement | 66.67% |
| Repair trigger count | 1 |
| Repair success | 100.00% |
| New error rate | 0.00% |
| Final usable | 100.00% |

## 8. Difficulty Analysis

| Group | Runs | Agreement | Final usable | Repair triggers | Avg latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| hard | 6 | 33.33% | 100.00% | 1 | 59.51s |
| medium | 6 | 100.00% | 100.00% | 0 | 76.36s |

## 9. Beat Type Analysis

| Group | Runs | Agreement | Final usable | Repair triggers | Avg latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| explicit_keyword | 2 | 100.00% | 100.00% | 0 | 97.29s |
| forbidden_entity | 2 | 100.00% | 100.00% | 0 | 45.77s |
| knowledge_boundary | 10 | 60.00% | 100.00% | 1 | 67.40s |
| semantic_condition | 12 | 66.67% | 100.00% | 1 | 67.94s |
| state_constraint | 6 | 66.67% | 100.00% | 1 | 70.05s |
| terminal_hook | 2 | 0.00% | 100.00% | 0 | 54.41s |

## 10. Validator Agreement

Agreement improved from 50.00% to 66.67%. The remaining disagreements are concentrated in hard cases, especially `terminal_hook` and `knowledge_boundary` / medicine side-effect scenarios.

## 11. JSON Parse Rate

JSON parse rate is 100.00%. This supports using JSON validator output as structured candidate metadata, as long as it remains warning-only in product usage.

## 12. Repair Success

Repair triggered 1 time and succeeded in that run. This is encouraging but not enough to allow automatic repair, because the sample size is still small and manual audit found ambiguous cases.

## 13. Repair Risk Breakdown

| Repair Risk | Count |
| --- | ---: |
| not_triggered | 11 |
| safe_repair | 1 |
| risky_repair | 0 |
| failed_repair | 0 |
| harmful_repair | 0 |

Decision:

- automatic repair: not allowed
- repair candidate: allowed with preview/adopt
- validator warning only: recommended

## 14. Audit Candidates

Audit candidate count: 4

| Sample | Human Overall | Closest Validator | Disagreement Type |
| --- | --- | --- | --- |
| case-02-ending-hook-s1 | pass | natural/json | rule_too_strict |
| case-02-ending-hook-s2 | pass | natural/json | rule_too_strict |
| case-04-item-handover-s1 | needs_repair | json | ambiguous_case |
| case-04-item-handover-s2 | needs_repair | mixed | ambiguous_case |

## 15. Manual Audit Results

Manual audit confirms that ending-hook samples were valid and rule precheck was too strict because of broad forbidden keyword matching. Item-handover samples remain the hardest because side-effect hints, pronoun ownership, and reader/character knowledge boundaries are semantically subtle.

## 16. Productization Decision Matrix Summary

See `../audit/t8-3-productization-decision-matrix.md` for details.

Current decision:

- JSON validator warning: productizable
- Natural validator explanation: productizable as supporting explanation
- Rule precheck: internal weak signal only
- Automatic repair: not productizable
- Repair candidate: productizable only with explicit preview/adopt
- Required beats UI: productizable

## 17. Next Step

Proceed to T8.3-mini design: Required Beat Warning Candidate Metadata. Do not implement automatic repair. The first product surface should display validation warnings on candidates and allow the user to request a separate repair candidate.
