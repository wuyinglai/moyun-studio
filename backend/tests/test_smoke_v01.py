"""v0.1 Smoke Test — 完整小说创作闭环

验证流程：
1. 创建测试项目
2. 创建 chapters/vol-01/ch-001/sec-001.md
3. 写入 600-1000 字场景正文
4. 调用 rewrite/polish 生成候选稿
5. 采用候选稿
6. 检查：
   - 正文被更新
   - revision-log 已生成
   - candidate status 变为 adopted
   - recent-context.md 更新
   - 没有 project_id/project_id 路径
   - file.updated 事件不包含 content
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from backend.core.file_ops import FileService
from backend.core.candidate_service import CandidateService, AdoptResult
from backend.application.scene_service import SceneService
from backend.application.memory_service import MemoryService
from backend.domain.events import make_file_updated_event, EventType
from backend.schemas.candidate import CandidateAction


# ─── 测试用场景正文（约 800 字）──────────────────────────

SCENE_CONTENT = """\
夜色如墨，长安城的街巷在月光下显得格外寂静。李云舒独自走在青石板路上，脚步声在空旷的巷子里回荡，像是某种不祥的预兆。

她停下脚步，回头望了一眼身后的黑暗。那道影子又出现了——从她离开客栈起，就一直跟在她身后，不远不近，仿佛在等待什么时机。

"出来吧。"她的声音平静而清冷，在夜风中却没有丝毫颤抖。

影子从墙角缓缓走出，月光照亮了一张苍白的面孔。那是一个年轻男子，穿着一身墨色长衫，腰间别着一柄古朴的长剑。他的眼神深邃而复杂，似乎藏着无数未说出口的秘密。

"李姑娘好眼力。"男子微微一笑，声音低沉而富有磁性，"在下沈墨，久仰大名。"

李云舒没有放松警惕，右手已经悄悄握住了袖中的暗器。她知道，在这个时候出现在长安夜巷中的人，绝不会是普通路人。

"你跟了我三条街，不是只为了说一句久仰大名吧？"

沈墨的笑容微微一滞，随即恢复了从容。"确实不是。"他从怀中取出一枚玉佩，在月光下泛着淡淡的光芒，"这是令尊留给你的，他让我在你到达长安后交给你。"

李云舒的瞳孔猛然收缩。那枚玉佩她再熟悉不过——那是父亲在她幼年时随身佩戴的，后来父亲突然失踪，这枚玉佩也随之消失。如今它出现在一个陌生人手中，意味着什么？

"我父亲……他还活着？"她的声音终于有了一丝颤抖。

沈墨沉默了片刻，目光投向远处城楼的轮廓。"这个问题的答案，比你想象的要复杂得多。"他缓缓说道，"但有一件事可以确定——他希望你找到天机阁。"

天机阁。那个传说中的地方，据说藏着天下最大的秘密。李云舒曾以为那只是江湖传闻，从未想过有一天会与自己的命运产生交集。

夜风忽然变得凛冽，远处的更鼓声沉沉地敲响。子时已到，长安城的宵禁即将开始。她必须做出选择——是相信这个突然出现的陌生人，还是转身离开，当作什么都没有发生。

李云舒深吸一口气，将暗器收回袖中，向沈墨伸出了手。

