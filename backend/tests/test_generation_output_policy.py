"""墨韵 - 生成输出策略测试

覆盖 CandidatePolicy 和 GenerationOutputPolicy 的核心规则。
"""

import pytest

from backend.policies.candidate_policy import (
    should_create_candidate,
    is_scene_file as candidate_is_scene_file,
    is_core_state_file,
    HIGH_RISK_ACTIONS,
    SAFE_ACTIONS,
)
from backend.policies.generation_output_policy import (
    decide_output,
    is_dangerous_output,
    is_scene_file,
    OutputDecision,
)


# ═══════════════════════════════════════════════════════════
# CandidatePolicy 测试
# ═══════════════════════════════════════════════════════════


class TestShouldCreateCandidate:
    """should_create_candidate 契约测试"""

    # ── 高风险操作 → candidate ─────────────────────────

    @pytest.mark.parametrize("action", HIGH_RISK_ACTIONS)
    def test_high_risk_actions_always_candidate(self, action: str):
        """rewrite / polish / chat_edit / more_exciting / more_reasonable → candidate"""
        assert should_create_candidate(action, "chapters/vol-01/ch-001/sec-001.md", True, True) is True
        # 即使目标为空，高风险操作也生成 candidate
        assert should_create_candidate(action, "chapters/vol-01/ch-001/sec-001.md", False, False) is True

    def test_rewrite_current_sec(self):
        """rewrite 当前 sec → candidate"""
        assert should_create_candidate("rewrite", "chapters/vol-01/ch-001/sec-001.md", True, True) is True

    def test_polish_current_sec(self):
        """polish 当前 sec → candidate"""
        assert should_create_candidate("polish", "chapters/vol-01/ch-001/sec-001.md", True, True) is True

    def test_more_exciting(self):
        """more_exciting → candidate"""
        assert should_create_candidate("more_exciting", "chapters/vol-01/ch-001/sec-003.md", True, True) is True

    def test_more_reasonable(self):
        """more_reasonable → candidate"""
        assert should_create_candidate("more_reasonable", "chapters/vol-01/ch-001/sec-003.md", True, True) is True

    # ── 安全操作 → 直接写入 ────────────────────────────

    def test_write_new_scene_empty_sec(self):
        """write_new_scene 空 sec → 直接写入"""
        assert should_create_candidate("write_new_scene", "chapters/vol-01/ch-001/sec-001.md", False, False) is False

    def test_write_empty_sec(self):
        """write 空 sec → 直接写入"""
        assert should_create_candidate("write", "chapters/vol-01/ch-001/sec-001.md", False, False) is False

    # ── write_next_scene / write_current_scene ──────────

    def test_write_next_scene_empty(self):
        """write_next_scene 空 sec → 直接写入"""
        assert should_create_candidate("write_next_scene", "chapters/vol-01/ch-001/sec-001.md", False, False) is False

    def test_write_next_scene_with_content(self):
        """write_next_scene 已有内容 → candidate"""
        assert should_create_candidate("write_next_scene", "chapters/vol-01/ch-001/sec-001.md", True, True) is True

    def test_write_current_scene_empty(self):
        """write_current_scene 空 sec → 直接写入"""
        assert should_create_candidate("write_current_scene", "chapters/vol-01/ch-001/sec-001.md", False, False) is False

    def test_write_current_scene_with_content(self):
        """write_current_scene 已有内容 → candidate"""
        assert should_create_candidate("write_current_scene", "chapters/vol-01/ch-001/sec-001.md", True, True) is True

    # ── rewrite_current_scene / polish_current_scene ────

    def test_rewrite_current_scene_always_candidate(self):
        """rewrite_current_scene → candidate（即使目标为空）"""
        assert should_create_candidate("rewrite_current_scene", "chapters/vol-01/ch-001/sec-001.md", True, True) is True
        assert should_create_candidate("rewrite_current_scene", "chapters/vol-01/ch-001/sec-001.md", False, False) is True

    def test_polish_current_scene_always_candidate(self):
        """polish_current_scene → candidate（即使目标为空）"""
        assert should_create_candidate("polish_current_scene", "chapters/vol-01/ch-001/sec-001.md", True, True) is True
        assert should_create_candidate("polish_current_scene", "chapters/vol-01/ch-001/sec-001.md", False, False) is True

    def test_extract_materials(self):
        """extract → 直接写入"""
        assert should_create_candidate("extract", "materials/extracted/characters.md", True, True) is False

    # ── 场景文件已有内容 → candidate ────────────────────

    def test_scene_file_with_content(self):
        """场景文件已有内容 → candidate"""
        assert should_create_candidate("continue", "chapters/vol-01/ch-001/sec-001.md", True, True) is True

    def test_scene_file_empty(self):
        """场景文件为空 → 直接写入"""
        assert should_create_candidate("continue", "chapters/vol-01/ch-001/sec-001.md", True, False) is False

    # ── 核心状态文件 ────────────────────────────────────

    def test_story_state_with_content(self):
        """story-state.md 已有内容 → candidate"""
        assert should_create_candidate("update", "story-state.md", True, True) is True

    def test_recent_context_with_content(self):
        """recent-context.md 已有内容 → candidate"""
        assert should_create_candidate("update", "recent-context.md", True, True) is True

    def test_style_guide_with_content(self):
        """style-guide.md 已有内容 → candidate"""
        assert should_create_candidate("update", "style-guide.md", True, True) is True

    # ── append/continue 且目标为空 ─────────────────────

    def test_continue_empty_target(self):
        """continue 空 sec → 直接写入"""
        assert should_create_candidate("continue", "chapters/vol-01/ch-001/sec-001.md", False, False) is False

    def test_append_empty_target(self):
        """append 空 sec → 直接写入"""
        assert should_create_candidate("append", "chapters/vol-01/ch-001/sec-001.md", False, False) is False

    # ── 兜底 ───────────────────────────────────────────

    def test_unknown_action_with_content(self):
        """未知操作 + 有内容 → candidate（兜底）"""
        assert should_create_candidate("unknown_action", "some/file.md", True, True) is True

    def test_unknown_action_no_content(self):
        """未知操作 + 无内容 → 直接写入"""
        assert should_create_candidate("unknown_action", "some/file.md", False, False) is False


