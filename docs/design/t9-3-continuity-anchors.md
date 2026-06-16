# T9.3 Continuity Anchors Minimal Design

Date: 2026-06-17

Risk: Risk C

Mode: Product Design Only

Baseline:

```text
949eeab docs: close T9.2 test debt stage
```

## 1. Background

Moyun Studio v0.2.0 has closed the first writing-quality loop:

- required / forbidden beats input;
- prompt injection for generate / rewrite / polish / feedback revision;
- beat validator metadata;
- CandidatePanel quality warning display;
- warning / unknown advisory status;
- feedback revision child candidates;
- multi-round revision lineage;
- conservative polish rules;
- real Chinese backend prompt chain smoke;
- real UI + real LLM smoke;
- candidate-only safety boundaries.

T9.2 also closed the test debt phase:

```text
full mock E2E: 62 passed -> 74 passed
focused candidate workflow: 16 passed -> 22 passed
new T9.2c focused spec: 6 passed
full mock E2E: 0 failed
```

The next product risk is long-form continuity. Small models can follow local beats, but they still drift on character state, item ownership, relationship stage, location constraints, hidden clues, and world rules across multiple scenes.

## 2. Target Problem

Continuity Anchors solve cross-scene and cross-chapter state drift.

They are explicit user-controlled constraints that tell the model:

```text
These facts are currently true in the story. Respect them when generating candidates.
Do not silently change, resolve, skip, or contradict them.
```

Examples:

- The heroine's right shoulder is injured and has not healed.
- The silver chip is currently in the protagonist's possession.
- The "Seventh Layer Protocol" name is known, but its full truth is not revealed.
- Two characters are warmer toward each other but are not fully trusting yet.
- Healing cannot happen instantly; medicine and rest are required.

Continuity Anchors are not:

- Scene Plan;
- automatic outline;
- automatic story database;
- automatic repair;
- automatic official text edit;
- automatic adopt.

They only influence candidate generation and advisory warnings.

## 3. Difference From Required / Forbidden Beats

### Required / Forbidden Beats

Required / forbidden beats are local generation instructions.

They answer:

```text
What must happen or must not be revealed in this specific scene generation?
```

They are short-lived and task-specific.

Examples:

- This scene must mention the silver chip.
- This scene must not reveal the full destination coordinates.
- This generation must preserve the ending hook.

### Continuity Anchors

Continuity Anchors are longer-lived continuity constraints.

They answer:

```text
What story state must remain true across scenes until the author changes or archives it?
```

They are project-level or scope-level state.

Examples:

- The heroine still cannot use her right hand to fight.
- The protagonist does not yet know the master's real identity.
- The silver chip remains in the protagonist's hand.
- The "Seventh Layer Protocol" truth is still hidden.

### Priority Rule

If both exist:

```text
required / forbidden beats define the current generation goal;
Continuity Anchors define the long-term factual boundary.
```

If they conflict, the product should warn the user instead of silently choosing one.

## 4. Anchor Types

MVP should keep the taxonomy small.

### 4.1 Character State Anchors

Use for physical state, capability limits, psychological state, relationship stage, and current goal.

Examples:

```text
The heroine's right shoulder is injured; she cannot wield a sword with her right hand.
The protagonist suspects his master but has no proof yet.
```

### 4.2 Plot / Clue Anchors

Use for discovered clues, unrevealed truth, current mystery, and forbidden early revelation.

Examples:

```text
The silver chip has appeared, but the full destination coordinates remain unknown.
The Seventh Layer Protocol has only appeared as a name; its truth is not known.
```

### 4.3 Object / Location Anchors

Use for item ownership, location state, scene restriction, and spatial relation.

Examples:

```text
The silver chip is currently in the protagonist's possession.
The protagonist has not entered the study yet; he is still outside the door.
```

### 4.4 Relationship Anchors

Use for intimacy, conflict, trust, and forbidden jumps.

Examples:

```text
The heroine has softened toward the protagonist but still keeps her guard up.
They cannot suddenly confess love or fully reconcile.
```

### 4.5 World Rule Anchors

Use for magic / technology limits, organizational rules, time rules, and immutable settings.

Examples:

```text
Healing cannot complete instantly; it requires medicine and rest.
The chip can only display partial coordinates, not project a complete map.
```

## 5. Data Model

MVP schema:

