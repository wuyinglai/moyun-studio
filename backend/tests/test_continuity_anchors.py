import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from backend.core.candidate_service import CandidateService
from backend.core.continuity_anchor_service import ContinuityAnchorService
from backend.core.file_ops import FileService
from backend.core.pipeline import PipelineRunner
from backend.schemas.candidate import CandidateAction
from backend.schemas.continuity_anchor import ContinuityAnchor, ContinuityAnchorsDocument


class DummyLLM:
    def __init__(self, chunks: list[str] | None = None):
        self.chunks = chunks or ["候选稿正文提到沈知夏左臂受伤。"]
        self.config = SimpleNamespace(
            model="mock-model",
            max_prompt_tokens=120000,
            context_window=128000,
            reserved_output_tokens=8000,
        )

    async def complete(self, *args, **kwargs):
        for chunk in self.chunks:
            yield chunk

    async def complete_sync(self, messages, **kwargs):
        return "".join(self.chunks)


def _doc(*anchors: ContinuityAnchor) -> ContinuityAnchorsDocument:
    return ContinuityAnchorsDocument(version=1, anchors=list(anchors))


def _anchor(
    anchor_id: str = "anchor-1",
    *,
    status: str = "active",
    type: str = "character_state",
    title: str = "沈知夏左臂受伤",
    content: str = "沈知夏左臂仍有旧伤，不能高强度攀爬。",
) -> ContinuityAnchor:
    return ContinuityAnchor(
        id=anchor_id,
        type=type,
        title=title,
        content=content,
        status=status,
        source="user",
        updated_at=f"2026-06-17T00:00:0{anchor_id[-1] if anchor_id[-1].isdigit() else 1}+00:00",
    )


@pytest.mark.asyncio
async def test_missing_continuity_anchor_document_returns_empty(temp_workspace):
    service = ContinuityAnchorService(FileService(temp_workspace))

    document = await service.read_document("missing-project")

    assert document.version == 1
    assert document.anchors == []


@pytest.mark.asyncio
async def test_continuity_anchor_read_write_and_active_filter(temp_workspace):
    fs = FileService(temp_workspace)
    service = ContinuityAnchorService(fs)
    active = _anchor("anchor-1")
    archived = _anchor("anchor-2", status="archived")
    resolved = _anchor("anchor-3", status="resolved")

    saved = await service.write_document("test-project", _doc(archived, active, resolved))
    loaded = await service.read_document("test-project")
    active_only = await service.list_active("test-project")
    metadata = ContinuityAnchorService.metadata(active_only)

    assert len(saved.anchors) == 3
    assert len(loaded.anchors) == 3
    assert [anchor.id for anchor in active_only] == ["anchor-1"]
    assert metadata["enabled"] is True
    assert metadata["used_count"] == 1
    assert metadata["anchor_ids"] == ["anchor-1"]
    assert metadata["types"] == {"character_state": 1}


@pytest.mark.asyncio
async def test_invalid_continuity_anchor_document_returns_empty(temp_workspace):
    """Invalid / corrupt anchor JSON should degrade gracefully to empty document.

    This prevents unrelated pipelines from crashing when the anchors file
    contains stale or garbage data.  write_document still validates on write.
    """
    project_dir = temp_workspace / "test-project"
    project_dir.mkdir(exist_ok=True)
    (project_dir / "continuity-anchors.json").write_text('{"anchors":[{"id":""}]}', encoding="utf-8")
    service = ContinuityAnchorService(FileService(temp_workspace))

    doc = await service.read_document("test-project")
    assert doc.anchors == []


def test_continuity_anchor_api_get_put(client):
    project_id = "test-project"
    body = {
        "version": 1,
        "anchors": [
            {
                "id": "anchor-1",
                "type": "object_location",
                "title": "银色芯片归属",
                "content": "银色芯片仍在林澈手中。",
                "scope": "global",
                "status": "active",
                "priority": "high",
                "source": "user",
                "updated_at": "2026-06-17T00:00:00+00:00",
            }
        ],
    }

    put_resp = client.put(f"/api/projects/{project_id}/continuity-anchors", json=body)
    get_resp = client.get(f"/api/projects/{project_id}/continuity-anchors")

    assert put_resp.status_code == 200
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["anchors"][0]["id"] == "anchor-1"


