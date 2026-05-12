"""墨韵 - 事件总线

独立的事件发布/订阅系统。
与FileWatcher解耦，可被其他模块复用。
"""

from typing import Any, AsyncGenerator
import asyncio
import uuid


class EventBus:
    """事件总线 - 事件发布订阅"""

    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._all_subscribers: set[asyncio.Queue] = set()

    def subscribe(
        self,
        event_types: list[str] | None = None
    ) -> tuple[str, asyncio.Queue]:
        """订阅事件

        Args:
            event_types: 关注的EventTypes列表，None表示全部

        Returns:
            (client_id, queue) - 订阅者ID和消息队列
        """
        client_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        if event_types is None:
            self._all_subscribers.add(queue)
        else:
            for event_type in event_types:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = set()
                self._subscribers[event_type].add(queue)

        return client_id, queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """取消订阅"""
        if queue in self._all_subscribers:
            self._all_subscribers.discard(queue)
        for queues in self._subscribers.values():
            queues.discard(queue)

    async def publish(self, event_type: str, data: dict) -> None:
        """发布事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        message = {
            "type": event_type,
            "data": data
        }

        dead_queues: set[asyncio.Queue] = set()

        for queue in self._all_subscribers:
            try:
                await asyncio.wait_for(queue.put(message), timeout=1.0)
            except asyncio.TimeoutError:
                dead_queues.add(queue)
            except Exception:
                dead_queues.add(queue)

        if event_type in self._subscribers:
            for queue in self._subscribers[event_type]:
                try:
                    await asyncio.wait_for(queue.put(message), timeout=1.0)
                except asyncio.TimeoutError:
                    dead_queues.add(queue)
                except Exception:
                    dead_queues.add(queue)

        for queue in dead_queues:
            self.unsubscribe(queue)


class EventTypes:
    """事件类型常量"""

    FILE_CREATED = "file:created"
    FILE_MODIFIED = "file:modified"
    FILE_DELETED = "file:deleted"

    TASK_STARTED = "task:started"
    TASK_PROGRESS = "task:progress"
    TASK_COMPLETED = "task:completed"
    TASK_FAILED = "task:failed"

    PROJECT_CREATED = "project:created"
    PROJECT_UPDATED = "project:updated"

    BACKUP_CREATED = "backup:created"
    BACKUP_RESTORED = "backup:restored"
