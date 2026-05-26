"""墨韵 - FastAPI 应用入口"""

import asyncio
from contextlib import asynccontextmanager
import logging
import os

# 仅当明确启用时禁用代理检测（解决 Windows 下 aiohttp/httpx 的 SSL 连接问题）
if os.environ.get("MOYUN_DISABLE_PROXY_DETECTION", "").lower() in ("1", "true", "yes"):
    os.environ.setdefault('no_proxy', '*')

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.sse import sse_manager
from backend.config import get_settings
from backend.core.event_bus import EventBus
from backend.core.exceptions import MoyunException
from backend.core.file_ops import FileService
from backend.core.llm import LLMService, load_llm_config_from_workspace
from backend.core.llm_circuit_breaker import (
    CircuitBreakerConfig,
    get_circuit_breaker,
    get_state_file_path,
    init_circuit_breaker,
)
from backend.core.pipeline_validator import validate_all_pipelines
from backend.core.task_queue import TaskQueue, run_task_worker

logger = logging.getLogger(__name__)


# ─── 应用生命周期 ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动 / 关闭钩子"""
    settings = get_settings()

    # 确保工作区目录存在
    settings.workspace_path.mkdir(parents=True, exist_ok=True)
    settings.projects_path.mkdir(parents=True, exist_ok=True)
    settings.prompts_path.mkdir(parents=True, exist_ok=True)

    # ── LLM 熔断器初始化 ────────────────────────────────────────
    breaker_config = CircuitBreakerConfig(
        failure_threshold=settings.llm_circuit_failure_threshold,
        reset_timeout_seconds=settings.llm_circuit_reset_timeout_seconds,
        enabled=settings.llm_circuit_breaker_enabled,
    )
    init_circuit_breaker(breaker_config)

    # 恢复熔断器持久化状态
    state_file = get_state_file_path(settings.workspace_path)
    await get_circuit_breaker().load_state(state_file)

    # ── Pipeline YAML 校验 ──────────────────────────────────────
    if settings.validate_pipelines_on_start:
        # 校验系统 prompts 目录下的 pipeline YAML
        system_prompts = settings.system_prompts_path
        if system_prompts.exists():
            results = validate_all_pipelines(system_prompts)
            has_errors = any(not r.valid for r in results)
            if has_errors:
                error_details = []
                for r in results:
                    if r.errors:
                        for err in r.errors:
                            step_info = f" (step={err.step_id})" if err.step_id else ""
                            error_details.append(f"  [{r.file}]{step_info}: {err.message}")
                error_msg = "Pipeline YAML 校验失败:\n" + "\n".join(error_details)
                if settings.debug:
                    raise RuntimeError(error_msg)
                else:
                    logger.error(error_msg)
        else:
            logger.warning("系统 prompts 目录不存在，跳过 pipeline 校验: %s", system_prompts)

    # 初始化 EventBus 并挂载到 app.state
    event_bus = EventBus()
    app.state.event_bus = event_bus

    # 初始化 SSE Manager 并挂载到 app.state
    app.state.sse_manager = sse_manager

    # 启动 EventBus -> SSE 桥接任务
    sse_bridge_task = asyncio.create_task(_bridge_events_to_sse(event_bus, sse_manager))
    app.state.sse_bridge_task = sse_bridge_task

    # 初始化文件监听器（仅在项目目录存在时）
    watcher = None
    # if settings.projects_path.exists():
    #     watcher = FileWatcher(settings.projects_path, event_bus)
    #     await watcher.start()  # 异步启动
    #     app.state.watcher = watcher
    logger.info("文件监听器已禁用（测试模式）")

    # 初始化任务队列（带持久化）和工作线程
    persist_dir = settings.workspace_path / ".task-queue"
    task_queue = TaskQueue.restore(persist_dir)
    restored = len(task_queue._tasks)
    if restored:
        logger.info("任务队列已恢复: %d 个待处理任务", restored)
    app.state.task_queue = task_queue

    # 设置 LLM 并发限制
    LLMService.set_max_concurrent(settings.task_queue_max_concurrent)

    llm_cfg = load_llm_config_from_workspace(settings)
    llm_service = LLMService.from_workspace_config(llm_cfg)
    file_service = FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)

    worker_task = asyncio.create_task(
        run_task_worker(task_queue, llm_service, file_service, event_bus)
    )
    app.state.task_worker_task = worker_task

    logger.info(
        "墨韵后端启动完成 — workspace: %s",
        settings.workspace_path,
    )

    yield

    # 持久化熔断器状态
    try:
        await get_circuit_breaker().save_state(state_file)
    except Exception as e:
        logger.warning("熔断器状态保存失败: %s", e)

    # 关闭时停止桥接任务
    if hasattr(app.state, 'sse_bridge_task'):
        app.state.sse_bridge_task.cancel()
        try:
            await app.state.sse_bridge_task
        except asyncio.CancelledError:
            pass

    # 关闭时停止任务队列工作线程
    if hasattr(app.state, 'task_worker_task'):
        app.state.task_worker_task.cancel()
        try:
            await app.state.task_worker_task
        except asyncio.CancelledError:
            pass

    # 关闭时停止监听器
    if watcher:
        await watcher.stop()  # 异步停止
    logger.info("墨韵后端已关闭")