"把玉佩给我。然后，告诉我你知道的一切。"
"""


def _make_project(workspace: Path, project_id: str) -> Path:
    """创建最小化测试项目"""
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # 项目元数据
    meta = {
        "name": "烟测测试小说",
        "genre": "武侠",
        "author": "测试作者",
        "scenes_per_chapter": 5,
        "chapters_per_volume": 12,
        "scene_target_chars": 800,
    }
    (project_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    # 必要的目录和文件
    (project_dir / "chapters").mkdir(exist_ok=True)
    (project_dir / "characters").mkdir(exist_ok=True)
    (project_dir / "materials").mkdir(exist_ok=True)
    (project_dir / "backup").mkdir(exist_ok=True)
    (project_dir / "style-guide.md").write_text("# 风格指南\n\n武侠风格，古风语言。", encoding="utf-8")
    (project_dir / "story-state.md").write_text("# 故事状态\n\n暂无。", encoding="utf-8")
    (project_dir / "recent-context.md").write_text("# 近期上下文\n\n暂无。", encoding="utf-8")
    (project_dir / "outline.md").write_text("# 大纲\n\n第一卷：初入江湖", encoding="utf-8")

    return project_dir


def _make_scene_file(project_dir: Path) -> Path:
    """创建场景文件 chapters/vol-01/ch-001/sec-001.md"""
    scene_dir = project_dir / "chapters" / "vol-01" / "ch-001"
    scene_dir.mkdir(parents=True, exist_ok=True)
    scene_file = scene_dir / "sec-001.md"
    scene_file.write_text(SCENE_CONTENT, encoding="utf-8")
    return scene_file


class TestSceneWritingSmoke:
    """v0.1 烟雾测试 — 完整场景创作闭环"""

    @pytest.mark.asyncio
    async def test_full_scene_rewrite_loop(self, tmp_path):
        """完整闭环：创建项目 → 写场景 → 生成候选稿 → 采用 → 验证"""

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        project_id = "smoke-project"

        # ─── 1. 创建测试项目 ────────────────────────────
        project_dir = _make_project(workspace, project_id)
        assert project_dir.exists()

        fs = FileService(workspace)

        # ─── 2. 创建场景文件 ────────────────────────────
        scene_file = _make_scene_file(project_dir)
        assert scene_file.exists()

        scene_rel_path = "chapters/vol-01/ch-001/sec-001.md"
        full_scene_path = f"{project_id}/{scene_rel_path}"

        # ─── 3. 验证场景正文已写入（600-1000 字）─────────
        content, _, _ = await fs.read_file(full_scene_path)
        assert len(content) >= 600
        assert len(content) <= 1500  # 留余量

        # ─── 4. SceneService 路径解析 ────────────────────
        scene_svc = SceneService(fs)
        info = scene_svc.parse_scene_path(scene_rel_path)
        assert info.volume == 1
        assert info.chapter == 1
        assert info.scene == 1

        built_path = scene_svc.build_scene_path(1, 1, 1)
        assert built_path == scene_rel_path

        assert scene_svc.is_scene_file(scene_rel_path) is True
        assert scene_svc.is_scene_file("outline.md") is False

        # ─── 5. 生成候选稿（模拟 rewrite）───────────────
        candidate_svc = CandidateService(fs)

        rewritten_content = SCENE_CONTENT.replace(
            "夜色如墨",
            "夜色如墨，浓得化不开",
        ).replace(
            "她停下脚步",
            "她蓦然停下脚步",
        )
        # 确保改写后内容不同
        assert rewritten_content != SCENE_CONTENT

        candidate = await candidate_svc.create_candidate(
            project_id=project_id,
            source_path=scene_rel_path,
            action=CandidateAction.REWRITE,
            content=rewritten_content,
            model="fake-model",
            pipeline_id="rewrite",
        )

        # 验证候选稿创建
        assert candidate.id.startswith("cand_")
        assert candidate.project_id == project_id
        assert candidate.source_path == scene_rel_path
        assert candidate.base_hash != ""
        assert candidate.base_mtime is not None
        assert candidate.status.value == "pending"

        # ─── 6. 采用候选稿 ──────────────────────────────
        result = await candidate_svc.adopt_candidate(project_id, candidate.id)
        assert result == AdoptResult.SUCCESS

        # ─── 6a. 正文已被更新 ────────────────────────────
        updated_content, _, _ = await fs.read_file(full_scene_path)
        assert updated_content.strip() == rewritten_content.strip()
        assert "蓦然停下脚步" in updated_content

        # ─── 6b. candidate status 变为 adopted ───────────
        updated_candidate = await candidate_svc.get_candidate(project_id, candidate.id)
        assert updated_candidate.status.value == "adopted"
        assert updated_candidate.adopted_at is not None

        # ─── 6c. revision-log 已生成 ─────────────────────
        revision_log_dir = project_dir / "chapters" / "vol-01" / "ch-001" / "revision-log"
        assert revision_log_dir.exists(), f"revision-log 目录不存在: {revision_log_dir}"

        log_files = list(revision_log_dir.glob("*.json"))
        assert len(log_files) >= 1, "没有 revision-log 文件"

        log_data = json.loads(log_files[0].read_text(encoding="utf-8"))
        assert log_data["candidate_id"] == candidate.id
        assert log_data["source_path"] == scene_rel_path
        assert "word_count_before" in log_data
        assert "word_count_after" in log_data
        assert "adopted_at" in log_data

        # ─── 6d. 没有 project_id/project_id 路径 ────────
        # 检查候选稿的 source_path 不含双重 project_id
        assert candidate.source_path == scene_rel_path
        assert f"{project_id}/{project_id}" not in candidate.source_path
        assert f"{project_id}/{project_id}" not in candidate.candidate_path

        # 检查 revision-log 路径不含双重 project_id
        for log_file in log_files:
            log_rel = str(log_file.relative_to(project_dir))
            assert f"{project_id}/{project_id}" not in log_rel

    @pytest.mark.asyncio
    async def test_memory_update_after_adopt(self, tmp_path):
        """采用候选稿后，recent-context.md 被更新"""

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        project_id = "smoke-memory"
        project_dir = _make_project(workspace, project_id)
        _make_scene_file(project_dir)

        fs = FileService(workspace)
        memory_svc = MemoryService(fs)

        scene_rel_path = "chapters/vol-01/ch-001/sec-001.md"

        # 追加场景记忆
        summary = memory_svc.build_scene_memory_prompt_output(scene_rel_path, SCENE_CONTENT)
        await memory_svc.append_scene_memory(project_id, scene_rel_path, summary)

        # 验证 recent-context.md 更新
        rc_content = await memory_svc.read_recent_context(project_id)
        assert rc_content is not None
        assert len(rc_content) > 0
        # 记忆中包含场景标识（sec-001.md 或路径片段）
        assert "sec-001" in rc_content

        # 验证路径不含双重 project_id
        assert f"{project_id}/{project_id}" not in rc_content

    @pytest.mark.asyncio
    async def test_candidate_conflict_detection(self, tmp_path):
        """源文件被外部修改后，采用候选稿返回 conflict"""

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        project_id = "smoke-conflict"
        project_dir = _make_project(workspace, project_id)
        scene_file = _make_scene_file(project_dir)

        fs = FileService(workspace)
        candidate_svc = CandidateService(fs)

        scene_rel_path = "chapters/vol-01/ch-001/sec-001.md"

        # 创建候选稿
        candidate = await candidate_svc.create_candidate(
            project_id=project_id,
            source_path=scene_rel_path,
            action=CandidateAction.POLISH,
            content=SCENE_CONTENT + "\n\n润色后的内容。",
        )

        # 外部修改源文件
        scene_file.write_text(SCENE_CONTENT + "\n\n外部修改的内容。", encoding="utf-8")

        # 采用应返回 conflict
        result = await candidate_svc.adopt_candidate(project_id, candidate.id)
        assert result == AdoptResult.CONFLICT

        # 候选稿状态变为 rejected
        updated = await candidate_svc.get_candidate(project_id, candidate.id)
        assert updated.status.value == "rejected"

    @pytest.mark.asyncio
    async def test_file_updated_event_no_content(self):
        """file.updated 事件不包含 content"""

        evt = make_file_updated_event(
            project_id="test-project",
            path="chapters/vol-01/ch-001/sec-001.md",
            size=800,
            mtime=1700000000.0,
            source="smoke-test",
        )

        assert evt.type == EventType.FILE_UPDATED
        assert evt.project_id == "test-project"

        sse_dict = evt.to_sse_dict()
        assert "content" not in sse_dict, "file.updated 事件不应包含 content"
        assert sse_dict["payload"]["path"] == "chapters/vol-01/ch-001/sec-001.md"
        assert "content" not in sse_dict["payload"], "file.updated payload 不应包含 content"
        assert "path" in sse_dict
        assert "size" in sse_dict
        assert "mtime" in sse_dict
        assert "project_id" in sse_dict
        assert "event_id" in sse_dict

    @pytest.mark.asyncio
    async def test_scene_path_navigation(self, tmp_path):
        """场景路径导航：getNextScenePath 跨章/跨卷进位"""

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        fs = FileService(workspace)
        scene_svc = SceneService(fs)

        # 同章下一节
        next_path = scene_svc.get_next_scene_path("chapters/vol-01/ch-001/sec-003.md")
        info = scene_svc.parse_scene_path(next_path)
        assert info.scene == 4
        assert info.chapter == 1
        assert info.volume == 1

        # 当前 scene 已满 → 下一章 sec-001
        next_path = scene_svc.get_next_scene_path("chapters/vol-01/ch-001/sec-005.md")
        info = scene_svc.parse_scene_path(next_path)
        assert info.scene == 1
        assert info.chapter == 2
        assert info.volume == 1

        # 当前章已满 → 下一卷 ch-001/sec-001
        next_path = scene_svc.get_next_scene_path("chapters/vol-01/ch-012/sec-005.md")
        info = scene_svc.parse_scene_path(next_path)
        assert info.scene == 1
        assert info.chapter == 1
        assert info.volume == 2

    @pytest.mark.asyncio
    async def test_scene_is_empty_check(self, tmp_path):
        """SceneService.is_scene_empty 检测"""

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        project_id = "smoke-empty"
        project_dir = _make_project(workspace, project_id)

        fs = FileService(workspace)
        scene_svc = SceneService(fs)

        scene_rel_path = "chapters/vol-01/ch-001/sec-001.md"

        # 文件不存在 → 空
        assert await scene_svc.is_scene_empty(project_id, scene_rel_path) is True

        # 写入内容 → 非空
        _make_scene_file(project_dir)
        assert await scene_svc.is_scene_empty(project_id, scene_rel_path) is False

    @pytest.mark.asyncio
    async def test_pipeline_rewrite_with_mock_llm(self, tmp_path):
        """通过 PipelineRunner 执行 rewrite 管线（mock LLM）"""

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        project_id = "smoke-pipeline"
        project_dir = _make_project(workspace, project_id)
        _make_scene_file(project_dir)

        # 创建 prompt 文件
        prompts_dir = workspace / "prompts"
        pipeline_dir = prompts_dir / "pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)

        rewrite_yaml = pipeline_dir / "rewrite.yaml"
        rewrite_yaml.write_text(
            "name: rewrite\n"
            "label: 重写\n"
            "steps:\n"
            "  - id: rewrite\n"
            "    label: 重写场景\n"
            "    prompt: rewrite/scene\n"
            "    confirm: false\n",
            encoding="utf-8",
        )

        step_dir = prompts_dir / "rewrite"
        step_dir.mkdir(exist_ok=True)
        (step_dir / "scene.md").write_text(
            "请重写以下场景：\n\n{{ file_content }}",
            encoding="utf-8",
        )

        fs = FileService(workspace)

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.config.max_prompt_tokens = 120000
        mock_llm.config.context_window = 128000
        mock_llm.config.reserved_output_tokens = 8000

        async def mock_complete(*args, **kwargs):
            yield "这是重写后的场景内容，夜色如墨浓得化不开。"

        mock_llm.complete = mock_complete

        from backend.core.pipeline import PipelineRunner

        runner = PipelineRunner(
            prompts_path=prompts_dir,
            llm_service=mock_llm,
            file_service=fs,
        )

        scene_rel_path = "chapters/vol-01/ch-001/sec-001.md"

        # 运行管线
        events = []
        step_done_events = []
        async for event in runner.run(
            pipeline_name="rewrite",
            project_id=project_id,
            target_file=scene_rel_path,
        ):
            events.append(event)
            if event.get("event") == "step_done":
                step_done_events.append(event)

        # 验证管线产生了事件
        event_types = [e.get("event") for e in events]
        assert "thinking" in event_types
        assert "generation" in event_types
        assert "step_done" in event_types

        # 验证 rewrite 步骤完成
        assert len(step_done_events) >= 1
        step_data = step_done_events[0].get("data", "")
        if isinstance(step_data, str):
            step_data = json.loads(step_data)
        assert step_data.get("step_id") == "rewrite"
        assert step_data.get("status") == "done"

        # rewrite/polish 类高风险修改必须先生成候选稿，不直接覆盖正式场景。
        scene_file = project_dir / scene_rel_path
        assert scene_file.read_text(encoding="utf-8") == SCENE_CONTENT
        assert "candidate_created" in event_types

    @pytest.mark.asyncio
    async def test_pipeline_write_scene_existing_file_becomes_candidate(self, tmp_path):
        """write_scene 写已有 sec 文件时应转候选稿，不静默覆盖。"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        project_id = "smoke-write-scene"
        project_dir = _make_project(workspace, project_id)
        scene_file = _make_scene_file(project_dir)

        prompts_dir = workspace / "prompts"
        pipeline_dir = prompts_dir / "pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "generate.yaml").write_text(
            "name: generate\n"
            "label: 生成\n"
            "steps:\n"
            "  - id: draft\n"
            "    label: 生成场景\n"
            "    prompt: generate/scene\n"
            "    confirm: false\n",
            encoding="utf-8",
        )
        step_dir = prompts_dir / "generate"
        step_dir.mkdir(exist_ok=True)
        (step_dir / "scene.md").write_text("请写场景：{{ file_path }}", encoding="utf-8")

        fs = FileService(workspace)
        mock_llm = MagicMock()
        mock_llm.config.max_prompt_tokens = 120000
        mock_llm.config.context_window = 128000
        mock_llm.config.reserved_output_tokens = 8000

        async def mock_complete(*args, **kwargs):
            yield "这是新的第二版场景。"

        mock_llm.complete = mock_complete

        from backend.core.pipeline import PipelineRunner

        runner = PipelineRunner(prompts_path=prompts_dir, llm_service=mock_llm, file_service=fs)
        scene_rel_path = "chapters/vol-01/ch-001/sec-001.md"

        events = []
        async for event in runner.run(
            pipeline_name="generate",
            project_id=project_id,
            target_file=scene_rel_path,
            output_mode="write_scene",
        ):
            events.append(event)

        assert scene_file.read_text(encoding="utf-8") == SCENE_CONTENT
        assert "candidate_created" in [event.get("event") for event in events]
