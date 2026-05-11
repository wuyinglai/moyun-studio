"""墨韵 - 服务层实现

具体的服务实现类。
API层通过依赖注入使用这些实现。
"""

from .base import (
    FileServiceInterface,
    LLMServiceInterface,
    PromptEngineInterface,
    TaskQueueInterface,
    EventBusInterface,
    SnapshotServiceInterface,
)
from .file_service import FileService
from .llm_service import LLMService
from .prompt_service import PromptEngineService
from .snapshot_service import SnapshotService
from .project_service import ProjectService

__all__ = [
    # 接口
    "FileServiceInterface",
    "LLMServiceInterface",
    "PromptEngineInterface",
    "TaskQueueInterface",
    "EventBusInterface",
    "SnapshotServiceInterface",
    # 实现
    "FileService",
    "LLMService",
    "PromptEngineService",
    "SnapshotService",
    "ProjectService",
]
