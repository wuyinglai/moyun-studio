# T8.2.1 Required Beats Benchmark Summary

## 1. Background

T8.2 showed that facts-first prompt ordering did not solve required-beat omission. This experiment isolates that failure mode: whether small models reliably include mandatory scene beats in prose.

This task did not modify product code, production prompts, pipeline, frontend, backend, release tags, workspace data, or API-key configuration.

## 2. Relation to T8.0 / T8.1 / T8.2

| Stage | Focus | Result feeding this task |
| --- | --- | --- |
| T8.0 | Single prompt wording | Prompt wording alone was not enough to guarantee logic |
| T8.1 | Prompt assembly strategies | Facts-first looked practical but not decisive |
| T8.2 | Product opt-in facts-first + debug prompt export | Both current-like and facts-first missed a required beat |
| T8.2.1 | Required beats stability | Tests required-beat completion directly |

## 3. Model and Method

- Model: `agnes-2.0-flash`
- Calls: 4 cases x 4 variants = 16 generations
- Temperature: 0.1
- Output target: about 500 Chinese characters
- Scoring: deterministic required-beat checks plus leak/outline/contradiction checks
- API keys: not printed or written

## 4. Prompt Variants

| Variant | Strategy |
| --- | --- |
| A | Inline required beats |
| B | Numbered required beats |
| C | Silent self-check before final output |
| D | Beat outline first, final prose only |

## 5. Test Cases

| Case | Focus | Required beat count |
| --- | --- | ---: |
| case-01-seventh-protocol | Seventh Layer Protocol | 4 |
| case-02-item-handover | Item Handover | 4 |
| case-03-injury-limitation | Injury Limitation | 4 |
| case-04-ending-hook | Ending Hook | 4 |

## 6. Result Table

| Variant | Beat completion rate | Missing beats | Leak count | Usable candidates | Average time | Conclusion |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A Inline required beats | 81.25% | 3 | 1 | 3/4 | 3.44s | Mixed |
| B Numbered required beats | 87.50% | 2 | 1 | 3/4 | 9.07s | Mixed |
| C Self-check after draft | 93.75% | 1 | 0 | 4/4 | 6.31s | Best |
| D Beat outline first | 62.50% | 6 | 1 | 3/4 | 5.96s | Mixed |

## 7. Case-Level Detail

| Case | Variant | Completed | Missing | Leaks | Usability | Time |
| --- | --- | ---: | --- | --- | ---: | ---: |
| case-01-seventh-protocol | A | 4/4 | None | None | 1 | 3.99s |
| case-01-seventh-protocol | B | 4/4 | None | None | 1 | 2.86s |
| case-01-seventh-protocol | C | 4/4 | None | None | 2 | 3.32s |
| case-01-seventh-protocol | D | 4/4 | None | None | 2 | 2.67s |
| case-02-item-handover | A | 4/4 | None | None | 2 | 3.42s |
| case-02-item-handover | B | 4/4 | None | None | 2 | 7.56s |
| case-02-item-handover | C | 4/4 | None | None | 2 | 4.19s |
| case-02-item-handover | D | 2/4 | medicine_with_shen, side_effect_hint | None | 1 | 15.10s |
| case-03-injury-limitation | A | 3/4 | helps_by_observation | None | 1 | 2.70s |
| case-03-injury-limitation | B | 4/4 | None | None | 2 | 3.20s |
| case-03-injury-limitation | C | 4/4 | None | None | 2 | 4.81s |
| case-03-injury-limitation | D | 2/4 | no_high_fight, helps_by_observation | None | 1 | 4.26s |
| case-04-ending-hook | A | 2/4 | lin_recognizes, identity_hidden | 那是 | 0 | 3.64s |
| case-04-ending-hook | B | 2/4 | lin_recognizes, identity_hidden | 那是 | 0 | 22.68s |
| case-04-ending-hook | C | 3/4 | lin_recognizes | None | 1 | 12.94s |
| case-04-ending-hook | D | 2/4 | lin_recognizes, identity_hidden | 那是 | 0 | 1.82s |

## 8. Best Strategy

Best strategy in this run: **Variant C - Self-check after draft**.

The result should be treated as directional, not final. The sample is intentionally small and deterministic scoring can miss semantic equivalents.

## 9. Key Findings

1. Required beats can still be missed even when they are clearly present in the prompt.
2. Numbered or self-check wording improves auditability of the instruction but does not guarantee completion.
3. Beat-outline-first can help the model attend to required beats, but it risks mechanical prose or accidental outline leakage.
4. Required-beat omission should be treated as a reliability problem separate from general continuity or prose quality.
5. A product-grade solution likely needs post-generation beat validation, not prompt wording alone.

## 10. Should This Enter Product Prompt Assembly?

Not as a default prompt replacement yet.

Recommended product direction:

- keep production prompts unchanged;
- use debug prompt export to confirm beats enter final prompts;
- add a required-beat validator experiment before T8.3;
- only consider product prompt changes after a larger sample shows stable improvement.

## 11. Next Step

Run T8.2.2 with an explicit beat validator: generate prose, check required beats deterministically or with a separate model, then either repair the draft or create a candidate warning. Do not start Scene Plan + Checker productization until required-beat validation is understood.
