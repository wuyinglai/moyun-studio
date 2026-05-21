"""候选稿服务单元测试

测试要点：
1. CandidateService create_candidate 时 source_path 不包含 project_id
2. adopt_candidate 时 source_path 不会出现双重路径
3. 候选稿元数据中 source_path 格式正确
4. adopt_candidate 冲突检测（源文件已变化时返回 conflict）
"""

import pytest

from backend.core.file_ops import FileService
from backend.core.candidate_service import CandidateService, CandidateAction, CandidateStatus, AdoptResult


class TestCandidateServiceSourcePath:
    """source_path 路径格式测试"""

    @pytest.mark.asyncio
    async def test_create_candidate_source_path_no_project_id(self, temp_workspace):
        """创建候选稿时 source_path 不应包含 project_id"""
        fs = FileService(temp_workspace)

        # 创建测试项目目录
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建候选稿服务
        candidate_svc = CandidateService(fs)

        # 创建候选稿，使用项目内相对路径（不带 project_id）
        source_path = "chapters/vol-01/ch-001/sec-001.md"
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,  # 不带 project_id  AI_GUARDRAIL_ALLOW
            action=CandidateAction.REWRITE,
            content="# 测试内容",
        )

        # 验证 source_path 不包含 project_id
        assert candidate.source_path == source_path
        assert "test-project" not in candidate.source_path
        # 确保不会出现 "test-project/test-project/..." 这种双重路径
        path_parts = candidate.source_path.split("/")
        for i in range(len(path_parts) - 1):
            if path_parts[i] == path_parts[i + 1]:
                pytest.fail(f"发现双重路径: {candidate.source_path}")

    @pytest.mark.asyncio
    async def test_adopt_candidate_source_path_correct(self, temp_workspace):
        """采用候选稿时 source_path 格式正确"""
        fs = FileService(temp_workspace)

        # 创建测试项目
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建原始文件
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        original_file = chapters_dir / "sec-001.md"
        original_file.write_text("# 原始内容\n\n这是原始内容。", encoding="utf-8")

        # 创建候选稿服务
        candidate_svc = CandidateService(fs)

        # 创建候选稿
        source_path = "chapters/vol-01/ch-001/sec-001.md"
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
        )

        # 采用候选稿
        result = await candidate_svc.adopt_candidate(
            project_id="test-project",
            candidate_id=candidate.id,
        )
        assert result == AdoptResult.SUCCESS

        # 验证采用后的文件内容
        adopted_content, _, _ = await fs.read_file(f"test-project/{source_path}")
        assert "# 新内容" in adopted_content
        assert "这是新内容" in adopted_content

    @pytest.mark.asyncio
    async def test_candidate_metadata_source_path_format(self, temp_workspace):
        """候选稿元数据中 source_path 格式正确"""
        fs = FileService(temp_workspace)

        # 创建测试项目
        project_dir = temp_workspace / "my-novel"
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建候选稿服务
        candidate_svc = CandidateService(fs)

        # 使用各种路径格式创建候选稿
        test_cases = [
            ("outline.md", "outline.md"),
            ("chapters/vol-01/ch-001/sec-001.md", "chapters/vol-01/ch-001/sec-001.md"),
            ("characters/main.md", "characters/main.md"),
        ]

        for input_path, expected_path in test_cases:
            candidate = await candidate_svc.create_candidate(
                project_id="my-novel",
                source_path=input_path,
                action=CandidateAction.REWRITE,
                content=f"# {input_path}",
            )

            # 验证元数据中的 source_path 格式正确
            assert candidate.source_path == expected_path
            # 验证不会出现双重 project_id
            assert candidate.source_path.count("my-novel") == 0, \
                f"source_path 不应包含 project_id: {candidate.source_path}"

    @pytest.mark.asyncio
    async def test_candidate_path_never_has_double_project_id(self, temp_workspace):
        """确保候选稿路径永远不会有双重 project_id"""
        fs = FileService(temp_workspace)

        # 创建测试项目
        project_dir = temp_workspace / "novel-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        # 测试多种场景
        test_paths = [
            "chapters/vol-01/ch-001/sec-001.md",
            "chapters/vol-01/ch-002/sec-002.md",
            "outline.md",
        ]

        for rel_path in test_paths:
            candidate = await candidate_svc.create_candidate(
                project_id="novel-project",
                source_path=rel_path,
                action=CandidateAction.CONTINUE,
                content=f"Content for {rel_path}",
            )

            # 确保没有双重路径
            parts = candidate.source_path.split("/")
            for i in range(len(parts) - 1):
                assert parts[i] != parts[i + 1], \
                    f"双重路径检测失败: {candidate.source_path}"

            # 确保没有 project_id
            assert "novel-project" not in candidate.source_path, \
                f"source_path 不应包含 project_id: {candidate.source_path}"


