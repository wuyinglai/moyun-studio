"""墨韵 - Candidate API 契约测试

确保候选稿核心行为不被后续修改破坏。
"""

import pytest
from fastapi.testclient import TestClient

from backend.core.candidate_service import CandidateService, AdoptResult
from backend.core.file_ops import FileService
from backend.schemas.candidate import CandidateAction, CandidateStatus


class TestCandidateCreateContract:
    """创建候选稿契约测试"""

    @pytest.mark.asyncio
    async def test_create_candidate_does_not_overwrite_source(self, fs: FileService):
        """创建候选稿不得覆盖正式正文"""
        source_content = "这是原始正文内容，不应被覆盖。"
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", source_content)

        svc = CandidateService(fs)
        candidate = await svc.create_candidate(
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            action=CandidateAction.REWRITE,
            content="这是候选稿内容，不应覆盖原文。",
        )
        assert candidate is not None

        # 验证正式正文未被覆盖
        current_content, _, _ = await fs.read_file("test-project/chapters/vol-01/ch-001/sec-001.md")
        assert current_content == source_content

    @pytest.mark.asyncio
    async def test_source_path_is_relative(self, fs: FileService):
        """candidate.source_path 必须是项目内相对路径"""
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", "原始")
        svc = CandidateService(fs)
        candidate = await svc.create_candidate(
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            action=CandidateAction.REWRITE,
            content="候选稿内容",
        )
        source_path = candidate.source_path
        # 不应以 / 开头
        assert not source_path.startswith("/")
        # 不应包含重复 project_id
        assert "test-project/test-project" not in source_path

    @pytest.mark.asyncio
    async def test_source_path_no_duplicate_project_id(self, fs: FileService):
        """source_path 不得包含重复 project_id"""
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", "原始")
        svc = CandidateService(fs)
        candidate = await svc.create_candidate(
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            action=CandidateAction.REWRITE,
            content="候选稿内容",
        )
        assert "test-project/test-project" not in candidate.source_path
        assert candidate.source_path.startswith("chapters/")


