"""墨韵 - 修改日志 API

端点：
  GET  /api/revision-log/{project_id}      获取章节的修改日志
  POST /api/revision-log/{project_id}       记录修改日志
"""

import asyncio
from datetime import datetime
import difflib
import json
import logging
from pathlib import Path
import re
from typing import Any
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["修改日志"], prefix="/revision-log")


# ─── Schema ──────────────────────────────────────────────────────────

class RevisionLog(BaseModel):
    """修改日志"""
    id: str = Field(..., description="日志ID")
    chapter_path: str = Field(..., description="章节路径")
    revision_type: str = Field(
        ...,
        description="修改类型: ai_rewrite/user_edit/auto_save"
    )
    description: str = Field(..., description="修改描述")
    word_count_before: int = Field(default=0, ge=0, description="修改前字数")
    word_count_after: int = Field(default=0, ge=0, description="修改后字数")
    diff: str | None = Field(None, description="差异内容")
    created_at: str = Field(..., description="创建时间")


class CreateRevisionLogRequest(BaseModel):
    """创建修改日志请求"""
    chapter_path: str = Field(..., description="章节路径")
    revision_type: str = Field(
        ...,
        description="修改类型",
        pattern="^(ai_rewrite|user_edit|auto_save)$"
    )
    description: str = Field(..., description="修改描述")
    content_before: str = Field(default="", description="修改前内容")
    content_after: str = Field(default="", description="修改后内容")


# ─── 工具函数 ────────────────────────────────────────────────────────

def _get_revision_log_dir(
    project_id: str,
    chapter_path: str,
    settings: Settings
) -> Path:
    """获取修改日志目录路径"""
    parts = chapter_path.split("/")
    if len(parts) >= 2:
        chapter_dir = "/".join(parts[:-1])
    else:
        chapter_dir = chapter_path

    return settings.projects_path / project_id / chapter_dir / "revision-log"


def _generate_diff(before: str, after: str) -> str:
    """生成统一差异格式（unified diff）"""
    if not before and not after:
        return ""

    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)

    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile="修改前",
        tofile="修改后",
        lineterm=""
    )

    return "".join(diff)


async def _load_revision_logs(revision_dir: Path) -> list[dict[str, Any]]:
    """加载所有修改日志"""
    if not await asyncio.to_thread(revision_dir.exists):
        return []

    log_files = await asyncio.to_thread(lambda: list(revision_dir.glob("*.json")))
    logs = []
    for f in log_files:
        try:
            data = json.loads(await asyncio.to_thread(f.read_text, encoding="utf-8"))
            logs.append(data)
        except json.JSONDecodeError:
            logger.warning("修改日志文件解析失败: %s", f)

    # 按时间倒序排列
    logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return logs


