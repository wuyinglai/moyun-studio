# Moyun Studio Known Issues

## v0.2.0-alpha Known Issues

1. Small-context models can still hit token-limit risks during long-context writing or review.
2. Long-context generation can weaken, omit, or blur individual character details.
3. Continuity anchor extraction is improved, but low-frequency noise is still possible.
4. Slow real LLM responses still need a better waiting, cancel, and retry experience.
5. Local model or custom API endpoint misconfiguration can cause generation failures.
6. This alpha release is not recommended for important production drafts without backups.
7. On Windows or proxy-heavy networks, `git push` or GitHub operations may fail intermittently.
8. Real LLM smoke depends on a working API key and endpoint; secrets must stay out of the repository.
