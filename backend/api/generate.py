"""墨韵 - 生成任务 API

端点：
  POST /api/generate    发起LLM生成任务（流式SSE）
  POST /api/chat        发起聊天（流式SSE）
  POST /api/stop        停止当前任务
  GET  /api/tasks       获取任务队列状态
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
from backend.config import Settings, get_settings
from backend.core.llm import (
    LLMService,
    load_llm_config_from_workspace,
)
from backend.core.file_ops import FileService
from backend.core.prompt_engine import PromptEngine
from backend.schemas.common import ApiResponse
from backend.schemas.llm import GenerateRequest, ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["generate"])

# 全局停止信号
_stop_signals: dict[str, asyncio.Event] = {}


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """LLM 生成任务（流式输出，SSE 格式）"""

    async def _stream() -> AsyncGenerator[dict, None]:
        event_bus = getattr(request.app.state, "event_bus", None)
        task_id = f"gen-{id(req)}"
        _stop_signals[task_id] = asyncio.Event()

        if event_bus:
            await event_bus.publish("task", {"task_id": task_id, "status": "running", "name": f"生成 {req.file_path}"})

        yield {"event": "task_start", "data": json.dumps({"task_id": task_id})}

        try:
            # 加载 Prompt 模板
            file_service = FileService(settings.projects_path)
            prompt_engine = PromptEngine(settings.prompts_path, file_service)

            logger.info("开始生成任务", extra={"task_id": task_id, "project_id": req.project_id, "file_path": req.file_path})

            # 读取目标文件内容
            try:
                content, fm = await file_service.read_file(f"{req.project_id}/{req.file_path}")
            except Exception:
                content, fm = "", None

            # 渲染 Prompt
            variables = {
                "file_content": content,
                "file_path": req.file_path,
                "project_id": req.project_id,
                **req.extra_vars,
            }
            try:
                prompt_text = await prompt_engine.render(req.prompt_type, variables)
            except Exception as e:
                prompt_text = f"请根据以下内容进行创作：\n\n{content}"

            # 调用 LLM
            
            llm_cfg = load_llm_config_from_workspace(settings)
            svc = LLMService.from_workspace_config(llm_cfg)
            thinking = llm_cfg.get("thinking", settings.llm_thinking)

            messages = [{"role": "user", "content": prompt_text}]
            extra_kwargs = {}
            if thinking and "claude" in svc.config.model:
                extra_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2000}

            stop_event = _stop_signals[task_id]
            generated_text = ""
            async for content in svc.complete(messages, stop_event=stop_event, timeout=180, **extra_kwargs):
                generated_text += content
                yield {
                    "event": "generation",
                    "data": json.dumps({"delta": content, "task_id": task_id}),
                }
                if event_bus:
                    await event_bus.publish("generation", {"delta": content, "task_id": task_id})

            # 保存生成内容
            if generated_text and not _stop_signals[task_id].is_set():
                if req.mode == "rewrite":
                    await file_service.write_file(f"{req.project_id}/{req.file_path}", generated_text, fm)
                elif req.mode == "append":
                    new_content = content + "\n\n" + generated_text
                    await file_service.write_file(f"{req.project_id}/{req.file_path}", new_content, fm)

            yield {"event": "done", "data": json.dumps({"task_id": task_id, "message": "生成完成"})}
            if event_bus:
                await event_bus.publish("task", {"task_id": task_id, "status": "done"})
                await event_bus.publish("done", {"task_id": task_id})

        except Exception as e:
            logger.error(f"生成任务异常: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(e), "task_id": task_id})}
            if event_bus:
                await event_bus.publish("error", {"message": str(e)})
        finally:
            _stop_signals.pop(task_id, None)

    return EventSourceResponse(_stream())


@router.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """聊天对话（流式SSE）"""

    async def _stream() -> AsyncGenerator[dict, None]:
        event_bus = getattr(request.app.state, "event_bus", None)
        task_id = f"chat-{id(req)}"

        logger.info("开始聊天任务", extra={"task_id": task_id, "message_length": len(req.message)})

        yield {"event": "task_start", "data": json.dumps({"task_id": task_id})}

        try:
            
            llm_cfg = load_llm_config_from_workspace(settings)
            svc = LLMService.from_workspace_config(llm_cfg)

            messages = [{"role": "user", "content": req.message}]
            async for content in svc.complete(messages, timeout=120):
                yield {
                    "event": "generation",
                    "data": json.dumps({"delta": content, "task_id": task_id, "type": "chat"}),
                }

            yield {"event": "done", "data": json.dumps({"task_id": task_id})}

        except Exception as e:
            logger.error(f"聊天任务异常: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(_stream())


@router.post("/stop", response_model=ApiResponse[None])
async def stop_task(task_id: str | None = None):
    """停止当前任务"""
    if task_id and task_id in _stop_signals:
        _stop_signals[task_id].set()
        return ApiResponse.ok(message=f"任务 {task_id} 已停止")
    # 停止所有任务
    for sig in _stop_signals.values():
        sig.set()
    return ApiResponse.ok(message="所有任务已停止")


@router.get("/tasks", response_model=ApiResponse[dict])
async def get_tasks():
    """获取当前任务队列"""
    tasks = [
        {"task_id": tid, "status": "running" if not sig.is_set() else "stopping"}
        for tid, sig in _stop_signals.items()
    ]
    return ApiResponse.ok({"tasks": tasks, "count": len(tasks)})
