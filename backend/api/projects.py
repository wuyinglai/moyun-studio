"""墨韵 - 项目管理 API

端点：
  GET    /api/projects           获取项目列表
  POST   /api/projects           创建新项目
  GET    /api/projects/{id}      获取项目详情
  DELETE /api/projects/{id}      删除项目
"""

import asyncio
from datetime import datetime, timezone
import logging
import uuid

from fastapi import APIRouter, Depends

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError
from backend.core.project_service import ProjectService
from backend.schemas.common import ApiResponse
from backend.schemas.project import (
    ProjectCreateRequest,
    ProjectInfo,
    ProjectListResponse,
    ProjectStatsResponse,
    ProjectUpdateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=ApiResponse[ProjectListResponse])
async def list_projects(settings: Settings = Depends(get_settings)):
    """获取所有项目列表"""
    svc = ProjectService(settings)
    projects = svc.list_projects()
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

    svc = ProjectService(settings)
    project_dir = settings.projects_path / project_id
    await asyncio.to_thread(project_dir.mkdir, parents=True, exist_ok=True)

    # 写 meta.json
    meta = svc.create_project_meta(project_id, req.name, req)
    await asyncio.to_thread(svc.write_meta, project_dir, meta)

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
    await asyncio.to_thread(svc.write_context, project_dir, context)

    # 创建基础子目录
    for subdir in ["chapters", "characters", "materials/extracted", "backup", "revision-log", "feedback"]:
        await asyncio.to_thread((project_dir / subdir).mkdir, parents=True, exist_ok=True)

    # 初始化文件
    for filename, content in [
        ("style-guide.md", "# 文风指南\n\n在此描述写作风格、语气、叙事视角等要求。\n"),
        ("story-state.md", "# 故事状态\n\n## 主角状态\n\n## 势力关系\n\n## 伏笔追踪\n\n## 主线进度\n"),
        ("story-engine.md", "# 故事引擎\n\n## 人物欲望\n\n## 冲突推进\n\n## 场景直觉\n\n## 前文记忆\n\n## 读者期待\n\n## 阶段性目标\n"),
        ("recent-context.md", "# 近期上下文\n\n（最近5章摘要，由系统自动维护）\n"),
        ("outline.md", f"# {req.name} - 大纲\n\n"),
    ]:
        await asyncio.to_thread(
            (project_dir / filename).write_text, content, "utf-8",
        )

    info = svc.get_project_info(project_dir)
    return ApiResponse.ok(info, message="项目创建成功")


@router.get("/projects/{project_id}", response_model=ApiResponse[ProjectInfo])
async def get_project(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """获取项目详情"""
    svc = ProjectService(settings)
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    info = svc.get_project_info(project_dir)
    if info is None:
        logger.error("项目meta损坏", extra={"project_id": project_id})
        raise ProjectNotFoundError(project_id)
    return ApiResponse.ok(info)


@router.put("/projects/{project_id}", response_model=ApiResponse[ProjectInfo])
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    settings: Settings = Depends(get_settings),
):
    """更新项目元数据"""
    svc = ProjectService(settings)
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    meta = svc._load_meta(project_dir)
    if meta is None:
        logger.error("项目meta损坏", extra={"project_id": project_id})
        raise ProjectNotFoundError(project_id)

    updates = req.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if value is not None:
            meta[key] = value
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    await asyncio.to_thread(svc.write_meta, project_dir, meta)

    info = svc.get_project_info(project_dir)
    if info is None:
        raise ProjectNotFoundError(project_id)
    return ApiResponse.ok(info, message="项目已更新")


@router.post("/projects/{project_id}/recalculate-stats", response_model=ApiResponse[ProjectStatsResponse])
async def recalculate_project_stats(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """重新计算项目完成度统计"""
    svc = ProjectService(settings)
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    stats = svc.recalculate_stats(project_dir)
    completion_rate = (stats["completed_sections"] / stats["total_sections"]) if stats["total_sections"] > 0 else 0.0

    # 更新 context.json
    svc.save_stats(project_dir, stats)

    logger.info("项目统计已重新计算", extra={
        "project_id": project_id,
        "total_sections": stats["total_sections"],
        "completed_sections": stats["completed_sections"],
        "total_words": stats["total_words"],
    })

    return ApiResponse.ok(ProjectStatsResponse(
        total_sections=stats["total_sections"],
        completed_sections=stats["completed_sections"],
        total_words=stats["total_words"],
        chapter_count=stats["chapter_count"],
        volume_count=stats["volume_count"],
        completion_rate=round(completion_rate, 4),
    ))


@router.delete("/projects/{project_id}", response_model=ApiResponse[None])
async def delete_project(
    project_id: str,
    settings: Settings = Depends(get_settings),
):
    """删除项目（不可恢复）"""
    svc = ProjectService(settings)
    svc.delete_project_dir(project_id)
    logger.info("项目已删除", extra={"project_id": project_id})
    return ApiResponse.ok(message=f"项目 {project_id} 已删除")

