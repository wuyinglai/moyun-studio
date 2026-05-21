# SSE Event Contract

## Event Format

All SSE events follow this structure:

```json
{
  "event_id": "evt_abc123",
  "type": "file.updated",
  "project_id": "my-project",
  "task_id": null,
  "run_id": null,
  "source": "watcher",
  "timestamp": 1716200000.0,
  "payload": {}
}
```

Required fields:
- `type` - event type string
- `timestamp` - Unix timestamp as a float
- `payload` - type-specific data object

Optional fields:
- `event_id` - unique event identifier
- `project_id` - associated project
- `task_id` - associated task
- `run_id` - associated pipeline run
- `source` - event source identifier

## Key Rules

1. `file.updated` events must not carry full content. The payload contains only:

   ```json
   { "path": "chapters/vol-01/ch-001/sec-001.md", "size": 1234, "mtime": 1716200000.0 }
   ```

2. `sse.heartbeat` events must not trigger business logic refresh. Heartbeat is only for connection keep-alive:

   ```json
   { "server_time": 1716200000.0, "interval": 15 }
   ```

3. Event types use lowercase dotted names, such as `file.updated`, `pipeline.step`, and `candidate.created`.

## Event Types

| Type | Payload | Description |
|------|---------|-------------|
| `file.updated` | `{ path, size, mtime }` | File changed on disk |
| `file.created` | `{ path, size }` | New file created |
| `file.deleted` | `{ path }` | File deleted |
| `sse.heartbeat` | `{ server_time, interval? }` | Connection keep-alive |
| `candidate.created` | `{ candidate_id, source_path, action }` | New candidate generated |
| `candidate.adopted` | `{ candidate_id, source_path }` | Candidate adopted |
| `pipeline.started` | `{ pipeline, target_file }` | Pipeline run started |
| `pipeline.step` | `{ step_id, status, message? }` | Pipeline step update |
| `pipeline.done` | `{ pipeline, target_file }` | Pipeline run completed |
| `generation.delta` | `{ delta, file_path? }` | Streaming text delta |
| `generation.done` | `{ file_path, content? }` | Generation completed |
| `task.queued` | `{ task_id, label }` | Task queued |
| `task.started` | `{ task_id }` | Task started |
| `task.completed` | `{ task_id }` | Task completed |
| `task.failed` | `{ task_id, error }` | Task failed |
