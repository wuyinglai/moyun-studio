"""墨韵 - 任务模型"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskModel(BaseModel):
    """任务模型"""
    task_id: str
    template_category: str
    template_type: str
    variables: dict = {}
    status: TaskStatus = TaskStatus.PENDING
    target_file: str | None = None
    progress: float = 0.0
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
