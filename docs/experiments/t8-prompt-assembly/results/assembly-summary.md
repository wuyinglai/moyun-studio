# T8.1 Prompt Assembly Benchmark Summary

## 1. Background

T8.0 tested prompt quality in isolation. Its key finding was that direct generation and scene-plan-first generation tied on score under ideal short inputs, while a hard-constraint prompt did not reliably improve logic.

T8.1 tests the next layer: prompt assembly. The question is whether ordering facts, context, scene goals, intermediate plans, and logic checks can reduce small-model continuity errors before any product-code change.

This benchmark does not modify Moyun product code, production prompts, frontend, backend, pipeline, candidates, release tags, or workspace user data.

## 2. Relation to T8.0

| Item | T8.0 | T8.1 |
| --- | --- | --- |
| Test target | Single prompt wording | Prompt assembly strategy |
| Main comparison | A direct / B hard constraints / C plan then draft | A current-like / B facts-first / C plan -> checker -> draft |
| Core question | Can prompt wording alone help? | Does assembly order and intermediate validation help? |
| Result use | Decide whether assembly testing is worthwhile | Decide whether T8.2 product changes are justified |

## 3. Current Moyun Prompt Assembly Chain

Professional scene generation uses the pipeline system.

Observed code path:

1. Frontend `EditorToolbar` triggers `useFileGeneration.runPipeline(...)`.
2. For a scene file, frontend sends `POST /api/pipeline/run`.
3. Request body includes:
   - `pipeline`
   - `project_id`
   - `target_file`
   - `output_mode`
   - `extra_vars`
   - optional `scene_plan`
4. Backend `backend/api/pipeline.py` creates `PipelineRunner`.
5. `PipelineRunner.run(...)` loads:
   - pipeline YAML from `prompts/pipeline/{name}.yaml`
   - system variables: `style-guide.md`, `story-state.md`, `recent-context.md`, `outline.md`
   - project meta: genre, theme, tone, background, writing style, target word count, name
   - chapter variables from `ch-meta.json`: `pending_foreshadowing`, `active_quests`
   - `extra_vars`, including previous/current scene text if provided
6. The runner extracts continuity anchors from `previous_text` or `current_scene_text`.
7. Step variables are rendered into the Jinja prompt template.
8. `@{path}` references are resolved to project file content.
9. The rendered prompt is emitted as a `prompt` SSE event.
10. The LLM executor sends:
    - system message: generic text-processing instruction
    - user message: rendered prompt
11. Generation streams as `generation` events.
12. Final output is written to file or candidate according to output policy.

### Current Generate Template Shape

The main professional scene-writing template is:

- `prompts/pipeline/generate.yaml`
- `prompts/pipeline/generate/write.md`
- includes `prompts/blocks/writing-rules.md`

Current order in `write.md`:

1. scene writing identity and sec-as-scene writing unit;
2. previous/current scene context;
3. style guide;
4. outline / scene guide;
5. story state;
6. recent context;
7. writing rules include;
8. output requirements;
9. continuity hard lock.

### Prompt Observability

Rendered prompts are not persisted as durable debug artifacts, but they are observable during generation:

- backend emits a `prompt` SSE event;
- frontend `useFileGeneration.parseSSEStream` captures `prompt`;
- frontend stores it via `editorStore.setCompiledPrompt(...)`;
- `PromptPanel` can show the compiled prompt.

Limit: there is no stable debug prompt export file or benchmark-friendly endpoint for final prompt capture. For T8.2, a debug export option would make regression testing much easier.

## 4. Assembly Designs

### Assembly A: Current-Like Baseline

Simulates Moyun's current assembly style:

1. task identity;
2. previous/current context;
3. continuity anchors;
4. user action;
5. scene goal;
6. story/style/reference facts;
7. forbidden changes;
8. output requirements.

### Assembly B: Facts-First

Places hard facts and forbidden changes before narrative context:

1. task;
2. immutable facts;
3. forbidden changes;
4. scene goal;
5. reference context;
6. output requirements.

This is not the same as T8.0's heavy hard-constraint prompt. It tests information order and priority.

### Assembly C: Plan -> Check -> Draft

Uses three calls:

1. generate a scene plan from facts and context;
2. ask a checker to validate the plan;
3. draft from the plan and checker result.

This tests both output quality and intermediate-layer auditability.

## 5. Test Cases

| Case | Focus |
| --- | --- |
| case-01-injury-state | Injured body part and action limits |
| case-02-item-ownership | Silver chip ownership and information boundary |
| case-03-timeline | Future event / evidence must not appear early |
| case-04-location | No location jump from old port station to Gray Tower lab |
| case-05-no-new-entities | No new helpers, mentors, organizations, systems |
| case-06-foreshadowing | Seventh-layer protocol, trust boundary, restrained style |

## 6. Score Table

