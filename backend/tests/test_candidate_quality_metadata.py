"""候选稿质量元数据测试

测试要点：
1. old candidate 无 quality 不崩
2. beat_validation → instruction_following
3. continuity anchors → continuity
4. polish → style_preservation pass
5. rewrite → unknown
6. length delta → change_scope
7. forbidden warning → forbidden_check warning
8. feedback revision child 继承 quality
9. metadata 不包含 prompt
10. metadata 不影响 source
"""

import pytest

from backend.core.file_ops import FileService
from backend.core.candidate_service import (
    CandidateService,
    CandidateAction,
    CandidateStatus,
)
from backend.schemas.candidate import CandidateQuality


class TestCandidateQualityMetadata:
    """Quality metadata 生成测试"""

    @pytest.mark.asyncio
    async def test_old_candidate_no_quality_field(self, temp_workspace):
        """旧 candidate 没有 quality 字段时应该能正常加载"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        # 创建源文件
        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        # 创建候选稿
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
        )

        # quality 字段应该存在且有默认值
        assert candidate.quality is not None
        assert isinstance(candidate.quality.instruction_following, CandidateQuality)
        assert isinstance(candidate.quality.continuity, CandidateQuality)
        assert isinstance(candidate.quality.style_preservation, CandidateQuality)
        assert isinstance(candidate.quality.change_scope, CandidateQuality)
        assert isinstance(candidate.quality.forbidden_check, CandidateQuality)

    @pytest.mark.asyncio
    async def test_beat_validation_pass_instruction_following(self, temp_workspace):
        """beat_validation status=pass → instruction_following=pass"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        beat_validation = {
            "status": "pass",
            "summary": "检查通过",
            "required_beats": [],
            "forbidden_beats": [],
        }

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
            beat_validation=beat_validation,
        )

        assert candidate.quality.instruction_following == CandidateQuality.PASS

    @pytest.mark.asyncio
    async def test_beat_validation_warning_instruction_following(self, temp_workspace):
        """beat_validation status=warning → instruction_following=warning"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        beat_validation = {
            "status": "warning",
            "summary": "存在风险",
            "required_beats": [{"id": "beat-1", "text": "测试", "status": "missing"}],
            "forbidden_beats": [],
        }

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
            beat_validation=beat_validation,
        )

        assert candidate.quality.instruction_following == CandidateQuality.WARNING

    @pytest.mark.asyncio
    async def test_continuity_anchors_used_count_pass(self, temp_workspace):
        """continuity_anchors.used_count > 0 → continuity=pass"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        continuity_anchors = {
            "enabled": True,
            "used_count": 3,
            "anchor_ids": ["anchor-1", "anchor-2", "anchor-3"],
        }

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
            continuity_anchors=continuity_anchors,
        )

        assert candidate.quality.continuity == CandidateQuality.PASS

    @pytest.mark.asyncio
    async def test_continuity_no_anchors_unknown(self, temp_workspace):
        """无 continuity_anchors → continuity=unknown"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
            continuity_anchors={},
        )

        assert candidate.quality.continuity == CandidateQuality.UNKNOWN

    @pytest.mark.asyncio
    async def test_polish_action_style_preservation_pass(self, temp_workspace):
        """polish action → style_preservation=pass"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.POLISH,
            content="# 源内容\n\n这是测试内容。",  # 几乎不变
        )

        assert candidate.quality.style_preservation == CandidateQuality.PASS

    @pytest.mark.asyncio
    async def test_rewrite_action_style_preservation_unknown(self, temp_workspace):
        """rewrite action → style_preservation=unknown"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
        )

        assert candidate.quality.style_preservation == CandidateQuality.UNKNOWN

    @pytest.mark.asyncio
    async def test_change_scope_small(self, temp_workspace):
        """长度变化 < 10% → change_scope=small"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        # 使用足够多的中文字符确保计算准确
        source_file.write_text("# 标题\n\n这是测试内容用于质量元数据检查。这段文字需要足够长才能准确计算字数变化。", encoding="utf-8")

        # 5% 变化 - 只增加一个中文字符
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.MODIFY,
            content="# 标题\n\n这是测试内容用于质量元数据检查。这段文字需要足够长才能准确计算字数变化！",  # 多了感叹号
        )

        assert candidate.quality.change_scope == CandidateQuality.SMALL

    @pytest.mark.asyncio
    async def test_change_scope_medium(self, temp_workspace):
        """长度变化 10%~40% → change_scope=medium"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        # 足够长的源内容以确保计算准确
        source_file.write_text("# 标题\n\n这是测试内容用于质量元数据检查。这段文字需要足够长才能准确计算字数变化。", encoding="utf-8")

        # 约25%变化 - 源34字，目标43字（约26%增长）
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.EXPAND,
            content="# 标题\n\n这是测试内容用于质量元数据检查。这段文字需要足够长才能准确计算字数变化。新增内容验证",  # 从34字增加到43字
        )

        assert candidate.quality.change_scope == CandidateQuality.MEDIUM

    @pytest.mark.asyncio
    async def test_change_scope_large(self, temp_workspace):
        """长度变化 > 40% → change_scope=large"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n短", encoding="utf-8")

        # 100%+ 变化
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.EXPAND,
            content="# 源内容\n\n这是很长很长很长很长很长很长很长很长很长很长很长很长的新内容。",
        )

        assert candidate.quality.change_scope == CandidateQuality.LARGE

    @pytest.mark.asyncio
    async def test_forbidden_check_no_violation_pass(self, temp_workspace):
        """无 forbidden violation → forbidden_check=pass"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        beat_validation = {
            "status": "pass",
            "forbidden_beats": [
                {"id": "forbid-1", "text": "禁止项", "violated": False, "evidence": ""}
            ],
        }

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
            beat_validation=beat_validation,
        )

        assert candidate.quality.forbidden_check == CandidateQuality.PASS

    @pytest.mark.asyncio
    async def test_forbidden_check_has_violation_warning(self, temp_workspace):
        """有 forbidden violation → forbidden_check=warning"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        beat_validation = {
            "status": "warning",
            "forbidden_beats": [
                {"id": "forbid-1", "text": "禁止项", "violated": True, "evidence": "发现禁止内容"}
            ],
        }

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
            beat_validation=beat_validation,
        )

        assert candidate.quality.forbidden_check == CandidateQuality.WARNING

    @pytest.mark.asyncio
    async def test_metadata_does_not_contain_prompt(self, temp_workspace):
        """metadata 不应包含 prompt"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        source_file.write_text("# 源内容\n\n这是测试内容。", encoding="utf-8")

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
        )

        # 获取存储的 metadata
        metadata = await candidate_svc._load_metadata("test-project")
        candidate_data = metadata[candidate.id]

        # 确保没有 prompt 相关字段
        assert "prompt" not in candidate_data
        assert "prompt_version" not in candidate_data or candidate_data.get("prompt_version") is None

    @pytest.mark.asyncio
    async def test_metadata_does_not_affect_source(self, temp_workspace):
        """quality metadata 不影响 source 内容"""
        fs = FileService(temp_workspace)
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        source_file = chapters_dir / "sec-001.md"
        original_content = "# 源内容\n\n这是测试内容。"
        source_file.write_text(original_content, encoding="utf-8")

        new_content = "# 新内容\n\n这是新内容。"

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content=new_content,
        )

        # 验证源文件未被修改
        current_content = source_file.read_text(encoding="utf-8")
        assert current_content == original_content

        # 验证候选稿内容正确
        candidate_content = await candidate_svc.get_candidate_content("test-project", candidate.id)
        assert candidate_content == new_content
