"""墨韵 - 工作流引擎 API

端点：
  GET  /api/workflows                      获取工作流列表
  GET  /api/workflows/{name}               获取工作流详情
  POST /api/workflows/run                  运行工作流（SSE）
  POST /api/workflows/runs/{run_id}/resume 恢复工作流（SSE）
  POST /api/workflows/stop/{run_id}        停止工作流
  GET  /api/workflows/runs/{run_id}        查询工作流运行状态
"""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.config import Settings, get_settings
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.workflow import WorkflowError, WorkflowRunner
from backend.schemas.common import ApiResponse
from backend.schemas.workflow import WorkflowRunRequest, WorkflowSaveRequest, WorkflowResumeRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workflow"])

# 活跃运行的 stop_event 注册表
_active_stop_events: dict[str, asyncio.Event] = {}


def _build_runner(settings: Settings) -> WorkflowRunner:
    """构建 WorkflowRunner 实例"""
    workflows_path = settings.workspace_path / "workflows"
    file_service = FileService(
        settings.projects_path,
        max_file_write_size=settings.max_file_write_size,
    )
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
            "name": wf.name,
            "label": wf.label,
            "description": wf.description,
            "variables": wf.variables,
            "steps": [{"id": s.id, "label": s.label, "type": s.type} for s in wf.steps],
        }
        for wf in workflows
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
            "input": s.input,
            "output": s.output,
            "output_mode": s.output_mode,
            "output_key": s.output_key,
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
                    if ev_type in ("step_start", "step_done", "step_skip", "workflow_done", "workflow_error", "workflow_stopped", "step_waiting", "workflow_paused"):
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


@router.post("/workflows/runs/{run_id}/resume")
async def resume_workflow(
    run_id: str,
    req: WorkflowResumeRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """从暂停状态恢复工作流（SSE 流式输出进度）"""
    event_bus = getattr(request.app.state, "event_bus", None)
    runner = _build_runner(settings)

    # 创建 stop_event 并注册
    stop_event = asyncio.Event()
    _active_stop_events[run_id] = stop_event

    async def _stream():
        try:
            async for event in runner.resume(
                run_id=run_id,
                action=req.action,
                output=req.output,
                extra_vars=req.extra_vars,
                stop_event=stop_event,
            ):
                yield event
                if event_bus:
                    ev_type = event.get("event", "")
                    if ev_type in ("step_start", "step_done", "step_skip", "workflow_done", "workflow_error", "workflow_stopped", "step_waiting", "workflow_paused", "variable_update"):
                        try:
                            await event_bus.publish("workflow-" + ev_type.replace("_", "-"), json.loads(event["data"]))
                        except Exception:
                            pass

                # 运行完成/停止后清理
                if event.get("event") in ("workflow_done", "workflow_error", "workflow_stopped"):
                    _active_stop_events.pop(run_id, None)

        except WorkflowError as e:
            logger.error("工作流恢复失败: %s", e)
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
    runner = _build_runner(settings)
    state = runner._load_state(run_id)
    if not state:
        from backend.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="workflow_run", identifier=run_id)
    
    return ApiResponse.ok({
        "run": {
            "run_id": state.run_id,
            "workflow": state.workflow,
            "project_id": state.project_id,
            "status": state.status,
            "current_node": state.current_node,
            "waiting_reason": state.waiting_reason,
            "available_actions": state.available_actions,
            "waiting_input": state.waiting_input,
            "variables": state.variables,
            "step_outputs": state.step_outputs,
            "updated_at": state.updated_at,
        }
    })


# ─── Memory API ─────────────────────────────────────────────────────────────────


class MemoryUpdateRequest(BaseModel):
    """记忆更新请求"""
    project_id: str = Field(..., description="项目ID")
    content: str = Field(..., description="需要更新到记忆的内容")
    scene_path: str | None = Field(None, description="场景文件路径")
    chapter_id: str | None = Field(None, description="章节ID")
    force_review: bool = Field(False, description="是否强制人工审核")


