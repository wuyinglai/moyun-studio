import json
from types import SimpleNamespace

import pytest
import yaml

from backend.core.beat_validator import (
    RequiredBeatValidator,
    extract_beat_validation_inputs,
    is_beat_validation_enabled,
    normalize_beat_validation_result,
)
from backend.core.candidate_service import CandidateService
from backend.core.file_ops import FileService
from backend.core.pipeline import PipelineRunner
from backend.schemas.candidate import CandidateAction


class FakeValidatorLLM:
    def __init__(self, response: str):
        self.response = response
        self.config = SimpleNamespace(
            model="fake-validator",
            max_prompt_tokens=120000,
            context_window=128000,
            reserved_output_tokens=8000,
        )

    async def complete(self, *args, **kwargs):
        yield "candidate text with seventh protocol"

    async def complete_sync(self, *args, **kwargs):
        return self.response


class SequentialValidatorLLM(FakeValidatorLLM):
    def __init__(self, responses: list[object]):
        super().__init__("")
        self.responses = list(responses)
        self.calls = 0

    async def complete_sync(self, *args, **kwargs):
        self.calls += 1
        if not self.responses:
            return ""
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return str(response)


def test_beat_validation_is_opt_in_only():
    assert is_beat_validation_enabled({}) is False
    assert is_beat_validation_enabled({"_enable_beat_validation": False}) is False
    assert is_beat_validation_enabled({"_enable_beat_validation": "false"}) is False
    assert is_beat_validation_enabled({"_enable_beat_validation": True}) is True
    assert is_beat_validation_enabled({"_enable_beat_validation": "true"}) is True


def test_extract_beat_validation_inputs_normalizes_lists_and_strings():
    required, forbidden = extract_beat_validation_inputs({
        "required_beats": ["seventh protocol", {"text": "silver chip"}],
        "forbidden_beats": "reveal full truth\nadd new mentor",
    })

    assert required == ["seventh protocol", "silver chip"]
    assert forbidden == ["reveal full truth", "add new mentor"]


def test_normalize_beat_validation_result_marks_warning_for_missing_required():
    result = normalize_beat_validation_result(
        {
            "summary": "one beat missing",
            "required_beats": [
                {"text": "seventh protocol", "status": "satisfied"},
                {"text": "silver chip", "status": "missing"},
            ],
            "forbidden_beats": [{"text": "reveal full truth", "violated": False}],
        },
        ["seventh protocol", "silver chip"],
        ["reveal full truth"],
        model="fake",
    )

    assert result["status"] == "warning"
    assert result["required_beats"][1]["status"] == "missing"


def test_normalize_beat_validation_result_aligns_by_id_when_order_shuffled():
    result = normalize_beat_validation_result(
        {
            "summary": "order shuffled",
            "required_beats": [
                {"id": "beat-2", "text": "silver chip", "status": "missing"},
                {"id": "beat-1", "text": "seventh protocol", "status": "satisfied"},
            ],
            "forbidden_beats": [
                {"id": "forbid-1", "text": "reveal full truth", "violated": False},
            ],
        },
        ["seventh protocol", "silver chip"],
        ["reveal full truth"],
        model="fake",
    )

    assert result["required_beats"][0]["text"] == "seventh protocol"
    assert result["required_beats"][0]["status"] == "satisfied"
    assert result["required_beats"][0]["alignment"] == "id"
    assert result["required_beats"][1]["text"] == "silver chip"
    assert result["required_beats"][1]["status"] == "missing"
    assert result["required_beats"][1]["alignment"] == "id"


def test_normalize_beat_validation_result_aligns_by_text_exact_without_id():
    result = normalize_beat_validation_result(
        {
            "required_beats": [
                {"text": "silver chip", "status": "missing"},
                {"text": "seventh protocol", "status": "satisfied"},
            ],
        },
        ["seventh protocol", "silver chip"],
        [],
        model="fake",
    )

    assert result["required_beats"][0]["status"] == "satisfied"
    assert result["required_beats"][0]["alignment"] == "text_exact"
    assert result["required_beats"][1]["status"] == "missing"


def test_normalize_beat_validation_result_aligns_by_similarity():
    result = normalize_beat_validation_result(
        {
            "required_beats": [
                {"text": "seventh layer protocol", "status": "satisfied"},
            ],
        },
        ["seventh protocol"],
        [],
        model="fake",
    )

    assert result["required_beats"][0]["status"] == "satisfied"
    assert result["required_beats"][0]["alignment"] == "similarity"
    assert result["required_beats"][0]["alignment_score"] >= 0.62


