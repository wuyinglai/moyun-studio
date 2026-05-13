"""墨韵 - 任务队列 API

端点：
  POST /api/tasks             提交新任务
  GET  /api/tasks             获取任务列表
  GET  /api/tasks/{task_id}   获取任务详情
  POST /api/tasks/{task_id}/cancel  取消任务
"""

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import TaskNotFoundError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])


class TaskSubmitRequest(BaseModel):
    """提交任务请求"""
    template_category: str = Field(..., description="模板分类，如 generate / extract / transform")
    template_type: str = Field(..., description="模板类型，如 chapter / character")
    project_id: str = Field(..., description="项目ID")
    target_file: str | None = Field(default=None, description="生成结果写入的目标文件")
    variables: dict = Field(default_factory=dict, description="模板变量")
    frontmatter: dict | None = Field(default=None, description="写入文件的 frontmatter 元数据")


def _get_queue(request):
    """从 app.state 获取任务队列实例"""
    return request.app.state.task_queue


@router.post("/tasks", response_model=ApiResponse[dict], status_code=201)
async def submit_task(
    req: TaskSubmitRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """提交新任务到队列"""
    task_queue = _get_queue(request)

    task_data = {
        "template_category": req.template_category,
        "template_type": req.template_type,
        "project_id": req.project_id,
        "target_file": req.target_file,
        "variables": req.variables,
        "frontmatter": req.frontmatter,
    }

    task_id = await task_queue.enqueue(task_data)
    logger.info("任务已提交", extra={"task_id": task_id, "template": f"{req.template_category}/{req.template_type}"})

    return ApiResponse.ok({
        "task_id": task_id,
        "status": "pending",
        "template": f"{req.template_category}/{req.template_type}",
    }, message="任务已提交")


@router.get("/tasks", response_model=ApiResponse[dict])
async def list_tasks(request: Request):
    """获取所有任务"""
    task_queue = _get_queue(request)
    tasks = task_queue.get_all_tasks()

    # 精简输出
    summary = []
    for t in tasks:
        summary.append({
            "task_id": t["task_id"],
            "status": t.get("status"),
            "template": f"{t.get('template_category', '?')}/{t.get('template_type', '?')}",
            "created_at": t.get("created_at"),
            "completed_at": t.get("completed_at"),
            "error": t.get("error"),
        })

    return ApiResponse.ok({
        "tasks": summary,
        "total": len(summary),
        "running": task_queue.running_count,
    })


@router.get("/tasks/{task_id}", response_model=ApiResponse[dict])
async def get_task(task_id: str, request: Request):
    """获取任务详情"""
    task_queue = _get_queue(request)
    task = task_queue.get_task(task_id)
    if task is None:
        raise TaskNotFoundError(task_id)

    return ApiResponse.ok(task)


@router.post("/tasks/{task_id}/cancel", response_model=ApiResponse[None])
async def cancel_task(task_id: str, request: Request):
    """取消任务"""
    task_queue = _get_queue(request)
    ok = task_queue.cancel_task(task_id)
    if not ok:
        raise TaskNotFoundError(task_id)

    logger.info("任务已取消", extra={"task_id": task_id})
    return ApiResponse.ok(message=f"任务 {task_id} 已取消")