class TestIsSceneFile:
    """is_scene_file 测试"""

    def test_standard_scene(self):
        assert candidate_is_scene_file("chapters/vol-01/ch-001/sec-001.md") is True

    def test_high_number_scene(self):
        assert candidate_is_scene_file("chapters/vol-12/ch-123/sec-999.md") is True

    def test_ch_plan_not_scene(self):
        assert candidate_is_scene_file("chapters/vol-01/ch-001/ch-plan.md") is False

    def test_random_file(self):
        assert candidate_is_scene_file("story-state.md") is False


class TestIsCoreStateFile:
    """is_core_state_file 测试"""

    @pytest.mark.parametrize("filename", [
        "story-state.md", "recent-context.md", "style-guide.md",
        "outline.md", "story-engine.md", "meta.json",
    ])
    def test_core_files(self, filename: str):
        assert is_core_state_file(filename) is True
        assert is_core_state_file(f"project/{filename}") is True

    def test_non_core_file(self):
        assert is_core_state_file("chapters/vol-01/ch-001/sec-001.md") is False
        assert is_core_state_file("materials/extracted/chars.md") is False


# ═══════════════════════════════════════════════════════════
# GenerationOutputPolicy 测试
# ═══════════════════════════════════════════════════════════


class TestDecideOutput:
    """decide_output 契约测试"""

    # ── 强制 candidate ─────────────────────────────────

    def test_require_candidate(self):
        """require_candidate=True → candidate"""
        result = decide_output("write", "chapters/vol-01/ch-001/sec-001.md", require_candidate=True)
        assert result.mode == "candidate"
        assert "require_candidate" in result.reason

    # ── 高风险管线 → candidate ─────────────────────────

    def test_polish_pipeline(self):
        """polish 管线 → candidate"""
        result = decide_output("generate", "chapters/vol-01/ch-001/sec-001.md", pipeline_name="polish")
        assert result.mode == "candidate"

    def test_rewrite_pipeline(self):
        """rewrite 管线 → candidate"""
        result = decide_output("generate", "chapters/vol-01/ch-001/sec-001.md", pipeline_name="rewrite")
        assert result.mode == "candidate"

    def test_custom_polish_pipeline(self):
        """自定义 polish 管线（如 scene-polish）→ candidate"""
        result = decide_output("generate", "chapters/vol-01/ch-001/sec-001.md", pipeline_name="scene-polish")
        assert result.mode == "candidate"

    # ── 高风险操作 → candidate ─────────────────────────

    def test_rewrite_action(self):
        """rewrite 操作 → candidate"""
        result = decide_output("rewrite", "chapters/vol-01/ch-001/sec-001.md")
        assert result.mode == "candidate"

    def test_polish_action(self):
        """polish 操作 → candidate"""
        result = decide_output("polish", "chapters/vol-01/ch-001/sec-001.md")
        assert result.mode == "candidate"

    def test_more_exciting_action(self):
        """more_exciting 操作 → candidate"""
        result = decide_output("more_exciting", "chapters/vol-01/ch-001/sec-003.md")
        assert result.mode == "candidate"

    def test_more_reasonable_action(self):
        """more_reasonable 操作 → candidate"""
        result = decide_output("more_reasonable", "chapters/vol-01/ch-001/sec-003.md")
        assert result.mode == "candidate"

    # ── write_new_scene 空 sec → write ─────────────────

    def test_write_new_scene_empty(self):
        """write_new_scene 空 sec → write"""
        result = decide_output("write_new_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "write"

    def test_write_empty_sec(self):
        """write 空 sec → write"""
        result = decide_output("write", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "write"

    # ── write_new_scene 已有 sec → candidate ───────────

    def test_write_new_scene_existing_content(self):
        """write_new_scene 已有 sec → candidate"""
        result = decide_output("write_new_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=True)
        assert result.mode == "candidate"

    # ── write_next_scene / write_current_scene ──────────

    def test_write_next_scene_empty(self):
        """write_next_scene 空 sec → write"""
        result = decide_output("write_next_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "write"

    def test_write_next_scene_with_content(self):
        """write_next_scene 已有内容 → candidate"""
        result = decide_output("write_next_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=True)
        assert result.mode == "candidate"
        assert "已有内容" in result.reason

    def test_write_current_scene_empty(self):
        """write_current_scene 空 sec → write"""
        result = decide_output("write_current_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "write"

    def test_write_current_scene_with_content(self):
        """write_current_scene 已有内容 → candidate"""
        result = decide_output("write_current_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=True)
        assert result.mode == "candidate"
        assert "已有内容" in result.reason

    # ── rewrite_current_scene / polish_current_scene ────

    def test_rewrite_current_scene_always_candidate(self):
        """rewrite_current_scene → candidate（即使目标为空）"""
        result = decide_output("rewrite_current_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "candidate"

    def test_rewrite_current_scene_with_content(self):
        """rewrite_current_scene 有内容 → candidate"""
        result = decide_output("rewrite_current_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=True)
        assert result.mode == "candidate"

    def test_polish_current_scene_always_candidate(self):
        """polish_current_scene → candidate（即使目标为空）"""
        result = decide_output("polish_current_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "candidate"

    def test_polish_current_scene_with_content(self):
        """polish_current_scene 有内容 → candidate"""
        result = decide_output("polish_current_scene", "chapters/vol-01/ch-001/sec-001.md", file_has_content=True)
        assert result.mode == "candidate"

    # ── extract → write ────────────────────────────────

    def test_extract_materials(self):
        """extract → write"""
        result = decide_output("extract", "materials/extracted/characters.md")
        assert result.mode == "write"

    # ── output_mode 处理 ───────────────────────────────

    def test_output_mode_candidate(self):
        """output_mode=candidate → candidate"""
        result = decide_output("generate", "chapters/vol-01/ch-001/sec-001.md", output_mode="candidate")
        assert result.mode == "candidate"

    def test_output_mode_none(self):
        """output_mode=none → reject"""
        result = decide_output("generate", "chapters/vol-01/ch-001/sec-001.md", output_mode="none")
        assert result.mode == "reject"

    def test_output_mode_append(self):
        """output_mode=append → append"""
        result = decide_output("generate", "chapters/vol-01/ch-001/sec-001.md", output_mode="append")
        assert result.mode == "append"

    def test_output_mode_write_scene_empty(self):
        """output_mode=write_scene 空 sec → write"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="write_scene", file_has_content=False,
        )
        assert result.mode == "write"

    def test_output_mode_write_scene_with_content(self):
        """output_mode=write_scene 已有内容 → candidate"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="write_scene", file_has_content=True,
        )
        assert result.mode == "candidate"

    def test_output_mode_overwrite_dangerous_path(self):  # AI_GUARDRAIL_ALLOW
        """output_mode=overwrite 对危险路径 → candidate  AI_GUARDRAIL_ALLOW"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite", file_has_content=True,  # AI_GUARDRAIL_ALLOW: test param
        )
        assert result.mode == "candidate"

    def test_output_mode_overwrite_safe_path(self):  # AI_GUARDRAIL_ALLOW: test for overwrite safety
        """output_mode=overwrite 对安全路径 → write  AI_GUARDRAIL_ALLOW"""
        result = decide_output(
            "generate", "materials/extracted/chars.md",
            output_mode="overwrite", file_has_content=True,  # AI_GUARDRAIL_ALLOW: test param
        )
        assert result.mode == "write"

    # ── 核心状态文件 ───────────────────────────────────

    def test_story_state_overwrite(self):
        """story-state.md overwrite → candidate"""
        result = decide_output(
            "update", "story-state.md",
            output_mode="overwrite", file_has_content=True,  # AI_GUARDRAIL_ALLOW: test param
        )
        assert result.mode == "candidate"

    def test_recent_context_overwrite(self):
        """recent-context.md overwrite → candidate"""
        result = decide_output(
            "update", "recent-context.md",
            output_mode="overwrite", file_has_content=True,  # AI_GUARDRAIL_ALLOW: test param
        )
        assert result.mode == "candidate"

    def test_style_guide_overwrite(self):
        """style-guide.md overwrite → candidate"""
        result = decide_output(
            "update", "style-guide.md",
            output_mode="overwrite", file_has_content=True,  # AI_GUARDRAIL_ALLOW: test param
        )
        assert result.mode == "candidate"

    # ── continue/append 空 sec → write ─────────────────

    def test_continue_empty(self):
        """continue 空 sec → write"""
        result = decide_output("continue", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "write"

    def test_append_empty(self):
        """append 空 sec → write"""
        result = decide_output("append", "chapters/vol-01/ch-001/sec-001.md", file_has_content=False)
        assert result.mode == "write"


class TestIsDangerousOutput:
    """is_dangerous_output 测试"""

    def test_scene_file_dangerous(self):
        assert is_dangerous_output("chapters/vol-01/ch-001/sec-001.md") is True

    def test_story_state_dangerous(self):
        assert is_dangerous_output("story-state.md") is True

    def test_recent_context_dangerous(self):
        assert is_dangerous_output("recent-context.md") is True

    def test_style_guide_dangerous(self):
        assert is_dangerous_output("style-guide.md") is True

    def test_outline_dangerous(self):
        assert is_dangerous_output("outline.md") is True

    def test_meta_json_dangerous(self):
        assert is_dangerous_output("meta.json") is True

    def test_ch_meta_dangerous(self):
        assert is_dangerous_output("chapters/vol-01/ch-001/ch-meta.json") is True

    def test_materials_safe(self):
        assert is_dangerous_output("materials/extracted/chars.md") is False

    def test_candidates_safe(self):
        assert is_dangerous_output(".candidates/abc123.md") is False

    def test_revision_log_safe(self):
        assert is_dangerous_output("revision-log/rev-001.json") is False

    def test_logs_safe(self):
        assert is_dangerous_output("logs/generation.log") is False

    def test_materials_drafts_safe(self):
        assert is_dangerous_output("materials/drafts/outline.md") is False


class TestIsSceneFileGenerationPolicy:
    """generation_output_policy.is_scene_file 测试"""

    def test_standard_scene(self):
        assert is_scene_file("chapters/vol-01/ch-001/sec-001.md") is True

    def test_ch_plan_not_scene(self):
        assert is_scene_file("chapters/vol-01/ch-001/ch-plan.md") is False

    def test_random_file(self):
        assert is_scene_file("story-state.md") is False


class TestOverwriteLegacyCompat:
    """LEGACY_COMPAT: overwrite is accepted but normalized to safe modes."""

    def test_overwrite_empty_scene_becomes_write(self):
        """overwrite + 空 sec → write (treated as write_scene)"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite", file_has_content=False,
        )
        assert result.mode == "write"

    def test_overwrite_existing_scene_becomes_candidate(self):
        """overwrite + 已有 sec → candidate (no silent overwrite)"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite", file_has_content=True,
        )
        assert result.mode == "candidate"

    def test_overwrite_rewrite_action_always_candidate(self):
        """rewrite + overwrite → candidate (high-risk action overrides)"""
        result = decide_output(
            "rewrite", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite", file_has_content=False,
        )
        assert result.mode == "candidate"

    def test_overwrite_polish_action_always_candidate(self):
        """polish + overwrite → candidate (high-risk action overrides)"""
        result = decide_output(
            "polish", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="overwrite", file_has_content=False,
        )
        assert result.mode == "candidate"

    def test_overwrite_safe_path_empty(self):
        """overwrite + safe path + empty → write"""
        result = decide_output(
            "generate", "materials/extracted/chars.md",
            output_mode="overwrite", file_has_content=False,
        )
        assert result.mode == "write"

    def test_overwrite_safe_path_with_content(self):
        """overwrite + safe path + content → write (safe path allows overwrite)"""
        result = decide_output(
            "generate", "materials/extracted/chars.md",
            output_mode="overwrite", file_has_content=True,
        )
        assert result.mode == "write"

    def test_write_scene_empty(self):
        """write_scene + empty → write"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="write_scene", file_has_content=False,
        )
        assert result.mode == "write"

    def test_write_scene_with_content(self):
        """write_scene + content → candidate (no silent overwrite)"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="write_scene", file_has_content=True,
        )
        assert result.mode == "candidate"

    def test_candidate_always_candidate(self):
        """candidate mode → candidate regardless of content"""
        result = decide_output(
            "generate", "chapters/vol-01/ch-001/sec-001.md",
            output_mode="candidate", file_has_content=False,
        )
        assert result.mode == "candidate"

    def test_overwrite_dangerous_path(self):
        """overwrite + dangerous path → candidate"""
        result = decide_output(
            "generate", "story-state.md",
            output_mode="overwrite", file_has_content=True,
        )
        assert result.mode == "candidate"
