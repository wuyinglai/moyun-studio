# T8.11 Polish Prompt Tuning

## Background

T8.10 dogfood found that rewrite was mostly stable, while polish could preserve hard constraints but still introduce quality risks:

- awkward or invented micro-actions;
- unclear caring actions;
- subtle continuity expansion;
- over-literary phrases;
- occasional relationship jumps.

T8.11 focuses only on polish prompt tuning. It does not add UI, APIs, validator behavior, automatic repair, auto-adopt, Scene Plan, or candidate/adopt/delete logic.

Baseline commit:

```text
5492b04 docs: add T8.10 rewrite polish dogfood report
```

## Prompt Changes

Added a new polish-only prompt block:

```text
prompts/blocks/polish-conservative-rules.md
```

Included it in all polish pipeline steps:

- `prompts/pipeline/polish/depai.md`
- `prompts/pipeline/polish/prose.md`
- `prompts/pipeline/polish/logic.md`
- `prompts/pipeline/polish/rhythm.md`

This keeps rewrite prompts unchanged. A backend prompt-rendering test now verifies that polish includes the new block and rewrite does not.

## Micro-action Constraints

The new block states that polish is not rewrite and must keep:

- original facts;
- action order;
- character position;
- body state;
- held objects;
- relationship state.

It also tells the model not to invent unsupported:

- small actions;
- body contact;
- expression conclusions;
- psychological jumps;
- movements that conflict with injury, posture, distance, or held objects.

## Continuity Constraints

The block adds constraints for subtle continuity drift:

- Keep original narrative person and viewpoint.
- Preserve explicit body parts, props, locations, titles, and key nouns.
- Do not replace key nouns with rare words or words likely to drift in meaning.
- Do not turn softened relationship tension into reconciliation, confession, promise, or confirmed relationship.
- Keep direct quote meaning stable.
- Prefer plain clarity over decorative phrasing when action clarity is at risk.

## Prompt Impact

`scripts/prompt-impact.py` reported the new block affects only the polish prompt files:

```text
prompts/pipeline/polish/depai.md
prompts/pipeline/polish/logic.md
prompts/pipeline/polish/prose.md
prompts/pipeline/polish/rhythm.md
```

Individual polish prompt files still affect the expected `polish.yaml` pipeline. `logic/rhythm/depai` are also referenced by rewrite/review chains, so the tuning was isolated in a polish-only include and only inserted under `prompts/pipeline/polish/`.

## Dogfood Method

Model:

```text
agnes-2.0-flash
```

Transport limitation:

- Raw Chinese input/output through the Agnes MCP still triggered Unicode transport failures.
- Dogfood therefore used ASCII prompts and required Chinese output as JSON unicode escapes.
- A second pass gave the model key Chinese terms as unicode-escaped terms to better simulate product prompts that contain real Chinese source text.

This limitation means the dogfood is useful for trend-checking constraints, but the final quality should still be verified through the product backend with real Chinese prompt payloads.

## Scenario A: Injury / Action Constraint

Original:

```text
她右肩仍疼，靠在墙边，左手扶着剑鞘。主角走过去，把披风搭在她肩上。她没有躲，只低声说了一句：“别以为这样我就信你。”
```

Required beats:

- Right shoulder injury remains.
- She cannot use the right hand to hold a sword.
- The protagonist's caring action remains.
- Her attitude softens but she is still guarded.

Forbidden beats:

- No right-hand sword fighting.
- No sudden confession.
- No miracle healing medicine.

After tuning:

- The output kept right shoulder pain, wall position, left-hand scabbard support, and cloak care.
- It did not add right-hand sword fighting, confession, or healing medicine.
- It kept guardedness.
- Compared with T8.10 Scenario B, the action staging was clearer and did not invent a strange sword technique.
- Weakness: the model repeated the injury/guardedness and added some explanatory phrasing, so the output still needed light human polish before adoption.

Score:

| Dimension | Score |
|---|---:|
| Required beats retained | 5 |
| Forbidden beats avoided | 5 |
| Micro-action safety | 4 |
| Continuity safety | 4 |
| Polish quality | 3 |
| Adopt-worthy | 3 |

## Scenario B: Distance / Held Object Constraint

Original:

```text
主角站在门外，没有进屋。他手里握着那枚银色芯片，只从门缝里看见桌上的半张地图。
```

Required beats:

- The protagonist remains outside the door.
- The silver chip remains in the protagonist's hand.
- The protagonist can only see half a map through the door crack.

Forbidden beats:

