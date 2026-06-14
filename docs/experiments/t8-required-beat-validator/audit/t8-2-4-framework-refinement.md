# T8.2.4 Validator Schema / Prompt / Rule Semantics Refinement

## 1. Background

T8.2.3 found that the T8 required-beat validator benchmark had useful evidence, but its framework mixed three different judgment layers:

1. keyword-based rule precheck;
2. semantic LLM validation;
3. repair trigger and final usability scoring.

The main risk was that rule-based keyword checks could behave like a final judge. This created false repair triggers, especially for semantic paraphrases, terminal ending hooks, and knowledge-boundary cases.

This refinement changes only the benchmark framework under `docs/experiments/t8-required-beat-validator/`. It does not modify product code, production prompts, pipeline, frontend, backend, release tags, API keys, candidates, or workspace data.

## 2. Scope

Modified areas:

- case schema;
- six case JSON files;
- validator result schema;
- validator prompt documents;
- benchmark runner weak-rule semantics;
- benchmark summary output;
- this refinement report.

Out of scope:

- Moyun product code;
- production prompt templates;
- pipeline behavior;
- automatic adoption or candidate logic;
- release/tag work.

## 3. Schema Changes

`schemas/case.schema.json` now supports semantic fields for required and forbidden beats:

- `acceptable_paraphrases`;
- `required_semantic_condition`;
- `forbidden_semantic_condition`;
- `terminal_position_required`;
- `knowledge_boundary`;
- `violation_threshold`.

`schemas/validation-result.schema.json` now supports richer validator evidence:

- `evidence_quality`: `exact | paraphrase | weak | absent`;
- `reasoning_note`;
- `terminal_position_ok`;
- `knowledge_boundary_ok`.

The fields are additive so older result artifacts remain understandable while new runs can capture stronger semantic evidence.

## 4. Case Updates

All six cases were refined with semantic conditions:

| Case | Main refinement |
| --- | --- |
| `case-01-seventh-protocol` | Adds protocol knowledge-boundary constraints and paraphrases for incomplete coordinates. |
| `case-02-ending-hook` | Adds paraphrases for familiar footsteps and recognition, terminal-position requirement, and reader identity boundary. |
| `case-03-injury-limitation` | Adds paraphrases for observation/judgment assistance and a clearer injury-action violation threshold. |
| `case-04-item-handover` | Adds label-only knowledge boundary and reader/character medicine-use reveal constraints. |
| `case-05-location-lock` | Clarifies Gray Tower as clue-only, not physical location transfer. |
| `case-06-no-new-entity` | Clarifies existing-entity-only progress and keeps Seventh Layer Protocol unresolved. |

## 5. Validator Prompt Changes

The validator prompt documents and runner-embedded validator prompts now explicitly require:

- judge only generated text;
- keyword mention is not semantic satisfaction;
- acceptable paraphrases may satisfy a beat;
- uncertain evidence should be `partial`;
- no evidence means `missing`;
- forbidden beats stay in `forbidden_violations`, not `required_beats`;
- quote short evidence for satisfied, partial, or violated judgments;
- distinguish reader-facing reveal, character knowledge, and character suspicion;
- check `knowledge_boundary` when present;
- check terminal position when `terminal_position_required=true`.

The prompt documents are written in clear English to avoid extending the older encoding damage found in the experiment-only prompt files.

## 6. Rule-based Changes

Rule-based precheck is now explicitly weak:

```json
{
  "rule_is_final": false,
  "rule_status": "weak_pass | weak_fail | unknown"
}
```

The runner now records:

- keyword hits;
- acceptable paraphrase hits;
- terminal-position rough check;
- weak required failures;
- weak forbidden hits.

Rule-only failure no longer triggers repair and no longer blocks final usability. It is used as an audit signal and disagreement input only.

## 7. Runner Changes

The benchmark runner now:

1. bases repair triggering on JSON validator semantic result, not rule precheck;
2. derives initial beat completion from JSON validator when parsing succeeds;
3. treats rule precheck as weak audit metadata;
4. records disagreement with:
   - `between`;
   - `likely_reason`;
   - `rule_vs_json`;
   - `rule_vs_natural`;
   - `natural_vs_json`;
5. reports weak rule counts in CSV/Markdown summaries;
6. considers final usability from JSON re-validation rather than rule precheck.

This matches the T8.2.3 recommendation: do not let brittle rule matching automatically trigger repair.

## 8. Smoke Result

Validation commands were run as:

```powershell
python -m py_compile docs/experiments/t8-required-beat-validator/run_validator_benchmark.py
python docs/experiments/t8-required-beat-validator/run_validator_benchmark.py --help
python docs/experiments/t8-required-beat-validator/run_validator_benchmark.py --dry-run
python docs/experiments/t8-required-beat-validator/run_validator_benchmark.py --samples 1 --cases case-02-ending-hook
```

Single-case real LLM smoke result:

| Field | Value |
| --- | ---: |
| Model | `agnes-2.0-flash` |
| Case | `case-02-ending-hook` |
| Runs | 1 |
| JSON parse rate | 100.00% |
| Validator agreement rate | 100.00% |
| Repair trigger count | 1 |
| Repair success rate | 100.00% |
| New error rate | 0.00% |
| Final usable rate | 100.00% |
| Average total latency | 32.83s |

The single-case smoke was used only to verify the refined framework. Smoke-generated result files were restored from backup and were not treated as a new committed benchmark result.

## 9. Risk Notes

Low risk:

- changes are contained to the experiment directory;
- schema changes are additive;
- product code is untouched.

Remaining evaluation risk:

- rule weak signals are still string based and should not be interpreted as human-level judgment;
- JSON validator may still over-infer ambiguous identity or knowledge-boundary evidence;
- repair remains experimental and should not be productized without human review.

## 10. Recommendation

T8.2.4 is a framework refinement, not a product prompt change.

Recommended next step:

1. run a fresh `--samples 2` benchmark after this correction;
2. manually audit disagreements again;
3. only then decide whether T8.3 product design should use validator warnings, repair candidates, or both.

Do not productize automatic repair from this framework yet. Product-facing use should start as warning/candidate generation, not direct overwrite.
