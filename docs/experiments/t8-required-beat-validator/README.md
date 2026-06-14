# T8.2.2 Required Beat Validator Benchmark

This directory contains a reusable benchmark framework for testing whether small models can validate and repair required-beat omissions in scene-level fiction.

Scope:

- Product code: unchanged
- Production prompts: unchanged
- Pipeline: unchanged
- Frontend/backend business logic: unchanged
- Candidate adoption/deletion/hash/file-save logic: unchanged
- Release/tag: unchanged
- API keys: never written to this directory

## Pipeline

For each case and sample:

1. Generate scene text with a numbered-beats + self-check prompt.
2. Run a rule-based precheck.
3. Run a natural-language LLM validator.
4. Run a strict JSON LLM validator.
5. Compare rule / natural / JSON results.
6. If missing / partial / forbidden violation exists, run repair.
7. Re-validate repaired text with rule and JSON validator.
8. Write raw and scored artifacts.

## Run

Dry run:

```powershell
python docs/experiments/t8-required-beat-validator/run_validator_benchmark.py --dry-run
```

Real run:

```powershell
python docs/experiments/t8-required-beat-validator/run_validator_benchmark.py --samples 1
```

The runner reads the existing local LLM configuration from `workspace/.config.json` unless `AGNES_API_KEY`, `AGNES_API_URL`, or `AGNES_MODEL` are provided. It never prints or writes API keys.

## Outputs

- `results/raw/*.md`
- `results/scored/*.json`
- `results/validator-summary.md`
- `results/validator-summary.json`
- `results/validator-summary.csv`

## Recommendation Use

This benchmark is designed to answer whether Moyun should later productize:

- validator warning only;
- validator + manual repair suggestion;
- validator + automatic repair;
- or no validator yet.

It does not itself productize any of those flows.
