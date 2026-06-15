"""Feedback revision candidate tests.

These tests keep the T8.5-mini contract focused: user feedback creates a child
candidate, never edits the official scene, and only pending parent candidates
can be revised.
"""

from types import SimpleNamespace
from pathlib import Path

import pytest

from backend.api import candidates as candidates_api
from backend.core.candidate_service import CandidateService
from backend.core.file_ops import FileService
from backend.schemas.candidate import CandidateAction, CandidateStatus


class DummyLLMService:
    def __init__(self, output: str = "修订后的候选稿正文"):
        self.output = output
        self.config = SimpleNamespace(model="mock-model")

    async def complete_sync(self, messages, **kwargs):
        return self.output


class FailingLLMService:
    config = SimpleNamespace(model="mock-model")

    async def complete_sync(self, messages, **kwargs):
        raise RuntimeError("mock llm down")


class SequentialLLMService:
    def __init__(self, outputs: list[str]):
        self.outputs = list(outputs)
        self.config = SimpleNamespace(model="mock-model")

    async def complete_sync(self, messages, **kwargs):
        if not self.outputs:
            return ""
        return self.outputs.pop(0)


async def _create_source_and_parent(
    temp_workspace,
    *,
    status: CandidateStatus = CandidateStatus.PENDING,
    generation_context: dict | None = None,
    beat_validation: dict | None = None,
):
    fs = FileService(temp_workspace)
    project_id = "test-project"
    source_path = "chapters/vol-01/ch-001/sec-001.md"
    source_full_path = temp_workspace / project_id / source_path
    source_full_path.parent.mkdir(parents=True, exist_ok=True)
    source_full_path.write_text("official scene text", encoding="utf-8")

    service = CandidateService(fs)
    parent = await service.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content="parent candidate text",
        generation_context=generation_context or {},
        beat_validation=beat_validation or {},
    )
    if status != CandidateStatus.PENDING:
        metadata = await service._load_metadata(project_id)
        metadata[parent.id]["status"] = status.value
        await service._save_metadata(project_id, metadata)
        parent = await service.get_candidate(project_id, parent.id)
    return service, project_id, source_path, source_full_path, parent


@pytest.mark.asyncio
async def test_feedback_revision_creates_child_candidate_without_touching_parent(temp_workspace):
    fs = FileService(temp_workspace)
    project_id = "test-project"
    source_path = "chapters/vol-01/ch-001/sec-001.md"
    source_full_path = temp_workspace / project_id / source_path
    source_full_path.parent.mkdir(parents=True, exist_ok=True)
    source_full_path.write_text("正式场景正文", encoding="utf-8")

    service = CandidateService(fs)
    parent = await service.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content="父候选稿正文",
        generation_context={
            "required_beats_input": [{"id": "beat-1", "text": "第七层协议必须被提及"}],
            "forbidden_beats_input": [{"id": "forbid-1", "text": "不能揭晓完整真相"}],
        },
        beat_validation={"status": "warning", "summary": "缺少信息点"},
    )

    child = await service.create_feedback_revision_candidate(
        project_id=project_id,
        parent_candidate_id=parent.id,
        feedback_text="补上缺失信息点，保持悬念",
        quick_actions=["fix_missing_beats"],
        repair_scope="full_candidate",
        llm_service=DummyLLMService("子候选稿正文"),
        prompt_template="source={{ official_source_text }} parent={{ parent_candidate_text }} feedback={{ feedback_text }}",
        run_beat_validation=False,
    )

    parent_after = await service.get_candidate(project_id, parent.id)
    source_after = source_full_path.read_text(encoding="utf-8")

    assert child.id != parent.id
    assert child.action == CandidateAction.FEEDBACK_REVISION
    assert child.status == CandidateStatus.PENDING
    assert child.source_path == parent.source_path
    assert child.parent_candidate_id == parent.id
    assert child.revision_index == 1
    assert child.generation_context["revision_type"] == "feedback_revision"
    assert child.generation_context["feedback_text"] == "补上缺失信息点，保持悬念"
    assert child.generation_context["quick_actions"] == ["fix_missing_beats"]
    assert child.generation_context["required_beats_input"][0]["text"] == "第七层协议必须被提及"
    assert child.generation_context["forbidden_beats_input"][0]["text"] == "不能揭晓完整真相"
    assert await service.get_candidate_content(project_id, child.id) == "子候选稿正文"
    assert parent_after.status == CandidateStatus.PENDING
    assert source_after == "正式场景正文"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [CandidateStatus.ADOPTED, CandidateStatus.DISCARDED, CandidateStatus.REJECTED],
)
async def test_feedback_revision_rejects_non_pending_parent(temp_workspace, status):
    service, project_id, _, _, parent = await _create_source_and_parent(
        temp_workspace,
        status=status,
    )
    with pytest.raises(ValueError, match="PARENT_NOT_PENDING"):
        await service.create_feedback_revision_candidate(
            project_id=project_id,
            parent_candidate_id=parent.id,
            feedback_text="再改一下",
            quick_actions=[],
            repair_scope="full_candidate",
            llm_service=DummyLLMService(),
            prompt_template="{{ feedback_text }}",
            run_beat_validation=False,
        )


