# T5.17-H1 Scene Plan Target Binding Fix

Date: 2026-06-09

## 1. Background

The T5.17-pre architecture audit found that Scene Plan objects were not strongly bound to the scene file requested by the caller across the full chain. A Scene Plan generated for scene A could be accidentally saved, loaded, or passed into pipeline execution for scene B if caller code supplied mismatched values.

This task fixes only H1 target binding. H2 candidate provenance remains a separate follow-up.

## 2. Risk

Without target binding, a with-plan pipeline run could use the wrong plan for a scene. That would make generated candidates and scoring evidence unreliable even when all file writes still go through the candidate safety layer.

## 3. Fix Points

### Generate API

`/api/scene-plan/generate` already forces:

- `scene_plan.project_id = request.project_id`
- `scene_plan.source_path = request.target_file`
- `candidate_policy.require_candidate = true`
- `candidate_policy.allow_direct_write = false`

A regression test now covers the case where the mocked LLM returns the wrong `source_path`; the API response is still bound to the requested `target_file`.

### Save API

`/api/scene-plan/save` now rejects any request where:

```text
scene_plan.source_path != target_file
```

The check happens after structural validation and before file existence / overwrite handling. `overwrite=true` cannot bypass the binding rule.

### Load API

`/api/scene-plan/load` still locates the file from `project_id + target_file`, then validates the loaded content:

```text
loaded_scene_plan.source_path == target_file
```

If the file exists but contains a mismatched `source_path`, the API returns `exists=true`, `scene_plan=null`, and a structured `SCENE_PLAN_TARGET_MISMATCH` error.

The load path also now returns `mtime` from the third value of `FileService.read_file()`.

### Pipeline

`PipelineRunner.run()` now rejects mismatched Scene Plans before loading the pipeline definition:

```text
scene_plan.source_path == target_file
```

If the values differ, it emits an SSE error event with:

```json
{
  "code": "SCENE_PLAN_TARGET_MISMATCH"
}
```

No pipeline is loaded, no LLM is called, no candidate is created, and no file is written.

## 4. Test Coverage

Added or updated tests cover:

- generate API forces `source_path` to requested `target_file`
- save API accepts matching `source_path`
- save API rejects mismatched `source_path`
- `overwrite=true` cannot bypass mismatch rejection
- load API rejects existing Scene Plan files whose `source_path` does not match the requested `target_file`
- pipeline rejects mismatched `scene_plan.source_path` before loading or running
- existing validate and validator tests remain in place

## 5. Safety Notes

- No real LLM was called.
- No Scene Plan was generated.
- No candidate was generated.
- No adopt was executed.
- `workspace/` was not modified.
- scoring/final/multi-score/errata/gap-analysis artifacts were not modified.
- `.env` and API keys were not modified or committed.
- H2 candidate provenance was intentionally not changed in this task.

## 6. H2 Follow-Up

Candidate provenance should be handled separately by adding generation metadata such as:

- `generation_context.scene_plan_used`
- `scene_plan_path`
- `scene_plan_hash`
- `scene_plan_source_path`

That work is outside T5.17-H1.

