"""快照管理单元测试

测试要点：
1. create_snapshot（创建成功，自动生成 ID）
2. list_snapshots（空列表、有快照）
3. restore_snapshot（正常恢复、不存在快照）
4. compare_versions（正常对比、不存在）
5. index 自动裁剪（最多 50 条）
6. ResourceNotFoundError
"""

import json
from unittest.mock import AsyncMock

import pytest

from backend.core.exceptions import MoyunFileNotFoundError, ResourceNotFoundError
from backend.core.snapshot import Snapshot, SnapshotManager


class TestSnapshotData:
    """Snapshot 数据类测试"""

    def test_init(self):
        snap = Snapshot(
            snapshot_id="snap-001",
            file_path="chapters/test.md",
            content="# 测试内容\n\n一段文本",
            label="v1.0",
            created_at="2026-01-01T00:00:00",
        )
        assert snap.snapshot_id == "snap-001"
        assert snap.file_path == "chapters/test.md"
        assert snap.label == "v1.0"

    def test_to_dict(self):
        snap = Snapshot(
            snapshot_id="snap-002",
            file_path="chapters/test.md",
            content="ABCDE",
            label=None,
            created_at="2026-01-01T00:00:00",
        )
        d = snap.to_dict()
        assert d["snapshot_id"] == "snap-002"
        assert d["file_path"] == "chapters/test.md"
        assert d["label"] is None
        assert d["word_count"] == 5  # len("ABCDE")


class TestSnapshotManagerCreate:
    """快照创建测试"""

    @pytest.mark.asyncio
    async def test_create_snapshot(self, mock_file_service):
        mock_file_service.read_file = AsyncMock(
            return_value=("# 测试章节\n\n内容", {"title": "第一章", "word_count": 100}, 1700000000.0)
        )
        mock_file_service.write_file = AsyncMock()

        mgr = SnapshotManager(mock_file_service)
        snap = await mgr.create_snapshot("chapters/test.md", label="第一次快照")

        assert snap is not None
        assert snap.file_path == "chapters/test.md"
        assert snap.label == "第一次快照"
        assert len(snap.snapshot_id) == 8  # uuid4()[:8]
        assert "# 测试章节" in snap.content

    @pytest.mark.asyncio
    async def test_create_snapshot_without_label(self, mock_file_service):
        mock_file_service.read_file = AsyncMock(
            return_value=("内容", None, 1700000000.0)
        )
        mock_file_service.write_file = AsyncMock()

        mgr = SnapshotManager(mock_file_service)
        snap = await mgr.create_snapshot("chapters/test.md")
        assert snap.label is None

    @pytest.mark.asyncio
    async def test_create_snapshot_writes_files(self, mock_file_service):
        mock_file_service.read_file = AsyncMock(
            return_value=("内容", None, 1700000000.0)
        )
        mock_file_service.write_file = AsyncMock()

        mgr = SnapshotManager(mock_file_service)
        await mgr.create_snapshot("chapters/test.md")

        # 应该写入了快照文件和索引文件
        assert mock_file_service.write_file.call_count == 2


class TestSnapshotManagerList:
    """快照列表测试"""

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_file_service):
        mock_file_service.read_file = AsyncMock(side_effect=MoyunFileNotFoundError("not found"))

        mgr = SnapshotManager(mock_file_service)
        snapshots = await mgr.list_snapshots("chapters/test.md")
        assert snapshots == []

    @pytest.mark.asyncio
    async def test_list_with_snapshots(self, mock_file_service):
        index_data = {
            "file_path": "chapters/test.md",
            "snapshots": [
                {"snapshot_id": "s1", "file_path": "chapters/test.md", "label": "v1", "created_at": "2026-01-01", "word_count": 100},
                {"snapshot_id": "s2", "file_path": "chapters/test.md", "label": "v2", "created_at": "2026-01-02", "word_count": 150},
            ],
        }
        mock_file_service.read_file = AsyncMock(return_value=(json.dumps(index_data, ensure_ascii=False), None, 1700000000.0))

        mgr = SnapshotManager(mock_file_service)
        snapshots = await mgr.list_snapshots("chapters/test.md")
        assert len(snapshots) == 2

    @pytest.mark.asyncio
    async def test_list_exception_returns_empty(self, mock_file_service):
        mock_file_service.read_file = AsyncMock(side_effect=Exception("generic error"))

        mgr = SnapshotManager(mock_file_service)
        snapshots = await mgr.list_snapshots("chapters/test.md")
        assert snapshots == []


class TestSnapshotManagerRestore:
    """快照恢复测试"""

    @pytest.mark.asyncio
    async def test_restore_not_found(self, mock_file_service):
        mock_file_service.read_file = AsyncMock(return_value=(json.dumps({"snapshots": []}), None, 1700000000.0))

        mgr = SnapshotManager(mock_file_service)
        with pytest.raises(ResourceNotFoundError):
            await mgr.restore_snapshot("nonexistent")

    @pytest.mark.asyncio
    async def test_restore_uses_file_service(self, mock_file_service, tmp_path):
        # _find_snapshot uses direct filesystem access, so write snapshot file to disk
        # 使用与 SnapshotManager.SNAPSHOT_DIR 一致的路径
        snap_dir = tmp_path / "backup" / "snapshots" / "chapters" / "test.md"
        snap_dir.mkdir(parents=True, exist_ok=True)
        snapshot_data = {
            "snapshot_id": "snap-001",
            "file_path": "chapters/test.md",
            "content": "# 恢复的内容",
            "metadata": {"title": "第一章"},
            "label": "v1",
            "created_at": "2026-01-01",
        }
        (snap_dir / "snap-001.json").write_text(
            json.dumps(snapshot_data, ensure_ascii=False), encoding="utf-8"
        )

        # 设置 file_service.workspace 以便 _find_snapshot 能找到正确路径
        mock_file_service.workspace = str(tmp_path)

        mgr = SnapshotManager(mock_file_service)
        await mgr.restore_snapshot("snap-001")

        mock_file_service.write_file.assert_called_once()


class TestSnapshotManagerCompare:
    """版本对比测试"""

    @pytest.mark.asyncio
    async def test_compare_not_found(self, mock_file_service):
        mock_file_service.read_file = AsyncMock(return_value=(json.dumps({"snapshots": []}), None, 1700000000.0))

        mgr = SnapshotManager(mock_file_service)
        with pytest.raises(ResourceNotFoundError):
            await mgr.compare_versions("s1", "s2")


class TestSnapshotManagerIndexClip:
    """Index 裁剪测试"""

    @pytest.mark.asyncio
    async def test_index_clips_to_50(self, mock_file_service):
        # 构建60条快照
        snapshots = []
        for i in range(60):
            snapshots.append({"snapshot_id": f"s{i}", "word_count": 100 + i})

        old_index = json.dumps({"file_path": "chapters/test.md", "snapshots": snapshots}, ensure_ascii=False)

        mock_file_service.read_file = AsyncMock(return_value=(old_index, None, 1700000000.0))
        mock_file_service.write_file = AsyncMock()

        mgr = SnapshotManager(mock_file_service)

        # 调用 _update_index 添加第61条
        await mgr._update_index("chapters/test.md", {"snapshot_id": "s61", "word_count": 161})

        # write_file 应该被调用，写入的内容不超过50条
        call_args = mock_file_service.write_file.call_args[0]
        written_content = call_args[1]
        written_data = json.loads(written_content)
        assert len(written_data["snapshots"]) <= 50
