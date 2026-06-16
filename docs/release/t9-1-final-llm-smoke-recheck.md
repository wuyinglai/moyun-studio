# T9.1-final-b: Real LLM Endpoint Recovery + Release Readiness Recheck

Date: 2026-06-16

Base commit: `f7df8e0 docs: add T9.1 release readiness report`

Mode: Environment Diagnosis + Real LLM Smoke + Readiness Update

Risk: Risk B+ / Release Blocker Triage + Smoke Recheck

## Summary

T9.1-final was blocked because the real LLM smoke returned HTTP 502 against the previously configured endpoint. This follow-up rechecked the endpoint, circuit-breaker state, real product LLM path, and candidate safety behavior.

Result:

- The release blocker is resolved for the product LLM path.
- The real product `LLMService` path using `openai/agnes-2.0-flash` and `https://apihub.agnes-ai.com/v1` completed successfully.
- Polish, rewrite, and feedback revision smoke scenarios all generated candidates.
- Source scene files stayed unchanged before adopt.
- Parent candidate stayed pending after feedback revision.
- Beat validation ran and produced advisory `warning` statuses.
- No product code was changed.
- No API key, `.env`, workspace project data, or temporary smoke data was committed.

Recommendation:

```text
T9.1-final blocker resolved.
v0.2.0 developer preview release readiness passed.
Recommendation: proceed to tag / GitHub Release preparation.
```

## Original Blocker

T9.1-final reported:

```text
Real LLM Smoke failed with configured endpoint HTTP 502.
```

The earlier failure was treated as a release readiness blocker because the developer preview depends on real LLM polish / rewrite / feedback revision flows being usable.

## Endpoint Configuration Summary

Configuration was read through the product path:

1. `workspace/llm_config.json`
2. `workspace/.config.json`
3. fallback `Settings` / `.env`

Effective summary, with sensitive values redacted:

| Field | Value |
| --- | --- |
| Config source | `workspace/.config.json` |
| Provider type | `custom`, normalized by product code to OpenAI-compatible |
| API base | `https://apihub.agnes-ai.com/v1` |
| Model | `openai/agnes-2.0-flash` |
| API key | configured, redacted |
| Thinking | false |
| Reasoning format | null |

## Direct Endpoint Check

Two endpoint paths were checked:

| Check | Result | Notes |
| --- | --- | --- |
| Raw `httpx` `/models` and `/chat/completions` without proxy | Failed | TLS `UNEXPECTED_EOF_WHILE_READING` from the local shell networking path. |
| Raw `httpx` with `127.0.0.1:7897` proxy | Failed | Local proxy port refused connections. |
| Product `LLMService` / LiteLLM path | Passed | Real request completed. |

Product-path direct LLM checks:

| Prompt | Result | Elapsed | Chinese OK |
| --- | --- | ---: | --- |
| Strict two-character Chinese reply | `可用` | 1.89s | yes |
| Chinese fiction sentence containing `旧港站` | Chinese sentence returned | 36.10s | yes |

The raw `httpx` result appears to be a shell/network transport difference rather than a product LLM failure, because the product LiteLLM path successfully reached the same configured base URL and model.

## Circuit Breaker / Failure Cache

`workspace/.circuit-breaker-state.json` exists and contains historical entries, including open states for fake-model test keys.

For this recheck:

- The persisted workspace circuit-breaker file was not modified.
- The smoke runner reset only the in-process circuit breaker before each real scenario.
- This avoided cached failure state affecting the smoke while preserving workspace files.

## Real LLM Smoke Recheck

Smoke was run through product services with a temporary project directory outside the repository workspace:

- `LLMService.from_workspace_config(...)`
- `PipelineRunner`
- `FileService`
- `CandidateService`
- Product prompts from `prompts/pipeline/*`
- Candidate metadata and beat validation enabled

The temporary smoke directory was removed after the run.

### Scenario A: Polish

Input scene:

```text
她右肩仍疼，靠在墙边，左手扶着剑鞘。主角走过去，把披风搭在她肩上。她没有躲，只低声说了一句：“别以为这样我就信你。”
```

Required beats:

- 女主右肩受伤必须保留
- 女主不能用右手持剑
- 主角照顾她的动作必须保留
- 女主态度软化但仍有戒心

Forbidden beats:

- 女主不能突然右手持剑战斗
- 两人不能突然表白
- 不能出现治疗神药

Result:

| Item | Result |
| --- | --- |
| Completed | yes |
| Elapsed | 127.87s |
| Candidate created | yes |
| Candidate id | `cand_e0cb5d84` |
| Beat validation | `warning` |
| Source unchanged before adopt | yes |
| Error events | none |

### Scenario B: Rewrite

Input scene:

```text
主角在旧码头发现一枚银色芯片。芯片表面有残缺坐标，但他还不知道坐标指向哪里。
```

Required beats:

- 银色芯片必须保留
- 残缺坐标必须保留
- 主角不能完全理解坐标含义

Forbidden beats:

- 不能揭晓坐标完整目的地
- 不能新增神秘组织

Result:

| Item | Result |
| --- | --- |
| Completed | yes |
| Elapsed | 50.28s |
| Candidate created | yes |
| Candidate id | `cand_03f6128b` |
| Beat validation | `warning` |
| Source unchanged before adopt | yes |
| Error events | none |

### Scenario C: Feedback Revision

Parent candidate:

- Parent id: `cand_e0cb5d84`
- Parent status before revision: `pending`

Feedback:

```text
补上缺失信息点，不要新增人物，保持原来的悬念，句子更自然。
```

Result:

| Item | Result |
| --- | --- |
| Completed | yes |
| Elapsed | 66.31s |
| Child candidate created | yes |
| Child id | `cand_0d66c0c3` |
| Child status | `pending` |
| Parent status after revision | `pending` |
| Parent candidate id recorded | yes |
| Revision index | 1 |
| Beat validation | `warning` |
| Source unchanged before adopt | yes |
| Auto adopt | no |

## Candidate Safety Results

| Safety rule | Result |
| --- | --- |
| Polish only creates candidate | passed |
| Rewrite only creates candidate | passed |
| Feedback revision only creates child candidate | passed |
| Source正文 unchanged before adopt | passed |
| Parent candidate unchanged | passed |
| Child candidate defaults to pending | passed |
| No auto adopt | passed |
| Required / forbidden beats inherited for child revision | passed |
| Beat validator reruns for child revision | passed |
| Warning remains advisory | passed |
| No bad candidate on observed failure path | not triggered in this recheck; covered by existing tests |

## Release Blocker Status

Resolved.

The original blocker was real LLM unavailability. The product LLM path now successfully completed all required smoke scenarios.

Remaining caveat:

- Raw `httpx` from the shell still sees TLS/proxy transport issues. This does not reproduce through the product LiteLLM path and should be tracked as an environment diagnostic note, not as a release blocker.

## Recommendation

Proceed to tag / GitHub Release preparation for the v0.2.0 developer preview.

## Commands Run

```powershell
git status --short
git log -1 --oneline
git diff --check
```

Endpoint and smoke checks were run with temporary Python one-off scripts through the product service path. The scripts were not committed and did not print API keys.

## Final Status

| Item | Status |
| --- | --- |
| Product code changed | no |
| Prompt changed | no |
| Candidate service changed | no |
| `.env` changed | no |
| API key committed | no |
| Workspace project data committed | no |
| Tag created | no |
| GitHub Release created | no |
| Release blocker | resolved |

