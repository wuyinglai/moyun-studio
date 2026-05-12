"""墨韵 - 服务层基类

定义所有Service模块的抽象接口。
API层只依赖这些接口，不直接依赖具体实现。
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
import asyncio


class FileServiceInterface(ABC):
    """文件服务接口"""

    @abstractmethod
    async def read_file(
        self,
        relative_path: str
    ) -> tuple[str, dict | None]:
        """读取文件，返回(内容, frontmatter)"""

    @abstractmethod
    async def write_file(
        self,
        relative_path: str,
        content: str,
        frontmatter: dict | None = None
    ) -> None:
        """写入文件"""

    @abstractmethod
    async def create_directory(self, relative_path: str) -> None:
        """创建目录"""

    @abstractmethod
    async def delete_file(self, relative_path: str) -> None:
        """删除文件"""

    @abstractmethod
    async def list_directory(self, relative_path: str) -> list[dict]:
        """列出目录"""

    @abstractmethod
    async def exists(self, relative_path: str) -> bool:
        """检查文件是否存在"""


class LLMServiceInterface(ABC):
    """LLM服务接口"""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """流式生成"""

    @abstractmethod
    async def complete_sync(
        self,
        messages: list[dict],
        model: str | None = None
    ) -> str:
        """同步生成"""

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """计算token数"""


class PromptEngineInterface(ABC):
    """Prompt引擎接口"""

    @abstractmethod
    async def render(
        self,
        prompt_type: str,
        variables: dict[str, Any]
    ) -> str:
        """渲染模板（prompt_type格式: category/template_type）"""


class TaskQueueInterface(ABC):
    """任务队列接口"""

    @abstractmethod
    async def enqueue(self, task_data: dict) -> str:
        """添加任务，返回task_id"""

    @abstractmethod
    async def get_task(self, task_id: str) -> dict | None:
        """获取任务状态"""

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""

    @abstractmethod
    async def get_all_tasks(self) -> list[dict]:
        """获取所有任务"""


class EventBusInterface(ABC):
    """事件总线接口"""

    @abstractmethod
    async def publish(self, event_type: str, data: dict) -> None:
        """发布事件"""

    @abstractmethod
    def subscribe(
        self,
        event_types: list[str] | None = None
    ) -> tuple[str, asyncio.Queue]:
        """订阅事件，返回 (client_id, queue)"""


class SnapshotServiceInterface(ABC):
    """快照服务接口"""

    @abstractmethod
    async def create_snapshot(
        self,
        project_id: str,
        file_path: str,
        content: str,
        label: str | None = None
    ) -> dict[str, Any]:
        """创建快照"""

    @abstractmethod
    async def list_snapshots(
        self,
        project_id: str,
        file_path: str
    ) -> list[dict[str, Any]]:
        """列出快照"""

    @abstractmethod
    async def restore_snapshot(
        self,
        project_id: str,
        snapshot_id: str
    ) -> dict[str, Any]:
        """恢复快照"""

    @abstractmethod
    async def compare_versions(
        self,
        project_id: str,
        snapshot_id1: str,
        snapshot_id2: str
    ) -> str:
        """对比两个版本"""
