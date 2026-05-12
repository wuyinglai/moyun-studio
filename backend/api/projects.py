"""墨韵 - 项目管理 API

端点：
  GET    /api/projects           获取项目列表
  POST   /api/projects           创建新项目
  GET    /api/projects/{id}      获取项目详情
  DELETE /api/projects/{id}      删除项目
"""

import asyncio
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectError, ProjectNotFoundError
from backend.schemas.common import ApiResponse
from backend.schemas.project import (
    ProjectCreateRequest,
    ProjectInfo,
    ProjectListResponse,
    BookIdeaRequest,
    BookIdeaResponse,
    GenerateOutlineRequest,
    OutlineResponse,
    ConfirmOutlineRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["projects"])


# ─── 辅助函数 ──────────────────────────────────────────────────────

def _meta_path(project_dir: Path) -> Path:
    return project_dir / "meta.json"


def _load_meta(project_dir: Path) -> dict | None:
    mp = _meta_path(project_dir)
    if not mp.exists():
        return None
    return json.loads(mp.read_text(encoding="utf-8"))


def _context_path(project_dir: Path) -> Path:
    return project_dir / "context.json"


def _load_context(project_dir: Path) -> dict:
    cp = _context_path(project_dir)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    return {"stats": {"total_words": 0, "total_sections": 0, "completed_sections": 0}}


def _compute_completion(meta: dict, context: dict) -> tuple[float, int]:
    """返回 (completion_rate, total_words)"""
    stats = context.get("stats", {})
    total = stats.get("total_sections", 0)
    completed = stats.get("completed_sections", 0)
    rate = (completed / total) if total > 0 else 0.0
    return rate, stats.get("total_words", 0)


def _project_info(project_dir: Path) -> ProjectInfo | None:
    meta = _load_meta(project_dir)
    if meta is None:
        return None
    context = _load_context(project_dir)
    rate, words = _compute_completion(meta, context)

    # datetime 兼容处理
    def _dt(s: str) -> datetime:
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.now(timezone.utc)

    return ProjectInfo(
        project_id=meta["project_id"],
        name=meta.get("name", project_dir.name),
        genre=meta.get("genre", ""),
        theme=meta.get("theme", ""),
        tone=meta.get("tone", ""),
        target_word_count=meta.get("target_word_count", 0),
        completion_rate=round(rate, 4),
        total_words=words,
        created_at=_dt(meta.get("created_at", "")),
        updated_at=_dt(meta.get("updated_at", "")),
    )


# ─── 路由 ─────────────────────────────────────────────────────────

@router.get("/projects", response_model=ApiResponse[ProjectListResponse])
async def list_projects(settings: Settings = Depends(get_settings)):
    """获取所有项目列表"""
    projects_path = settings.projects_path
    projects_path.mkdir(parents=True, exist_ok=True)

    projects: list[ProjectInfo] = []
    for d in sorted(projects_path.iterdir()):
        if d.is_dir():
            info = _project_info(d)
            if info:
                projects.append(info)

    # 按更新时间倒序
    projects.sort(key=lambda p: p.updated_at, reverse=True)
    return ApiResponse.ok(ProjectListResponse(projects=projects, total=len(projects)))


@router.post("/projects", response_model=ApiResponse[ProjectInfo], status_code=201)
async def create_project(
    req: ProjectCreateRequest,
    settings: Settings = Depends(get_settings),
):
    """创建新项目"""
    project_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    logger.info("创建新项目", extra={"project_id": project_id, "name": req.name, "genre": req.genre})

    project_dir = settings.projects_path / project_id
    await asyncio.to_thread(project_dir.mkdir, parents=True, exist_ok=True)

    # 写 meta.json
    meta = {
        "project_id": project_id,
        "name": req.name,
        "genre": req.genre,
        "theme": req.theme,
        "tone": req.tone,
        "background": req.background,
        "writing_style": req.writing_style,
        "target_word_count": req.target_word_count,
        "author": req.author,
        "created_at": now,
        "updated_at": now,
    }
    await asyncio.to_thread(
        _meta_path(project_dir).write_text,
        json.dumps(meta, ensure_ascii=False, indent=2),
        "utf-8",
    )

    # 写 context.json
    context = {
        "project_id": project_id,
        "stats": {
            "total_words": 0,
            "total_sections": 0,
            "completed_sections": 0,
            "chapter_count": 0,
            "volume_count": 0,
            "character_count": 0,
        },
        "updated_at": now,
    }
    await asyncio.to_thread(
        _context_path(project_dir).write_text,
        json.dumps(context, ensure_ascii=False, indent=2),
        "utf-8",
    )

    # 创建基础子目录
    for subdir in ["chapters", "characters", "materials/extracted", "backup", "revision-log", "feedback"]:
        await asyncio.to_thread((project_dir / subdir).mkdir, parents=True, exist_ok=True)

    # 初始化 style-guide.md / story-state.md / recent-context.md
    for filename, content in [
        ("style-guide.md", "# 文风指南\n\n在此描述写作风格、语气、叙事视角等要求。\n"),
        ("story-state.md", "# 故事状态\n\n## 主角状态\n\n## 势力关系\n\n## 伏笔追踪\n\n## 主线进度\n"),
        ("recent-context.md", "# 近期上下文\n\n（最近5章摘要，由系统自动维护）\n"),
        ("outline.md", f"# {req.name} - 大纲\n\n"),
    ]:
        await asyncio.to_thread(
            (project_dir / filename).write_text, content, "utf-8",
        )

    info = _project_info(project_dir)
    return ApiResponse.ok(info, message="项目创建成功")


@router.get("/projects/{project_id}", response_model=ApiResponse[ProjectInfo])
async def get_project(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """获取项目详情"""
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    info = _project_info(project_dir)
    if info is None:
        logger.error("项目meta损坏", extra={"project_id": project_id})
        raise ProjectNotFoundError(project_id)
    return ApiResponse.ok(info)


@router.delete("/projects/{project_id}", response_model=ApiResponse[None])
async def delete_project(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """删除项目（不可恢复）"""
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    try:
        await asyncio.to_thread(shutil.rmtree, project_dir)
    except Exception as e:
        logger.error("删除项目失败", extra={"project_id": project_id, "error": str(e)})
        raise ProjectError(f"删除项目失败: {str(e)}")

    logger.info("项目已删除", extra={"project_id": project_id})
    return ApiResponse.ok(message=f"项目 {project_id} 已删除")

