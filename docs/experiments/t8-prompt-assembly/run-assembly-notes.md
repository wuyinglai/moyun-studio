# T8.1 Benchmark Run Notes

## Run Scope

- Task: T8.1 Prompt 装配一致性测试
- Product code changed: No
- Existing production prompts changed: No
- Pipeline/frontend/backend changed: No
- Candidate generated: No
- Workspace files modified: No
- API key recorded: No

## Model

- Model: `agnes-2.0-flash`
- API base: `https://apihub.agnes-ai.com/v1`
- Assembly C uses three calls per case: plan, checker, draft.

## Runner Safety

`run_assembly_benchmark.py` reads the local runtime LLM configuration to call the model. It does not print, store, or export the API key. Outputs contain prompt text, generated model text, timing, scoring, and aggregate metrics only.

## Output Files

- `results/assembly-data.json`
- `results/raw-assembly-generations.md`
- `results/assembly-summary.md`