```json
{
  "anchors": [
    {
      "id": "anchor-character-001",
      "type": "character_state",
      "title": "Heroine right shoulder injury",
      "content": "The heroine's right shoulder is injured and not healed; she cannot wield a sword with her right hand.",
      "scope": "global",
      "status": "active",
      "priority": "high",
      "source": "user",
      "updated_at": "2026-06-17T00:00:00Z"
    }
  ]
}
```

Field meanings:

| Field | Meaning |
| --- | --- |
| `id` | Stable anchor reference. |
| `type` | One of `character_state`, `plot_clue`, `object_location`, `relationship`, `world_rule`. |
| `title` | Short label for UI and prompt grouping. |
| `content` | Full continuity constraint. |
| `scope` | `global`, `chapter`, `scene`, or `character`. |
| `status` | `active`, `resolved`, or `archived`. |
| `priority` | `high`, `normal`, or `low`. |
| `source` | `user`, `extracted`, or `imported`. MVP only creates `user`. |
| `updated_at` | Last edited timestamp. |

MVP constraints:

- support user-created anchors only;
- no automatic extraction;
- no automatic update;
- no graph;
- no automatic resolution detection.

Suggested storage:

```text
continuity-anchors.json
```

This should be a project-level system file, separate from official scene body files and candidate files.

## 6. UI Design

MVP UI should be a lightweight right-panel section, not a complex knowledge-base editor.

Recommended entry:

```text
Right Panel -> Continuity Anchors
```

Minimal controls:

- add anchor;
- edit anchor;
- archive anchor;
- filter by type;
- filter by active / archived;
- priority selector;
- enable / disable anchors for the next generation;
- show active anchors count.

Generation flow:

```text
User opens project
-> adds or edits anchors in the Continuity Anchors section
-> generate / rewrite / polish / feedback revision uses active anchors
-> CandidatePanel shows "Used N continuity anchors"
-> if candidate may violate anchors, CandidatePanel shows warning
-> user preview / adopt manually
```

UI should avoid:

- graph view;
- full database UI;
- auto-extracted fact lists;
- mandatory confirmation before each generation.

## 7. Prompt Design

Anchors should enter prompt as a grouped factual constraint block.

Recommended prompt block:

```text
【Continuity Anchors / 连续性锚点】
The following items represent current story state. Respect them during generation.
Do not silently change, resolve, skip, or contradict them.

Character State:
- The heroine's right shoulder is injured; she cannot wield a sword with her right hand.

Plot / Clue:
- The silver chip has appeared, but the complete destination coordinates are not revealed.

Relationship:
- The heroine has softened toward the protagonist but still keeps her guard up; they cannot suddenly confess love.
```

Rules:

- `generate`, `rewrite`, `polish`, and `feedback_revision` should be able to read active anchors.
- Anchors and required beats are parallel inputs.
- Required beats take priority for the current scene task.
- Anchors take priority for long-term factual continuity.
- If prompt budget is tight, inject only `active` + `high` priority anchors first.

Prompt safety instruction:

```text
If an anchor seems incompatible with the requested scene, do not invent a workaround.
Keep the anchor true and write the scene around it, or surface uncertainty as a warning in metadata.
```

## 8. Candidate Metadata

Candidates should record which anchors were used for generation.

Recommended metadata:

```json
{
  "generation_context": {
    "continuity_anchors_enabled": true,
    "anchors_used": [
      {
        "id": "anchor-character-001",
        "type": "character_state",
        "title": "Heroine right shoulder injury",
        "priority": "high",
        "content_hash": "sha256:..."
      }
    ]
  },
  "anchor_validation": {
    "status": "warning",
    "warnings": [
      {
        "anchor_id": "anchor-character-001",
        "message": "The candidate seems to let the heroine use her right hand to fight, which may violate the shoulder injury anchor."
      }
    ]
  }
}
```

Why store `content_hash`:

- Candidate provenance stays stable even if the user later edits the anchor text.
- The UI can still show the title and id without storing large repeated anchor content in every candidate.

MVP can also store a short snapshot for display:

```json
{
  "anchor_snapshot": "The heroine's right shoulder is injured..."
}
```

This should be capped in length and must not include secrets.

## 9. Validator / Warning Design

No automatic repair in MVP.

Anchor validation should be advisory, like beat validation.

Suggested status:

```text
pass
warning
unknown
```

Behavior:

- `pass`: no obvious anchor violation detected.
- `warning`: candidate may violate one or more anchors.
- `unknown`: validator could not determine reliably.

CandidatePanel display:

```text
Continuity: Used 4 anchors
Status: Warning
Possible issue: The heroine may have used her injured arm.
```

Adopt behavior:

