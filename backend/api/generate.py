"""墨韵 - 生成任务 API

端点：
  POST /api/generate         发起LLM生成任务（流式SSE）
  POST /api/generate/batch   批量生成章节内容
  POST /api/chat             发起聊天（流式SSE）
  POST /api/stop             停止当前任务
  GET  /api/tasks            获取任务队列状态
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import Settings, get_settings
from backend.core.generation_service import GenerationService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.file_ops import FileService
from backend.core.pipeline import PipelineRunner, PipelineError
from backend.schemas.common import ApiResponse
from backend.schemas.llm import (
    GenerateRequest,
    ChatRequest,
    BatchGenerateRequest,
    BatchGenerateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["generate"])


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """LLM 生成任务（流式输出，SSE 格式）"""
    svc = GenerationService(settings)

    async def _stream() -> AsyncGenerator[dict, None]:
        event_bus = getattr(request.app.state, "event_bus", None)
        task_id = f"gen-{id(req)}"
        svc.create_stop_signal(task_id)

        try:
            async for event in svc.generate_stream(
                project_id=req.project_id,
                file_path=req.file_path,
                prompt_type=req.prompt_type,
                extra_vars=req.extra_vars,
                mode=req.mode,
                task_id=task_id,
                event_bus=event_bus,
            ):
                yield event
        finally:
            svc.remove_stop_signal(task_id)

    return EventSourceResponse(_stream())


@router.post("/generate/batch", response_model=ApiResponse[BatchGenerateResponse])
async def batch_generate(
    req: BatchGenerateRequest,
    settings: Settings = Depends(get_settings),
):
    """批量生成章节内容"""
    svc = GenerationService(settings)
    result = await svc.batch_generate(
        project_id=req.project_id,
        prompt_type=req.prompt_type,
        volume_number=req.volume_number,
        chapter_number=req.chapter_number,
        section_numbers=req.section_numbers,
        temperature=req.temperature,
    )

    if result.total == 0:
        return ApiResponse.ok(result, message="未找到匹配的生成目标")

    return ApiResponse.ok(
        result,
        message=f"批量生成完成：成功 {result.succeeded}，失败 {result.failed}",
    )


@router.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """聊天对话（流式SSE），使用 chat 管线"""

    async def _stream() -> AsyncGenerator[dict, None]:
        logger.info("开始聊天任务", extra={"project_id": req.project_id, "message_length": len(req.message)})

        try:
            file_service = FileService(settings.projects_path)
            llm_cfg = load_llm_config_from_workspace(settings)
            svc = LLMService.from_workspace_config(llm_cfg)
            runner = PipelineRunner(settings.prompts_path, svc, file_service, system_prompts_path=settings.system_prompts_path)

            async for event in runner.run(
                pipeline_name="chat",
                project_id=req.project_id,
                target_file=req.context_file,
                user_input=req.message,
                output_mode="append",
            ):
                yield event

        except PipelineError as e:
            logger.error("聊天管线失败: %s", e)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(_stream())


# 模块级 GenerationService 实例，管理跨请求的停止信号
_shared_gen_svc: GenerationService | None = None


def _get_gen_svc(settings: Settings) -> GenerationService:
    global _shared_gen_svc
    if _shared_gen_svc is None:
        _shared_gen_svc = GenerationService(settings)
    return _shared_gen_svc


@router.post("/stop", response_model=ApiResponse[None])
async def stop_task(settings: Settings = Depends(get_settings), task_id: str | None = None):
    """停止当前任务"""
    svc = _get_gen_svc(settings)
    svc.stop_task(task_id)
    if task_id:
        return ApiResponse.ok(message=f"任务 {task_id} 已停止")
    return ApiResponse.ok(message="所有任务已停止")


@router.get("/generate-tasks", response_model=ApiResponse[dict], include_in_schema=False)
async def get_generate_tasks():
    """当前运行的生成任务（旧端点）"""
    return ApiResponse.ok({"tasks": [], "count": 0})
