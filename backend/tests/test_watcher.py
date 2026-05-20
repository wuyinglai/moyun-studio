"""墨韵 - 文件监听器单元测试

测试要点：
1. start/stop 生命周期
2. 文件事件转发到 EventBus
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.watcher import FileWatcher


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def watcher(tmp_path, mock_event_bus):
    return FileWatcher(tmp_path, mock_event_bus)


class TestFileWatcherStartStop:
    """start/stop 生命周期测试"""

    @pytest.mark.asyncio
    async def test_start_creates_task(self, watcher):
        assert watcher._watch_task is None
        await watcher.start()
        assert watcher._watch_task is not None
        assert not watcher._watch_task.done()
        await watcher.stop()
        assert watcher._watch_task is None

    @pytest.mark.asyncio
    async def test_stop_without_start_no_error(self, watcher):
        await watcher.stop()
        assert watcher._watch_task is None

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, watcher):
        await watcher.start()
        await watcher.stop()
        assert watcher._watch_task is None


class TestFileWatcherEvents:
    """文件事件发布测试"""

    @pytest.mark.asyncio
    async def test_publishes_added_event(self, tmp_path, mock_event_bus):
        """验证 added 事件被发布到 EventBus"""
        watcher = FileWatcher(tmp_path, mock_event_bus)

        # Mock watchfiles.watch 返回一个添加事件（同步 generator）
        changes = [(1, str(tmp_path / "new.md"))]  # 1 = Change.added

        with patch("backend.core.watcher.watchfiles.watch") as mock_watch:
            def mock_watch_iter(*args, **kwargs):
                yield changes
            mock_watch.return_value = mock_watch_iter()

            await watcher.start()
            # 给事件循环一个机会运行 _watch_loop
            await asyncio.sleep(0.1)
            await watcher.stop()

        mock_event_bus.publish.assert_awaited_once()
        args, _ = mock_event_bus.publish.call_args
        assert args[0] == "file:created"
        assert args[1]["path"] == "new.md"

    @pytest.mark.asyncio
    async def test_publishes_modified_event(self, tmp_path, mock_event_bus):
        watcher = FileWatcher(tmp_path, mock_event_bus)
        changes = [(2, str(tmp_path / "edit.md"))]  # 2 = Change.modified

        with patch("backend.core.watcher.watchfiles.watch") as mock_watch:
            def mock_watch_iter(*args, **kwargs):
                yield changes
            mock_watch.return_value = mock_watch_iter()

            await watcher.start()
            await asyncio.sleep(0.1)
            await watcher.stop()

        mock_event_bus.publish.assert_awaited_once()
        assert mock_event_bus.publish.call_args[0][0] == "file:modified"

    @pytest.mark.asyncio
    async def test_publishes_deleted_event(self, tmp_path, mock_event_bus):
        watcher = FileWatcher(tmp_path, mock_event_bus)
        changes = [(3, str(tmp_path / "gone.md"))]  # 3 = Change.deleted

        with patch("backend.core.watcher.watchfiles.watch") as mock_watch:
            def mock_watch_iter(*args, **kwargs):
                yield changes
            mock_watch.return_value = mock_watch_iter()

            await watcher.start()
            await asyncio.sleep(0.1)
            await watcher.stop()

        mock_event_bus.publish.assert_awaited_once()
        assert mock_event_bus.publish.call_args[0][0] == "file:deleted"

    @pytest.mark.asyncio
    async def test_unknown_change_type_skipped(self, tmp_path, mock_event_bus):
        watcher = FileWatcher(tmp_path, mock_event_bus)
        changes = [(99, str(tmp_path / "unknown.md"))]  # 99 = unknown

        with patch("backend.core.watcher.watchfiles.watch") as mock_watch:
            def mock_watch_iter(*args, **kwargs):
                yield changes
            mock_watch.return_value = mock_watch_iter()

            await watcher.start()
            await asyncio.sleep(0.1)
            await watcher.stop()

        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_path_outside_workspace_uses_absolute(self, tmp_path, mock_event_bus):
        """路径不在工作区内时保留绝对路径"""
        watcher = FileWatcher(tmp_path, mock_event_bus)
        outside_path = Path("C:/outside/file.md")
        changes = [(1, str(outside_path))]

        with patch("backend.core.watcher.watchfiles.watch") as mock_watch:
            def mock_watch_iter(*args, **kwargs):
                yield changes
            mock_watch.return_value = mock_watch_iter()

            await watcher.start()
            await asyncio.sleep(0.1)
            await watcher.stop()

        mock_event_bus.publish.assert_awaited_once()
        assert mock_event_bus.publish.call_args[0][1]["path"] == str(outside_path)

    @pytest.mark.asyncio
    async def test_watch_loop_exception_logged(self, tmp_path, mock_event_bus, caplog):
        """_watch_loop 异常被记录日志不崩溃"""
        watcher = FileWatcher(tmp_path, mock_event_bus)

        with patch("backend.core.watcher.watchfiles.watch") as mock_watch:
            # 模拟抛出异常（同步 generator）
            class MockWatchIter:
                def __iter__(self):
                    return self
                def __next__(self):
                    raise Exception("watch error")
            mock_watch.return_value = MockWatchIter()

            await watcher.start()
            await asyncio.sleep(0.1)
            await watcher.stop()

        assert "文件监听异常" in caplog.text