| Assembly | 总分 | 逻辑矛盾数 | 可用候选数 | 平均耗时 | 关键信息保留率 | 中间层可审查性 | 结论 |
| --- | -: | -: | -: | -: | -: | --- | --- |
| A current-like | 105/108 | 1 case | 5/6 | 13.08s | 1.00 | None | Baseline remains competitive but still misses injury-state details |
| B facts-first | 105/108 | 1 case | 5/6 | 6.80s | 1.00 | None | Best practical result in this small run: same score as A, fewer error hits, fastest |
| C plan-check-draft | 102/108 | 2 cases | 4/6 | 21.49s | 1.00 | Medium | Checker exposed a real plan problem, but draft still proceeded and repeated the issue |

## 7. Logic Error Comparison

| Case | A | B | C |
| --- | --- | --- | --- |
| injury-state | 15: lets沈知夏 use right-arm support but also drifts wound to right shoulder / high-action phrasing | 15: writes left hand as forcefully pressed against wall | 15: checker parse failed; draft includes "攀爬后" wording |
| item-ownership | 18 | 18 | 18 |
| timeline | 18 | 18 | 15: checker caught plan issue, but draft still writes "佐证爆炸发生具体时刻" |
| location | 18 | 18 | 18 |
| no-new-entities | 18 | 18 | 18 |
| foreshadowing | 18 | 18 | 18 |

The hardest sample remains injury-state continuity. Reordering prompt blocks helps speed and clarity but does not reliably prevent embodied-state mistakes.

## 8. Latency Comparison

| Assembly | Calls per case | Average time |
| --- | -: | -: |
| A | 1 | 13.08s |
| B | 1 | 6.80s |
| C | 3 | 21.49s |

Assembly C is roughly 3.16x slower than B in this run. The latency is expected because C uses three model calls.

## 9. Intermediate-Layer Auditability

Assembly C is the only variant with a real intermediate layer.

Observed behavior:

- Checker parsed successfully in 5/6 cases.
- Checker detected a high-risk timeline issue in `case-03-timeline`.
- The draft stage still used the invalid plan/checker context and produced the same risk.
- In `case-01-injury-state`, checker output failed JSON parsing because the model returned a very verbose natural-language issue report inside JSON-like text.

Conclusion: a checker is useful only if it gates or rewrites the plan. If the draft step merely receives checker output as context, the model may ignore it.

## 10. Key Findings

1. Current-like assembly is not the main bottleneck under clean short inputs.
2. Facts-first ordering is the best small change in this run: same total score as A, fewer detected issue strings, and lower latency.
3. Plan-check-draft did not outperform A/B. It found a plan issue, but the chain had no enforcement mechanism.
4. Key information retention was 100% in all final prompts because the benchmark explicitly assembled every case fact into each prompt.
5. The remaining failures are not caused by missing information. They are caused by weak constraint execution inside the model.
6. The current product already exposes rendered prompts during streaming, but there is no stable debug prompt export artifact for repeatable evaluation.

## 11. Should T8.2 Start?

Not as a full Scene Plan + Checker productization.

The evidence is not strong enough to justify a broad product-code change. Assembly C is slower and scored lower in this run. However, two narrow T8.2 candidates are justified:

1. facts-first ordering experiment for the production `generate/write` prompt assembly;
2. debug prompt export for repeatable evaluation.

The checker should not be productized as a passive extra context block. If introduced later, it must become a gate:

- checker valid -> draft;
- checker invalid -> repair plan or stop;
- draft must never proceed blindly with a known invalid plan.

## 12. Recommended Minimum Product Direction

If moving into T8.2, keep it minimal:

1. Add a debug prompt export option for Professional pipeline runs.
2. Add a facts-first variant behind an experiment flag or test-only prompt assembly path.
3. Do not yet enable scene-plan/checker by default.
4. If testing checker again, enforce a hard gate:
   - parse checker JSON;
   - if invalid or high risk, do not draft;
   - optionally run a repair-plan step.
5. Add a targeted validator for embodied-state errors, especially injured body part usage.

## 13. Recommendation

Best assembly in this small benchmark: Assembly B facts-first.

Recommended next step: do not rush broad T8.2 workflow changes. Run a larger T8.1.1 sample set or enter a narrow T8.2 only for facts-first ordering plus debug prompt export. Scene Plan + Checker should wait until it has a real gate/repair mechanism.

## 14. Raw Artifacts

- Assembly variants: `docs/experiments/t8-prompt-assembly/assembly-variants/`
- Cases: `docs/experiments/t8-prompt-assembly/cases/`
- Raw generations: `docs/experiments/t8-prompt-assembly/results/raw-assembly-generations.md`
- Scored JSON: `docs/experiments/t8-prompt-assembly/results/assembly-data.json`
- Runner: `docs/experiments/t8-prompt-assembly/run_assembly_benchmark.py`

