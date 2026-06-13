# T8.2.1 Run Notes

Benchmark runner:

```powershell
python docs/experiments/t8-required-beats/run_required_beats_benchmark.py
```

The runner:

- reads LLM configuration from local workspace config;
- does not print or write API keys;
- calls the OpenAI-compatible chat completion endpoint;
- writes benchmark artifacts under `docs/experiments/t8-required-beats/results/`;
- scores required-beat completion with simple deterministic checks.

If the API is unavailable, record the error in `results/required-beats-summary.md` and do not fake scores.
