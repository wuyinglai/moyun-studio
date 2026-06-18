import json
from unittest.mock import AsyncMock, MagicMock

from jinja2 import Environment, FileSystemLoader
import pytest
import yaml

from backend.core.pipeline import PipelineRunner


@pytest.fixture
def mock_llm_service():
    service = MagicMock()

    async def mock_complete(*args, **kwargs):
        for chunk in ["生成", "文风", "指南"]:
            yield chunk

    service.complete = mock_complete
    service.config.max_prompt_tokens = 120000
    service.config.context_window = 128000
    return service


@pytest.fixture
def mock_file_service():
    service = MagicMock()
    return service


@pytest.fixture
def runner(mock_llm_service, mock_file_service, tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    return PipelineRunner(prompts_dir, mock_llm_service, mock_file_service)


@pytest.mark.asyncio
async def test_style_guide_placeholder_normalizes_to_write_scene(runner, mock_file_service):
    async def mock_read(path):
        path_str = str(path)
        if "style-guide.md" in path_str:
            return "# 文风指南\n\n在此描述写作风格、语气、叙事视角等要求。", None
        return "", None

    mock_file_service.read_file = AsyncMock(side_effect=mock_read)

    result = await runner._normalize_output_mode(
        pipeline_name="style-guide",
        project_id="test-project",
        target_file="style-guide.md",
        output_mode="write_scene",
    )

    assert result == "write_scene"


@pytest.mark.asyncio
async def test_write_scene_replaces_style_guide_placeholder(runner, mock_file_service, tmp_path):
    async def mock_read(path):
        path_str = str(path)
        if "style-guide.md" in path_str:
            return "# 文风指南\n\n在此描述写作风格、语气、叙事视角等要求。", None, None
        if ".candidates/metadata.json" in path_str:
            return "{}", None, None
        if "meta.json" in path_str:
            return json.dumps({"name": "test", "genre": "玄幻"}), None, None
        return "", None, None

    mock_file_service.read_file = AsyncMock(side_effect=mock_read)

    write_calls = []

    async def mock_write(path, content, frontmatter=None):
        write_calls.append({"path": str(path), "content": content})  # AI_GUARDRAIL_ALLOW: test mock data, not SSE

    mock_file_service.write_file = AsyncMock(side_effect=mock_write)

    pipeline_dir = tmp_path / "prompts" / "pipeline" / "style-guide"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "step1.md").write_text("生成文风指南", encoding="utf-8")

    yaml_content = {
        "name": "style-guide",
        "label": "生成文风指南",
        "steps": [{"id": "step1", "label": "测试", "prompt": "pipeline/style-guide/step1"}],
    }
    yaml_path = tmp_path / "prompts" / "pipeline" / "style-guide.yaml"
    yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")

    runner.prompts_path = tmp_path / "prompts"
    runner.env = Environment(loader=FileSystemLoader(str(tmp_path / "prompts")), autoescape=False)

    events = []
    async for event in runner.run(
        "style-guide",
        "test-project",
        "style-guide.md",
        output_mode="write_scene",
    ):
        events.append(event)

    style_writes = [c for c in write_calls if c["path"].endswith("style-guide.md")]
    candidate_events = [e for e in events if e.get("event") == "candidate_created"]

    assert len(style_writes) > 0
    assert len(candidate_events) == 0