class MemoryUpdateResponse(BaseModel):
    """记忆更新响应"""
    draft_update: str = Field(..., description="生成的记忆更新草稿")
    risk_level: str = Field(..., description="风险等级：low/medium/high")
    risk_reason: str = Field(..., description="风险说明")
    updated_files: list[str] = Field(default_factory=list, description="已更新的文件列表")
    requires_review: bool = Field(False, description="是否需要人工审核")


@router.post("/memory/update", response_model=ApiResponse)
async def update_memory(
    req: MemoryUpdateRequest,
    settings: Settings = Depends(get_settings),
):
    """触发记忆更新

    在内容被正式采用后调用，更新 story-state.md 和 recent-context.md。
    高风险更新会自动暂停等待人工确认。
    """
    # 验证项目
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        from backend.core.exceptions import ProjectNotFoundError
        raise ProjectNotFoundError(req.project_id)

    # 读取现有记忆
    story_state_path = project_dir / "story-state.md"
    recent_context_path = project_dir / "recent-context.md"

    story_state = ""
    recent_context = ""

    if story_state_path.exists():
        story_state = story_state_path.read_text(encoding="utf-8")

    if recent_context_path.exists():
        recent_context = recent_context_path.read_text(encoding="utf-8")

    # 评估风险
    from backend.core.node_types import assess_memory_risk
    risk_level, risk_reason = assess_memory_risk(req.content, story_state)

    # 如果强制审核或高风险，需要人工确认
    if req.force_review or risk_level == "high":
        return ApiResponse.ok({
            "draft_update": "",
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "updated_files": [],
            "requires_review": True,
            "content": req.content,  # AI_GUARDRAIL_ALLOW: workflow API response, not SSE
            "scene_path": req.scene_path,
        })

    # 低风险：直接执行记忆更新
    # 生成草稿
    # 这里简化处理，实际应该使用 workflow 的 memory 节点
    from datetime import datetime

    draft_content = f"""# 故事状态更新草案

## 时间
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 内容摘要
{req.content[:500]}...

## 风险评估
- 风险等级：{risk_level}
- 风险说明：{risk_reason}

## 更新内容
{req.content}
"""

    # 更新文件
    updated_files = []

    # 更新 story-state.md
    updated_story_state = story_state + "\n\n## 更新于 " + \
        datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n" + draft_content

    try:
        story_state_path.write_text(updated_story_state, encoding="utf-8")
        updated_files.append("story-state.md")
    except Exception as e:
        logger.error("更新 story-state.md 失败: %s", e)

    # 更新 recent-context.md
    if req.scene_path:
        summary_entry = f"""
## {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - {req.scene_path}
【场景摘要】
{req.content[:200]}...

【人物状态变化】
暂无

【新增线索/伏笔】
暂无

【下一场承接点】
待续
"""
        updated_recent = recent_context + summary_entry

        try:
            recent_context_path.write_text(updated_recent, encoding="utf-8")
            updated_files.append("recent-context.md")
        except Exception as e:
            logger.error("更新 recent-context.md 失败: %s", e)

    return ApiResponse.ok({
        "draft_update": draft_content,
        "risk_level": risk_level,
        "risk_reason": risk_reason,
        "updated_files": updated_files,
        "requires_review": False,
    })


@router.get("/memory/status/{project_id}", response_model=ApiResponse)
async def get_memory_status(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """查询项目的记忆状态"""
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        from backend.core.exceptions import ProjectNotFoundError
        raise ProjectNotFoundError(project_id)

    story_state_path = project_dir / "story-state.md"
    recent_context_path = project_dir / "recent-context.md"

    story_state = ""
    recent_context = ""
    last_updated = None

    if story_state_path.exists():
        story_state = story_state_path.read_text(encoding="utf-8")
        last_updated = story_state_path.stat().st_mtime

    if recent_context_path.exists():
        recent_context = recent_context_path.read_text(encoding="utf-8")

    # 统计近期上下文中最近的条目数
    recent_entries = recent_context.count("## ") if recent_context else 0

    return ApiResponse.ok({
        "project_id": project_id,
        "story_state_exists": story_state_path.exists(),
        "recent_context_exists": recent_context_path.exists(),
        "recent_entries_count": recent_entries,
        "story_state_length": len(story_state),
        "recent_context_length": len(recent_context),
        "last_updated": last_updated,
    })
