"""墨韵 - FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.core.event_bus import EventBus
from backend.core.exceptions import MoyunException

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

    # 初始化文件监听器（仅在项目目录存在时）
    watcher = None
    if settings.projects_path.exists():
        from backend.core.watcher import FileWatcher
        watcher = FileWatcher(settings.projects_path, event_bus)
        watcher.start()  # 同步方法
        app.state.watcher = watcher

    logger.info(
        "墨韵后端启动完成 — workspace: %s",
        settings.workspace_path,
    )

    yield

    # 关闭时停止监听器
    if watcher:
        watcher.stop()  # 同步方法
    logger.info("墨韵后端已关闭")


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
        allow_origins=["*"],  # 本地单用户部署，全开
        allow_credentials=True,
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
    from backend.api import projects, files, llm, generate, events, prompts

    app.include_router(projects.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(llm.router, prefix="/api")
    app.include_router(generate.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(prompts.router, prefix="/api")

    # ─── 前端静态文件 & 单页入口 ──────────────────────────────────
    frontend_dir = settings.workspace_path.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")
        app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
        app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")

    # 根路径返回主页面
    prototype_html = settings.workspace_path.parent / "prototype.html"

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_index():
        if prototype_html.exists():
            return HTMLResponse(prototype_html.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>墨韵</h1><p>前端文件不存在</p>")

    return app


def _moyun_to_http_status(error_code: str) -> int:
    _map = {
        "PROJECT_NOT_FOUND": 404,
        "FILE_NOT_FOUND": 404,
        "FILE_ALREADY_EXISTS": 409,
        "TEMPLATE_NOT_FOUND": 404,
        "INVALID_TEMPLATE": 422,
        "INVALID_VARIABLE": 422,
        "LLM_ERROR": 503,
        "LLM_TIMEOUT": 504,
        "VALIDATION_ERROR": 422,
        "RATE_LIMIT": 429,
    }
    return _map.get(error_code, 500)


# 全局 app 实例（供 uvicorn 直接引用）
app = create_app()
