# T8.2.2 Run Notes

Recommended command:

```powershell
python docs/experiments/t8-required-beat-validator/run_validator_benchmark.py --samples 1
```

Useful options:

- `--dry-run`: use deterministic local mock outputs, no network.
- `--samples N`: run N samples per case.
- `--cases case-01-seventh-protocol case-02-ending-hook`: limit cases.
- `--timeout 180`: request timeout in seconds.

The runner is intentionally self-contained and does not import Moyun product modules.

Artifacts can be deleted and regenerated. Do not edit generated `results/scored/*.json` by hand unless documenting a manual audit.
