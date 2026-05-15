"""墨韵 - 文件监听器

监听文件系统变化，发布事件到EventBus。
使用 watchfiles（原生异步）替代 watchdog。
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import watchfiles

if TYPE_CHECKING:
    from backend.core.event_bus import EventBus


class FileWatcher:
    """文件监听器

    职责：
    - 监听文件系统变化（使用 watchfiles，原生异步）
    - 将变化转换为事件发布到 EventBus

    不负责：
    - 事件发布的具体逻辑（由 EventBus 处理）
    - SSE 推送（由 API 层处理）
    """

    def __init__(self, workspace_path: Path, event_bus: "EventBus"):
        self.workspace = Path(workspace_path)
        self.event_bus = event_bus
        self._watch_task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动监听（异步）"""
        self._watch_task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """停止监听"""
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

    async def _watch_loop(self) -> None:
        """异步监听循环"""
        try:
            gen = watchfiles.watch(
                str(self.workspace),
                recursive=True,
                watch_filter=None,
                stop_event=None,
            )
            loop = asyncio.get_event_loop()
            while True:
                def _next():
                    try: return next(gen)
                    except StopIteration: return None
                changes = await loop.run_in_executor(None, _next)
                if changes is None:
                    break
                for change in changes:
                    kind, path = change
                    # watchfiles.Change: added=1, modified=2, deleted=3
                    if kind == watchfiles.Change.added:
                        event_type = "file:created"
                    elif kind == watchfiles.Change.modified:
                        event_type = "file:modified"
                    elif kind == watchfiles.Change.deleted:
                        event_type = "file:deleted"
                    else:
                        continue
                    # 转换为相对路径
                    try:
                        rel = Path(path).relative_to(self.workspace).as_posix()
                    except ValueError:
                        rel = path
                    await self.event_bus.publish(event_type, {"path": rel})
        except asyncio.CancelledError:
            pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("文件监听异常: %s", e)
