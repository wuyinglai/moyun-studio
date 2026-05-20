"""事件总线单元测试 — 覆盖订阅/发布/取消/死队列

测试要点：
1. 订阅指定类型和全部类型
2. 发布事件到指定订阅者
3. 取消订阅
4. 死队列检测和自动清理
5. 队列满时的超时处理
6. 多订阅者并发发布
7. EventTypes 常量验证
"""

import asyncio

import pytest

from backend.core.event_bus import EventBus, EventTypes


class TestEventBusSubscribe:
    """订阅功能测试"""

    def test_subscribe_all_returns_client_id_and_queue(self):
        bus = EventBus()
        client_id, queue = bus.subscribe()
        assert isinstance(client_id, str)
        assert len(client_id) > 0
        assert isinstance(queue, asyncio.Queue)

    def test_subscribe_all_adds_to_all_subscribers(self):
        bus = EventBus()
        _, queue = bus.subscribe()
        assert queue in bus._all_subscribers

    def test_subscribe_specific_types(self):
        bus = EventBus()
        _, queue = bus.subscribe(event_types=["file:created", "file:modified"])
        assert "file:created" in bus._subscribers
        assert "file:modified" in bus._subscribers
        assert queue in bus._subscribers["file:created"]
        assert queue in bus._subscribers["file:modified"]

    def test_subscribe_multiple_types_creates_sets(self):
        bus = EventBus()
        _, q1 = bus.subscribe(event_types=["file:created"])
        _, q2 = bus.subscribe(event_types=["file:created"])
        assert len(bus._subscribers["file:created"]) == 2

    def test_different_clients_get_different_ids(self):
        bus = EventBus()
        cid1, _ = bus.subscribe()
        cid2, _ = bus.subscribe()
        assert cid1 != cid2


class TestEventBusUnsubscribe:
    """取消订阅测试"""

    def test_unsubscribe_from_all(self):
        bus = EventBus()
        _, queue = bus.subscribe()
        bus.unsubscribe(queue)
        assert queue not in bus._all_subscribers

    def test_unsubscribe_from_specific_type(self):
        bus = EventBus()
        _, queue = bus.subscribe(event_types=["file:created"])
        bus.unsubscribe(queue)
        assert queue not in bus._subscribers["file:created"]

    def test_unsubscribe_nonexistent_queue_safe(self):
        bus = EventBus()
        fake_queue = asyncio.Queue()
        bus.unsubscribe(fake_queue)  # 不应抛异常

    def test_unsubscribe_twice_safe(self):
        bus = EventBus()
        _, queue = bus.subscribe()
        bus.unsubscribe(queue)
        bus.unsubscribe(queue)  # 幂等操作


class TestEventBusPublish:
    """发布事件测试"""

    @pytest.mark.asyncio
    async def test_publish_to_all_subscriber(self):
        bus = EventBus()
        _, queue = bus.subscribe()
        await bus.publish("file:created", {"path": "test.md"})
        msg = queue.get_nowait()
        assert msg["type"] == "file:created"
        assert msg["data"] == {"path": "test.md"}

    @pytest.mark.asyncio
    async def test_publish_to_specific_type_subscriber(self):
        bus = EventBus()
        _, queue = bus.subscribe(event_types=["file:created"])
        await bus.publish("file:created", {"path": "test.md"})
        msg = queue.get_nowait()
        assert msg["type"] == "file:created"

    @pytest.mark.asyncio
    async def test_publish_not_sent_to_wrong_type(self):
        bus = EventBus()
        _, queue = bus.subscribe(event_types=["file:created"])
        await bus.publish("task:started", {"task_id": "1"})
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_publish_to_mixed_subscribers(self):
        bus = EventBus()
        _, q_all = bus.subscribe()  # 订阅全部
        _, q_specific = bus.subscribe(event_types=["file:created"])

        await bus.publish("file:created", {"path": "test.md"})

        # q_all 和 q_specific 都应该收到
        msg_all = q_all.get_nowait()
        msg_specific = q_specific.get_nowait()
        assert msg_all["type"] == "file:created"
        assert msg_specific["type"] == "file:created"

    @pytest.mark.asyncio
    async def test_publish_non_matching_type_only_all_subscriber(self):
        bus = EventBus()
        _, q_all = bus.subscribe()
        _, q_specific = bus.subscribe(event_types=["file:modified"])

        await bus.publish("file:created", {"path": "test.md"})

        assert not q_all.empty()  # 全订阅者收到
        assert q_specific.empty()  # 特定类型订阅者不应收到


class TestEventBusDeadQueue:
    """死队列检测测试"""

    @pytest.mark.asyncio
    async def test_dead_queue_removed_on_timeout(self):
        """队列满时发布超时，应被自动清理"""
        bus = EventBus()
        # 创建一个只有1个位置的队列，填满它
        small_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        bus._all_subscribers.add(small_queue)
        small_queue.put_nowait({"type": "x", "data": {}})  # 填满

        # 发布事件，应该超时并从订阅者中移除
        await bus.publish("file:created", {"path": "test.md"})
        assert small_queue not in bus._all_subscribers

    @pytest.mark.asyncio
    async def test_dead_queue_in_specific_subscribers(self):
        bus = EventBus()
        small_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        bus._subscribers["file:created"] = {small_queue}
        small_queue.put_nowait({"type": "x", "data": {}})

        await bus.publish("file:created", {"path": "test.md"})
        assert small_queue not in bus._subscribers["file:created"]


class TestEventBusConcurrent:
    """并发测试"""

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_events(self):
        bus = EventBus()
        _, q1 = bus.subscribe()
        _, q2 = bus.subscribe()
        _, q3 = bus.subscribe()

        await bus.publish("task:completed", {"task_id": "t1", "result": "ok"})

        for q in [q1, q2, q3]:
            msg = q.get_nowait()
            assert msg["type"] == "task:completed"

    @pytest.mark.asyncio
    async def test_event_types_mixed_subscriptions(self):
        bus = EventBus()
        _, q_all = bus.subscribe()
        _, q_file = bus.subscribe(event_types=["file:created"])
        _, q_task = bus.subscribe(event_types=["task:started"])

        await bus.publish("file:created", {"path": "a.md"})
        await bus.publish("task:started", {"task_id": "1"})
        await bus.publish("project:created", {"project_id": "p1"})

        # q_all 收到3条
        assert q_all.qsize() == 3
        # q_file 收到1条
        assert q_file.qsize() == 1
        # q_task 收到1条
        assert q_task.qsize() == 1


class TestEventTypes:
    """事件类型常量测试"""

    def test_file_event_types(self):
        assert EventTypes.FILE_CREATED == "file:created"
        assert EventTypes.FILE_MODIFIED == "file:modified"
        assert EventTypes.FILE_DELETED == "file:deleted"

    def test_task_event_types(self):
        assert EventTypes.TASK_STARTED == "task:started"
        assert EventTypes.TASK_PROGRESS == "task:progress"
        assert EventTypes.TASK_COMPLETED == "task:completed"
        assert EventTypes.TASK_FAILED == "task:failed"

    def test_project_event_types(self):
        assert EventTypes.PROJECT_CREATED == "project:created"
        assert EventTypes.PROJECT_UPDATED == "project:updated"

    def test_backup_event_types(self):
        assert EventTypes.BACKUP_CREATED == "backup:created"
        assert EventTypes.BACKUP_RESTORED == "backup:restored"
