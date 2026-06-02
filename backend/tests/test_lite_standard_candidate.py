"""墨韵 - Lite 标准候选稿行为测试

验证 Lite 高风险改稿动作真的创建标准 .candidates/ Candidate，
而不是旧 .lite-candidates/ 机制。
"""

import json
import tempfile
from pathlib import Path

import pytest

from backend.core.candidate_service import CandidateService
from backend.core.file_ops import FileService
from backend.schemas.candidate import CandidateAction, CandidateStatus


@pytest.fixture
def file_service(tmp_path):
    """创建临时文件服务"""
    return FileService(str(tmp_path), max_file_write_size=10 * 1024 * 1024)


@pytest.fixture
def candidate_service(file_service):
    """创建候选稿服务"""
    return CandidateService(file_service)


@pytest.fixture
def project_id():
    """测试项目 ID"""
    return "test-lite-candidate"


@pytest.fixture
def source_file_content():
    """测试源文件内容"""
    return """# 第1卷 第1章 第1场景 开局

这是一个测试场景的正文内容。
主角正在经历一场重要的冲突。
场景结尾有一个钩子，吸引读者继续阅读。
"""


@pytest.fixture
def source_file_path():
    """测试源文件路径"""
    return "chapters/vol-01/ch-001/sec-001.md"


@pytest.fixture
def setup_project(file_service, project_id, source_file_path, source_file_content):
    """设置测试项目环境"""
    import asyncio

    async def _setup():
        # 创建源文件
        full_path = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_path, source_file_content)

    asyncio.get_event_loop().run_until_complete(_setup())
    return project_id, source_file_path


class TestLiteStandardCandidateCreation:
    """测试 Lite 创建标准候选稿"""

    @pytest.mark.asyncio
    async def test_lite_rewrite_creates_standard_candidates_dir(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite rewrite 创建标准 .candidates/ 目录"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写后的新内容。",
            source_mode="lite",
        )

        # 验证：候选稿路径在 .candidates/ 而不是 .lite-candidates/
        # candidate_path 格式为 project_id/.candidates/xxx.md
        assert ".candidates/" in candidate_info.candidate_path
        assert ".lite-candidates/" not in candidate_info.candidate_path
        # 路径格式应该是 project_id/.candidates/cand_xxx.rewrite.md
        assert f"{project_id}/.candidates/" in candidate_info.candidate_path

    @pytest.mark.asyncio
    async def test_lite_candidate_metadata_has_source_mode(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite 候选稿 metadata 包含 source_mode='lite'"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写后的新内容。",
            source_mode="lite",
        )

        # 验证：metadata 包含 source_mode
        assert candidate_info.source_mode == "lite"

        # 验证：通过 list_candidates 也能看到 source_mode
        candidates = await candidate_service.list_candidates(project_id)
        assert len(candidates) == 1
        assert candidates[0].source_mode == "lite"

    @pytest.mark.asyncio
    async def test_lite_candidate_has_base_hash_and_mtime(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite 候选稿 metadata 包含 base_hash 和 base_mtime"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写后的新内容。",
            source_mode="lite",
        )

        # 验证：metadata 包含 base_hash 和 base_mtime
        assert candidate_info.base_hash != ""
        assert candidate_info.base_mtime is not None
        assert candidate_info.base_mtime > 0

    @pytest.mark.asyncio
    async def test_lite_polish_creates_standard_candidate(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite polish_current_scene 创建标准候选稿"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.POLISH,
            content="润色后的新内容。",
            source_mode="lite",
        )

        # 验证
        assert ".candidates/" in candidate_info.candidate_path
        assert candidate_info.action == CandidateAction.POLISH
        assert candidate_info.source_mode == "lite"
        assert candidate_info.base_hash != ""


