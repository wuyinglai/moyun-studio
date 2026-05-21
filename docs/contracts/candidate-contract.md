# Candidate Contract

## Core Rules

1. High-risk actions must generate candidates, not overwrite directly. The following actions default to candidate mode:
   - `rewrite` - full rewrite of a scene
   - `polish` - prose polishing
   - `chat edit` - chat-guided revision
   - `more_exciting` - intensity boost
   - `more_reasonable` - logic improvement

2. `candidate.source_path` must be a project-relative path without duplicate `project_id`.
   - Correct: `chapters/vol-01/ch-001/sec-001.md`
   - Wrong: `my-project/chapters/vol-01/ch-001/sec-001.md`

3. Before adopting a candidate, the backend must verify `base_hash` or `base_mtime`. If the source file changed after the candidate was created, adoption fails with a conflict error.

4. Before adopting, the backend must write a revision-log entry. The revision log records what changed, why, and which candidate was adopted.

## Candidate Lifecycle

```text
pending -> adopted
pending -> rejected
pending -> discarded
```

- `pending` - candidate generated, awaiting user decision
- `adopted` - user accepted, source file replaced with candidate content
- `rejected` - user declined, candidate marked as rejected
- `discarded` - candidate cleaned up without explicit decision

## Candidate Storage

Candidates are stored in the project `.candidates/` directory:

```text
project/
  .candidates/
    chapters__vol-01__ch-001__sec-001.rewrite.md
    chapters__vol-01__ch-001__sec-001.polish.md
```

## API

### POST /api/candidates

Create a new candidate.

### GET /api/candidates?project_id=xxx&source_path=yyy

List candidates for a source file.

### POST /api/candidates/{id}/adopt

Adopt a candidate. Checks `base_hash` or `base_mtime` before applying.

### POST /api/candidates/{id}/reject

Reject a candidate.

## Safety Checks

- Adopting a candidate whose source file has changed must fail with a conflict error.
- Candidate content must never be saved directly to the source file without the adopt flow.
- The frontend must prevent direct editing of candidate files in the main editor.

## 必须生成候选稿的动作

以下动作默认必须生成候选稿，不直接覆盖正式正文：

- `rewrite_current_scene` — 重写当前场景
- `polish_current_scene` — 润色当前场景
- `chat_edit_current_scene` — 对话编辑当前场景
- `more_exciting` — 让当前场景更爽
- `more_reasonable` — 让当前场景更合理

以下动作由 GenerationOutputPolicy 判断：

- `write_next_scene` — 目标为空时直接写入，目标已有内容时生成候选稿
- `write_current_scene` — 目标为空时直接写入，目标已有内容时生成候选稿

> **output_mode=overwrite 兼容**：后端收到 `overwrite` 时，如果目标是已有 sec 文件，自动转为 `candidate`；如果目标为空，转为 `write_scene`。前端不再主动发送 `overwrite`。