def test_normalize_beat_validation_result_low_similarity_is_unknown():
    result = normalize_beat_validation_result(
        {
            "required_beats": [
                {"text": "unrelated mentor arrives", "status": "satisfied"},
            ],
            "forbidden_beats": [
                {"text": "unrelated place", "violated": False},
            ],
        },
        ["seventh protocol"],
        ["reveal full truth"],
        model="fake",
    )

    assert result["status"] == "warning"
    assert result["required_beats"][0]["status"] == "unknown"
    assert result["required_beats"][0]["alignment"] == "unknown"
    assert result["forbidden_beats"][0]["violated"] is None
    assert result["forbidden_beats"][0]["alignment"] == "unknown"


@pytest.mark.asyncio
async def test_validator_json_parse_failure_returns_unknown():
    validator = RequiredBeatValidator(FakeValidatorLLM("not json"))

    result = await validator.validate(
        "body",
        required_beats=["seventh protocol"],
        forbidden_beats=[],
    )

    assert result["status"] == "unknown"
    assert result["required_beats"][0]["status"] == "unknown"
    assert result["validator"]["retry_count"] == 1


@pytest.mark.asyncio
async def test_validator_retries_once_and_succeeds():
    validator = RequiredBeatValidator(SequentialValidatorLLM([
        RuntimeError("temporary"),
        json.dumps({
            "summary": "pass on retry",
            "required_beats": [{"id": "beat-1", "text": "seventh protocol", "status": "satisfied"}],
            "forbidden_beats": [],
        }),
    ]))

    result = await validator.validate(
        "body with seventh protocol",
        required_beats=["seventh protocol"],
        forbidden_beats=[],
    )

    assert result["status"] == "pass"
    assert result["validator"]["retry_count"] == 1
    assert result["validator"]["last_error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_validator_two_failures_returns_unknown_with_retry_metadata():
    llm = SequentialValidatorLLM([RuntimeError("first"), RuntimeError("second")])
    validator = RequiredBeatValidator(llm)

    result = await validator.validate(
        "body",
        required_beats=["seventh protocol"],
        forbidden_beats=[],
    )

    assert llm.calls == 2
    assert result["status"] == "unknown"
    assert result["validator"]["retry_count"] == 1
    assert result["validator"]["last_error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_candidate_service_persists_beat_validation_metadata(tmp_path):
    project_dir = tmp_path / "test-project" / "chapters" / "vol-01" / "ch-001"
    project_dir.mkdir(parents=True)
    (project_dir / "sec-001.md").write_text("original", encoding="utf-8")

    svc = CandidateService(FileService(tmp_path))
    candidate = await svc.create_candidate(
        project_id="test-project",
        source_path="chapters/vol-01/ch-001/sec-001.md",
        action=CandidateAction.REWRITE,
        content="candidate",
        beat_validation={"status": "warning", "summary": "missing beat"},
    )

    loaded = await svc.get_candidate("test-project", candidate.id)
    assert loaded is not None
    assert loaded.beat_validation["status"] == "warning"
    assert loaded.beat_validation["summary"] == "missing beat"


@pytest.mark.asyncio
async def test_pipeline_candidate_opt_in_writes_beat_validation(tmp_path):
    project_dir = tmp_path / "test-project" / "chapters" / "vol-01" / "ch-001"
    project_dir.mkdir(parents=True)
    (project_dir / "sec-001.md").write_text("original scene", encoding="utf-8")

    prompts_dir = tmp_path / "prompts"
    pipeline_dir = prompts_dir / "pipeline" / "generate"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "write.md").write_text("write next scene", encoding="utf-8")
    (prompts_dir / "pipeline" / "generate.yaml").write_text(
        yaml.dump({
            "name": "generate",
            "label": "Generate",
            "steps": [{"id": "write", "label": "Write", "prompt": "pipeline/generate/write"}],
        }),
        encoding="utf-8",
    )

    llm = FakeValidatorLLM(json.dumps({
        "summary": "required beats pass",
        "required_beats": [{"text": "seventh protocol", "status": "satisfied", "evidence": "seventh protocol"}],
        "forbidden_beats": [],
        "logic_risks": [],
    }))
    runner = PipelineRunner(prompts_dir, llm, FileService(tmp_path))

    events = []
    async for event in runner.run(
        "generate",
        "test-project",
        "chapters/vol-01/ch-001/sec-001.md",
        output_mode="candidate",
        extra_vars={
            "_enable_beat_validation": True,
            "required_beats": ["seventh protocol"],
        },
    ):
        events.append(event)

    created = [json.loads(e["data"]) for e in events if e.get("event") == "candidate_created"]
    assert created
    assert created[0]["beat_validation_status"] == "pass"

    metadata = json.loads((tmp_path / "test-project" / ".candidates" / "metadata.json").read_text(encoding="utf-8"))
    saved = metadata[created[0]["candidate_id"]]
    assert saved["beat_validation"]["status"] == "pass"