class TestLiteCandidateAdoptFlow:
    """测试 Lite 候选稿 adopt 流程"""

    @pytest.mark.asyncio
    async def test_lite_candidate_adopt_does_not_overwrite_before_adopt(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """验证 adopt 前原文不被覆盖"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写后的新内容，替换原文。",
            source_mode="lite",
        )

        # adopt 前读取原文
        original_content, _, _ = await file_service.read_file(full_source)

        # 验证：原文未被修改（使用 strip() 处理可能的换行符差异）
        assert original_content.strip() == source_file_content.strip()
        # 验证：候选稿内容和原文不同
        assert candidate_info.candidate_path != full_source

    @pytest.mark.asyncio
    async def test_lite_candidate_adopt_updates_source(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite 候选稿 adopt 后更新原文"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写后的新内容，替换原文。",
            source_mode="lite",
        )

        # adopt 候选稿
        result = await candidate_service.adopt_candidate(project_id, candidate_info.id)

        # 验证：adopt 成功
        assert result == "success"

        # adopt 后读取原文
        adopted_content, _, _ = await file_service.read_file(full_source)

        # 验证：原文被更新为候选稿内容
        assert adopted_content == "重写后的新内容，替换原文。"
        assert adopted_content != source_file_content

    @pytest.mark.asyncio
    async def test_lite_candidate_adopt_updates_status(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite 候选稿 adopt 后状态更新为 adopted"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写后的新内容。",
            source_mode="lite",
        )

        # adopt 候选稿
        await candidate_service.adopt_candidate(project_id, candidate_info.id)

        # 重新获取候选稿信息
        updated_info = await candidate_service.get_candidate(project_id, candidate_info.id)

        # 验证：状态更新为 adopted
        assert updated_info is not None
        assert updated_info.status == CandidateStatus.ADOPTED
        assert updated_info.adopted_at is not None

    @pytest.mark.asyncio
    async def test_lite_candidate_adopt_conflict_detection(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite 候选稿 adopt 时检测 hash 冲突"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写后的新内容。",
            source_mode="lite",
        )

        # 在 adopt 前修改原文
        await file_service.write_file(full_source, "被其他操作修改的原文内容。")

        # adopt 候选稿（应该冲突）
        result = await candidate_service.adopt_candidate(project_id, candidate_info.id)

        # 验证：返回冲突
        assert result == "conflict"

        # 验证：状态更新为 rejected
        updated_info = await candidate_service.get_candidate(project_id, candidate_info.id)
        assert updated_info is not None
        assert updated_info.status == CandidateStatus.REJECTED


class TestLiteCandidateListAndDetail:
    """测试 Lite 候选稿列表和详情"""

    @pytest.mark.asyncio
    async def test_list_lite_candidates(self, file_service, candidate_service, project_id, source_file_path, source_file_content):
        """列出 Lite 候选稿"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建多个候选稿
        await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="重写版本1。",
            source_mode="lite",
        )
        await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.POLISH,
            content="润色版本1。",
            source_mode="lite",
        )

        # 列出所有候选稿
        candidates = await candidate_service.list_candidates(project_id)

        # 验证
        assert len(candidates) == 2

        # 验证：source_mode 都是 lite
        for c in candidates:
            assert c.source_mode == "lite"

    @pytest.mark.asyncio
    async def test_get_lite_candidate_content(self, file_service, candidate_service, project_id, source_file_path, source_file_content):
        """获取 Lite 候选稿内容"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        expected_content = "这是候选稿的完整内容。"
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content=expected_content,
            source_mode="lite",
        )

        # 获取候选稿内容
        content = await candidate_service.get_candidate_content(project_id, candidate_info.id)

        # 验证
        assert content == expected_content

    @pytest.mark.asyncio
    async def test_delete_lite_candidate(self, file_service, candidate_service, project_id, source_file_path, source_file_content):
        """删除 Lite 候选稿"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建候选稿
        candidate_info = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="将被删除的候选稿。",
            source_mode="lite",
        )

        # 删除候选稿
        success = await candidate_service.delete_candidate(project_id, candidate_info.id)

        # 验证
        assert success is True

        # 验证：状态更新为 discarded
        updated_info = await candidate_service.get_candidate(project_id, candidate_info.id)
        assert updated_info is not None
        assert updated_info.status == CandidateStatus.DISCARDED


class TestLiteCandidateVsProfessional:
    """测试 Lite 和 Professional 候选稿共存"""

    @pytest.mark.asyncio
    async def test_lite_and_professional_candidates_in_same_list(
        self, file_service, candidate_service, project_id, source_file_path, source_file_content
    ):
        """Lite 和 Professional 候选稿在同一个列表中"""
        # 写入源文件
        full_source = f"{project_id}/{source_file_path}"
        await file_service.write_file(full_source, source_file_content)

        # 创建 Lite 候选稿
        lite_candidate = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="Lite 重写版本。",
            source_mode="lite",
        )

        # 创建 Professional 候选稿
        pro_candidate = await candidate_service.create_candidate(
            project_id=project_id,
            source_path=source_file_path,
            action=CandidateAction.REWRITE,
            content="Professional 重写版本。",
            source_mode="professional",
        )

        # 列出所有候选稿
        candidates = await candidate_service.list_candidates(project_id)

        # 验证
        assert len(candidates) == 2

        # 验证：可以通过 source_mode 区分来源
        lite_candidates = [c for c in candidates if c.source_mode == "lite"]
        pro_candidates = [c for c in candidates if c.source_mode == "professional"]

        assert len(lite_candidates) == 1
        assert len(pro_candidates) == 1
        assert lite_candidates[0].id == lite_candidate.id
        assert pro_candidates[0].id == pro_candidate.id
