"""墨韵 - 统一应用事件模型

所有事件都遵循 AppEvent 结构，确保：
1. 所有事件都带 project_id
2. 有任务上下文时带 task_id
3. file.updated 不发送完整正文 content
4. 前端收到 SSE 后按 project_id/task_id 过滤
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── 统一事件类型 ──────────────────────────────────────

class EventType(str, Enum):
    """标准化事件类型命名"""

    # 文件事件
    FILE_CREATED = "file.created"
    FILE_UPDATED = "file.updated"
    FILE_DELETED = "file.deleted"

    # 候选稿事件
    CANDIDATE_CREATED = "candidate.created"
    CANDIDATE_ADOPTED = "candidate.adopted"

    # 管线事件
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_STEP_STARTED = "pipeline.step.started"
    PIPELINE_STEP_COMPLETED = "pipeline.step.completed"
    PIPELINE_STEP_FAILED = "pipeline.step.failed"

    # 任务事件
    TASK_WAITING_FOR_USER = "task.waiting_for_user"
    TASK_COMPLETED = "task.completed"

    # 记忆事件
    MEMORY_UPDATED = "memory.updated"

    # ─── 兼容旧前端的事件别名 ──────────────────────────
    # 旧事件名映射，保持旧前端不崩
    LEGACY_TASK = "task"
    LEGACY_GENERATION = "generation"
    LEGACY_THINKING = "thinking"
    LEGACY_DONE = "done"
    LEGACY_ERROR = "error"
    LEGACY_STEP_DONE = "step_done"
    LEGACY_PROMPT = "prompt"
    LEGACY_DIFF_SUMMARY = "diff_summary"


# ─── 旧事件名 → 新事件名映射 ──────────────────────────

LEGACY_TO_NEW = {
    "file:created": EventType.FILE_CREATED,
    "file:modified": EventType.FILE_UPDATED,
    "file:deleted": EventType.FILE_DELETED,
    "file-created": EventType.FILE_CREATED,
    "file-updated": EventType.FILE_UPDATED,
    "file-renamed": EventType.FILE_UPDATED,
    "file-deleted": EventType.FILE_DELETED,
    "directory-created": EventType.FILE_CREATED,
    "directory-deleted": EventType.FILE_DELETED,
    "task:started": EventType.PIPELINE_STARTED,
    "task:progress": EventType.PIPELINE_STEP_STARTED,
    "task:completed": EventType.TASK_COMPLETED,
    "task:failed": EventType.PIPELINE_STEP_FAILED,
    "task": EventType.LEGACY_TASK,
    "generation": EventType.LEGACY_GENERATION,
    "thinking": EventType.LEGACY_THINKING,
    "done": EventType.LEGACY_DONE,
    "error": EventType.LEGACY_ERROR,
    "step_done": EventType.LEGACY_STEP_DONE,
    "prompt": EventType.LEGACY_PROMPT,
    "diff_summary": EventType.LEGACY_DIFF_SUMMARY,
}


# ─── AppEvent ──────────────────────────────────────────

class AppEvent(BaseModel):
    """统一应用事件"""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="事件唯一标识")
    type: str = Field(..., description="事件类型（EventType 值）")
    project_id: str = Field("", description="项目ID")
    task_id: str | None = Field(None, description="任务ID（有任务上下文时）")
    run_id: str | None = Field(None, description="运行ID")
    source: str = Field("", description="事件来源模块")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="事件时间")
    payload: dict = Field(default_factory=dict, description="事件数据")

    # ─── 兼容旧前端 ────────────────────────────────────
    # 旧前端期望 data 在顶层，这里通过 to_sse_dict 输出

    def to_sse_dict(self) -> dict:
        """转换为 SSE 广播格式

        新字段必须存在，同时保留旧字段兼容。
        """
        result = {
            "event_id": self.event_id,
            "type": self.type,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "payload": self.payload,
            **self.payload,
        }
        return result

    def to_event_bus_dict(self) -> dict:
        """转换为 EventBus 内部格式"""
        return {
            "type": self.type,
            "data": self.to_sse_dict(),
        }


# ─── 便捷构造函数 ──────────────────────────────────────

def make_file_created_event(
    project_id: str,
    path: str,
    name: str | None = None,
    source: str = "",
) -> AppEvent:
    """构造 file.created 事件"""
    return AppEvent(
        type=EventType.FILE_CREATED,
        project_id=project_id,
        source=source,
        payload={"path": path, "name": name or path.split("/")[-1]},
    )


def make_file_updated_event(
    project_id: str,
    path: str,
    size: int | None = None,
    mtime: float | None = None,
    source: str = "",
) -> AppEvent:
    """构造 file.updated 事件（不发送完整正文 content）"""
    payload: dict = {"path": path}
    if size is not None:
        payload["size"] = size
    if mtime is not None:
        payload["mtime"] = mtime
    return AppEvent(
        type=EventType.FILE_UPDATED,
        project_id=project_id,
        source=source,
        payload=payload,
    )


def make_file_deleted_event(
    project_id: str,
    path: str,
    source: str = "",
) -> AppEvent:
    """构造 file.deleted 事件"""
    return AppEvent(
        type=EventType.FILE_DELETED,
        project_id=project_id,
        source=source,
        payload={"path": path},
    )


def make_candidate_created_event(
    project_id: str,
    candidate_id: str,
    source_path: str,
    action: str,
    source: str = "",
) -> AppEvent:
    """构造 candidate.created 事件"""
    return AppEvent(
        type=EventType.CANDIDATE_CREATED,
        project_id=project_id,
        source=source,
        payload={"candidate_id": candidate_id, "source_path": source_path, "action": action},
    )


def make_candidate_adopted_event(
    project_id: str,
    candidate_id: str,
    source_path: str,
    source: str = "",
) -> AppEvent:
    """构造 candidate.adopted 事件"""
    return AppEvent(
        type=EventType.CANDIDATE_ADOPTED,
        project_id=project_id,
        source=source,
        payload={"candidate_id": candidate_id, "source_path": source_path},
    )


def make_pipeline_started_event(
    project_id: str,
    pipeline_name: str,
    task_id: str | None = None,
    source: str = "",
) -> AppEvent:
    """构造 pipeline.started 事件"""
    return AppEvent(
        type=EventType.PIPELINE_STARTED,
        project_id=project_id,
        task_id=task_id,
        source=source,
        payload={"pipeline": pipeline_name},
    )


def make_pipeline_step_started_event(
    project_id: str,
    step_id: str,
    step_label: str,
    task_id: str | None = None,
    source: str = "",
) -> AppEvent:
    """构造 pipeline.step.started 事件"""
    return AppEvent(
        type=EventType.PIPELINE_STEP_STARTED,
        project_id=project_id,
        task_id=task_id,
        source=source,
        payload={"step_id": step_id, "label": step_label},
    )


def make_pipeline_step_completed_event(
    project_id: str,
    step_id: str,
    step_label: str,
    task_id: str | None = None,
    source: str = "",
) -> AppEvent:
    """构造 pipeline.step.completed 事件"""
    return AppEvent(
        type=EventType.PIPELINE_STEP_COMPLETED,
        project_id=project_id,
        task_id=task_id,
        source=source,
        payload={"step_id": step_id, "label": step_label},
    )


def make_pipeline_step_failed_event(
    project_id: str,
    step_id: str,
    error: str,
    task_id: str | None = None,
    source: str = "",
) -> AppEvent:
    """构造 pipeline.step.failed 事件"""
    return AppEvent(
        type=EventType.PIPELINE_STEP_FAILED,
        project_id=project_id,
        task_id=task_id,
        source=source,
        payload={"step_id": step_id, "error": error},
    )


def make_task_waiting_for_user_event(
    project_id: str,
    task_id: str,
    source: str = "",
) -> AppEvent:
    """构造 task.waiting_for_user 事件"""
    return AppEvent(
        type=EventType.TASK_WAITING_FOR_USER,
        project_id=project_id,
        task_id=task_id,
        source=source,
        payload={},
    )


def make_task_completed_event(
    project_id: str,
    task_id: str,
    source: str = "",
) -> AppEvent:
    """构造 task.completed 事件"""
    return AppEvent(
        type=EventType.TASK_COMPLETED,
        project_id=project_id,
        task_id=task_id,
        source=source,
        payload={},
    )


def make_memory_updated_event(
    project_id: str,
    source: str = "",
) -> AppEvent:
    """构造 memory.updated 事件"""
    return AppEvent(
        type=EventType.MEMORY_UPDATED,
        project_id=project_id,
        source=source,
        payload={},
    )
