# T8.0 Prompt Quality Benchmark

This benchmark tests prompt quality in isolation. It does not use Moyun Studio frontend, backend pipeline assembly, or product workflow.

Goal: compare whether prompt wording alone can reduce small-model logic errors in long-form scene writing.

## Scope

- Product code: unchanged
- Existing production prompts: unchanged
- Pipeline: unchanged
- Frontend/backend: unchanged
- Real LLM: allowed for benchmark only
- API keys: never written to this directory

## Prompt Variants

- Prompt A: direct generation baseline
- Prompt B: hard-constraint fact-first generation
- Prompt C: scene plan first, then draft from plan

## Cases

1. Injury state
2. Item ownership
3. Timeline order
4. Location constraint
5. No new entities
6. Foreshadowing and relationship/style stability

## Scoring

Each generated result is scored from 0 to 2 on:

- character state consistency
- item ownership consistency
- timeline consistency
- location consistency
- forbidden-instruction compliance
- scene goal completion
- foreshadowing handling
- contradiction count
- usability as a candidate draft

The benchmark prioritizes hard logic over prose style.

