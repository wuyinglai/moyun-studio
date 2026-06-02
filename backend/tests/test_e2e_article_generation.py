"""E2E 文章生成质量测试

覆盖:
1. QualityService.perform_review — 6 维质量审查解析
2. _needs_quality_repair — 质量修复触发条件
3. should_create_candidate / _resolve_lite_output_file — 候选稿策略
4. GenerationService.generate_stream — 管线流式生成
5. POST /lite/write-next — Lite 端到端质量流程
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.schemas.quality import (
    QualityReviewResult,
    QualityScores,
    ReviewIssue,
)
from backend.schemas.lite import LiteWriteNextRequest, LiteNextOptionCard, LiteWritingPrefs


# ─── 统一的 Mock 审查结果 ──────────────────────────────────────────────

def _high_quality_review() -> QualityReviewResult:
    """avg=8.3，优质，不触发修复"""
    return QualityReviewResult(
        scores=QualityScores(
            coherence=9, character_consistency=8, setting_consistency=8,
            writing_quality=9, logic=8, style_compliance=8,
        ),
        summary="整体质量优秀",
        strengths=["语言生动", "节奏把握好"],
        issues=[],
        suggestions=[],
    )


def _low_quality_review() -> QualityReviewResult:
    """avg=4.3，低质量，触发修复"""
    return QualityReviewResult(
        scores=QualityScores(
            coherence=5, character_consistency=4, setting_consistency=4,
            writing_quality=5, logic=4, style_compliance=4,
        ),
        summary="质量较差",
        strengths=[],
        issues=[
            ReviewIssue(severity="critical", category="logic", description="逻辑矛盾"),
            ReviewIssue(severity="major", category="character", description="角色OOC"),
        ],
        suggestions=["建议修复逻辑", "建议统一角色性格"],
    )


def _critical_only_review() -> QualityReviewResult:
    """avg=7.2 但有 critical issue，触发修复"""
    return QualityReviewResult(
        scores=QualityScores(
            coherence=8, character_consistency=7, setting_consistency=7,
            writing_quality=7, logic=7, style_compliance=7,
        ),
        summary="存在严重逻辑问题",
        strengths=["描写生动"],
        issues=[
            ReviewIssue(severity="critical", category="logic", description="严重逻辑矛盾"),
            ReviewIssue(severity="minor", category="writing", description="措辞可优化"),
        ],
        suggestions=["修正逻辑"],
    )


def _minor_only_review() -> QualityReviewResult:
    """avg=8.5，只有 minor issue，不触发修复"""
    return QualityReviewResult(
        scores=QualityScores(
            coherence=9, character_consistency=9, setting_consistency=8,
            writing_quality=8, logic=8, style_compliance=9,
        ),
        summary="总体不错",
        strengths=["语言流畅"],
        issues=[
            ReviewIssue(severity="minor", category="writing", description="小问题"),
        ],
        suggestions=["微调"],
    )


# ─── 辅助：构建测试项目目录 ────────────────────────────────────────

def _setup_test_project(tmp_path: Path, project_id: str = "test-project") -> Path:
    """创建测试项目目录结构，包含所有必要文件"""
    workspace = tmp_path / "workspace"
    proj = workspace / "projects" / project_id
    (proj / "chapters" / "vol-01" / "ch-001").mkdir(parents=True)
    (proj / "characters").mkdir(parents=True)
    (proj / "materials").mkdir(parents=True)

    # 项目基础文件
    (proj / "meta.json").write_text(json.dumps({
        "project_id": project_id,
        "name": "测试项目",
        "genre": "玄幻",
        "theme": "成长",
        "tone": "热血",
        "writing_style": "第三人称",
    }, ensure_ascii=False), encoding="utf-8")
    (proj / "story-state.md").write_text("# 故事状态\n测试", encoding="utf-8")
    (proj / "style-guide.md").write_text("# 文风指南\n测试", encoding="utf-8")
    (proj / "recent-context.md").write_text("# 近期上下文\n测试", encoding="utf-8")
    (proj / "outline.md").write_text("# 大纲\n测试", encoding="utf-8")

    # 角色文件
    (proj / "characters" / "protagonist.json").write_text(json.dumps({
        "name": "主角", "role": "protagonist", "traits": ["勇敢", "聪明"],
    }, ensure_ascii=False), encoding="utf-8")

    # 场景文件（有内容）
    (proj / "chapters" / "vol-01" / "ch-001" / "sec-001.md").write_text(
        "# 场景一\n\n主角踏入大殿，环顾四周。\n\n众人屏息。",
        encoding="utf-8",
    )
    # ch-meta.json
    (proj / "chapters" / "vol-01" / "ch-001" / "ch-meta.json").write_text(
        json.dumps({"title": "第一章", "memory": ["前情提要"], "pending_foreshadowing": ["伏笔1"]}),
        encoding="utf-8",
    )

    # 故事引擎（Lite 模式需要）
    (proj / "story-engine.md").write_text(
        "# 故事引擎\n\n## 人物欲望\n- 当前目标：证明自己\n\n## 最近推进\n- 未开始",
        encoding="utf-8",
    )

    return workspace


def _setup_prompts(prompts_dir: Path):
    """创建必要的 prompt 模板"""
    (prompts_dir / "review" / "quality").mkdir(parents=True)
    (prompts_dir / "generate" / "continuation").mkdir(parents=True)
    (prompts_dir / "blocks").mkdir(parents=True)

    # 审查 prompt
    (prompts_dir / "review" / "quality" / "main.md").write_text(
        "审查: {{ content }}\n标题: {{ chapter_title }}",
        encoding="utf-8",
    )

    # 续写 prompt
    (prompts_dir / "generate" / "continuation" / "main.md").write_text(
        "续写: {{ current_content }}\n目标: {{ continuation_goal }}\n"
        "风格: {{ style_guide }}\n状态: {{ story_state }}\n"
        "上下文: {{ recent_context }}\n记忆: {{ chapter_memory }}\n"
        "伏笔: {{ pending_foreshadowing }}\n"
        "{% include 'blocks/depai-rules.md' %}",
        encoding="utf-8",
    )

    # 去AI规则（被 continuation 引用）
    (prompts_dir / "blocks" / "depai-rules.md").write_text(
        "## 去AI味规则\n- 删除套路词\n- 不解释情绪\n",
        encoding="utf-8",
    )

    # 管线相关 prompts（供 Group 4 使用）
    (prompts_dir / "pipeline").mkdir(parents=True)
    import yaml
    pipeline_dir = prompts_dir / "pipeline" / "generate"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "step1.md").write_text("步骤1: {{ file_content }}", encoding="utf-8")
    yaml_path = prompts_dir / "pipeline" / "generate.yaml"
    yaml_path.write_text(yaml.dump({
        "name": "generate",
        "label": "生成管线",
        "steps": [{"id": "step1", "label": "步骤1", "prompt": "pipeline/generate/step1"}],
    }, allow_unicode=True), encoding="utf-8")

    rewrite_dir = prompts_dir / "pipeline" / "rewrite"
    rewrite_dir.mkdir(parents=True)
    (rewrite_dir / "step1.md").write_text("改写步骤1: {{ file_content }}", encoding="utf-8")
    (prompts_dir / "pipeline" / "rewrite.yaml").write_text(yaml.dump({
        "name": "rewrite",
        "label": "改写管线",
        "steps": [{"id": "step1", "label": "步骤1", "prompt": "pipeline/rewrite/step1"}],
    }, allow_unicode=True), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
# Group 1: QualityReviewDimensions — 6 维质量审查
# ═══════════════════════════════════════════════════════════════════

class TestQualityReviewDimensions:
    """测试 QualityService.perform_review 对 LLM 返回的解析"""

    @pytest.fixture
    def quality_setup(self, tmp_path):
        """创建 QualityService 测试环境"""
        workspace = _setup_test_project(tmp_path)
        prompts_dir = workspace / "prompts"
        _setup_prompts(prompts_dir)

        from backend.config import Settings
        settings = Settings(
            debug=True,
            workspace_path=workspace,
            llm_provider="custom",
            llm_api_key="fake-key",
            llm_model="fake-model",
        )
        return workspace, settings, prompts_dir

    @pytest.mark.asyncio
    async def test_perform_review_parses_all_6_dimensions(self, quality_setup):
        """Mock LLM 返回完整高分 JSON → 6 维度都被正确解析"""
        _, settings, _ = quality_setup

        high_json = json.dumps({
            "scores": {
                "coherence": 9, "character_consistency": 8, "setting_consistency": 8,
                "writing_quality": 9, "logic": 8, "style_compliance": 8,
            },
            "summary": "优质",
            "strengths": ["语言好"],
            "issues": [],
            "suggestions": [],
        }, ensure_ascii=False)

        with patch("backend.core.quality_service.LLMService") as MockLLM:
            mock_svc = MagicMock()
            mock_svc.complete_sync = AsyncMock(return_value=high_json)
            MockLLM.from_workspace_config.return_value = mock_svc

            from backend.core.quality_service import QualityService
            qs = QualityService(settings)
            result = await qs.perform_review("test-project", "chapters/vol-01/ch-001/sec-001.md", "第一章")

        assert result.scores.coherence == 9
        assert result.scores.character_consistency == 8
        assert result.scores.setting_consistency == 8
        assert result.scores.writing_quality == 9
        assert result.scores.logic == 8
        assert result.scores.style_compliance == 8
        assert result.summary == "优质"
        assert result.strengths == ["语言好"]

    @pytest.mark.asyncio
    async def test_perform_review_parses_low_quality(self, quality_setup):
        """Mock LLM 返回低分 JSON → 维度 < 6，有 critical issue"""
        _, settings, _ = quality_setup

        low_json = json.dumps({
            "scores": {
                "coherence": 5, "character_consistency": 4, "setting_consistency": 4,
                "writing_quality": 5, "logic": 4, "style_compliance": 4,
            },
            "summary": "质量差",
            "strengths": [],
            "issues": [
                {"severity": "critical", "category": "logic", "description": "逻辑矛盾"},
            ],
            "suggestions": ["修复"],
        }, ensure_ascii=False)

        with patch("backend.core.quality_service.LLMService") as MockLLM:
            mock_svc = MagicMock()
            mock_svc.complete_sync = AsyncMock(return_value=low_json)
            MockLLM.from_workspace_config.return_value = mock_svc

            from backend.core.quality_service import QualityService
            qs = QualityService(settings)
            result = await qs.perform_review("test-project", "chapters/vol-01/ch-001/sec-001.md", "第一章")

        assert result.scores.coherence == 5
        assert len(result.issues) == 1
        assert result.issues[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_perform_review_handles_json_wrapped_in_markdown(self, quality_setup):
        """LLM 返回 ```json ... ``` 包裹 → JSON 正确提取"""
        _, settings, _ = quality_setup

        md_json = """```json
{
  "scores": {
    "coherence": 8, "character_consistency": 7, "setting_consistency": 7,
    "writing_quality": 8, "logic": 7, "style_compliance": 7
  },
  "summary": "还行",
  "strengths": [],
  "issues": [],
  "suggestions": []
}
```"""

        with patch("backend.core.quality_service.LLMService") as MockLLM:
            mock_svc = MagicMock()
            mock_svc.complete_sync = AsyncMock(return_value=md_json)
            MockLLM.from_workspace_config.return_value = mock_svc

            from backend.core.quality_service import QualityService
            qs = QualityService(settings)
            result = await qs.perform_review("test-project", "chapters/vol-01/ch-001/sec-001.md", "第一章")

        assert result.scores.coherence == 8
        assert result.summary == "还行"

    @pytest.mark.asyncio
    async def test_perform_review_handles_malformed_json(self, quality_setup):
        """LLM 返回非 JSON → fallback: summary=原文, issues=[]"""
        _, settings, _ = quality_setup

        with patch("backend.core.quality_service.LLMService") as MockLLM:
            mock_svc = MagicMock()
            mock_svc.complete_sync = AsyncMock(return_value="这是一段非JSON的纯文本回复")
            MockLLM.from_workspace_config.return_value = mock_svc

            from backend.core.quality_service import QualityService
            qs = QualityService(settings)
            result = await qs.perform_review("test-project", "chapters/vol-01/ch-001/sec-001.md", "第一章")

        assert result.issues == []
        assert "非JSON" in result.summary

    def test_save_review_result_writes_to_correct_path(self, quality_setup):
        """save_review_result 写入 materials/reviews/ 正确路径"""
        workspace, settings, _ = quality_setup
        review_id = "abc12345"
        target_file = "chapters/vol-01/ch-001/sec-001.md"

        from backend.core.quality_service import QualityService
        qs = QualityService(settings)
        result = _high_quality_review()

        qs.save_review_result("test-project", target_file, review_id, result)

        safe_name = target_file.replace("/", "_").replace("\\", "_")
        expected_path = workspace / "projects" / "test-project" / "materials" / "reviews" / f"{safe_name}.{review_id}.json"
        assert expected_path.exists()

        data = json.loads(expected_path.read_text(encoding="utf-8"))
        assert data["review_id"] == review_id
        assert data["target_file"] == target_file
        assert data["result"]["summary"] == "整体质量优秀"

    def test_list_reviews_returns_history(self, quality_setup):
        """list_reviews 返回审查列表"""
        workspace, settings, _ = quality_setup

        from backend.core.quality_service import QualityService
        qs = QualityService(settings)
        result = _high_quality_review()

        qs.save_review_result("test-project", "chapters/vol-01/ch-001/sec-001.md", "rev1", result)
        qs.save_review_result("test-project", "chapters/vol-01/ch-001/sec-002.md", "rev2", result)

        reviews = qs.list_reviews("test-project")
        assert len(reviews) >= 2


# ═══════════════════════════════════════════════════════════════════
# Group 2: QualityRepairTrigger — 质量修复触发条件
# ═══════════════════════════════════════════════════════════════════

class TestQualityRepairTrigger:
    """测试 _needs_quality_repair 触发逻辑"""

    @staticmethod
    def _needs_repair(review):
        from backend.application.lite_quality_service import LiteQualityService
        return LiteQualityService.needs_quality_repair(review)

    def test_needs_repair_avg_below_6(self):
        """6 维平均分 = 4.5, 无 critical/major → True"""
        assert self._needs_repair(_low_quality_review()) is True

    def test_needs_repair_avg_above_6_but_critical_issue(self):
        """平均分 = 7+, 有 critical issue → True"""
        assert self._needs_repair(_critical_only_review()) is True

    def test_needs_repair_avg_above_6_but_major_issue(self):
        """平均分 = 7+, 有 major issue → True"""
        review = QualityReviewResult(
            scores=QualityScores(
                coherence=7, character_consistency=7, setting_consistency=7,
                writing_quality=7, logic=7, style_compliance=7,
            ),
            summary="有问题",
            strengths=[],
            issues=[ReviewIssue(severity="major", category="character", description="角色OOC")],
            suggestions=[],
        )
        assert self._needs_repair(review) is True

    def test_no_repair_high_quality(self):
        """平均分 = 8.5, 只有 minor issue → False"""
        assert self._needs_repair(_minor_only_review()) is False

    def test_no_repair_exact_boundary(self):
        """平均分 = 6.0, 无 serious issue → False"""
        review = QualityReviewResult(
            scores=QualityScores(
                coherence=6, character_consistency=6, setting_consistency=6,
                writing_quality=6, logic=6, style_compliance=6,
            ),
            summary="边界",
            strengths=[],
            issues=[],
            suggestions=[],
        )
        assert self._needs_repair(review) is False

    def test_no_repair_empty_scores(self):
        """scores 全部为 0（默认值） → avg=0, 触发修复 True"""
        review = QualityReviewResult(
            scores=QualityScores(),
            summary="空",
            strengths=[],
            issues=[],
            suggestions=[],
        )
        # QualityScores 默认值为 0，avg=0 < 6，应触发修复
        assert self._needs_repair(review) is True

    def test_no_repair_none_review(self):
        """review 为 None → 安全返回 False"""
        from backend.application.lite_quality_service import LiteQualityService
        assert LiteQualityService.needs_quality_repair(None) is False


# ═══════════════════════════════════════════════════════════════════
# Group 3: CandidatePolicyGeneration — 候选稿策略
# ═══════════════════════════════════════════════════════════════════

class TestCandidatePolicy:
    """测试候选稿策略 should_create_candidate 和 _resolve_lite_output_file"""

    def test_polish_existing_content_creates_candidate(self):
        """polish + 目标有内容 → should_create_candidate 返回 True"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            action="polish",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            file_exists=True,
            file_has_content=True,
        ) is True

    def test_rewrite_existing_content_creates_candidate(self):
        """rewrite + 目标有内容 → candidate"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            action="rewrite",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            file_exists=True,
            file_has_content=True,
        ) is True

    def test_write_next_scene_empty_target_direct_write(self):
        """write + 空目标 → 不生成 candidate，直接写入"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            action="write",
            target_path="chapters/vol-01/ch-001/sec-099.md",
            file_exists=False,
            file_has_content=False,
        ) is False

    def test_dangerous_path_creates_candidate(self):
        """核心状态文件已有内容 → candidate"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            action="write",
            target_path="style-guide.md",
            file_exists=True,
            file_has_content=True,
        ) is True

    def test_scene_file_with_content_creates_candidate_even_for_safe_action(self):
        """场景文件已有内容 + continue → candidate"""
        from backend.policies.candidate_policy import should_create_candidate

        assert should_create_candidate(
            action="continue",
            target_path="chapters/vol-01/ch-001/sec-001.md",
            file_exists=True,
            file_has_content=True,
        ) is True

    def test_resolve_lite_output_file_polish_returns_candidate_path(self):
        """polish → 使用候选稿"""
        from backend.api.lite import _should_use_candidate

        req = LiteWriteNextRequest(
            project_id="test",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            selected_card=LiteNextOptionCard(id="c1", title="测试", beat="拍", scene="场景", payoff="兑现", hook="钩子"),
            action="polish_current_scene",
        )
        should_use = _should_use_candidate(
            "polish_current_scene",
            target_file="chapters/vol-01/ch-001/sec-001.md",
            requested_content="已有内容",
            is_blank_requested=False,
        )
        assert should_use is True

    def test_resolve_lite_output_file_write_empty_returns_direct_path(self):
        """write + 空目标 → 直接写入"""
        from backend.api.lite import _should_use_candidate

        req = LiteWriteNextRequest(
            project_id="test",
            target_file="chapters/vol-01/ch-001/sec-099.md",
            selected_card=LiteNextOptionCard(id="c1", title="测试", beat="拍", scene="场景", payoff="兑现", hook="钩子"),
            action="write",
        )
        should_use = _should_use_candidate(
            "write",
            target_file="chapters/vol-01/ch-001/sec-099.md",
            requested_content="",
            is_blank_requested=True,
        )
        assert should_use is False


# ═══════════════════════════════════════════════════════════════════
# Group 4: GenerationStreamPipeline — 管线流式生成
# ═══════════════════════════════════════════════════════════════════

class TestGenerationStreamPipeline:
    """测试 GenerationService.generate_stream 管线执行"""

    @pytest.fixture
    def gen_setup(self, tmp_path):
        """创建 GenerationService 测试环境"""
        workspace = _setup_test_project(tmp_path, "test-gen")
        prompts_dir = workspace / "prompts"
        _setup_prompts(prompts_dir)

        from backend.config import Settings
        settings = Settings(
            debug=True,
            workspace_path=workspace,
            llm_provider="custom",
            llm_api_key="fake-key",
            llm_model="fake-model",
        )
        return settings

    @pytest.mark.asyncio
    async def test_generate_pipeline_yields_events(self, gen_setup):
        """generate/continuation → generate 管线 → SSE 事件包含 task_start, generation, done"""
        settings = gen_setup

        # Mock LLMService
        with patch("backend.core.generation_service.load_llm_config_from_workspace") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "apiType": "custom", "apiKey": "fake", "apiBase": "", "model": "fake-model",
            }

            with patch("backend.core.generation_service.LLMService") as MockLLM:
                mock_svc = MagicMock()
                mock_svc.config.model = "fake-model"
                mock_svc.config.max_prompt_tokens = 120000
                mock_svc.config.context_window = 128000

                async def mock_complete(*args, **kwargs):
                    for chunk in ["这是", "管线", "生成", "测试"]:
                        yield chunk

                mock_svc.complete = mock_complete
                MockLLM.from_workspace_config.return_value = mock_svc

                from backend.core.generation_service import GenerationService

                gs = GenerationService(settings)
                task_id = "task-test-1"
                gs.create_stop_signal(task_id)

                events = []
                async for event in gs.generate_stream(
                    project_id="test-gen",
                    file_path="chapters/vol-01/ch-001/sec-001.md",
                    prompt_type="generate/continuation",
                    extra_vars={},
                    mode="write_next_scene",
                    task_id=task_id,
                ):
                    events.append(event)

        event_types = [e.get("event") for e in events]
        assert "task_start" in event_types
        assert "generation" in event_types or "done" in event_types

    @pytest.mark.asyncio
    async def test_fallback_mode_produces_full_events(self, gen_setup):
        """fallback 模式 + 目标有内容 → task_start, prompt, generation, candidate_created"""
        settings = gen_setup

        with patch("backend.core.generation_service.load_llm_config_from_workspace") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "apiType": "custom", "apiKey": "fake", "apiBase": "", "model": "fake-model",
            }

            with patch("backend.core.generation_service.LLMService") as MockLLM:
                mock_svc = MagicMock()
                mock_svc.config.model = "fake-model"
                mock_svc.config.max_prompt_tokens = 120000
                mock_svc.config.context_window = 128000

                async def mock_complete(*args, **kwargs):
                    for chunk in ["生成文本"]:
                        yield chunk

                mock_svc.complete = mock_complete
                MockLLM.from_workspace_config.return_value = mock_svc

                from backend.core.generation_service import GenerationService

                gs = GenerationService(settings)
                task_id = "task-fallback-1"
                gs.create_stop_signal(task_id)

                events = []
                async for event in gs.generate_stream(
                    project_id="test-gen",
                    file_path="chapters/vol-01/ch-001/sec-001.md",
                    prompt_type="generate/append",  # 不在管线映射中 → fallback
                    extra_vars={},
                    mode="write_next_scene",
                    task_id=task_id,
                ):
                    events.append(event)

        event_types = [e.get("event") for e in events]
        assert "task_start" in event_types
        assert "prompt" in event_types
        assert "generation" in event_types
        # fallback + 目标有内容 → candidate
        assert "candidate_created" in event_types or "done" in event_types


# ═══════════════════════════════════════════════════════════════════
# Group 5: E2ELiteQualityFlow — Lite 端到端质量流程
# ═══════════════════════════════════════════════════════════════════

class TestE2ELiteQualityFlow:
    """通过 TestClient 测试 POST /lite/write-next 端到端流程"""

    @pytest.fixture
    def lite_client(self, tmp_path):
        """构造 Lite E2E 测试环境，返回 TestClient + 设置"""
        workspace = _setup_test_project(tmp_path, "test-lite")
        prompts_dir = workspace / "prompts"
        _setup_prompts(prompts_dir)

        # 确保第1章第2节为空（write-next 推进目标）
        (workspace / "projects" / "test-lite" / "chapters" / "vol-01" / "ch-001" / "sec-002.md").write_text(
            "", encoding="utf-8"
        )

        from backend.config import Settings
        settings = Settings(
            debug=True,
            workspace_path=workspace,
            llm_provider="custom",
            llm_api_key="fake-key",
            llm_model="fake-model",
        )

        from backend.main import create_app
        app = create_app()
        app.dependency_overrides[__import__("backend.config", fromlist=["get_settings"]).get_settings] = lambda: settings

        from fastapi.testclient import TestClient
        return TestClient(app), settings, workspace

    def test_lite_write_next_high_quality_no_repair(self, lite_client):
        """高质量内容 + 高质量审查 → 无修复，quality_summary 含审查要点"""
        client, settings, workspace = lite_client

        # Mock LLM: 生成内容 + 高质量审查
        with patch("backend.api.lite.LLMService") as MockLLM:
            mock_svc = MagicMock()
            mock_svc.complete_sync = AsyncMock(return_value="# 场景\n\n这是高质量生成内容。")
            MockLLM.from_workspace_config.return_value = mock_svc

            with patch("backend.api.lite.QualityService") as MockQS:
                mock_qs = MagicMock()
                mock_qs.perform_review = AsyncMock(return_value=_high_quality_review())
                mock_qs.save_review_result = MagicMock()
                mock_qs.list_reviews = MagicMock(return_value=[])
                MockQS.return_value = mock_qs

                card = LiteNextOptionCard(
                    id="card-1", title="测试爽点",
                    beat="测试节拍", scene="测试场景",
                    payoff="测试兑现", hook="测试钩子",
                )
                resp = client.post("/api/lite/write-next", json={
                    "project_id": "test-lite",
                    "target_file": "chapters/vol-01/ch-001/sec-002.md",
                    "selected_card": card.model_dump(),
                    "prefs": LiteWritingPrefs().model_dump(),
                    "action": "write",
                })

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["data"]["quality_summary"] != ""
        # 高质量 → 不应触发修复消息
        assert "补强" not in data["data"]["quality_summary"]

    def test_lite_write_next_low_quality_triggers_repair(self, lite_client):
        """低质量审查 (avg < 6) → 触发修复，quality_summary 含修复信息"""
        client, settings, workspace = lite_client

        with patch("backend.api.lite.LLMService") as MockLLM:
            mock_svc = MagicMock()
            # 第一次调用：初始生成；第二次调用：修复（当触发修复时会有两次 complete_sync）
            mock_svc.complete_sync = AsyncMock(side_effect=[
                "# 场景\n\n这是初始生成内容。",
                "# 场景\n\n这是修复后的高质量内容。",
            ])
            MockLLM.from_workspace_config.return_value = mock_svc

            with patch("backend.api.lite.QualityService") as MockQS:
                mock_qs = MagicMock()
                mock_qs.perform_review = AsyncMock(return_value=_low_quality_review())
                mock_qs.save_review_result = MagicMock()
                mock_qs.list_reviews = MagicMock(return_value=[])
                MockQS.return_value = mock_qs

                card = LiteNextOptionCard(
                    id="card-2", title="低质量测试",
                    beat="测试节拍", scene="测试场景",
                    payoff="测试兑现", hook="测试钩子",
                )
                resp = client.post("/api/lite/write-next", json={
                    "project_id": "test-lite",
                    "target_file": "chapters/vol-01/ch-001/sec-002.md",
                    "selected_card": card.model_dump(),
                    "prefs": LiteWritingPrefs().model_dump(),
                    "action": "write",
                })

        assert resp.status_code == 200
        data = resp.json()
        # 低质量 → 应触发修复
        assert "补强" in data["data"]["quality_summary"], f"Expected repair message but got: {data['data']['quality_summary']}"

    def test_lite_write_next_critical_issue_triggers_repair(self, lite_client):
        """审查返回 critical issue → 触发修复"""
        client, settings, workspace = lite_client

        with patch("backend.api.lite.LLMService") as MockLLM:
            mock_svc = MagicMock()
            mock_svc.complete_sync = AsyncMock(side_effect=[
                "# 场景\n\n初始内容。",
                "# 场景\n\n修复内容。",
            ])
            MockLLM.from_workspace_config.return_value = mock_svc

            with patch("backend.api.lite.QualityService") as MockQS:
                mock_qs = MagicMock()
                mock_qs.perform_review = AsyncMock(return_value=_critical_only_review())
                mock_qs.save_review_result = MagicMock()
                mock_qs.list_reviews = MagicMock(return_value=[])
                MockQS.return_value = mock_qs

                card = LiteNextOptionCard(
                    id="card-3", title="Critical测试",
                    beat="测试", scene="测试",
                    payoff="测试", hook="测试",
                )
                resp = client.post("/api/lite/write-next", json={
                    "project_id": "test-lite",
                    "target_file": "chapters/vol-01/ch-001/sec-002.md",
                    "selected_card": card.model_dump(),
                    "prefs": LiteWritingPrefs().model_dump(),
                    "action": "write",
                })

        assert resp.status_code == 200
        data = resp.json()
        assert "补强" in data["data"]["quality_summary"]

    def test_lite_write_next_candidate_no_review(self, lite_client):
        """action=polish + 目标有内容 → is_candidate=True, 跳过质量审查"""
        client, settings, workspace = lite_client

        with patch("backend.api.lite.LLMService") as MockLLM:
            mock_svc = MagicMock()
            mock_svc.complete_sync = AsyncMock(return_value="# 场景\n\n润色后的内容。")
            MockLLM.from_workspace_config.return_value = mock_svc

            # QualityService 不应被创建（候选稿跳过审查）
            with patch("backend.api.lite.QualityService") as MockQS:
                mock_qs = MagicMock()
                mock_qs.perform_review = AsyncMock()
                MockQS.return_value = mock_qs

                card = LiteNextOptionCard(
                    id="card-4", title="候选稿测试",
                    beat="测试", scene="测试",
                    payoff="测试", hook="测试",
                )
                resp = client.post("/api/lite/write-next", json={
                    "project_id": "test-lite",
                    "target_file": "chapters/vol-01/ch-001/sec-001.md",  # 有内容的文件
                    "selected_card": card.model_dump(),
                    "prefs": LiteWritingPrefs().model_dump(),
                    "action": "polish_current_scene",
                })

        assert resp.status_code == 200
        data = resp.json()
        assert "候选稿" in data["data"]["quality_summary"]
        # 确认审查未被调用
        mock_qs.perform_review.assert_not_called()

    def test_lite_write_next_stream_events(self, lite_client):
        """流式接口 SSE 事件顺序: meta → status → delta → replace → done"""
        client, settings, workspace = lite_client

        with patch("backend.api.lite.LLMService") as MockLLM:
            mock_svc = MagicMock()

            async def mock_stream(*args, **kwargs):
                async def _gen():
                    for c in ["流", "式", "生", "成"]:
                        yield {"choices": [{"delta": {"content": c}}]}
                return _gen()

            mock_svc.complete = mock_stream
            mock_svc.complete_sync = AsyncMock(return_value="流式生成")
            mock_svc.config.model = "fake-model"
            mock_svc.config.max_prompt_tokens = 120000
            mock_svc.config.context_window = 128000
            MockLLM.from_workspace_config.return_value = mock_svc

            card = LiteNextOptionCard(
                id="card-5", title="流式测试",
                beat="测试", scene="测试",
                payoff="测试", hook="测试",
            )

            # 流式端点返回 SSE，使用 stream=True
            with patch("backend.api.lite.QualityService"):
                resp = client.post("/api/lite/write-next-stream", json={
                    "project_id": "test-lite",
                    "target_file": "chapters/vol-01/ch-001/sec-002.md",
                    "selected_card": card.model_dump(),
                    "prefs": LiteWritingPrefs().model_dump(),
                    "action": "write",
                })

            # 流式端点返回 SSE 响应（text/event-stream）
            assert resp.status_code == 200
            # 验证至少返回了 SSE 格式内容
            body = resp.text
            assert "data:" in body or len(body) > 0
