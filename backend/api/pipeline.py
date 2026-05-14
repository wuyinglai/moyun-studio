"""墨韵 - 管线引擎 API

端点：
  POST /api/pipeline/run         运行管线（SSE）
  GET  /api/pipeline/list        获取管线列表
  GET  /api/pipeline/{name}      获取管线详情（含 prompt）
  PUT  /api/pipeline/{name}      保存管线/步骤 prompt
  POST /api/pipeline/custom      创建自定义管线
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import Settings, get_settings
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.file_ops import FileService
from backend.core.pipeline import PipelineRunner, PipelineError
from backend.schemas.common import ApiResponse
from backend.schemas.pipeline import (
    PipelineRunRequest,
    PipelineSaveRequest,
    CreatePipelineRequest,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline"])


@router.post("/pipeline/run")
async def run_pipeline(
    req: PipelineRunRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """运行管线（流式 SSE）"""
    event_bus = getattr(request.app.state, "event_bus", None)

    # 验证项目存在
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        from backend.core.exceptions import ProjectNotFoundError
        raise ProjectNotFoundError(req.project_id)

    # 初始化服务
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    async def _stream():
        task_id = f"pipeline-{req.pipeline}"

        if event_bus:
            await event_bus.publish("task", {
                "task_id": task_id,
                "status": "running",
                "name": req.pipeline,
            })

        try:
            async for event in runner.run(
                pipeline_name=req.pipeline,
                project_id=req.project_id,
                target_file=req.target_file,
                user_input=req.user_input,
                output_mode=req.output_mode,
                extra_vars=req.extra_vars,
            ):
                # 直接返回事件到 streaming 响应
                yield event
                # 只发布非 generation 事件到 EventBus
                # generation 事件只通过 streaming 响应返回，避免重复
                if event_bus and event.get("event") in ("thinking", "done", "error", "step_done", "prompt"):
                    await event_bus.publish(event["event"], json.loads(event["data"]))

        except PipelineError as e:
            logger.error("管线运行失败: %s", e)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(_stream())


@router.get("/pipeline/list")
async def list_pipelines(
    settings: Settings = Depends(get_settings),
):
    """获取所有可用管线"""
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    pipelines = runner.list_pipelines()
    result = [
        {"name": p.name, "label": p.label, "steps": [{"id": s.id, "label": s.label} for s in p.steps], "source": "system"}
        for p in pipelines
    ]

    # 检查自定义管线
    custom_dir = settings.workspace_path / ".moyun" / "custom-pipelines"
    if custom_dir.exists():
        for f in sorted(custom_dir.glob("*.yaml")):
            try:
                p = runner.load_pipeline(f.stem)
                result.append({
                    "name": p.name, "label": p.label,
                    "steps": [{"id": s.id, "label": s.label} for s in p.steps],
                    "source": "custom",
                })
            except Exception:
                pass

    return ApiResponse.ok({"pipelines": result, "total": len(result)})


@router.get("/pipeline/{name}")
async def get_pipeline(
    name: str,
    settings: Settings = Depends(get_settings),
):
    """获取管线详情"""
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    try:
        detail = runner.get_pipeline_detail(name)
        return ApiResponse.ok({"pipeline": detail})
    except PipelineError as e:
        from backend.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="pipeline", identifier=name)


@router.put("/pipeline/{name}")
async def save_pipeline(
    name: str,
    req: PipelineSaveRequest,
    settings: Settings = Depends(get_settings),
):
    """保存管线定义或步骤 prompt"""
    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(settings.prompts_path, llm_service, file_service)

    if req.steps is not None:
        runner.save_pipeline_yaml(name, req.label or name, req.steps)

    if req.steps:
        for step in req.steps:
            if step.get("prompt_content"):
                runner.save_step_prompt(name, step["id"], step["prompt_content"])

    return ApiResponse.ok(message=f"管线 {name} 已保存")


@router.post("/pipeline/custom")
async def create_custom_pipeline(
    req: CreatePipelineRequest,
    settings: Settings = Depends(get_settings),
):
    """创建自定义管线"""
    custom_dir = settings.workspace_path / ".moyun" / "custom-pipelines"
    custom_dir.mkdir(parents=True, exist_ok=True)

    file_service = FileService(settings.projects_path)
    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    runner = PipelineRunner(custom_dir, llm_service, file_service)

    # 保存 YAML
    runner.save_pipeline_yaml(req.name, req.label, req.steps)

    # 保存每步 prompt
    for step in req.steps:
        if step.get("prompt_content"):
            runner.save_step_prompt(req.name, step["id"], step["prompt_content"])

    return ApiResponse.ok(message=f"自定义管线 {req.name} 已创建")