@pytest.mark.asyncio
async def test_revise_candidate_llm_failure_does_not_create_child(temp_workspace):
    service, project_id, _, source_full_path, parent = await _create_source_and_parent(temp_workspace)
    metadata_before = await service._load_metadata(project_id)

    with pytest.raises(ValueError, match="REVISION_LLM_FAILED"):
        await service.create_feedback_revision_candidate(
            project_id=project_id,
            parent_candidate_id=parent.id,
            feedback_text="make it sharper",
            quick_actions=[],
            repair_scope="full_candidate",
            llm_service=FailingLLMService(),
            prompt_template="{{ feedback_text }} {{ parent_candidate_text }}",
            run_beat_validation=False,
        )

    metadata_after = await service._load_metadata(project_id)
    parent_after = await service.get_candidate(project_id, parent.id)

    assert set(metadata_after.keys()) == set(metadata_before.keys())
    assert parent_after.status == CandidateStatus.PENDING
    assert parent_after.model_dump(mode="json") == metadata_before[parent.id]
    assert source_full_path.read_text(encoding="utf-8") == "official scene text"


@pytest.mark.asyncio
async def test_revise_candidate_retry_after_llm_failure(temp_workspace):
    service, project_id, _, source_full_path, parent = await _create_source_and_parent(temp_workspace)

    with pytest.raises(ValueError, match="REVISION_LLM_FAILED"):
        await service.create_feedback_revision_candidate(
            project_id=project_id,
            parent_candidate_id=parent.id,
            feedback_text="first try fails",
            quick_actions=[],
            repair_scope="full_candidate",
            llm_service=FailingLLMService(),
            prompt_template="{{ feedback_text }}",
            run_beat_validation=False,
        )

    child = await service.create_feedback_revision_candidate(
        project_id=project_id,
        parent_candidate_id=parent.id,
        feedback_text="retry succeeds",
        quick_actions=[],
        repair_scope="full_candidate",
        llm_service=DummyLLMService("retried child candidate"),
        prompt_template="{{ feedback_text }}",
        run_beat_validation=False,
    )

    assert child.parent_candidate_id == parent.id
    assert child.status == CandidateStatus.PENDING
    assert await service.get_candidate_content(project_id, child.id) == "retried child candidate"
    assert source_full_path.read_text(encoding="utf-8") == "official scene text"


@pytest.mark.asyncio
async def test_feedback_revision_supports_multi_round_lineage(temp_workspace):
    service, project_id, _, source_full_path, parent = await _create_source_and_parent(temp_workspace)

    first_child = await service.create_feedback_revision_candidate(
        project_id=project_id,
        parent_candidate_id=parent.id,
        feedback_text="first revision",
        quick_actions=[],
        repair_scope="full_candidate",
        llm_service=DummyLLMService("first child"),
        prompt_template="{{ feedback_text }}",
        run_beat_validation=False,
    )
    second_child = await service.create_feedback_revision_candidate(
        project_id=project_id,
        parent_candidate_id=first_child.id,
        feedback_text="second revision",
        quick_actions=[],
        repair_scope="full_candidate",
        llm_service=DummyLLMService("second child"),
        prompt_template="{{ feedback_text }}",
        run_beat_validation=False,
    )

    assert first_child.parent_candidate_id == parent.id
    assert second_child.parent_candidate_id == first_child.id
    assert first_child.revision_group_id == second_child.revision_group_id
    assert first_child.revision_index == 1
    assert second_child.revision_index == 2
    assert (await service.get_candidate(project_id, parent.id)).status == CandidateStatus.PENDING
    assert (await service.get_candidate(project_id, first_child.id)).status == CandidateStatus.PENDING
    assert second_child.status == CandidateStatus.PENDING
    assert source_full_path.read_text(encoding="utf-8") == "official scene text"


