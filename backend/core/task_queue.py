"""墨韵 - 任务执行器

实际执行生成任务的模块。
TaskQueue只负责状态管理，TaskExecutor负责具体执行。
"""

from typing import Any, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from backend.services.base import LLMServiceInterface, FileServiceInterface, EventBusInterface


class TaskExecutor:
    """任务执行器"""

    def __init__(
        self,
        llm_service: "LLMServiceInterface",
        file_service: "FileServiceInterface",
        event_bus: "EventBusInterface",
    ):
        self.llm = llm_service
        self.file_service = file_service
        self.event_bus = event_bus

    async def execute_task(self, task: dict) -> dict:
        """执行单个任务

        Args:
            task: 任务数据，包含:
                - task_id: str
                - template_category: str
                - template_type: str
                - variables: dict
                - target_file: str | None

        Returns:
            执行结果 dict
        """
        task_id = task["task_id"]
        template = f"{task['template_category']}/{task['template_type']}"

        try:
            await self.event_bus.publish("task_started", {
                "task_id": task_id,
                "template": template
            })

            variables = task.get("variables", {})

            rendered_prompt = await self._render_prompt(
                task["template_category"],
                task["template_type"],
                variables
            )

            token_count = await self.llm.count_tokens(rendered_prompt)
            if token_count > 128000:
                raise ValueError(f"Context too long: {token_count} tokens")

            generated_content = await self._generate_content(
                rendered_prompt,
                task.get("model")
            )

            if task.get("target_file"):
                await self.file_service.write_file(
                    task["target_file"],
                    generated_content,
                    frontmatter=task.get("frontmatter")
                )

            result = {
                "task_id": task_id,
                "content": generated_content,
                "token_count": token_count,
                "target_file": task.get("target_file")
            }

            await self.event_bus.publish("task_completed", {
                "task_id": task_id,
                "result": result
            })

            return result

        except Exception as e:
            await self.event_bus.publish("task_failed", {
                "task_id": task_id,
                "error": str(e)
            })
            raise

    async def _render_prompt(
        self,
        category: str,
        template_type: str,
        variables: dict[str, Any]
    ) -> str:
        """渲染Prompt模板"""
        from backend.core.prompt_engine import PromptEngine

        engine = PromptEngine(file_service=self.file_service)
        return await engine.render(category, template_type, variables)

    async def _generate_content(
        self,
        prompt: str,
        model: str | None = None
    ) -> str:
        """调用LLM生成内容"""
        messages = [{"role": "user", "content": prompt}]

        chunks = []
        async for chunk in self.llm.complete(messages, model=model, stream=True):
            chunks.append(chunk)

        return "".join(chunks)


class TaskQueue:
    """任务队列（仅状态管理）"""

    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running: set[str] = set()
        self._executor: TaskExecutor | None = None

    def set_executor(self, executor: TaskExecutor) -> None:
        """设置执行器"""
        self._executor = executor

    async def enqueue(self, task_data: dict) -> str:
        """添加任务到队列"""
        import uuid
        from datetime import datetime

        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            **task_data
        }

        self._tasks[task_id] = task
        await self._queue.put(task_id)

        return task_id

    async def dequeue(self) -> str | None:
        """从队列取任务ID"""
        try:
            task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            return task_id
        except asyncio.TimeoutError:
            return None

    async def start_task(self, task_id: str) -> None:
        """标记任务开始执行"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "running"
            self._tasks[task_id]["started_at"] = __import__("datetime").datetime.now().isoformat()
            self._running.add(task_id)

    async def complete_task(self, task_id: str, result: Any) -> None:
        """标记任务完成"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["completed_at"] = __import__("datetime").datetime.now().isoformat()
            self._tasks[task_id]["result"] = result
            self._running.discard(task_id)

    async def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["completed_at"] = __import__("datetime").datetime.now().isoformat()
            self._tasks[task_id]["error"] = error
            self._running.discard(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task["status"] in ("pending", "running"):
                task["status"] = "cancelled"
                task["completed_at"] = __import__("datetime").datetime.now().isoformat()
                self._running.discard(task_id)
                return True
        return False

    def get_task(self, task_id: str) -> dict | None:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[dict]:
        """获取所有任务"""
        return list(self._tasks.values())

    @property
    def running_count(self) -> int:
        """正在运行的任务数"""
        return len(self._running)


async def run_task_worker(
    task_queue: TaskQueue,
    llm_service: "LLMServiceInterface",
    file_service: "FileServiceInterface",
    event_bus: "EventBusInterface"
) -> None:
    """任务工作器 - 持续从队列取任务并执行"""
    executor = TaskExecutor(llm_service, file_service, event_bus)
    task_queue.set_executor(executor)

    while True:
        task_id = await task_queue.dequeue()
        if task_id is None:
            await asyncio.sleep(0.5)
            continue

        task = task_queue.get_task(task_id)
        if task is None:
            continue

        await task_queue.start_task(task_id)

        try:
            result = await executor.execute_task(task)
            await task_queue.complete_task(task_id, result)
        except Exception as e:
            await task_queue.fail_task(task_id, str(e))
