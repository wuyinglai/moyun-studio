"""墨韵 - 生成任务 API

端点：
  POST /api/generate    发起LLM生成任务（流式SSE）
  POST /api/chat        发起聊天（流式SSE）
  POST /api/stop        停止当前任务
  GET  /api/tasks       获取任务队列状态
"""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import Settings, get_settings
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

        # 通知任务开始
        if event_bus:
            await event_bus.publish("task", {"task_id": task_id, "status": "running", "name": f"生成 {req.file_path}"})

        yield {"event": "task_start", "data": json.dumps({"task_id": task_id})}

        try:
            import json

            # 加载 Prompt 模板
            from backend.core.file_ops import FileService
            from backend.core.prompt_engine import PromptEngine

            file_service = FileService(settings.projects_path)
            prompt_engine = PromptEngine(settings.prompts_path, file_service)

            # 记录生成开始
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
            import json as _json
            cfg_file = settings.workspace_path / ".config.json"
            llm_cfg = {}
            if cfg_file.exists():
                try:
                    llm_cfg = _json.loads(cfg_file.read_text(encoding="utf-8")).get("llm", {})
                except Exception:
                    pass

            import litellm
            if llm_cfg.get("apiKey"):
                litellm.api_key = llm_cfg["apiKey"]
            if llm_cfg.get("apiUrl"):
                litellm.api_base = llm_cfg["apiUrl"]

            model = llm_cfg.get("model", settings.llm_model)
            thinking = llm_cfg.get("thinking", settings.llm_thinking)

            messages = [{"role": "user", "content": prompt_text}]
            extra_kwargs = {}
            if thinking and "claude" in model:
                extra_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2000}

            generated_text = ""
            async for chunk in await litellm.acompletion(
                model=model,
                messages=messages,
                stream=True,
                **extra_kwargs,
            ):
                if _stop_signals[task_id].is_set():
                    break
                delta = chunk.choices[0].delta.content or ""
                generated_text += delta
                if delta:
                    yield {
                        "event": "generation",
                        "data": json.dumps({"delta": delta, "task_id": task_id}),
                    }
                    if event_bus:
                        await event_bus.publish("generation", {"delta": delta, "task_id": task_id})

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
        import json

        event_bus = getattr(request.app.state, "event_bus", None)
        task_id = f"chat-{id(req)}"

        logger.info("开始聊天任务", extra={"task_id": task_id, "message_length": len(req.message)})

        yield {"event": "task_start", "data": json.dumps({"task_id": task_id})}

        try:
            import litellm
            import json as _json

            cfg_file = settings.workspace_path / ".config.json"
            llm_cfg = {}
            if cfg_file.exists():
                try:
                    llm_cfg = _json.loads(cfg_file.read_text(encoding="utf-8")).get("llm", {})
                except Exception:
                    pass

            # 处理 deepseek 格式
            model = llm_cfg.get("model", settings.llm_model)
            api_type = llm_cfg.get("apiType", "openai")
            if api_type == "deepseek" and not model.startswith("deepseek/"):
                model = "deepseek/" + model

            messages = [{"role": "user", "content": req.message}]

            kwargs = {
                "model": model,
                "messages": messages,
                "stream": True,
            }
            if llm_cfg.get("apiKey"):
                kwargs["api_key"] = llm_cfg["apiKey"]
            if llm_cfg.get("apiUrl"):
                kwargs["api_base"] = llm_cfg["apiUrl"]

            async for chunk in await litellm.acompletion(**kwargs):
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield {
                        "event": "generation",
                        "data": json.dumps({"delta": delta, "task_id": task_id, "type": "chat"}),
                    }

            yield {"event": "done", "data": json.dumps({"task_id": task_id})}

        except Exception as e:
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