@pytest.mark.asyncio
async def test_feedback_revision_inherits_beats_and_reruns_validator(temp_workspace):
    service, project_id, _, _, parent = await _create_source_and_parent(
        temp_workspace,
        generation_context={
            "required_beats_input": [{"id": "beat-1", "text": "mention the seventh protocol"}],
            "forbidden_beats_input": [{"id": "forbid-1", "text": "do not reveal the full truth"}],
        },
        beat_validation={"status": "warning", "summary": "missing required beat"},
    )
    validator_json = """
    {
      "summary": "all required beats are present",
      "required_beats": [
        {
          "text": "mention the seventh protocol",
          "status": "satisfied",
          "evidence": "seventh protocol",
          "confidence": 0.9
        }
      ],
      "forbidden_beats": [
        {
          "text": "do not reveal the full truth",
          "violated": false,
          "evidence": "",
          "confidence": 0.9
        }
      ],
      "logic_risks": []
    }
    """

    child = await service.create_feedback_revision_candidate(
        project_id=project_id,
        parent_candidate_id=parent.id,
        feedback_text="restore the missing beat",
        quick_actions=["fix_missing_beats"],
        repair_scope="full_candidate",
        llm_service=SequentialLLMService(["child mentions the seventh protocol", validator_json]),
        prompt_template="{{ feedback_text }}",
        run_beat_validation=True,
    )

    assert child.generation_context["required_beats_input"][0]["text"] == "mention the seventh protocol"
    assert child.generation_context["forbidden_beats_input"][0]["text"] == "do not reveal the full truth"
    assert child.beat_validation["status"] == "pass"


def test_candidate_revision_api_rejects_empty_feedback(client):
    response = client.post(
        "/api/candidates/test-project/cand_missing/revise",
        json={"feedback_text": "", "quick_actions": []},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_candidate_revision_api_rejects_adopted_parent(client, temp_workspace, monkeypatch):
    project_id = "test-project"
    source_path = "chapters/vol-01/ch-001/sec-001.md"
    source_full_path = temp_workspace / "projects" / project_id / source_path
    source_full_path.parent.mkdir(parents=True, exist_ok=True)
    source_full_path.write_text("正式场景正文", encoding="utf-8")

    fs = FileService(temp_workspace / "projects")
    service = CandidateService(fs)
    parent = await service.create_candidate(
        project_id=project_id,
        source_path=source_path,
        action=CandidateAction.REWRITE,
        content="父候选稿正文",
    )

    metadata = await service._load_metadata(project_id)
    metadata[parent.id]["status"] = CandidateStatus.ADOPTED.value
    await service._save_metadata(project_id, metadata)

    monkeypatch.setattr(
        candidates_api,
        "get_settings",
        lambda: SimpleNamespace(
            projects_path=temp_workspace / "projects",
            prompts_path=temp_workspace / "prompts",
            system_prompts_path=Path("prompts").resolve(),
            max_file_write_size=5 * 1024 * 1024,
        ),
    )
    monkeypatch.setattr(candidates_api, "load_llm_config_from_workspace", lambda settings: SimpleNamespace())
    monkeypatch.setattr(
        candidates_api.LLMService,
        "from_workspace_config",
        staticmethod(lambda config: DummyLLMService()),
    )

    response = client.post(
        f"/api/candidates/{project_id}/{parent.id}/revise",
        json={"feedback_text": "再改一下", "quick_actions": []},
    )

    assert response.status_code == 409
