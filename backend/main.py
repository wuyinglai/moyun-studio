"""墨韵 - FastAPI 应用入口"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.core.event_bus import EventBus
from backend.core.exceptions import MoyunException
from backend.api.sse import sse_manager
from backend.core.watcher import FileWatcher

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
    if settings.projects_path.exists():
        watcher = FileWatcher(settings.projects_path, event_bus)
        watcher.start()  # 同步方法
        app.state.watcher = watcher

    logger.info(
        "墨韵后端启动完成 — workspace: %s",
        settings.workspace_path,
    )

    yield

    # 关闭时停止桥接任务
    if hasattr(app.state, 'sse_bridge_task'):
        app.state.sse_bridge_task.cancel()
        try:
            await app.state.sse_bridge_task
        except asyncio.CancelledError:
            pass

    # 关闭时停止监听器
    if watcher:
        watcher.stop()  # 同步方法
    logger.info("墨韵后端已关闭")


async def _bridge_events_to_sse(event_bus: EventBus, sse_manager) -> None:
    """将EventBus事件桥接到SSE"""
    _, queue = event_bus.subscribe()
    
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
                event_type = event.get("type", "unknown")
                data = event.get("data", {})
                await sse_manager.broadcast(event_type, data)
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
        projects,
        wizard,
        files,
        llm,
        generate,
        events,
        prompts,
        style_guide,
        story_state,
        recent_context,
        feedback,
        revision_log,
        tokens,
        compare,
        backup,
        characters,
        materials,
        sse,
    )

    app.include_router(projects.router, prefix="/api")
    app.include_router(wizard.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(llm.router, prefix="/api")
    app.include_router(generate.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
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
        "RESOURCE_NOT_FOUND": 404,
        "FILE_ALREADY_EXISTS": 409,
        "TEMPLATE_ERROR": 400,
        "TEMPLATE_NOT_FOUND": 404,
        "INVALID_TEMPLATE": 422,
        "INVALID_VARIABLE": 422,
        "VALIDATION_ERROR": 422,
        "LLM_ERROR": 503,
        "LLM_TIMEOUT": 504,
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