- Warning does not block adopt.
- If warning exists, show confirm text before adopt.
- Official source remains unchanged until manual adopt.
- No automatic repair.
- No automatic rewrite.

MVP may postpone full anchor validator implementation, but the metadata shape and UI contract should reserve `anchor_validation`.

## 10. Candidate-only Safety Rules

Continuity Anchors must preserve the existing safety model:

- high-risk generation creates candidates;
- official scene files are not overwritten by anchor logic;
- anchors do not auto-adopt;
- anchors do not auto-repair;
- anchors do not auto-edit official scene text;
- anchor warning is advisory;
- candidate adopt still checks base hash / mtime and writes revision log;
- Lite and Professional must eventually share the same candidate safety boundary.

## 11. MVP Scope

T9.3 MVP includes:

- user manually creates anchors;
- user manually edits anchors;
- user archives anchors;
- active anchors inject into prompt;
- candidate metadata records anchors used;
- CandidatePanel displays anchors used count;
- no automatic extraction;
- no automatic update;
- no graph;
- no automatic repair;
- no Scene Plan.

MVP should not attempt to solve all story memory. It should give the author a small set of explicit continuity constraints that the model must respect.

## 12. Deferred Features

Explicitly deferred:

- automatic anchor extraction from official prose;
- automatic anchor resolution detection;
- automatic story-state update;
- automatic text repair;
- full-book Scene Plan;
- character relationship graph;
- complex knowledge base;
- multi-model consistency arbitration;
- automatic validator-driven regenerate;
- automatic adopt;
- automatic official scene overwrite.

Reason:

These features are complex and can break candidate-only safety. They also reduce user control if introduced before the author has a clear manual anchor workflow.

## 13. Risks And Mitigations

### Risk: too many anchors make prompt too long

Mitigation:

- inject `active` + `high` priority anchors first;
- show anchors used count;
- cap low-priority anchors;
- allow user to disable anchors for a generation.

### Risk: stale anchors mislead generation

Mitigation:

- make archive/edit easy;
- show updated time;
- show active anchors count near generation entry;
- do not auto-update anchors in MVP.

### Risk: anchors conflict with required beats

Mitigation:

- required beats are local task goals;
- anchors are factual boundaries;
- if they conflict, show warning instead of silently choosing.

### Risk: users do not want to maintain anchors

Mitigation:

- keep MVP manual but lightweight;
- support short titles and quick edit;
- do not require anchors for generation.

### Risk: validator is unstable for narrative semantics

Mitigation:

- keep warning advisory;
- allow `unknown`;
- never block preview / adopt / delete solely because of anchor validation.

### Risk: UI becomes too complex

Mitigation:

- use a simple right-panel section;
- avoid graph/database UI;
- hide archived anchors by default.

## 14. Recommended Follow-up Task Split

### T9.3b: Continuity Anchors Data Model + Prompt Assembly MVP

Scope:

```text
define anchors schema
save / read anchors
inject active anchors into prompt
no large UI redesign
```

Acceptance:

- project can persist `continuity-anchors.json`;
- prompt assembly can include active anchors;
- generation remains candidate-only.

### T9.3c: Continuity Anchors Minimal UI

Scope:

```text
right-panel minimal add / edit / archive anchors
type filter
active anchors count
```

Acceptance:

- user can create and maintain anchors without editing raw JSON;
- archived anchors do not enter prompt by default.

### T9.3d: Anchor Usage Metadata + CandidatePanel Display

Scope:

```text
candidate metadata records anchors_used
CandidatePanel displays used anchor count and anchor warning status
```

Acceptance:

- users can tell which anchors influenced a candidate;
- missing metadata on old candidates does not break UI.

### T9.3-final: Continuity Anchors Smoke + Archive

Scope:

```text
real Chinese scene smoke
candidate-only safety smoke
stage closure report
```

Acceptance:

- Professional and Lite flows preserve candidate-only safety;
- no automatic repair or adopt;
- phase is documented and ready for the next roadmap decision.

## 15. Final Conclusion

Continuity Anchors are the right T9.3 direction because they address a different problem than required beats.

Required beats make the next scene hit the user's local target. Continuity Anchors keep the long-form story from drifting away from established state.

The minimal version should be manual, visible, editable, and candidate-only:

```text
author writes anchors
-> active anchors enter prompt
-> generated candidate records anchors used
-> advisory warning may appear
-> author previews and manually adopts
```

This is small enough to implement safely after T9.2, while directly targeting the long-form continuity failures that matter most for serious fiction writing.
