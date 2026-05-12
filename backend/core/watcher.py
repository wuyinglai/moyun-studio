"""墨韵 - 文件监听器

监听文件系统变化，发布事件到EventBus。
仅负责监听，不负责事件发布逻辑。
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from backend.core.event_bus import EventBus


class FileWatcher:
    """文件监听器

    职责：
    - 监听文件系统变化（使用watchdog）
    - 将变化转换为事件发布到EventBus

    不负责：
    - 事件发布的具体逻辑（由EventBus处理）
    - SSE推送（由API层处理）
    """

    def __init__(self, workspace_path: Path, event_bus: "EventBus"):
        self.workspace = Path(workspace_path)
        self.event_bus = event_bus
        self._observer = None

    def start(self) -> None:
        """启动监听"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        class Handler(FileSystemEventHandler):
            def __init__(self, watcher: FileWatcher, loop: asyncio.AbstractEventLoop):
                super().__init__()
                self._watcher = watcher
                self._loop = loop

            def _publish(self, event_type: str, data: dict) -> None:
                """从 watchdog 线程向异步 EventBus 发布事件的同步包装"""
                asyncio.run_coroutine_threadsafe(
                    self._watcher.event_bus.publish(event_type, data),
                    self._loop,
                )

            def on_created(self, event):
                if not event.is_directory:
                    self._publish("file:created", {"path": event.src_path})

            def on_modified(self, event):
                if not event.is_directory:
                    self._publish("file:modified", {"path": event.src_path})

            def on_deleted(self, event):
                if not event.is_directory:
                    self._publish("file:deleted", {"path": event.src_path})

            def on_moved(self, event):
                if not event.is_directory:
                    self._publish("file:modified",
                                  {"path": event.dest_path, "old_path": event.src_path})

        self._observer = Observer()
        handler = Handler(self, loop)
        self._observer.schedule(handler, str(self.workspace), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        """停止监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