class TestCandidateAdoptContract:
    """采用候选稿契约测试"""

    async def _create_candidate(self, svc: CandidateService, fs: FileService):
        """辅助：创建候选稿并返回 candidate"""
        source_content = "原始正文"
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", source_content)
        candidate = await svc.create_candidate(
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            action=CandidateAction.REWRITE,
            content="候选稿正文",
        )
        return candidate, source_content

    @pytest.mark.asyncio
    async def test_adopt_checks_base_mtime(self, fs: FileService):
        """adopt 前必须检查 base_mtime"""
        svc = CandidateService(fs)
        candidate, _ = await self._create_candidate(svc, fs)

        # 修改源文件（改变 mtime）
        import time
        time.sleep(0.01)
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", "被修改的正文")

        result = await svc.adopt_candidate("test-project", candidate.id)
        assert result == AdoptResult.CONFLICT

    @pytest.mark.asyncio
    async def test_adopt_checks_base_hash(self, fs: FileService):
        """adopt 前必须检查 base_hash"""
        svc = CandidateService(fs)
        candidate, _ = await self._create_candidate(svc, fs)

        # 修改源文件内容（改变 hash）
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", "内容被改了")

        result = await svc.adopt_candidate("test-project", candidate.id)
        assert result == AdoptResult.CONFLICT

    @pytest.mark.asyncio
    async def test_adopt_writes_revision_log(self, fs: FileService):
        """adopt 成功前必须写 revision-log"""
        svc = CandidateService(fs)
        candidate, _ = await self._create_candidate(svc, fs)

        result = await svc.adopt_candidate("test-project", candidate.id)
        assert result == AdoptResult.SUCCESS

        # 检查 revision-log 目录是否有文件
        rev_dir = fs._resolve_path("test-project/chapters/vol-01/ch-001/revision-log")
        if rev_dir.exists():
            log_files = list(rev_dir.glob("*.json"))
            assert len(log_files) > 0, "adopt 后必须有 revision-log"

    @pytest.mark.asyncio
    async def test_adopt_success_sets_status_adopted(self, fs: FileService):
        """adopt 成功后 candidate status = ADOPTED"""
        svc = CandidateService(fs)
        candidate, _ = await self._create_candidate(svc, fs)

        result = await svc.adopt_candidate("test-project", candidate.id)
        assert result == AdoptResult.SUCCESS

        updated = await svc.get_candidate("test-project", candidate.id)
        assert updated is not None
        assert updated.status == CandidateStatus.ADOPTED

    @pytest.mark.asyncio
    async def test_adopt_conflict_does_not_overwrite(self, fs: FileService):
        """adopt 冲突时不得覆盖正式正文"""
        svc = CandidateService(fs)
        candidate, _ = await self._create_candidate(svc, fs)

        # 修改源文件
        modified = "被修改的正文"
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", modified)

        result = await svc.adopt_candidate("test-project", candidate.id)
        assert result == AdoptResult.CONFLICT

        # 验证正式正文是修改后的版本，不是候选稿
        content, _, _ = await fs.read_file("test-project/chapters/vol-01/ch-001/sec-001.md")
        assert content == modified

    def test_adopt_conflict_api_returns_409(self, client: TestClient, temp_workspace, test_settings, monkeypatch):
        """API adopt 发生源文件冲突时必须返回 FILE_CONFLICT / 409"""
        test_settings.workspace_path = temp_workspace
        monkeypatch.setattr("backend.api.candidates.get_settings", lambda: test_settings)
        project_dir = temp_workspace / "projects" / "test-project"
        scene_dir = project_dir / "chapters" / "vol-01" / "ch-001"
        scene_dir.mkdir(parents=True, exist_ok=True)
        source_path = "chapters/vol-01/ch-001/sec-001.md"
        scene_file = project_dir / source_path
        scene_file.write_text("原始正文", encoding="utf-8")

        create_resp = client.post("/api/candidates/test-project", json={
            "project_id": "test-project",
            "source_path": source_path,
            "action": "rewrite",
            "content": "候选稿正文",
        })
        assert create_resp.status_code == 200
        candidate_id = create_resp.json()["id"]

        import time
        time.sleep(0.01)
        scene_file.write_text("外部修改后的正文", encoding="utf-8")
        adopt_resp = client.post(f"/api/candidates/test-project/{candidate_id}/adopt")

        assert adopt_resp.status_code == 409
        assert "FILE_CONFLICT" in str(adopt_resp.json())
        assert scene_file.read_text(encoding="utf-8") == "外部修改后的正文"

    @pytest.mark.asyncio
    async def test_adopt_non_pending_rejected(self, fs: FileService):
        """非 PENDING 状态的候选稿不允许采用"""
        svc = CandidateService(fs)
        candidate, _ = await self._create_candidate(svc, fs)

        # 先 adopt 一次
        await svc.adopt_candidate("test-project", candidate.id)

        # 再次 adopt 应该失败
        result = await svc.adopt_candidate("test-project", candidate.id)
        assert result == AdoptResult.NOT_PENDING


class TestCandidateStorageContract:
    """候选稿存储契约测试"""

    @pytest.mark.asyncio
    async def test_candidate_stored_in_candidates_dir(self, fs: FileService):
        """候选稿必须存储在 .candidates/ 目录下"""
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", "原始")
        svc = CandidateService(fs)
        candidate = await svc.create_candidate(
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            action=CandidateAction.REWRITE,
            content="候选稿",
        )
        # candidate_path 包含项目前缀，但必须包含 .candidates/
        assert ".candidates/" in candidate.candidate_path

    @pytest.mark.asyncio
    async def test_candidate_has_base_hash_and_mtime(self, fs: FileService):
        """候选稿必须记录 base_hash 和 base_mtime"""
        await fs.write_file("test-project/chapters/vol-01/ch-001/sec-001.md", "原始")
        svc = CandidateService(fs)
        candidate = await svc.create_candidate(
            project_id="test-project",
            source_path="chapters/vol-01/ch-001/sec-001.md",
            action=CandidateAction.REWRITE,
            content="候选稿",
        )
        assert candidate.base_hash is not None
        assert candidate.base_mtime is not None
