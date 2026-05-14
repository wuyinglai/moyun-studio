"""墨韵 - 生成任务 API

端点：
  POST /api/generate         发起LLM生成任务（流式SSE）
  POST /api/generate/batch   批量生成章节内容
  POST /api/chat             发起聊天（流式SSE）
  POST /api/stop             停止当前任务
  GET  /api/tasks            获取任务队列状态
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
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
from backend.core.pipeline import PipelineRunner, PipelineError
from backend.schemas.common import ApiResponse
from backend.schemas.llm import (
    GenerateRequest,
    ChatRequest,
    BatchGenerateRequest,
    BatchGenerateResponse,
    BatchGenerateItem,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["generate"])

# 全局停止信号
_stop_signals: dict[str, asyncio.Event] = {}


# prompt_type → pipeline 映射
_GENERATE_PIPELINE_MAP = {
    "generate/continuation": ("generate", "append"),
    "generate/rewrite": ("rewrite", "overwrite"),
}


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """LLM 生成任务（流式输出，SSE 格式）

    支持两种模式：
    1. 管线模式：prompt_type 匹配 _GENERATE_PIPELINE_MAP 时，走 PipelineRunner
    2. 回退模式：其余情况走原有的 PromptEngine + 直接 LLM 调用
    """

    async def _stream() -> AsyncGenerator[dict, None]:
        event_bus = getattr(request.app.state, "event_bus", None)
        task_id = f"gen-{id(req)}"
        _stop_signals[task_id] = asyncio.Event()

        # 检测是否可路由到管线
        if req.prompt_type in _GENERATE_PIPELINE_MAP:
            pipeline_name, output_mode = _GENERATE_PIPELINE_MAP[req.prompt_type]
            try:
                file_service = FileService(settings.projects_path)
                llm_cfg = load_llm_config_from_workspace(settings)
                svc = LLMService.from_workspace_config(llm_cfg)
                runner = PipelineRunner(settings.prompts_path, svc, file_service)

                # 构建 LLM 额外参数（含 thinking 配置）
                llm_extra_kwargs = {}
                thinking = llm_cfg.get("thinking", settings.llm_thinking)
                if thinking and "claude" in svc.config.model:
                    llm_extra_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2000}

                async for event in runner.run(
                    pipeline_name=pipeline_name,
                    project_id=req.project_id,
                    target_file=req.file_path,
                    user_input=req.extra_vars.get("user_prompt", ""),
                    output_mode=output_mode,
                    extra_vars=req.extra_vars,
                    stop_event=_stop_signals[task_id],
                    llm_extra_kwargs=llm_extra_kwargs,
                ):
                    yield event
                    if event_bus and event.get("event") in ("generation", "done", "error"):
                        await event_bus.publish(event["event"], json.loads(event["data"]))
            except PipelineError as e:
                logger.error("管线生成失败: %s", e)
                yield {"event": "error", "data": json.dumps({"message": str(e), "task_id": task_id})}
            finally:
                _stop_signals.pop(task_id, None)
            return

        # ——— 回退模式（旧逻辑） ———
        if event_bus:
            await event_bus.publish("task", {"task_id": task_id, "status": "running", "name": f"生成 {req.file_path}"})

        yield {"event": "task_start", "data": json.dumps({"task_id": task_id})}

        try:
            file_service = FileService(settings.projects_path)
            prompt_engine = PromptEngine(settings.prompts_path, file_service)

            logger.info("开始生成任务", extra={"task_id": task_id, "project_id": req.project_id, "file_path": req.file_path})

            try:
                content, fm = await file_service.read_file(f"{req.project_id}/{req.file_path}")
            except Exception:
                content, fm = "", None

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

            yield {"event": "prompt", "data": json.dumps({"prompt": prompt_text, "task_id": task_id})}

            # G0118: 自动 token 检查
            try:
                import tiktoken
                enc = tiktoken.get_encoding("cl100k_base")
                prompt_tokens = len(enc.encode(prompt_text))
                if prompt_tokens > 120000:
                    yield {"event": "error", "data": json.dumps({
                        "message": f"Prompt 过长（约 {prompt_tokens} tokens），可能超出模型上下文限制",
                        "task_id": task_id,
                        "warning": True,
                    })}
            except Exception:
                pass

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


@router.post("/generate/batch", response_model=ApiResponse[BatchGenerateResponse])
async def batch_generate(
    req: BatchGenerateRequest,
    settings: Settings = Depends(get_settings),
):
    """批量生成章节内容

    根据卷/章/节筛选条件，对目标章节逐节调用LLM生成内容。
    每节使用 generate/chapter 模板，模板变量自动从项目文件中提取。
    """
    project_dir = settings.projects_path / req.project_id
    if not project_dir.exists():
        from backend.core.exceptions import ProjectNotFoundError
        raise ProjectNotFoundError(req.project_id)

    logger.info("批量生成开始", extra={
        "project_id": req.project_id,
        "volume": req.volume_number,
        "chapter": req.chapter_number,
        "sections": req.section_numbers,
    })

    # 列出所有目标文件：chapters/vol-{v}/ch-{c}/sec-{s}.md
    chapters_dir = project_dir / "chapters"
    targets: list[dict] = []

    # 确定卷范围
    if req.volume_number:
        vol_dirs = [chapters_dir / f"vol-{req.volume_number:02d}"]
    else:
        vol_dirs = sorted(chapters_dir.glob("vol-*"))

    for vol_dir in vol_dirs:
        if not vol_dir.is_dir():
            continue
        vol_match = vol_dir.name  # vol-XX

        # 确定章范围
        if req.chapter_number:
            ch_dirs = [vol_dir / f"ch-{req.chapter_number:03d}"]
        else:
            ch_dirs = sorted(vol_dir.glob("ch-*"))

        for ch_dir in ch_dirs:
            if not ch_dir.is_dir():
                continue

            # 解析章节号
            ch_match = ch_dir.name  # ch-XXX
            ch_num = int(ch_match.split("-")[1])

            # 确定节范围
            if req.section_numbers:
                sec_nums = req.section_numbers
            else:
                # 所有未写的节
                sec_nums = []
                for sec_file in sorted(ch_dir.glob("sec-*.md")):
                    sec_num = int(sec_file.stem.split("-")[1])
                    sec_nums.append(sec_num)

            for sec_num in sec_nums:
                sec_file = ch_dir / f"sec-{sec_num:03d}.md"
                if sec_file.exists():
                    targets.append({
                        "vol_dir": vol_dir,
                        "ch_dir": ch_dir,
                        "ch_num": ch_num,
                        "sec_num": sec_num,
                        "target_file": f"{req.project_id}/chapters/{vol_dir.name}/{ch_dir.name}/sec-{sec_num:03d}.md",
                    })

    if not targets:
        return ApiResponse.ok(
            BatchGenerateResponse(tasks=[], total=0, succeeded=0, failed=0),
            message="未找到匹配的生成目标",
        )

    # 加载 LLM 配置和服务
    llm_cfg = load_llm_config_from_workspace(settings)
    svc = LLMService.from_workspace_config(llm_cfg)
    file_service = FileService(settings.projects_path)
    prompt_engine = PromptEngine(settings.prompts_path, file_service)

    # 读取共享上下文（只读一次）
    shared_vars = {}
    for ctx_file, var_name in [
        ("style-guide.md", "style_guide"),
        ("story-state.md", "story_state"),
        ("recent-context.md", "recent_context"),
    ]:
        try:
            content, _ = await file_service.read_file(f"{req.project_id}/{ctx_file}")
            shared_vars[var_name] = content
        except Exception:
            shared_vars[var_name] = ""

    # 读取项目 meta 获取 pov
    pov = "第三人称"  # 默认值
    meta_file = project_dir / "meta.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            pov = meta.get("writing_style") or meta.get("pov", "第三人称")
        except Exception:
            pass

    tasks: list[BatchGenerateItem] = []
    succeeded = 0
    failed = 0

    for tgt in targets:
        item = BatchGenerateItem(target_file=tgt["target_file"])

        try:
            # 读取章节 meta
            ch_meta = {}
            ch_meta_file = tgt["ch_dir"] / "ch-meta.json"
            if ch_meta_file.exists():
                ch_meta = json.loads(ch_meta_file.read_text(encoding="utf-8"))

            chapter_title = ch_meta.get("title", f"第{tgt['ch_num']}章")

            # 构建模板变量
            variables = {
                "chapter_name": f"第{tgt['ch_num']}章 {chapter_title}",
                "chapter_number": str(tgt["ch_num"]),
                "section_number": str(tgt["sec_num"]),
                "goal": ch_meta.get("goal", ""),
                "pov": pov,
                **shared_vars,
            }

            # 渲染 prompt
            prompt_text = await prompt_engine.render(req.prompt_type, variables)

            # 保存 prompt 到返回项，供前端右侧面板展示
            item.prompt = prompt_text

            # 调用 LLM
            messages = [{"role": "user", "content": prompt_text}]
            generated = await svc.complete_sync(
                messages, temperature=req.temperature, max_tokens=4000, timeout=180
            )

            # 写入文件
            await file_service.write_file(tgt["target_file"], generated.strip())

            word_count = len(generated.replace(" ", ""))
            item.status = "success"
            item.word_count = word_count
            succeeded += 1

            logger.info("章节生成完成", extra={
                "target": tgt["target_file"],
                "words": word_count,
            })

        except Exception as e:
            logger.error("章节生成失败", extra={
                "target": tgt["target_file"],
                "error": str(e)[:200],
            })
            item.status = "error"
            item.error = str(e)[:200]
            failed += 1

        tasks.append(item)

    logger.info("批量生成完成", extra={
        "total": len(targets),
        "succeeded": succeeded,
        "failed": failed,
    })

    return ApiResponse.ok(
        BatchGenerateResponse(tasks=tasks, total=len(tasks), succeeded=succeeded, failed=failed),
        message=f"批量生成完成：成功 {succeeded}，失败 {failed}",
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
            runner = PipelineRunner(settings.prompts_path, svc, file_service)

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


@router.get("/generate-tasks", response_model=ApiResponse[dict], include_in_schema=False)
async def get_generate_tasks():
    """当前运行的生成任务（旧端点，新端点在 /api/tasks）"""
    running = [
        {"task_id": tid, "status": "running" if not sig.is_set() else "stopping"}
        for tid, sig in _stop_signals.items()
    ]
    return ApiResponse.ok({"tasks": running, "count": len(running)})
