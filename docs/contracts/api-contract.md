# API Contract

## File API

### GET /api/file

Read a file's content and metadata.

**Response:**

```json
{
  "path": "chapters/vol-01/ch-001/sec-001.md",
  "content": "# 第1卷 第1章 第1场景\n\n正文内容...",
  "frontmatter": {},
  "mtime": 1716200000.0,
  "hash": "abc123"
}
```

Fields:
- `path` - relative path within the project
- `content` - full file content (markdown)
- `frontmatter` - parsed YAML frontmatter (object or null)
- `mtime` - file modification timestamp
- `hash` - content hash used by the frontend for conflict detection

### POST /api/file

Write a file with conflict detection.

**Request:**

```json
{
  "path": "chapters/vol-01/ch-001/sec-001.md",
  "content": "updated content",
  "frontmatter": {},
  "expected_mtime": 1716200000.0,
  "expected_hash": "abc123"
}
```

Fields:
- `path` - required, relative path within the project
- `content` - required, new file content
- `frontmatter` - optional, YAML frontmatter to prepend
- `expected_mtime` - optional, last-known mtime for conflict detection
- `expected_hash` - optional, last-known content hash for conflict detection

**Conflict Response (409):**

```json
{
  "error": {
    "code": "FILE_CONFLICT",
    "message": "File has been modified since last read",
    "details": {
      "current_mtime": 1716200100.0,
      "current_hash": "def456"
    }
  }
}
```

## Safety Rules

1. API layer must not construct file paths with `project_dir / req.path`. All file operations go through `FileService`, which validates and resolves paths safely.
2. Frontend saves must send `expected_mtime` and `expected_hash`, then handle `FILE_CONFLICT` (409) responses.
3. `file.updated` SSE events must not carry full content. They send metadata only: `path`, `size`, and `mtime`.
