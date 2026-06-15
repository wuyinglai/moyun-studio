# T8.3.3 Required Beats Prompt Assembly Quality

## Background

T8.3.2 added a minimal Professional UI for per-scene required beats and forbidden beats. The UI passes these values through `extra_vars.required_beats`, `extra_vars.forbidden_beats`, and `_enable_beat_validation=true` when either input is non-empty.

This check verifies the next layer: whether those values are visible in the final generation prompt, whether blank input keeps the default prompt unchanged, and whether candidate metadata remains compatible with the existing warning flow.

## Current Problem

Before this task, `required_beats` and `forbidden_beats` were present in pipeline `step_vars`, but the generation prompt templates did not render them explicitly. The validator could inspect the generated candidate after the fact, but the model was not clearly instructed to include or avoid those beats during generation.

## Prompt Assembly Findings

- Frontend input mapping is already present in `useRequiredBeatsInput`.
- Professional generation actions merge the beat extra vars before calling pipeline.
- `PipelineRunner.run` merges `extra_vars` into `step_vars`.
- Debug prompt export emits the rendered prompt before the LLM call.
- The missing link was the prompt template body.

## Prompt Template Changes

Updated:

- `prompts/pipeline/generate/write.md`
- `prompts/pipeline/generate/write_facts_first.md`

Both templates now render the same lightweight conditional sections:

```text
## 本场必须出现的信息点
- ...

## 本场禁止出现 / 禁止揭晓
- ...
```

The sections only appear when the corresponding list is non-empty. Blank input does not add either section.

## Required Beats Section

The required beats section is placed after the common writing rules and before the final special-output requirements in the default generation prompt. This keeps it close to the model's final task instructions without moving the existing story context blocks.

For the facts-first experimental prompt, the required beats section is placed after the hard fact / forbidden fact rules and before the scene goal. This keeps required beats near the highest-priority factual constraints.

## Forbidden Beats Section

Forbidden beats are rendered in a separate section named `本场禁止出现 / 禁止揭晓`. They are not mixed into required beats.

## Debug Prompt Verification

Direct pipeline debug prompt export was run with:

- `_debug_prompt_export=true`
- `_enable_beat_validation=true`
- `required_beats=[{"id":"beat-1","text":"正文必须提到第七层协议"}]`
- `forbidden_beats=[{"id":"forbid-1","text":"不能揭晓第七层协议完整真相"}]`

Results:

| Case | Template | Required Text | Forbidden Text | Required Section | Forbidden Section |
|---|---|---:|---:|---:|---:|
| default with beats | `pipeline/generate/write.md` | yes | yes | yes | yes |
| facts-first with beats | `pipeline/generate/write_facts_first.md` | yes | yes | yes | yes |
| blank input | `pipeline/generate/write.md` | no | no | no | no |

Full debug prompts were not committed to avoid storing prompt dumps or user content.

## Real LLM Smoke

Real pipeline smoke used the configured project LLM through `LLMService.from_workspace_config(...)` against a temporary project outside the repository workspace. API keys were not printed or stored.

| Case | Result | Chars | Required Phrase | Forbidden Reveal | Candidate | Beat Status |
|---|---|---:|---:|---:|---:|---|
| required + forbidden | success | 560 | yes | no | yes | pass |
| forbidden only | success | 563 | yes, incidental | no | yes | pass |
| blank input | success | 521 | no | no | yes | none |

The forbidden-only case incidentally mentioned `第七层协议`, which is acceptable because it was not forbidden; the required section was absent from the debug prompt.

## Browser E2E

Browser checks were run against an isolated backend workspace and local Vite frontend.

Verified:

- Professional page opens a project scene.
- The `本场信息点` UI is present.
- Filling required and forbidden text shows `已启用检查`.
- CandidatePanel displays `信息点警告` for a candidate containing `beat_validation.status=warning`.
- Candidate preview opens and shows the warning message.

Not fully verified:

- Clicking the right-panel `重写当前场景` button did not complete a candidate in this browser run. The page showed a pre-existing `Request failed with status code 404` prompt/panel error and remained in a generating state.
- Delete button browser click was not completed because the in-app browser tab became unresponsive after preview interaction. Candidate delete itself was not changed in this task.

## Default Behavior

Blank input keeps the default prompt free of required/forbidden beat sections. `_enable_beat_validation` is not sent by the UI when both inputs are empty, preserving the default generation path.

## Candidate Metadata

Real pipeline candidate creation with beat validation enabled emitted `candidate_created` with `beat_validation_status=pass`, and `metadata.json` persisted `beat_validation.status=pass`.

Candidates without beat input did not include beat validation status.

## Commands

```powershell
python scripts/prompt-impact.py prompts\pipeline\generate\write.md
python scripts/prompt-impact.py prompts\pipeline\generate\write_facts_first.md
python -m py_compile backend\core\pipeline.py backend\api\pipeline.py backend\core\candidate_service.py
python -m pytest backend/tests/test_beat_validator.py backend/tests/test_candidate_service.py backend/tests/test_pipeline.py -q --tb=short
cd frontend; npm run build
git diff --check
```

## Risks

- The prompt change is intentionally small, but all generation prompt edits can affect prose style and output reliability.
- The browser E2E exposed an existing Professional right-panel generation reliability issue unrelated to the prompt template insertion. It should be tracked separately before relying on that button as a release smoke path.

## Recommendation

Proceed to the next prompt-quality step with this assembly fix in place. Before expanding UI around required beats, separately stabilize the Professional right-panel generation button path so browser E2E can validate generation, candidate creation, preview, adopt, and delete in one uninterrupted user flow.

