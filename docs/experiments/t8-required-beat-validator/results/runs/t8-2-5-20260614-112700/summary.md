# T8.2.5 Expanded Required Beat Validator Benchmark

## 1. Background

T8.2.2 created the validator benchmark, T8.2.3 audited disagreement, and T8.2.4 refined schema, prompt, and weak-rule semantics. T8.2.5 hardens the regression framework and expands the run to two samples per six cases.

## 2. Run Manifest

- Run ID: `t8-2-5-20260614-112700`
- Timestamp: `2026-06-14T11:27:00Z`
- Model: `agnes-2.0-flash`
- Samples: `2`
- Cases: `case-01-seventh-protocol, case-02-ending-hook, case-03-injury-limitation, case-04-item-handover, case-05-location-lock, case-06-no-new-entity`
- Commit: `487c361c35ebc8848e45bae80f13fb9afd8e5f12`
- Case schema version: `t8-required-beat-case-v2`
- Validator prompt version: `t8-validator-semantic-v2`
- Repair prompt version: `t8-repair-minimal-v1`

## 3. Summary Metrics

| Metric | Value |
| --- | ---: |
| Runs | 12 |
| Initial beat completion rate | 97.67% |
| JSON parse rate | 100.00% |
| Validator agreement rate | 66.67% |
| Repair trigger count | 1 |
| Repair success rate | 100.00% |
| New error rate | 0.00% |
| Final usable rate | 100.00% |
| Average total latency | 67.94s |

## 4. Comparison With T8.2.2 Baseline

| Metric | T8.2.2 | T8.2.5 | Delta |
| --- | ---: | ---: | ---: |
| Validator agreement | 50.00% | 66.67% | +16.67% |
| Repair success | 33.33% | 100.00% | +66.67% |
| Final usable | 66.67% | 100.00% | +33.33% |

## 5. Difficulty Analysis

| Group | Runs | Agreement | Final usable | Repair triggers | Avg latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| hard | 6 | 33.33% | 100.00% | 1 | 59.51s |
| medium | 6 | 100.00% | 100.00% | 0 | 76.36s |

## 6. Beat Type Analysis

| Group | Runs | Agreement | Final usable | Repair triggers | Avg latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| explicit_keyword | 2 | 100.00% | 100.00% | 0 | 97.29s |
| forbidden_entity | 2 | 100.00% | 100.00% | 0 | 45.77s |
| knowledge_boundary | 10 | 60.00% | 100.00% | 1 | 67.40s |
| semantic_condition | 12 | 66.67% | 100.00% | 1 | 67.94s |
| state_constraint | 6 | 66.67% | 100.00% | 1 | 70.05s |
| terminal_hook | 2 | 0.00% | 100.00% | 0 | 54.41s |

## 7. Repair Risk Breakdown

| Type | Count |
| --- | ---: |
| not_triggered | 11 |
| safe_repair | 1 |
| risky_repair | 0 |
| failed_repair | 0 |
| harmful_repair | 0 |

Decision defaults:

- automatic repair: not allowed
- repair candidate: allowed with user preview/adopt only
- validator warning only: recommended

## 8. Run Details

| Case | Sample | Initial completion | JSON parse | Disagreement | Repair triggered | Repair success | Final usable | Repair risk | Latency |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: |
| case-01-seventh-protocol | s1 | 100.00% | True | False | False | False | True | not_triggered | 141.91s |
| case-01-seventh-protocol | s2 | 100.00% | True | False | False | False | True | not_triggered | 52.67s |
| case-02-ending-hook | s1 | 100.00% | True | True | False | False | True | not_triggered | 84.52s |
| case-02-ending-hook | s2 | 100.00% | True | True | False | False | True | not_triggered | 24.31s |
| case-03-injury-limitation | s1 | 80.00% | True | False | False | False | True | not_triggered | 103.56s |
| case-03-injury-limitation | s2 | 100.00% | True | False | False | False | True | not_triggered | 37.75s |
| case-04-item-handover | s1 | 100.00% | True | True | True | True | True | safe_repair | 48.21s |
| case-04-item-handover | s2 | 100.00% | True | True | False | False | True | not_triggered | 58.74s |
| case-05-location-lock | s1 | 100.00% | True | False | False | False | True | not_triggered | 95.63s |
| case-05-location-lock | s2 | 100.00% | True | False | False | False | True | not_triggered | 76.44s |
| case-06-no-new-entity | s1 | 100.00% | True | False | False | False | True | not_triggered | 34.88s |
| case-06-no-new-entity | s2 | 100.00% | True | False | False | False | True | not_triggered | 56.65s |

## 9. Audit Candidates

Audit candidates: 4

See `audit-candidates.csv` for samples requiring manual review.

## 10. Productization Reading

JSON validator warnings are the strongest productization candidate. Rule-based precheck remains useful as a weak audit signal, not a blocker. Natural validator explanations may be useful for user-facing explanations but should not be the only machine gate.

Automatic repair is not recommended. Repair candidate generation may be useful if the user previews and adopts it manually.
