# Moyun Studio Code Map

This document provides a code navigation guide for AI / Codex / Solo agents. It maps each feature area to its frontend and backend files, lists important rules, and highlights common pitfalls.

---

## 1. Project Management / 项目管理

Project creation, opening, switching, and deletion.

**Frontend:**
- `frontend/src/stores/project.ts`
- `frontend/src/modules/project/`
- `frontend/src/components/modals/CreateProjectModal.vue`
- `frontend/src/components/modals/OpenProjectModal.vue`

**Backend:**
- `backend/api/projects.py`
- `backend/core/project_service.py`

**Important notes:**
- Professional mode creates a project and navigates to `/project/:projectId`.
- Lite mode creates a project and navigates to `/project/:projectId/lite`.
- Do not modify only one entry point — both must be considered.

**Common pitfalls:**
- Creating a project may trigger pendingGeneration / workflow guide.
- Lite project creation auto-writes the first scene.

---

## 2. File Editing / 文件编辑

**Frontend:**
- `frontend/src/stores/file.ts`
- `frontend/src/stores/editor.ts`
- `frontend/src/components/editor/MarkdownEditor.vue`
- `frontend/src/components/editor/EditorToolbar.vue`
- `frontend/src/composables/useAutoSave.ts`

**Backend:**
- `backend/api/files.py`
- `backend/core/file_ops.py`

**Important notes:**
- All backend file operations must go through FileService.
- API layer must not use `project_dir / path` directly.
- Frontend saves must include `expected_mtime` / `expected_hash`.
- `FILE_CONFLICT` must prompt the user; never silently overwrite.

**Common pitfalls:**
- `file.updated` SSE must not carry full body content.
- Lite textarea saves must follow the same file-save rules.

---

## 3. Scene Path / 场景路径

**Frontend:**
- `frontend/src/modules/scene/scenePath.ts`

**Backend:**
- `backend/application/scene_service.py`

**Rules:**
- `sec-*.md` = single scene, not a chapter.
- Standard path: `chapters/vol-01/ch-001/sec-001.md`
- Default: 5 scenes per chapter.
- Default: 12 chapters per volume.
- After `sec-005`, next is next chapter `sec-001`.
- After `ch-012/sec-005`, next is next volume `vol-02/ch-001/sec-001`.

**Common pitfalls:**
- Do not re-implement path increment logic in Vue components — use `scenePath.ts`.
- Do not rename `ch-001` "chapter" to "scene". Chapters still exist; only `sec-*` are scenes.
- Only `sec-*.md` files are scene content files.

---

## 4. Professional Workspace / 专业工作台

**Frontend:**
- `frontend/src/components/layout/AppLayout.vue`
- `frontend/src/components/editor/EditorToolbar.vue`
- `frontend/src/components/editor/MarkdownEditor.vue`
- `frontend/src/components/right-panel/RightPanel.vue`
- `frontend/src/components/right-panel/ProfessionalQuickPanel.vue`

**Backend:**
- `backend/api/pipeline.py`
- `backend/core/pipeline.py`
- `backend/application/pipeline/`

**Important notes:**
- "Write next scene" is not a simple direct generation.
- It derives the next scene path, then calls pipeline for streaming execution.
- After pipeline completes, it re-reads the file to refresh the editor.
- Polish / rewrite on current scene must default to candidate, not directly overwrite the live text.

**Common pitfalls:**
- Do not treat pipeline stream as a regular POST response.
- Do not let rewrite / polish directly overwrite the current sec body.

---

## 5. Lite Writing / 轻量写作入口

**Frontend:**
- `frontend/src/views/LiteWritingView.vue`

**Backend:**
- `backend/api/lite.py`

**Important notes:**
- `/lite` without a project shows idea cards (开局卡).
- Selecting an idea card creates a project, navigates to `/project/:projectId/lite`, and auto-writes the first scene.
- `/project/:projectId/lite` uses a `<textarea>`, not CodeMirror.
- Lite write action writes to sec body.
- Lite rewrite / more exciting / more reasonable / chat revision generate candidates, not overwriting original text.

**Common pitfalls:**
- Do not assume Lite always has a project.
- Do not assume Lite results always write directly to the live text.
- Do not test only Professional mode — Lite must also be tested.

