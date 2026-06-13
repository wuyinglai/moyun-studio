# T8.1 Prompt Assembly Benchmark

This experiment tests prompt assembly strategies, not individual prompt templates.

It compares whether different ordering and intermediate layers help a small model preserve hard story facts when writing scene-level fiction.

## Scope

- Product code: unchanged
- Existing production prompts: unchanged
- Pipeline: unchanged
- Frontend/backend: unchanged
- Release/tag: unchanged
- Real LLM: allowed for benchmark only
- API keys: never written to this directory

## Assembly Variants

- Assembly A: current-like baseline
- Assembly B: facts-first assembly
- Assembly C: plan -> checker -> draft assembly

## Cases

The six T8.0 continuity cases are reused:

1. Injury state
2. Item ownership
3. Timeline order
4. Location constraint
5. No new entities
6. Foreshadowing / relationship / style stability

## Outputs

- `results/assembly-data.json`
- `results/raw-assembly-generations.md`
- `results/assembly-summary.md`

