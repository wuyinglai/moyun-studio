# T8.0 Benchmark Run Notes

## Run Scope

- Task: T8.0 小模型 Prompt 单体质量基准测试
- Product code changed: No
- Existing production prompts changed: No
- Pipeline/frontend/backend changed: No
- Real LLM called: Yes
- Candidate generated: No
- Workspace files modified: No
- API key recorded: No

## Model

- Model: `agnes-2.0-flash`
- API base: `https://apihub.agnes-ai.com/v1`
- Calls: 24 attempted in the valid run
- Prompt C uses two calls per case: scene plan, then draft from plan.

## Execution Notes

The first direct inline PowerShell runner was discarded because Chinese literals in the inline script were corrupted by shell encoding, causing empty case fields. No valid benchmark conclusion was taken from that run.

The valid run used `run_benchmark.py`, a UTF-8 experiment script under this directory. It parsed all case fields before calling the model and wrote only generated text, timing, scores, and metadata. The API key was read from local runtime configuration and was not printed or written to any file.

After the valid run, scoring rules were tightened for the injury-state case and foreshadowing over-disclosure case. Scores in `benchmark-data.json` and `raw-generations.md` were recomputed from existing generated text without additional LLM calls.

## Output Files

- `results/benchmark-data.json`
- `results/raw-generations.md`
- `results/benchmark-summary.md`
