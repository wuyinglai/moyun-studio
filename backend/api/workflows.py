"""墨韵 - 工作流引擎 API

端点：
  GET  /api/workflows            获取工作流列表
  GET  /api/workflows/{name}     获取工作流详情
  POST /api/workflows/run        运行工作流（SSE）
"""

import asyncio
import json
import logging
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import Settings, get_settings
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.workflow import WorkflowError, WorkflowRunner
from backend.schemas.common import ApiResponse
from backend.schemas.workflow import WorkflowRunRequest, WorkflowSaveRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workflow"])

# 活跃运行的 stop_event 注册表
_active_stop_events: dict[str, asyncio.Event] = {}


def _build_runner(settings: Settings) -> WorkflowRunner:
    """构建 WorkflowRunner 实例"""
    workflows_path = settings.workspace_path / "workflows"
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    return WorkflowRunner(workflows_path, settings.prompts_path, llm_service, file_service, system_prompts_path=settings.system_prompts_path)


@router.get("/workflows")
async def list_workflows(
    settings: Settings = Depends(get_settings),
):
    """获取所有可用工作流"""
    runner = _build_runner(settings)
    workflows = runner.list_workflows()
    result = [
        {
            "name": w.name,
            "label": w.label,
            "description": w.description,
            "variables": w.variables,
            "steps": [{"id": s.id, "label": s.label, "type": s.type} for s in w.steps],
        }
        for w in workflows
    ]
    return ApiResponse.ok({"workflows": result, "total": len(result)})


@router.get("/workflows/{name}")
async def get_workflow(
    name: str,
    settings: Settings = Depends(get_settings),
):
    """获取工作流详情"""
    runner = _build_runner(settings)
    try:
        wf = runner.load_workflow(name)
    except WorkflowError:
        from backend.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="workflow", identifier=name)

    def _step_to_dict(s):
        return {
            "id": s.id,
            "label": s.label,
            "type": s.type,
            "pipeline": s.pipeline,
            "count": s.count,
            "var": s.var,
            "action": s.action,
            "output": s.output,
            "output_mode": s.output_mode,
            "steps": [_step_to_dict(ss) for ss in s.steps] if s.steps else [],
        }

    return ApiResponse.ok({
        "workflow": {
            "name": wf.name,
            "label": wf.label,
            "description": wf.description,
            "variables": wf.variables,
            "steps": [_step_to_dict(s) for s in wf.steps],
        }
    })


@router.post("/workflows/save")
async def save_workflow(
    req: WorkflowSaveRequest,
    settings: Settings = Depends(get_settings),
):
    """保存（创建或更新）工作流"""
    runner = _build_runner(settings)
    try:
        wf = runner.save_workflow(req)
        return ApiResponse.ok({"workflow": {"name": wf.name, "label": wf.label}})
    except WorkflowError as e:
        from backend.core.exceptions import MoyunException
        raise MoyunException(code="WORKFLOW_ERROR", message=str(e))


@router.delete("/workflows/{name}")
async def delete_workflow(
    name: str,
    settings: Settings = Depends(get_settings),
):
    """删除工作流"""
    runner = _build_runner(settings)
    try:
        result = runner.delete_workflow(name)
        return ApiResponse.ok({
            "message": f"工作流 {name} 已删除到回收站",
            "trash": result,
        })
    except WorkflowError:
        from backend.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="workflow", identifier=name)


@router.post("/workflows/run")
async def run_workflow(
    req: WorkflowRunRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """运行工作流（SSE 流式输出进度）"""
    event_bus = getattr(request.app.state, "event_bus", None)

    # 验证项目
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        from backend.core.exceptions import ProjectNotFoundError
        raise ProjectNotFoundError(req.project_id)

    runner = _build_runner(settings)

    # 创建 stop_event 并注册
    stop_event = asyncio.Event()
    run_id = f"wf-{uuid.uuid4().hex[:8]}"
    _active_stop_events[run_id] = stop_event

    async def _stream():
        try:
            async for event in runner.run(
                workflow_name=req.workflow,
                project_id=req.project_id,
                variables=req.variables,
                stop_event=stop_event,
                run_id=run_id,
            ):
                yield event
                if event_bus:
                    ev_type = event.get("event", "")
                    if ev_type in ("step_start", "step_done", "step_skip", "workflow_done", "workflow_error", "workflow_stopped"):
                        try:
                            await event_bus.publish("workflow-" + ev_type.replace("_", "-"), json.loads(event["data"]))
                        except Exception:
                            pass

                # 运行完成/停止后清理
                if event.get("event") in ("workflow_done", "workflow_error", "workflow_stopped"):
                    _active_stop_events.pop(run_id, None)

        except WorkflowError as e:
            logger.error("工作流执行失败: %s", e)
            yield {"event": "workflow_error", "data": json.dumps({"message": str(e)})}
            _active_stop_events.pop(run_id, None)

    return EventSourceResponse(_stream())


@router.post("/workflows/stop/{run_id}")
async def stop_workflow(
    run_id: str,
):
    """停止正在运行的工作流"""
    stop_event = _active_stop_events.get(run_id)
    if not stop_event:
        return ApiResponse.ok({"message": "工作流未在运行或已完成"})
    stop_event.set()
    return ApiResponse.ok({"message": "已发送停止信号"})


@router.get("/workflows/runs/{run_id}")
async def get_workflow_run_status(
    run_id: str,
    settings: Settings = Depends(get_settings),
):
    """查询工作流执行状态（断点续跑用）"""
    state_dir = Path(".moyun/workflow-runs")
    state_path = state_dir / f"{run_id}.json"
    if not state_path.exists():
        from backend.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="workflow_run", identifier=run_id)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        return ApiResponse.ok({"run": state})
    except Exception as e:
        return ApiResponse.ok({"run": None, "error": str(e)})