async def _save_revision_log(revision_dir: Path, log_data: dict[str, Any]) -> None:
    """保存修改日志"""
    await asyncio.to_thread(revision_dir.mkdir, parents=True, exist_ok=True)
    file_path = revision_dir / f"{log_data['id']}.json"
    await asyncio.to_thread(
        file_path.write_text,
        json.dumps(log_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _get_revision_log_file(revision_dir: Path, log_id: str) -> Path | None:
    """获取修改日志文件路径"""
    file_path = revision_dir / f"{log_id}.json"
    return file_path if await asyncio.to_thread(file_path.exists) else None


def _count_words(text: str) -> int:
    """统计字数（中英文混合）"""
    # 匹配中文字符和英文单词
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    # 简单估算：中文每个字算1词，英文每个单词算1词
    return chinese_chars + english_words


# ─── 路由 ────────────────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ApiResponse[list[RevisionLog]])
async def list_revision_logs(
    project_id: str,
    chapter_path: str | None = None,
    revision_type: str | None = None,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[list[RevisionLog]]:
    """获取修改日志列表

    Args:
        project_id: 项目ID
        chapter_path: 可选，筛选特定章节的日志
        revision_type: 可选，筛选特定类型的日志

    Returns:
        修改日志列表
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    all_logs: list[dict[str, Any]] = []

    if chapter_path:
        # 获取特定章节的日志
        revision_dir = _get_revision_log_dir(project_id, chapter_path, settings)
        all_logs = await _load_revision_logs(revision_dir)
    else:
        # 获取所有章节的日志
        chapters_dir = settings.projects_path / project_id / "chapters"
        if await asyncio.to_thread(chapters_dir.exists):
            revision_dirs = await asyncio.to_thread(
                lambda: list(chapters_dir.rglob("revision-log"))
            )
            for rev_dir in revision_dirs:
                logs = await _load_revision_logs(rev_dir)
                all_logs.extend(logs)

    # 过滤
    if revision_type:
        all_logs = [log for log in all_logs if log.get("revision_type") == revision_type]

    # 按时间倒序排列
    all_logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # 转换为响应模型
    result = [RevisionLog(**log) for log in all_logs]

    logger.debug(
        "获取修改日志列表: 项目=%s, 章节=%s, 类型=%s, 数量=%d",
        project_id, chapter_path, revision_type, len(result)
    )
    return ApiResponse.ok(result)


@router.post("/{project_id}", response_model=ApiResponse[RevisionLog])
async def create_revision_log(
    project_id: str,
    req: CreateRevisionLogRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[RevisionLog]:
    """记录修改日志

    Args:
        project_id: 项目ID
        req: 修改日志内容

    Returns:
        创建的修改日志
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    # 生成日志ID
    log_id = f"rev-{uuid.uuid4().hex[:8]}"

    # 统计字数
    word_count_before = _count_words(req.content_before)
    word_count_after = _count_words(req.content_after)

    # 生成差异
    diff = _generate_diff(req.content_before, req.content_after)

    # 计算字数变化
    word_count_change = word_count_after - word_count_before
    change_str = f"+{word_count_change}" if word_count_change >= 0 else str(word_count_change)

    # 创建日志数据
    log_data: dict[str, Any] = {
        "id": log_id,
        "chapter_path": req.chapter_path,
        "revision_type": req.revision_type,
        "description": req.description,
        "word_count_before": word_count_before,
        "word_count_after": word_count_after,
        "word_count_change": change_str,
        "diff": diff if diff else None,
        "created_at": datetime.now().isoformat()
    }

    # 获取日志目录并保存
    revision_dir = _get_revision_log_dir(project_id, req.chapter_path, settings)
    await _save_revision_log(revision_dir, log_data)

    logger.info(
        "修改日志已创建: 项目=%s, 章节=%s, 类型=%s, 字数变化=%s",
        project_id, req.chapter_path, req.revision_type, change_str
    )

    return ApiResponse.ok(
        RevisionLog(**log_data),
        message="修改日志已记录"
    )


@router.get("/{project_id}/{log_id}", response_model=ApiResponse[RevisionLog])
async def get_revision_log(
    project_id: str,
    log_id: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[RevisionLog]:
    """获取特定修改日志详情

    Args:
        project_id: 项目ID
        log_id: 日志ID

    Returns:
        修改日志详情
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not await asyncio.to_thread(project_dir.exists):
        raise ProjectNotFoundError(project_id)

    # 查找日志文件
    log_file = None
    chapters_dir = settings.projects_path / project_id / "chapters"
    if await asyncio.to_thread(chapters_dir.exists):
        revision_dirs = await asyncio.to_thread(
            lambda: list(chapters_dir.rglob("revision-log"))
        )
        for rev_dir in revision_dirs:
            f = await _get_revision_log_file(rev_dir, log_id)
            if f:
                log_file = f
                break

    if not log_file:
        raise ResourceNotFoundError(resource="revision-log", identifier=log_id)

    # 加载日志
    log_data = json.loads(await asyncio.to_thread(log_file.read_text, encoding="utf-8"))

    logger.debug("获取修改日志详情: %s", log_id)
    return ApiResponse.ok(RevisionLog(**log_data))
