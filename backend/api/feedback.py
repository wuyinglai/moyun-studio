"""墨韵 - 用户反馈 API

端点：
  GET  /api/feedback/{project_id}      获取章节的用户反馈列表
  POST /api/feedback/{project_id}       提交用户反馈
  PATCH /api/feedback/{project_id}/{feedback_id}  更新反馈状态
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError, ResourceNotFoundError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["用户反馈"], prefix="/feedback")


# ─── Schema ──────────────────────────────────────────────────────────

class UserFeedback(BaseModel):
    """用户反馈"""
    id: str = Field(..., description="反馈ID")
    chapter_path: str = Field(..., description="章节路径")
    type: str = Field(..., description="反馈类型: suggestion/error/improvement")
    content: str = Field(..., description="反馈内容")
    location: str | None = Field(None, description="问题位置")
    satisfaction_level: str | None = Field(None, description="满意度: 满意/一般/不满意")
    resolved: bool = Field(default=False, description="是否已解决")
    created_at: str = Field(..., description="创建时间")
    resolved_at: str | None = Field(None, description="解决时间")


class CreateFeedbackRequest(BaseModel):
    """创建反馈请求"""
    chapter_path: str = Field(..., description="章节路径")
    type: str = Field(
        ...,
        description="反馈类型",
        pattern="^(suggestion|error|improvement)$"
    )
    content: str = Field(..., min_length=1, description="反馈内容")
    location: str | None = Field(None, description="问题位置")
    satisfaction_level: str | None = Field(
        None,
        description="满意度",
        pattern="^(满意|一般|不满意)?$"
    )


class UpdateFeedbackRequest(BaseModel):
    """更新反馈请求"""
    resolved: bool | None = Field(None, description="是否已解决")
    content: str | None = Field(None, description="更新反馈内容")


# ─── 工具函数 ────────────────────────────────────────────────────────

def _get_feedback_dir(project_id: str, chapter_path: str, settings: Settings) -> Path:
    """获取反馈目录路径"""
    # 从 chapter_path 提取章节目录
    # 例如: chapters/vol-01/ch-001/sec-001.md -> chapters/vol-01/ch-001/feedback
    parts = chapter_path.split("/")
    if len(parts) >= 2:
        # 获取 ch-xxx 目录
        chapter_dir = "/".join(parts[:-1])
    else:
        chapter_dir = chapter_path

    return settings.projects_path / project_id / chapter_dir / "feedback"


def _load_feedbacks(feedback_dir: Path) -> list[dict[str, Any]]:
    """加载所有反馈"""
    if not feedback_dir.exists():
        return []

    feedbacks = []
    for f in feedback_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            feedbacks.append(data)
        except json.JSONDecodeError:
            logger.warning("反馈文件解析失败: %s", f)

    # 按时间倒序排列
    feedbacks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return feedbacks


def _save_feedback(feedback_dir: Path, feedback_data: dict[str, Any]) -> None:
    """保存反馈"""
    feedback_dir.mkdir(parents=True, exist_ok=True)
    file_path = feedback_dir / f"{feedback_data['id']}.json"
    file_path.write_text(
        json.dumps(feedback_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _get_feedback_file(feedback_dir: Path, feedback_id: str) -> Path | None:
    """获取反馈文件路径"""
    file_path = feedback_dir / f"{feedback_id}.json"
    return file_path if file_path.exists() else None


# ─── 路由 ────────────────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ApiResponse[list[UserFeedback]])
async def list_feedbacks(
    project_id: str,
    chapter_path: str | None = None,
    resolved: bool | None = None,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[list[UserFeedback]]:
    """获取用户反馈列表

    Args:
        project_id: 项目ID
        chapter_path: 可选，筛选特定章节的反馈
        resolved: 可选，筛选已解决/未解决的反馈

    Returns:
        反馈列表
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    all_feedbacks: list[dict[str, Any]] = []

    if chapter_path:
        # 获取特定章节的反馈
        feedback_dir = _get_feedback_dir(project_id, chapter_path, settings)
        all_feedbacks = _load_feedbacks(feedback_dir)
    else:
        # 获取所有章节的反馈
        chapters_dir = settings.projects_path / project_id / "chapters"
        if chapters_dir.exists():
            for feedback_dir in chapters_dir.rglob("feedback"):
                feedbacks = _load_feedbacks(feedback_dir)
                all_feedbacks.extend(feedbacks)

    # 过滤
    if resolved is not None:
        all_feedbacks = [f for f in all_feedbacks if f.get("resolved") == resolved]

    # 转换为响应模型
    result = [UserFeedback(**f) for f in all_feedbacks]

    logger.debug("获取反馈列表: 项目=%s, 章节=%s, 数量=%d", project_id, chapter_path, len(result))
    return ApiResponse.ok(result)


