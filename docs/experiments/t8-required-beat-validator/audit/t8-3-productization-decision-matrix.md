# T8.3 Productization Decision Matrix

## 1. Productizable Capability List

| Capability | Productize? | Reason |
| --- | --- | --- |
| JSON validator warning | Yes | JSON parse rate reached 100% in the expanded run and structured beat completion is suitable for candidate metadata. |
| Natural validator explanation | Yes, limited | Useful for human-readable explanations and causal concerns, but should not be the sole machine gate. |
| Rule-based precheck | Yes, internal only | Useful as a weak, cheap audit signal. It must not block adoption or trigger repair by itself. |
| Auto repair | No | Even successful repairs require author review; ambiguous side-effect/knowledge-boundary cases remain. |
| Repair candidate | Yes | Generate a separate candidate only after validation warnings, with explicit user preview/adopt. |
| Required beats UI | Yes | Showing missing/partial beats and validator warnings can help authors control scene goals. |

## 2. Minimum T8.3 Plan

Recommended minimum scope:

```text
T8.3-mini: Required Beat Warning Candidate Metadata
```

Proposed behavior:

1. After a candidate is generated, run required-beat validation.
2. Store validation summary in candidate metadata.
3. CandidatePanel displays warnings such as missing beat, partial beat, forbidden-risk, terminal-hook issue, or knowledge-boundary risk.
4. No automatic repair.
5. User may click `Generate repair candidate` to create a separate repair candidate.
6. Adopt flow shows warnings before the user adopts the candidate.

## 3. Candidate Metadata Draft

```json
{
  "validation": {
    "validator_version": "t8-validator-semantic-v2",
    "case_schema_version": "t8-required-beat-case-v2",
    "overall_status": "satisfied | needs_repair | unusable",
    "required_beats": [
      {
        "id": "beat-1",
        "status": "satisfied | partial | missing",
        "evidence": "short quote",
        "evidence_quality": "exact | paraphrase | weak | absent"
      }
    ],
    "forbidden_violations": [
      {
        "id": "forbid-1",
        "violated": false,
        "evidence": ""
      }
    ],
    "logic_risks": [],
    "repair_candidate_available": true
  }
}
```

## 4. Do Not Enter T8.3 Conditions

Do not implement product validator flow if any of these occur in the next regression:

- JSON parse rate drops below 95%.
- Final usable rate drops below 80%.
- Repair introduces harmful errors above 10%.
- Agreement falls below the T8.2.2 baseline of 50%.
- Manual audit finds JSON validator frequently over-infers identity or knowledge-boundary violations.

## 5. Decision

Enter T8.3 only for warning/candidate metadata.

Do not productize automatic repair. Repair should remain a user-triggered candidate generation path with preview and explicit adopt.
