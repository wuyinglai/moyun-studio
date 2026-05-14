"""墨韵 - 任务执行器

实际执行生成任务的模块。
TaskQueue只负责状态管理，TaskExecutor负责具体执行。

持久化：enqueue 时将任务写入 <project>/.task-queue/<task_id>.json，
complete/fail/cancel 时同步更新状态。启动时调用 restore() 恢复中断的任务。
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.exceptions import ContextLengthError
from backend.core.prompt_engine import PromptEngine


class TaskExecutor:
    """任务执行器"""

    def __init__(
        self,
        llm_service: Any,
        file_service: Any,
        event_bus: Any,
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
            await self.event_bus.publish("task:started", {
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
                raise ContextLengthError(token_count, 128000)

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

            await self.event_bus.publish("task:completed", {
                "task_id": task_id,
                "result": result
            })

            return result

        except Exception as e:
            await self.event_bus.publish("task:failed", {
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
        engine = PromptEngine(file_service=self.file_service)
        prompt_type = f"{category}/{template_type}"
        return await engine.render(prompt_type, variables)

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
    """任务队列（状态管理 + 磁盘持久化）"""

    def __init__(self, persist_dir: str | Path | None = None):
        self._tasks: dict[str, dict] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running: set[str] = set()
        self._executor: TaskExecutor | None = None
        self._persist_dir = Path(persist_dir) if persist_dir else None

    def _task_file(self, task_id: str) -> Path:
        """返回任务对应的持久化文件路径"""
        return self._persist_dir / f"{task_id}.json" if self._persist_dir else None  # type: ignore[return-value]

    def _save_task(self, task: dict) -> None:
        """将任务写入磁盘"""
        if not self._persist_dir:
            return
        # 序列化时排除 result（可能含大文本，单独存储）
        persist_data = {k: v for k, v in task.items() if k != "result"}
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        path = self._persist_dir / f"{task['task_id']}.json"
        path.write_text(json.dumps(persist_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _remove_task_file(self, task_id: str) -> None:
        """从磁盘移除任务文件（仅 completed/failed/cancelled 的归档清理用）"""
        if not self._persist_dir:
            return
        path = self._persist_dir / f"{task_id}.json"
        if path.exists():
            path.unlink()

    def set_executor(self, executor: TaskExecutor) -> None:
        """设置执行器"""
        self._executor = executor

    async def enqueue(self, task_data: dict) -> str:
        """添加任务到队列"""
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            **task_data
        }

        self._tasks[task_id] = task
        self._save_task(task)
        await self._queue.put(task_id)

        return task_id

    async def dequeue(self) -> str | None:
        """从队列取任务ID"""
        try:
            task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            return task_id
        except asyncio.TimeoutError:
            return None

    def start_task(self, task_id: str) -> None:
        """标记任务开始执行"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "running"
            self._tasks[task_id]["started_at"] = datetime.now().isoformat()
            self._running.add(task_id)
            self._save_task(self._tasks[task_id])

    def complete_task(self, task_id: str, result: Any) -> None:
        """标记任务完成"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["completed_at"] = datetime.now().isoformat()
            self._tasks[task_id]["result"] = result
            self._running.discard(task_id)
            self._remove_task_file(task_id)

    def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["completed_at"] = datetime.now().isoformat()
            self._tasks[task_id]["error"] = error
            self._running.discard(task_id)
            self._remove_task_file(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task["status"] in ("pending", "running"):
                task["status"] = "cancelled"
                task["completed_at"] = datetime.now().isoformat()
                self._running.discard(task_id)
                self._remove_task_file(task_id)
                return True
        return False

    def get_task(self, task_id: str) -> dict | None:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[dict]:
        """获取所有任务"""
        return list(self._tasks.values())

    @classmethod
    def restore(cls, persist_dir: str | Path) -> "TaskQueue":
        """从磁盘恢复中断的任务

        读取 <persist_dir>/*.json 中所有 status=pending 或 running 的任务，
        将其重新入队。completed/failed/cancelled 的归档文件会被清除。
        """
        queue = cls(persist_dir=persist_dir)
        persist_path = Path(persist_dir)
        if not persist_path.exists():
            return queue

        for f in sorted(persist_path.glob("*.json")):
            try:
                task = json.loads(f.read_text(encoding="utf-8"))
                if task.get("status") in ("pending", "running"):
                    task["status"] = "pending"  # 重启后统一重置为 pending
                    task_id = task["task_id"]
                    queue._tasks[task_id] = task
                    queue._queue.put_nowait(task_id)
                else:
                    f.unlink()  # 清理已完成/失败的归档
            except (json.JSONDecodeError, KeyError, OSError):
                pass  # 跳过损坏的文件

        return queue

    @property
    def running_count(self) -> int:
        """正在运行的任务数"""
        return len(self._running)


async def run_task_worker(
    task_queue: TaskQueue,
    llm_service: Any,
    file_service: Any,
    event_bus: Any
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

        task_queue.start_task(task_id)

        try:
            result = await executor.execute_task(task)
            task_queue.complete_task(task_id, result)
        except Exception as e:
            task_queue.fail_task(task_id, str(e))