- The protagonist cannot enter the room.
- The protagonist cannot pick up the map.
- The full map content cannot be revealed.

After tuning:

- The output kept the protagonist outside the door.
- The silver chip remained in hand.
- The protagonist only observed half the map through the door crack.
- The map was not picked up and full content was not revealed.
- A previous dogfood pass changed viewpoint into first person; the tuned pass preserved third-person viewpoint when explicitly constrained.
- Weakness: the model used one awkward phrase, which suggests the "avoid odd phrases" rule helps but does not fully solve small-model diction issues.

Score:

| Dimension | Score |
|---|---:|
| Required beats retained | 5 |
| Forbidden beats avoided | 5 |
| Micro-action safety | 5 |
| Continuity safety | 4 |
| Polish quality | 3 |
| Adopt-worthy | 4 |

## Scenario C: Restrained Relationship Constraint

Original:

```text
她替他把衣领理平，手指停了一瞬，又很快收回去。主角没有说谢，只看着她避开的眼神。
```

Required beats:

- She adjusts the protagonist's collar.
- Her action remains restrained.
- The protagonist notices her avoiding gaze.
- The relationship is ambiguous but cannot be named directly.

Forbidden beats:

- No direct confession.
- No kissing.
- Do not write them as a confirmed couple.

After tuning:

- The output preserved collar adjustment, brief finger pause, quick withdrawal, and avoided gaze.
- It did not add confession, kissing, or confirmed relationship.
- It kept restraint better than the earlier T8.10-style polish.
- Weakness: it still added a small extra movement and used a few over-literary phrases. It also came close to naming the relationship too explicitly near the end.

Score:

| Dimension | Score |
|---|---:|
| Required beats retained | 4 |
| Forbidden beats avoided | 5 |
| Micro-action safety | 3 |
| Continuity safety | 4 |
| Polish quality | 3 |
| Adopt-worthy | 3 |

## Before / After

T8.10 baseline polish issue:

```text
Required and forbidden beats were mostly retained, but the output introduced an awkward invented sword-technique phrase and unclear caring action.
```

T8.11 tuned result:

- The model became more likely to preserve held objects, injury limits, and distance boundaries.
- The model was less likely to create a large forbidden action.
- Explicit viewpoint and key-noun constraints reduced the first-person drift and noun drift seen in early dogfood attempts.
- The model still sometimes produces awkward wording, repetition, or mild over-literary phrasing.

## Required / Forbidden Beats

| Scenario | Required beats | Forbidden beats |
|---|---|---|
| A | Passed | Passed |
| B | Passed | Passed |
| C | Mostly passed | Passed |

## Polish Quality

| Scenario | T8.10 baseline reference | T8.11 tuned dogfood | Change |
|---|---:|---:|---|
| A injury/action | 2/5 from similar T8.10 B | 3/5 | Improved |
| B distance/object | Not directly tested | 3/5 | Safe but wording imperfect |
| C restrained relation | Not directly tested | 3/5 | Safe but still ornate |

## Bugs Found

No confirmed product-code bug was found.

Dogfood findings:

1. Agnes MCP remains unreliable for raw Chinese input/output, requiring unicode-escaped workarounds.
2. Small models can still produce awkward phrases even with stronger constraints.
3. The prompt is better at preventing hard continuity violations than at guaranteeing elegant prose.

## Fixes

Implemented:

- Added `prompts/blocks/polish-conservative-rules.md`.
- Included the block in all polish steps.
- Added backend prompt-rendering tests for polish constraints and rewrite isolation.

No frontend, API, candidate service, validator core, adopt/delete/hash, or Scene Plan code was changed.

## Remaining Issues

- Need one future in-product dogfood run through the actual backend LLM path using real Chinese prompt payloads, because MCP transport constraints are not identical to the product path.
- The polish prompt should remain candidate-only; do not auto-adopt polished output.
- If polish quality remains uneven, the next improvement should be evaluator-side quality notes or feedback revision, not automatic repair.

## Recommendation

T8.11 can close.

The tuned prompt improves safety around micro-actions, held objects, viewpoint, and relationship progression. It does not fully solve small-model prose awkwardness, but it reduces the most dangerous polish regressions without touching candidate safety.

## Next Step

Recommended next task:

```text
T8.12: In-product Chinese LLM dogfood for polish candidate quality
```

Focus:

- Run through the backend pipeline with real Chinese source text.
- Verify candidate metadata and UI remain stable.
- Compare adopt-worthy rate against T8.10/T8.11 reports.
