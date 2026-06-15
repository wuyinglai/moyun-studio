# T8.10 Rewrite / Polish Real LLM Dogfood

## Background

T8.9 fixed the writing quality chain by rendering required / forbidden beats into rewrite and polish prompts, hardening beat validator result alignment, and adding one retry for validator failures.

This dogfood checks whether the rewrite / polish / feedback revision flow behaves well with a real LLM under small-model constraints.

Baseline commit:

```text
c7de22e fix: improve writing quality chain reliability
```

## T8.9 Fixes Checked

- Rewrite prompts include required / forbidden beats through `prompts/blocks/beat-constraints.md`.
- Polish prompts include required / forbidden beats through the same shared block.
- Required beat validator no longer trusts model result order as the primary alignment method.
- Validator metadata records alignment and retry context.
- Feedback revision candidates inherit beat context and do not overwrite source content.

## Method

Real LLM model used:

```text
agnes-2.0-flash
```

Notes:

- The Agnes MCP handled ASCII prompts normally, but raw Chinese prompt input/output triggered MCP Unicode transport failures or timeouts.
- To avoid leaking keys and to keep using the real LLM, dogfood generation asked the model to return JSON with Chinese text encoded as JSON unicode escapes.
- Actual project prompt assembly was verified locally by rendering the repository templates with Jinja2. The rendered rewrite and polish prompts contained all required and forbidden beats.
- No product code, production prompt, workspace data, candidate files, or source scenes were modified.

Prompt assembly evidence:

| Scenario | Action | Template | Required beats in prompt | Forbidden beats in prompt |
|---|---|---|---:|---:|
| A | rewrite | `pipeline/rewrite/draft.md` | Yes | Yes |
| B | polish | `pipeline/polish/prose.md` | Yes | Yes |
| C | rewrite | `pipeline/rewrite/draft.md` | Yes | Yes |
| D | feedback revision | inherited context | Yes | Yes |

## Scenario A: Clue-preserving Rewrite

Input facts:

- The protagonist finds a silver chip at an old pier.
- The chip has incomplete coordinates.
- The protagonist does not know what the coordinates point to.

Required beats:

- Silver chip remains.
- Incomplete coordinates remain.
- The protagonist cannot fully understand the coordinate meaning.

Forbidden beats:

- Do not reveal the full coordinate destination.
- Do not introduce a mysterious organization.

Result summary:

- The output kept the old pier, silver chip, and incomplete coordinates.
- The protagonist still did not understand the destination.
- The text only hinted at unknown danger and did not reveal the destination.
- No mysterious organization was introduced.
- Prose quality was usable, though some suspense phrasing was generic.

Validator-style check:

```text
status: pass
missing required beats: none
forbidden violations: none
```

Score:

| Dimension | Score |
|---|---:|
| Prompt assembly | 5 |
| Rewrite quality | 4 |
| Required beats retained | 5 |
| Forbidden beats avoided | 5 |
| Validator warning usefulness | 4 |
| Feedback revision improvement | N/A |
| Adopt safety | 5 |

## Scenario B: Character-state Polish

Input facts:

- The heroine's right shoulder is injured.
- She cannot hold a sword with her right hand.
- She and the protagonist are close, but she still has guarded distrust.

Required beats:

- Right shoulder injury appears.
- The heroine cannot use the right hand to hold a sword.
- The protagonist performs one caring action.
- The relationship may soften but cannot fully reconcile.

Forbidden beats:

- No right-hand sword fighting.
- No sudden confession.
- No miracle healing medicine.

Result summary:

- The output kept the right shoulder injury and right-hand limitation.
- It avoided confession and miracle healing.
- It included a caring action, but the action was not cleanly staged.
- The output introduced an awkward phrase around sword technique, making the scene less natural than intended.

Validator-style check:

```text
status: warning
missing required beats: none
forbidden violations: none
quality risks:
- awkward invented phrase
- unclear caring action
```

Score:

| Dimension | Score |
|---|---:|
| Prompt assembly | 5 |
| Polish quality | 2 |
| Required beats retained | 4 |
| Forbidden beats avoided | 5 |
| Validator warning usefulness | 4 |
| Feedback revision improvement | 4 |
| Adopt safety | 5 |

## Scenario C: Ending-suspense Rewrite

Input facts:

- The protagonist finds a page left by the master in an abandoned study.
- Only half of the page remains.

Required beats:

- The ending must leave a new question.
- An abnormal trace left by the master must appear.
- Readers know there is a secret, but the protagonist cannot fully know the answer.

Forbidden beats:

- Do not reveal the master's true identity.
- Do not include a behind-the-scenes villain confession.
- Do not explain the whole mystery with narration.

Result summary:

- The output created an abnormal trace and a new question around a hidden box.
- It did not reveal the master's identity or explain the full mystery.
- It introduced an unrequested implication that the master may be dead. This is not a direct forbidden violation, but it is a continuity risk if the source story has not established that fact.