async def _bridge_events_to_sse(event_bus: EventBus, sse_manager) -> None:
    """将EventBus事件桥接到SSE

    新事件类型使用点分格式（如 file.created），同时保留旧连字符格式兼容前端。
    """
    _, queue = event_bus.subscribe()

    # 新事件类型 → 前端兼容事件名映射
    _NEW_TO_FRONTEND = {
        "file.created": "file-created",
        "file.updated": "file-updated",  # AI_GUARDRAIL_ALLOW: event name mapping
        "file.deleted": "file-deleted",
        "candidate.created": "file-created",
        "candidate.adopted": "file-updated",
        "pipeline.started": "task",
        "pipeline.step.started": "task",
        "pipeline.step.completed": "task",
        "pipeline.step.failed": "error",
        "task.waiting_for_user": "task",
        "task.completed": "task",
        "memory.updated": "file-updated",
    }

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
                raw_type = event.get("type", "unknown")
                data = event.get("data", {})

                # 1. 新点分格式 → 映射到前端兼容名
                if raw_type in _NEW_TO_FRONTEND:
                    frontend_type = _NEW_TO_FRONTEND[raw_type]
                else:
                    # 2. 旧格式兼容：file:created → file-created
                    frontend_type = raw_type.replace(":", "-")

                await sse_manager.broadcast(frontend_type, data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"事件桥接异常: {e}")
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("SSE桥接任务已取消")
    finally:
        event_bus.unsubscribe(queue)


# ─── 创建应用 ─────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="墨韵 API",
        description="AI 小说创作助手后端服务",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"http://(127\.0\.0\.1|localhost):(517[0-9]|3000).*",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── 全局异常处理 ─────────────────────────────────────────────
    @app.exception_handler(MoyunException)
    async def moyun_exception_handler(
        request: Request, exc: MoyunException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=_moyun_to_http_status(exc.code),
            content={
                "success": False,
                "data": None,
                "message": exc.message,
                "error": exc.to_dict(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("未处理异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "message": "服务器内部错误",
                "error": {"code": "INTERNAL_ERROR", "details": str(exc)},
            },
        )

    # ─── 注册路由 ─────────────────────────────────────────────────
    from backend.api import (
        backup,
        candidates,
        characters,
        compare,
        config,
        feedback,
        files,
        generate,
        lite,
        llm,
        materials,
        pipeline,
        projects,
        prompts,
        quality,
        recent_context,
        revision_log,
        snapshots,
        sse,
        story_state,
        style_guide,
        tasks,
        tokens,
        trash,
        wizard,
        workflows,
    )

    app.include_router(projects.router, prefix="/api")
    app.include_router(wizard.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(llm.router, prefix="/api")
    app.include_router(generate.router, prefix="/api")
    app.include_router(sse.router, prefix="/api")
    app.include_router(prompts.router, prefix="/api")
    app.include_router(style_guide.router, prefix="/api")
    app.include_router(story_state.router, prefix="/api")
    app.include_router(recent_context.router, prefix="/api")
    app.include_router(feedback.router, prefix="/api")
    app.include_router(revision_log.router, prefix="/api")
    app.include_router(tokens.router, prefix="/api")
    app.include_router(compare.router, prefix="/api")
    app.include_router(backup.router, prefix="/api")
    app.include_router(characters.router, prefix="/api")
    app.include_router(materials.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(quality.router, prefix="/api")
    app.include_router(pipeline.router, prefix="/api")
    app.include_router(snapshots.router, prefix="/api")
    app.include_router(config.router, prefix="/api")
    app.include_router(workflows.router, prefix="/api")
    app.include_router(trash.router, prefix="/api")
    app.include_router(lite.router, prefix="/api")
    app.include_router(candidates.router, prefix="/api")

    # ── 前端静态文件 & 单页入口 ──────────────────────────────────
    # 优先 serve Vue 构建产物 (dist/)，fallback 到 prototype.html
    frontend_parent = settings.workspace_path.parent
    frontend_dist = frontend_parent / "frontend" / "dist"
    frontend_dev = frontend_parent / "frontend"

    # 1) 生产环境：Vue build 输出在 frontend/dist/，StaticFiles(html=True) 自动 serve index.html
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend-dist")
    else:
        # 2) 开发环境：手动挂载 frontend/ 下的子目录，根路径 fallback 到 prototype.html
        if frontend_dev.exists():
            for mount_path, subdir in [("/assets", "assets"), ("/css", "css"), ("/js", "js")]:
                subdir_path = frontend_dev / subdir
                if subdir_path.exists():
                    app.mount(mount_path, StaticFiles(directory=str(subdir_path)), name=subdir)

        prototype_html = frontend_parent / "prototype.html"

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def serve_index():
            if prototype_html.exists():
                return HTMLResponse(prototype_html.read_text(encoding="utf-8"))
            return HTMLResponse("<h1>墨韵</h1><p>前端文件不存在</p>")

    return app


def _moyun_to_http_status(error_code: str) -> int:
    _map = {
        "PROJECT_ERROR": 400,
        "PROJECT_NOT_FOUND": 404,
        "FILE_ERROR": 400,
        "FILE_NOT_FOUND": 404,
        "FILE_CONFLICT": 409,
        "RESOURCE_NOT_FOUND": 404,
        "FILE_ALREADY_EXISTS": 409,
        "TEMPLATE_ERROR": 400,
        "TEMPLATE_NOT_FOUND": 404,
        "INVALID_TEMPLATE": 422,
        "INVALID_VARIABLE": 422,
        "VALIDATION_ERROR": 422,
        "LLM_ERROR": 503,
        "LLM_TIMEOUT": 504,
        "LLM_CIRCUIT_OPEN": 503,
        "TASK_ERROR": 400,
        "TASK_NOT_FOUND": 404,
        "RATE_LIMIT": 429,
        "CONFIG_ERROR": 400,
        "CONTEXT_LENGTH_ERROR": 413,
    }
    return _map.get(error_code, 500)


# 全局 app 实例（供 uvicorn 直接引用）
# 测试时请使用 create_app() 创建隔离实例，不要直接 import 此变量
app = create_app()