def test_continuity_anchor_prompt_block_is_conditional(tmp_path):
    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "blocks").mkdir(parents=True)
    (prompts_dir / "blocks" / "continuity-anchors.md").write_text(
        Path("prompts/blocks/continuity-anchors.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (prompts_dir / "pipeline" / "generate").mkdir(parents=True)
    (prompts_dir / "pipeline" / "generate" / "write.md").write_text(
        "before\n{% include 'blocks/continuity-anchors.md' %}\nafter",
        encoding="utf-8",
    )
    runner = PipelineRunner(prompts_dir, DummyLLM(), FileService(tmp_path))

    rendered_empty = runner.render_prompt("pipeline/generate/write.md", {"continuity_anchor_items": []})
    rendered_with_anchor = runner.render_prompt(
        "pipeline/generate/write.md",
        {
            "continuity_anchor_items": [
                {
                    "id": "anchor-1",
                    "type": "character_state",
                    "title": "沈知夏左臂受伤",
                    "content": "沈知夏左臂仍有旧伤。",
                    "scope": "global",
                    "priority": "high",
                }
            ]
        },
    )

    assert "连续性锚点" not in rendered_empty
    assert "沈知夏左臂仍有旧伤" in rendered_with_anchor


@pytest.mark.asyncio
async def test_pipeline_candidate_records_continuity_anchor_metadata(temp_workspace):
    fs = FileService(temp_workspace)
    project_id = "test-project"
    source_path = "chapters/vol-01/ch-001/sec-001.md"
    project_dir = temp_workspace / project_id
    (project_dir / "chapters" / "vol-01" / "ch-001").mkdir(parents=True)
    (project_dir / source_path).write_text("正式正文不应被覆盖", encoding="utf-8")
    (project_dir / "meta.json").write_text("{}", encoding="utf-8")
    await ContinuityAnchorService(fs).write_document(project_id, _doc(_anchor("anchor-1")))

    prompts_dir = temp_workspace / "prompts"
    pipeline_dir = prompts_dir / "pipeline" / "rewrite"
    pipeline_dir.mkdir(parents=True)
    (prompts_dir / "pipeline" / "rewrite.yaml").write_text(
        yaml.safe_dump({
            "name": "rewrite",
            "label": "Rewrite",
            "steps": [
                {"id": "draft", "label": "Draft", "prompt": "pipeline/rewrite/draft", "fallback": None}
            ],
        }, allow_unicode=True),
        encoding="utf-8",
    )
    (pipeline_dir / "draft.md").write_text(
        "{% for anchor in continuity_anchor_items %}{{ anchor.content }}{% endfor %}",
        encoding="utf-8",
    )
    runner = PipelineRunner(prompts_dir, DummyLLM(["新候选稿"]), fs)

    events = [
        event
        async for event in runner.run(
            "rewrite",
            project_id,
            target_file=source_path,
            output_mode="candidate",
        )
    ]
    candidates = await CandidateService(fs).list_candidates(project_id)

    assert any(event.get("event") == "candidate_created" for event in events)
    assert len(candidates) == 1
    assert candidates[0].continuity_anchors["used_count"] == 1
    assert candidates[0].continuity_anchors["anchor_ids"] == ["anchor-1"]
    assert "content" not in candidates[0].continuity_anchors
    assert (project_dir / source_path).read_text(encoding="utf-8") == "正式正文不应被覆盖"


@pytest.mark.asyncio
async def test_feedback_revision_records_active_continuity_anchor_metadata(temp_workspace):
    fs = FileService(temp_workspace)
    project_id = "test-project"
    source_path = "chapters/vol-01/ch-001/sec-001.md"
    source_file = temp_workspace / project_id / source_path
    source_file.parent.mkdir(parents=True)
    source_file.write_text("正式正文", encoding="utf-8")
    await ContinuityAnchorService(fs).write_document(project_id, _doc(_anchor("anchor-1")))

    service = CandidateService(fs)
    parent = await service.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content="父候选稿",
    )
    child = await service.create_feedback_revision_candidate(
        project_id=project_id,
        parent_candidate_id=parent.id,
        feedback_text="保留锚点",
        quick_actions=[],
        repair_scope="full_candidate",
        llm_service=DummyLLM(["子候选稿"]),
        prompt_template="{% for anchor in continuity_anchor_items %}{{ anchor.content }}{% endfor %}\n{{ feedback_text }}",
        run_beat_validation=False,
    )

    assert child.continuity_anchors["used_count"] == 1
    assert child.continuity_anchors["anchor_ids"] == ["anchor-1"]
    assert child.generation_context["continuity_anchor_ids"] == ["anchor-1"]
    assert source_file.read_text(encoding="utf-8") == "正式正文"