Validator-style check:

```text
status: pass
missing required beats: none
forbidden violations: none
quality risks:
- unrequested implication of the master's death
```

Score:

| Dimension | Score |
|---|---:|
| Prompt assembly | 5 |
| Rewrite quality | 4 |
| Required beats retained | 5 |
| Forbidden beats avoided | 4 |
| Validator warning usefulness | 3 |
| Feedback revision improvement | N/A |
| Adopt safety | 5 |

## Scenario D: Feedback Revision

Parent:

- Scenario B polish candidate.

Feedback:

```text
补上缺失信息点，不要新增人物，保持原来的悬念。
```

Dogfood feedback instruction:

- Fix awkward wording.
- Clarify the caring action.
- Preserve right shoulder injury, right-hand limitation, guarded relationship, and no-confession constraint.

Result summary:

- The child revision removed the awkward sword-technique phrase.
- It made the protagonist's care clearer by moving the sword hilt to the left hand and placing a coat over the heroine's shoulder.
- The relationship softened slightly but remained guarded.
- The child did not auto-adopt and should remain a candidate until explicit adoption.
- Minor stiffness remained, but the revision was clearly more usable than the parent.

Validator-style check:

```text
status: pass by manual review
model evaluator note: one ASCII-only validator-style response contradicted itself by listing forbidden items while summarizing "No forbidden elements present."
manual verdict: no actual forbidden violation found
```

Score:

| Dimension | Score |
|---|---:|
| Prompt assembly | 5 |
| Revision quality | 4 |
| Required beats retained | 5 |
| Forbidden beats avoided | 5 |
| Validator warning usefulness | 3 |
| Feedback revision improvement | 4 |
| Adopt safety | 5 |

## Score Summary

| Scenario | Action | Prompt assembly | Quality | Required beats | Forbidden beats | Validator usefulness | Revision improvement | Adopt safety | Average |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | rewrite | 5 | 4 | 5 | 5 | 4 | N/A | 5 | 4.7 |
| B | polish | 5 | 2 | 4 | 5 | 4 | 4 | 5 | 4.1 |
| C | rewrite | 5 | 4 | 5 | 4 | 3 | N/A | 5 | 4.3 |
| D | revise | 5 | 4 | 5 | 5 | 3 | 4 | 5 | 4.4 |

Overall average across scored dimensions:

```text
4.4 / 5
```

## Safety Checks

| Safety point | Result |
|---|---|
| rewrite / polish generate candidates, not source overwrites | Passed by existing candidate contract and T8.9/T8.10 test coverage |
| feedback revision creates child candidate, not source overwrite | Passed by existing feedback revision tests |
| source text changes only after adopt | Passed by contract and existing tests |
| delete does not affect source text | Passed by candidate workflow E2E coverage |
| parent candidate is not modified by child revision | Passed by existing feedback revision tests |
| warning does not block adopt | Passed by T8.4/T8.5 coverage |
| unknown state does not crash | Passed by beat validator tests |
| debug prompt is not persisted into private files | No persistence observed in this dogfood |
| API key leakage | No API key was read, printed, or committed |
| old candidate compatibility | Covered by previous T8.3/T8.4 E2E reports |

## Bugs Found

No product-code bug was confirmed in this dogfood.

Quality / evaluation findings:

1. Polish is more likely than rewrite to introduce awkward micro-actions or unnatural phrases.
2. Ending rewrite can introduce subtle unrequested facts, such as implying a character is dead.
3. Validator-style LLM output can still be internally contradictory even when the final human-readable summary is correct.
4. Long unicode-escaped Chinese output can be truncated when using the Agnes MCP workaround; actual product streaming should not use this workaround.

## Fixes

No code fix was made in this task.

## Remaining Issues

1. Real in-product Chinese LLM dogfood should be repeated through the actual backend provider once a safe non-MCP key path is available.
2. Validator usefulness is good for missing beats, but less reliable for prose-quality risks and subtle continuity expansion.
3. Polish prompts may need an additional "do not invent action technique / do not over-stage physical action" style constraint in a future prompt-tuning task.
4. Revision feedback worked, but it should be tested on longer 600-1000 character real scenes before release-level confidence.

## Recommendation

T8.10 can close as a dogfood checkpoint.

The chain is directionally stable:

- Prompt assembly is correct.
- Required beats survived rewrite, polish, and feedback revision.
- Forbidden beats were avoided in all dogfood scenarios.
- Feedback revision improved the weakest parent candidate.

Do not turn on automatic repair yet. The better next step is a focused T8.11 prompt-quality pass for polish micro-actions and subtle continuity expansion.

## Next Step

Recommended next task:

```text
T8.11: Polish micro-action and continuity expansion prompt tuning
```

Focus:

- Add a small polish-specific constraint against invented physical techniques.
- Add evaluation cases for subtle continuity expansion.
- Keep all high-risk changes candidate-only.
