# T8.2.5 Expanded Disagreement Manual Audit

## 1. Scope

Manual audit of `audit-candidates.csv` from run `t8-2-5-20260614-112700`.

This audit does not modify product code, production prompts, pipeline, workspace data, candidates, releases, or API-key configuration.

## 2. Audit Summary

| Sample | Human Overall | Closest Validator | Disagreement Type | Auto Repair |
| --- | --- | --- | --- | --- |
| case-02-ending-hook-s1 | pass | natural/json | rule_too_strict | no |
| case-02-ending-hook-s2 | pass | natural/json | rule_too_strict | no |
| case-04-item-handover-s1 | needs_repair | json | ambiguous_case | no |
| case-04-item-handover-s2 | needs_repair | mixed | ambiguous_case | no |

## 3. Findings

### case-02-ending-hook

Both samples satisfy the terminal hook and preserve the identity boundary. The rule weak signal fired because the forbidden keyword `??` appears in harmless recognition phrasing. This confirms T8.2.4's design: rule precheck is useful for audit triage, but it must not trigger repair or block final usability.

### case-04-item-handover-s1

JSON was closest to human judgment. The original text completes the hard beats but has a real pronoun ambiguity: the medicine is controlled by Shen Zhixia, while a later sentence says it must remain in `???`. The repair is safe in this run, but should still be a candidate requiring preview/adopt.

### case-04-item-handover-s2

This is an ambiguous quality case. Required beats pass, but the side-effect trigger is under-specified because the scene says Shen does not inject the medicine, then shows symptoms. Natural validation is closer on the logic gap; JSON is closer on strict beat completion. This is exactly the type of sample that should surface as a warning, not automatic repair.

## 4. Validator Lessons

- JSON validator is reliable for structured beat completion and candidate metadata.
- Natural validator is useful for explaining causal/quality concerns.
- Rule weak signal remains useful as a cheap audit candidate extractor, especially for terminal hooks and forbidden phrases, but is too blunt for final judgment.
- Repair should not be auto-applied even when the single repair in this run was safe.

## 5. Repair Risk Judgment

| Repair Mode | Judgment | Reason |
| --- | --- | --- |
| Automatic repair | Not allowed | Ambiguous quality issues still need author review. |
| Repair candidate | Allowed | Safe if generated as separate candidate with preview/adopt. |
| Validator warning only | Recommended | Best current productization target. |

## 6. Next Step

Proceed to T8.3 design only as validator warning/candidate metadata, not automatic repair.
