# T8.2.1 Required Beats Benchmark

This experiment tests whether small models reliably include required scene beats in generated fiction.

Scope:

- Product code: unchanged
- Production prompts: unchanged
- Pipeline: unchanged
- Frontend/backend: unchanged
- Release/tag: unchanged
- Real LLM: allowed for benchmark only
- API keys: never written to this directory

Core question:

When a scene prompt says several facts or beats must appear, does the model reliably write them into the prose without leaking forbidden secrets or creating new contradictions?

## Variants

- Variant A: inline required beats
- Variant B: numbered required beats
- Variant C: silent self-check before final output
- Variant D: beat outline first, then prose

## Cases

1. Seventh Layer Protocol
2. Item handover
3. Injury limitation
4. Ending hook

## Outputs

- `results/required-beats-data.json`
- `results/raw-required-beats-generations.md`
- `results/required-beats-summary.md`