@router.post("/{project_id}", response_model=ApiResponse[UserFeedback])
async def create_feedback(
    project_id: str,
    req: CreateFeedbackRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[UserFeedback]:
    """提交用户反馈

    Args:
        project_id: 项目ID
        req: 反馈内容

    Returns:
        创建的反馈
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    # 生成反馈ID
    feedback_id = f"fb-{uuid.uuid4().hex[:8]}"

    # 创建反馈数据
    feedback_data: dict[str, Any] = {
        "id": feedback_id,
        "chapter_path": req.chapter_path,
        "type": req.type,
        "content": req.content,
        "location": req.location,
        "satisfaction_level": req.satisfaction_level,
        "resolved": False,
        "created_at": datetime.now().isoformat(),
        "resolved_at": None
    }

    # 获取反馈目录并保存
    feedback_dir = _get_feedback_dir(project_id, req.chapter_path, settings)
    _save_feedback(feedback_dir, feedback_data)

    logger.info(
        "用户反馈已创建: 项目=%s, 章节=%s, 反馈ID=%s",
        project_id, req.chapter_path, feedback_id
    )

    return ApiResponse.ok(
        UserFeedback(**feedback_data),
        message="反馈已提交"
    )


@router.patch("/{project_id}/{feedback_id}", response_model=ApiResponse[UserFeedback])
async def update_feedback(
    project_id: str,
    feedback_id: str,
    req: UpdateFeedbackRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[UserFeedback]:
    """更新反馈状态

    Args:
        project_id: 项目ID
        feedback_id: 反馈ID
        req: 更新内容

    Returns:
        更新后的反馈
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    # 查找反馈文件
    feedback_file = None
    feedback_dir = None

    # 搜索反馈文件
    chapters_dir = settings.projects_path / project_id / "chapters"
    if chapters_dir.exists():
        for fd in chapters_dir.rglob("feedback"):
            f = _get_feedback_file(fd, feedback_id)
            if f:
                feedback_file = f
                feedback_dir = fd
                break

    if not feedback_file:
        raise ResourceNotFoundError(resource="feedback", identifier=feedback_id)

    # 加载并更新反馈
    feedback_data = json.loads(feedback_file.read_text(encoding="utf-8"))

    if req.resolved is not None:
        feedback_data["resolved"] = req.resolved
        if req.resolved:
            feedback_data["resolved_at"] = datetime.now().isoformat()

    if req.content is not None:
        feedback_data["content"] = req.content

    # 保存更新
    _save_feedback(feedback_dir, feedback_data)

    logger.info("反馈已更新: %s", feedback_id)

    return ApiResponse.ok(
        UserFeedback(**feedback_data),
        message="反馈已更新"
    )


@router.delete("/{project_id}/{feedback_id}", response_model=ApiResponse[None])
async def delete_feedback(
    project_id: str,
    feedback_id: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    """删除反馈（标记为已解决）

    Args:
        project_id: 项目ID
        feedback_id: 反馈ID

    Returns:
        删除成功响应
    """
    # 查找反馈文件
    feedback_file = None
    feedback_dir = None

    chapters_dir = settings.projects_path / project_id / "chapters"
    if chapters_dir.exists():
        for fd in chapters_dir.rglob("feedback"):
            f = _get_feedback_file(fd, feedback_id)
            if f:
                feedback_file = f
                feedback_dir = fd
                break

    if not feedback_file:
        raise ResourceNotFoundError(resource="feedback", identifier=feedback_id)

    # 标记为已解决而非物理删除
    feedback_data = json.loads(feedback_file.read_text(encoding="utf-8"))
    feedback_data["resolved"] = True
    feedback_data["resolved_at"] = datetime.now().isoformat()
    _save_feedback(feedback_dir, feedback_data)

    logger.info("反馈已标记为已解决: %s", feedback_id)

    return ApiResponse.ok(message="反馈已删除")