---

## 6. Candidate / Safe Revisions / 候选稿

**Frontend:**
- `frontend/src/components/right-panel/CandidatePanel.vue`
- `frontend/src/modules/candidate/`

**Backend:**
- `backend/api/candidates.py`
- `backend/core/candidate_service.py`

**Rules:**
- Rewrite / polish / chat edit / more exciting / more reasonable default to candidate.
- `candidate.source_path` must be a project-relative path, no duplicate `project_id`.
- Must check `base_hash` / `base_mtime` before adopt.
- Must write revision-log before adopt.
- Only after adopt does the candidate overwrite the live text.

**Common pitfalls:**
- Do not modify the live text before adopt.
- Do not let candidate path become `project_id/project_id/chapters/...`

---

## 7. Pipeline / Prompt System / 管线系统

**Frontend:**
- `frontend/src/stores/pipeline.ts`
- `frontend/src/components/editor/EditorToolbar.vue`
- `frontend/src/components/right-panel/ProfessionalQuickPanel.vue`

**Backend:**
- `backend/api/pipeline.py`
- `backend/core/pipeline.py`
- `backend/application/pipeline/`
- `backend/core/pipeline_validator.py`
- `backend/schemas/pipeline_config.py`

**Files:**
- `prompts/pipeline/`
- `prompts/blocks/`
- `prompts/generate/`
- `prompts/rewrite/`
- `prompts/polish/`

**Important notes:**
- Pipeline YAML is validated at startup (`pipeline_validator.py`).
- High-risk outputs must go to candidate.
- In prompts, `sec` must be treated as a single scene.

**Common pitfalls:**
- Do not let prompts request generating an entire chapter body at once.
- Do not let `output_mode: overwrite` directly overwrite an existing sec.

---

## 8. Story Memory / 故事记忆

**Backend:**
- `backend/application/memory_service.py`

**Files:**
- `recent-context.md`
- `story-state.md`
- `ch-meta.json`

**Rules:**
- `recent-context` = memory of recent scenes.
- `story-state` = long-term global state.
- `ch-meta.json` = chapter plan and scene cards.
- Ordinary scene details should not all be written to `story-state`.

**Common pitfalls:**
- Do not turn `story-state` into a running log.
- Do not dump all `recent-context` content into the LLM long context.

---

## 9. SSE / Events / 事件系统

**Frontend:**
- `frontend/src/composables/useSSE.ts`
- `frontend/src/modules/sse/`
- `frontend/src/stores/task.ts`

**Backend:**
- `backend/core/event_bus.py`
- `backend/api/sse.py` (contains SSEManager)
- `backend/main.py` (EventBus → SSE bridge)

**Rules:**
- `file.updated` must not send body content.
- Events must include `project_id`.
- Standard events should contain `type`, `timestamp`, `payload`.
- SSE heartbeat (`sse.heartbeat`) must not trigger business logic refresh.

**Common pitfalls:**
- Do not treat heartbeat as a task event.
- Do not let project A respond to project B's events.

---

## 10. LLM Settings / 模型设置

**Frontend:**
- `frontend/src/stores/llm.ts`
- Settings modal components

**Backend:**
- `backend/core/llm.py`
- `backend/core/llm_circuit_breaker.py`
- `backend/api/settings.py`

**Rules:**
- API Key must not be written to localStorage.
- API Key must not appear in logs, screenshots, or test reports.
- Real LLM E2E must be skippable.
- Mock LLM E2E should run stably in CI.

---

## 11. E2E Tests / 自动化测试

**Frontend:**
- `frontend/tests/e2e/`
- `frontend/playwright.config.ts`

**Rules:**
- Mock E2E for CI.
- Real LLM E2E for quality assessment.
- Both entry points must be tested: Professional and Lite.
- Quality reports must not contain API Key.

---

## 12. Where Not To Change / 不要随便改的地方

- Do not concatenate file paths directly in the API layer.
- Do not hardcode API paths in Vue components.
- Do not re-implement scene path rules in components.
- Do not bypass CandidateService to adopt candidates.
- Do not bypass MemoryService to update story memory.
- Do not let rewrite / polish directly overwrite the live text.
- Do not commit Wiki working copies to the main repository.
