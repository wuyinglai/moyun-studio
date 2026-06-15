# T8.4 Writing Quality Flow Stabilization

## Background

T8.3 established the small-model writing quality loop:

1. required / forbidden beats input;
2. prompt assembly support;
3. beat validator metadata;
4. CandidatePanel pass / warning / unknown display;
5. adopt warning confirmation;
6. Professional right-panel request-path repair.

T8.4 stabilized that loop as a user-facing flow rather than adding new generation features.

## Change Scope

Code changes were intentionally small and frontend-only:

- Professional right panel generation status and error UX.
- Required beats input clarity.
- CandidatePanel warning readability.
- Side-panel 404 noise reduction for scene prompt and missing default workflow loading.

No backend, prompt, pipeline architecture, validator, candidate adopt/delete/hash, file-save conflict, LLM provider, API key, release, or tag logic was changed.

## LLM Slow / Timeout UX

Professional right-panel actions now update status while waiting:

- Immediate: `正在准备生成……`
- Shortly after start: `正在调用模型……`
- After 15 seconds: `模型响应较慢，仍在等待生成结果……`
- After 60 seconds: `真实 LLM 生成可能需要更久。你可以继续等待，或稍后重试。`

If the pipeline reports an LLM error or timeout, the right panel now shows a friendlier message:

```text
模型生成失败，可能是模型响应超时或服务暂时不可用。请稍后重试，或缩短上下文后再生成。
```

Timers are cleared on success, failure, and final cleanup. Buttons recover after the action finishes or fails.

## Professional Right Panel Stability

Verified:

- `target_file` is project-relative and has no leading `/`.
- `output_mode` remains `candidate` for scene rewrite.
- `_action` is preserved.
- Required / forbidden beats are merged into `extra_vars` without overwriting `_action`.
- Empty required / forbidden inputs do not enable validator.
- Failed pipeline responses recover the local `running` state.

## Required Beats Input UX

Added lightweight clarity:

- More direct placeholders for required / forbidden lines.
- A parsed count summary:
  - `未设置检查项，生成将保持默认流程。`
  - `已设置 N 个必须信息点，M 个禁止项。`
- A soft warning for overly long single lines, suggesting users split them into multiple beats.

Parsing still trims whitespace and ignores empty lines.

## CandidatePanel Warning Display

Candidate warnings now show a clearer summary plus grouped details:

- `缺失：...`
- `不确定：...`
- `禁止项疑似出现：...`

The unknown state explains that validation did not complete and does not block adoption. Warning still remains advisory only; adopt is not blocked.

## Debug Prompt / Metadata Traceability

Confirmed through browser request capture and candidate API construction:

- Required / forbidden beats are present in `extra_vars` when filled.
- Empty input does not set `_enable_beat_validation`.
- Candidate metadata with `beat_validation.status = pass | warning | unknown` displays in CandidatePanel.
- Legacy candidates without `beat_validation` do not crash the panel.

No API key, real user private debug prompt, or workspace data was committed.

## 404 Noise Handling

T8.3.4 identified two 404 sources:

- `/api/prompts/generate/chapter`
- `/api/workflows/full-novel`

T8.4 reduced both:

- Scene files now load the `generate` pipeline prompt instead of falling back to the old `generate/chapter` prompt API.
- The workflow guide checks `/api/workflows` before requesting a specific default workflow, avoiding a missing `full-novel` detail request.

Browser E2E recorded no 404 / API error console noise in the stabilized flow.

## Browser E2E Results

Browser E2E used a real local frontend/backend with an isolated temp workspace. Pipeline streaming was mocked at the browser route layer for fast / slow / error cases; candidate creation, preview, delete, and metadata reads used the real backend Candidate API.

| # | Scenario | Result |
|---:|---|---|
| 1 | Empty required / forbidden input default generation | Pass: validator not enabled, candidate panel ok |
| 2 | Required beat generation | Pass: request includes `_enable_beat_validation` and required beat, panel shows validation status |
| 3 | Forbidden beat generation | Pass: request includes forbidden beat, warning detail visible |
| 4 | Right panel rewrite | Pass: `pipeline=rewrite`, `output_mode=candidate`, path normalized, state recovers |
| 5 | Slow LLM response over 15s | Pass: slow-response status appears, UI does not freeze |
| 6 | LLM error / timeout | Pass: friendly error appears, button can be clicked again |
| 7 | Preview then delete | Pass: preview modal opens/closes, delete dialog appears, candidate becomes `discarded` |
| 8 | Legacy candidate compatibility | Pass: candidate without `beat_validation` does not crash panel |

Additional long-wait E2E:

- Waited past 60 seconds.
- Verified long-wait status appears.
- Verified button recovers after stream completion.

## Test Commands

```powershell
git status --short
git log -1 --oneline
npx gitnexus impact --repo moyun-studio runAction --direction upstream
npx gitnexus impact --repo moyun-studio loadFilePrompt --direction upstream
npx gitnexus impact --repo moyun-studio usePromptSync --direction upstream
npx gitnexus impact --repo moyun-studio loadWorkflow --direction upstream
cd frontend
npm run build
cd ..
node %TEMP%\t84-e2e.js
node %TEMP%\t84-long-wait-e2e.js
```

## Bugs Found

1. Right-panel generation had poor long-wait visibility.
2. LLM errors surfaced as raw backend messages.
3. Scene prompt sync could request old `generate/chapter`.
4. Workflow guide could request missing `full-novel`.
5. Candidate warning details were too compressed for quick review.

## Remaining Issues

- This task did not change real LLM latency or provider behavior.
- Full real-LLM candidate creation can still fail if the model does not return output.
- The Professional rewrite pipeline is still multi-step and may be slow for small models.
- Some older source files still contain mojibake text in comments/UI strings from previous encoding history; this task did not broadly clean encoding.

## Recommendation

T8.5 can proceed. Suggested focus:

1. First-token timeout and retry policy at the backend LLM boundary.
2. A shorter Professional quick-rewrite pipeline or explicit "deep rewrite" vs "quick candidate" distinction.
3. A durable E2E smoke script committed under a test/dev path, if the team wants repeatable browser validation.
