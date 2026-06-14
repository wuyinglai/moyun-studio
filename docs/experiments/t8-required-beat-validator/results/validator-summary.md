# T8.2.2 Required Beat Validator Benchmark Summary

## 1. Background

T8.2.1 showed that prompt-only required-beat strategies still miss mandatory scene information. T8.2.2 builds a reusable benchmark for validator + repair + re-validation.

This task did not modify product code, production prompts, pipeline, frontend/backend business logic, release tags, or API-key configuration.

## 2. Experiment Framework

Each run executes:

1. Generate scene text with numbered beats + self-check.
2. Rule-based precheck.
3. Natural-language LLM validator.
4. Strict JSON LLM validator.
5. Disagreement check.
6. Repair if missing / partial / forbidden violation exists.
7. Rule + JSON re-validation.

## 3. Cases

Six cases are stored as structured JSON under `cases/`:

- case-01-seventh-protocol
- case-02-ending-hook
- case-03-injury-limitation
- case-04-item-handover
- case-05-location-lock
- case-06-no-new-entity

## 4. Validators

- Rule-based precheck: keyword and forbidden-keyword helper, not final authority.
- Natural validator: Markdown evidence and overall status.
- JSON validator: structured `satisfied / partial / missing` and forbidden violation output.

## 5. Repair Prompts

The benchmark uses a minimal repair prompt that asks the model to preserve most of the original text and only repair missing beats or violations. Additional prompt variants are documented under `repair-prompts/`.

## 6. Scoring Method

Metrics include initial beat completion, JSON parse rate, rule/natural/JSON agreement, repair trigger count, repair success, new error rate, final usable rate, and total latency.

## 7. Result Table

| Metric | Value |
| --- | ---: |
| Runs | 6 |
| Initial beat completion rate | 95.24% |
| Validator JSON parse rate | 100.00% |
| Validator agreement rate | 50.00% |
| Repair trigger count | 3 |
| Repair success rate | 33.33% |
| New error rate | 0.00% |
| Final usable rate | 66.67% |
| Average total latency | 42.70s |

## 8. Run Detail

| Case | Run | Initial completion | JSON parse | Disagreement | Repair triggered | Repair success | Final usable | Latency |
| --- | --- | ---: | --- | --- | --- | --- | --- | ---: |
| case-01-seventh-protocol | case-01-seventh-protocol-s1 | 100.00% | True | False | False | False | True | 35.58s |
| case-02-ending-hook | case-02-ending-hook-s1 | 100.00% | True | True | True | False | False | 47.14s |
| case-03-injury-limitation | case-03-injury-limitation-s1 | 75.00% | True | True | True | True | True | 45.17s |
| case-04-item-handover | case-04-item-handover-s1 | 100.00% | True | True | True | False | False | 44.10s |
| case-05-location-lock | case-05-location-lock-s1 | 100.00% | True | False | False | False | True | 48.10s |
| case-06-no-new-entity | case-06-no-new-entity-s1 | 100.00% | True | False | False | False | True | 36.10s |

## 9. Disagreement Analysis

Disagreement is marked when rule-based missing/violation ids differ from JSON validator ids, or when the natural validator's overall repair signal differs from the rule precheck.

Because rule-based checks are intentionally simple, disagreement should be interpreted as an audit target, not automatic validator failure.

## 10. Repair Success Analysis

Repair success requires both final rule precheck and JSON re-validation to report satisfied. This is stricter than prompt-only self-check and closer to a future product safety gate.

## 11. New Error Analysis

New errors are counted when repair increases forbidden violations or expands the text far beyond the original, which indicates broad rewriting rather than minimal repair.

## 12. Productization Recommendation

Do not productize validator yet; continue prompt, case, and model comparison.

## 13. Next Step

Before T8.3, run at least 2 samples per case and manually audit disagreement cases. If validator remains stable but repair is risky, productize warnings before automatic repair.
