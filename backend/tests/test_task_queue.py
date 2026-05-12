"""任务队列单元测试 — 覆盖任务状态流转和执行流程

测试要点：
1. 入队/出队（正常 + 空队列超时）
2. 任务状态流转：pending → running → completed/failed/cancelled
3. TaskExecutor 正常执行流程
4. ContextLengthError 触发场景
5. 并发控制（running_count）
"""

import asyncio
import pytest
from unittest.mock import AsyncMock

from backend.core.task_queue import TaskQueue, TaskExecutor, run_task_worker
from backend.core.exceptions import ContextLengthError


class TestTaskQueueBasic:
    """TaskQueue 基础入队/出队"""

    @pytest.mark.asyncio
    async def test_enqueue_adds_task(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate", "template_type": "chapter"})
        task = tq.get_task(task_id)
        assert task is not None
        assert task["status"] == "pending"
        assert task["template_category"] == "generate"
        assert task["template_type"] == "chapter"

    @pytest.mark.asyncio
    async def test_enqueue_generates_unique_ids(self):
        tq = TaskQueue()
        id1 = await tq.enqueue({"template_category": "generate"})
        id2 = await tq.enqueue({"template_category": "generate"})
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_enqueue_includes_timestamps(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        task = tq.get_task(task_id)
        assert "created_at" in task

    @pytest.mark.asyncio
    async def test_dequeue_returns_none_on_timeout(self):
        tq = TaskQueue()
        result = await tq.dequeue()
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_returns_task_id(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        dequeued = await tq.dequeue()
        assert dequeued == task_id

    @pytest.mark.asyncio
    async def test_dequeue_fifo_order(self):
        tq = TaskQueue()
        id1 = await tq.enqueue({"template_category": "generate", "template_type": "chapter"})
        id2 = await tq.enqueue({"template_category": "generate", "template_type": "outline"})
        assert await tq.dequeue() == id1
        assert await tq.dequeue() == id2


class TestTaskQueueStateFlow:
    """任务状态流转测试"""

    @pytest.mark.asyncio
    async def test_pending_to_running(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        task = tq.get_task(task_id)
        assert task["status"] == "running"
        assert "started_at" in task

    @pytest.mark.asyncio
    async def test_running_to_completed(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        tq.complete_task(task_id, {"content": "result"})
        task = tq.get_task(task_id)
        assert task["status"] == "completed"
        assert task["result"] == {"content": "result"}
        assert "completed_at" in task

    @pytest.mark.asyncio
    async def test_running_to_failed(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        tq.fail_task(task_id, "LLM timeout")
        task = tq.get_task(task_id)
        assert task["status"] == "failed"
        assert task["error"] == "LLM timeout"

    @pytest.mark.asyncio
    async def test_pending_to_cancelled(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        result = tq.cancel_task(task_id)
        assert result is True
        task = tq.get_task(task_id)
        assert task["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_running_to_cancelled(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        result = tq.cancel_task(task_id)
        assert result is True
        task = tq.get_task(task_id)
        assert task["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cannot_cancel_completed_task(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        tq.complete_task(task_id, {"content": "done"})
        result = tq.cancel_task(task_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_cannot_cancel_nonexistent_task(self):
        tq = TaskQueue()
        result = tq.cancel_task("nonexistent")
        assert result is False


class TestTaskQueueRunningCount:
    """并发控制测试"""

    @pytest.mark.asyncio
    async def test_running_count_zero_initially(self):
        tq = TaskQueue()
        assert tq.running_count == 0

    @pytest.mark.asyncio
    async def test_running_count_increments(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        assert tq.running_count == 1

    @pytest.mark.asyncio
    async def test_running_count_decrements_on_complete(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        tq.complete_task(task_id, {"content": "done"})
        assert tq.running_count == 0

    @pytest.mark.asyncio
    async def test_running_count_decrements_on_fail(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        tq.fail_task(task_id, "error")
        assert tq.running_count == 0

    @pytest.mark.asyncio
    async def test_running_count_decrements_on_cancel(self):
        tq = TaskQueue()
        task_id = await tq.enqueue({"template_category": "generate"})
        tq.start_task(task_id)
        tq.cancel_task(task_id)
        assert tq.running_count == 0


class TestTaskQueueGetMethods:
    """任务获取方法测试"""

    @pytest.mark.asyncio
    async def test_get_task_nonexistent(self):
        tq = TaskQueue()
        assert tq.get_task("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_all_tasks_empty(self):
        tq = TaskQueue()
        assert tq.get_all_tasks() == []

    @pytest.mark.asyncio
    async def test_get_all_tasks_returns_all(self):
        tq = TaskQueue()
        await tq.enqueue({"template_category": "a"})
        await tq.enqueue({"template_category": "b"})
        assert len(tq.get_all_tasks()) == 2


class TestTaskExecutor:
    """TaskExecutor 测试"""

    @pytest.mark.asyncio
    async def test_execute_task_success(self, mock_llm_service, mock_file_service, mock_event_bus):
        executor = TaskExecutor(mock_llm_service, mock_file_service, mock_event_bus)

        task = {
            "task_id": "test-1",
            "template_category": "generate",
            "template_type": "chapter",
            "variables": {"genre": "玄幻", "theme": "成长"},
            "target_file": "chapters/chapter-01.md",
        }

        result = await executor.execute_task(task)
        assert result["task_id"] == "test-1"
        assert "content" in result
        mock_event_bus.publish.assert_any_call("task:started", {"task_id": "test-1", "template": "generate/chapter"})
        mock_event_bus.publish.assert_any_call("task:completed", {"task_id": "test-1", "result": result})

    @pytest.mark.asyncio
    async def test_execute_task_failure_publishes_event(self, mock_llm_service, mock_file_service, mock_event_bus):
        # 让 count_tokens 抛异常模拟失败
        mock_llm_service.count_tokens = AsyncMock(side_effect=Exception("Token计数失败"))

        executor = TaskExecutor(mock_llm_service, mock_file_service, mock_event_bus)

        task = {
            "task_id": "test-fail",
            "template_category": "generate",
            "template_type": "chapter",
            "variables": {},
        }

        with pytest.raises(Exception, match="Token计数失败"):
            await executor.execute_task(task)

        mock_event_bus.publish.assert_any_call("task:failed", {
            "task_id": "test-fail",
            "error": "Token计数失败",
        })

    @pytest.mark.asyncio
    async def test_execute_task_context_length_error(self, mock_llm_service, mock_file_service, mock_event_bus):
        # 模拟 token 超限
        mock_llm_service.count_tokens = AsyncMock(return_value=200000)

        executor = TaskExecutor(mock_llm_service, mock_file_service, mock_event_bus)

        task = {
            "task_id": "test-overflow",
            "template_category": "generate",
            "template_type": "chapter",
            "variables": {"genre": "玄幻"},
        }

        with pytest.raises(ContextLengthError):
            await executor.execute_task(task)

    @pytest.mark.asyncio
    async def test_execute_task_without_target_file(self, mock_llm_service, mock_file_service, mock_event_bus):
        executor = TaskExecutor(mock_llm_service, mock_file_service, mock_event_bus)

        task = {
            "task_id": "test-no-file",
            "template_category": "generate",
            "template_type": "chapter",
            "variables": {},
            # 无 target_file
        }

        result = await executor.execute_task(task)
        assert result["target_file"] is None
        mock_file_service.write_file.assert_not_called()


class TestTaskQueueSetExecutor:
    """set_executor 测试"""

    @pytest.mark.asyncio
    async def test_set_executor(self, mock_llm_service, mock_file_service, mock_event_bus):
        tq = TaskQueue()
        executor = TaskExecutor(mock_llm_service, mock_file_service, mock_event_bus)
        tq.set_executor(executor)
        assert tq._executor is executor