class TestCandidateServiceBasic:
    """候选稿服务基本功能测试"""

    @pytest.mark.asyncio
    async def test_create_candidate_basic(self, temp_workspace):
        """基本创建候选稿功能"""
        fs = FileService(temp_workspace)

        # 创建测试项目
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path="chapters/vol-01/sec-001.md",
            action=CandidateAction.REWRITE,
            content="# 新章节",
        )

        assert candidate.id.startswith("cand_")
        assert candidate.status == CandidateStatus.PENDING
        assert candidate.action == CandidateAction.REWRITE

    @pytest.mark.asyncio
    async def test_list_candidates(self, temp_workspace):
        """列出候选稿"""
        fs = FileService(temp_workspace)

        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        # 创建多个候选稿
        for i in range(3):
            await candidate_svc.create_candidate(
                project_id="test-project",
                source_path=f"sec-{i:03d}.md",
                action=CandidateAction.REWRITE,
                content=f"Content {i}",
            )

        # 列出所有候选稿
        candidates = await candidate_svc.list_candidates("test-project")
        assert len(candidates) >= 3

    @pytest.mark.asyncio
    async def test_get_candidate_content(self, temp_workspace):
        """获取候选稿内容"""
        fs = FileService(temp_workspace)

        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        candidate_svc = CandidateService(fs)

        original_content = "# 测试章节\n\n这是测试内容。"
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path="outline.md",
            action=CandidateAction.REWRITE,
            content=original_content,
        )

        # 获取候选稿内容
        content = await candidate_svc.get_candidate_content(
            project_id="test-project",
            candidate_id=candidate.id,
        )

        assert content == original_content

    @pytest.mark.asyncio
    async def test_adopt_candidate_conflict_detection(self, temp_workspace):
        """源文件已变化时采用候选稿返回 conflict"""
        fs = FileService(temp_workspace)

        # 创建测试项目
        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建原始文件
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        original_file = chapters_dir / "sec-001.md"
        original_file.write_text("# 原始内容\n\n这是原始内容。", encoding="utf-8")

        candidate_svc = CandidateService(fs)

        # 创建候选稿（此时会记录 base_hash）
        source_path = "chapters/vol-01/ch-001/sec-001.md"
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容\n\n这是新内容。",
        )

        # 修改源文件（模拟外部修改）
        original_file.write_text("# 被外部修改的内容\n\n这是新修改的。", encoding="utf-8")

        # 采用候选稿应返回 conflict
        result = await candidate_svc.adopt_candidate(
            project_id="test-project",
            candidate_id=candidate.id,
        )
        assert result == AdoptResult.CONFLICT

        # 验证候选稿状态变为 rejected
        updated = await candidate_svc.get_candidate("test-project", candidate.id)
        assert updated.status == CandidateStatus.REJECTED

    @pytest.mark.asyncio
    async def test_create_candidate_records_base_hash(self, temp_workspace):
        """创建候选稿时记录 base_hash 和 base_mtime"""
        fs = FileService(temp_workspace)

        project_dir = temp_workspace / "test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建原始文件
        chapters_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        original_file = chapters_dir / "sec-001.md"
        original_file.write_text("# 原始内容", encoding="utf-8")

        candidate_svc = CandidateService(fs)

        source_path = "chapters/vol-01/ch-001/sec-001.md"
        candidate = await candidate_svc.create_candidate(
            project_id="test-project",
            source_path=source_path,
            action=CandidateAction.REWRITE,
            content="# 新内容",
        )

        # 验证 base_hash 和 base_mtime 被记录
        assert candidate.base_hash != ""
        assert candidate.base_mtime is not None
        assert candidate.project_id == "test-project"
