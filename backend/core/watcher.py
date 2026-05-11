"""墨韵 - 文件监听器

监听文件系统变化，发布事件到EventBus。
仅负责监听，不负责事件发布逻辑。
"""

from pathlib import Path
from typing import TYPE_CHECKING

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
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def __init__(watcher: FileWatcher):
                self._watcher = watcher

            def on_created(self, event):
                if not event.is_directory:
                    self._watcher.event_bus.publish(
                        "file:created",
                        {"path": event.src_path}
                    )

            def on_modified(self, event):
                if not event.is_directory:
                    self._watcher.event_bus.publish(
                        "file:modified",
                        {"path": event.src_path}
                    )

            def on_deleted(self, event):
                if not event.is_directory:
                    self._watcher.event_bus.publish(
                        "file:deleted",
                        {"path": event.src_path}
                    )

            def on_moved(self, event):
                if not event.is_directory:
                    self._watcher.event_bus.publish(
                        "file:modified",
                        {"path": event.dest_path, "old_path": event.src_path}
                    )

        self._observer = Observer()
        handler = Handler()
        handler._watcher = self
        self._observer.schedule(handler, str(self.workspace), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        """停止监听"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
