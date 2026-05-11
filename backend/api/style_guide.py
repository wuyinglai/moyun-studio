"""墨韵 - 文风指南 API

端点：
  GET  /api/style-guide/{project_id}  获取文风指南内容
  POST /api/style-guide/{project_id}  保存文风指南内容
"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["文风指南"], prefix="/style-guide")


# ─── Schema ──────────────────────────────────────────────────────────

class StyleGuideContent(BaseModel):
    """文风指南内容"""
    content: str = Field(..., description="文风指南Markdown内容")
    last_modified: str | None = Field(None, description="最后修改时间")


class SaveStyleGuideRequest(BaseModel):
    """保存文风指南请求"""
    content: str = Field(..., description="文风指南Markdown内容")


# ─── 默认文风指南模板 ─────────────────────────────────────────────────

DEFAULT_STYLE_GUIDE = """# 文风指南

## 一、文风定位
- 整体风格：简洁干练 / 华丽优美 / 口语化 / 古风典雅 / 冷峻硬朗 / 温暖治愈
- 句子节奏：
- 描写密度：
- 语言特点：

## 二、示范文字
（用户上传的示范文字片段，用于参考学习）

## 三、写作风格要点
- 叙述方式：
- 对话风格：
- 心理描写：
- 场景描写：

## 四、写作禁忌
- 避免的表达方式1：
- 避免的表达方式2：
- 避免的表达方式3：

## 五、题材特点
- 本题材特有的表达习惯：
- 行业术语/设定术语的使用规范：

## 六、角色说话风格
### 主角
- 说话风格：
- 口头禅：
- 语言习惯：

### 其他角色
- 说话风格：
- 语言特点：

## 七、参考范例
（用户认可的优秀文风范例）
"""


# ─── 路由 ────────────────────────────────────────────────────────────

def _get_style_guide_path(project_id: str, settings: Settings) -> Path:
    """获取文风指南文件路径"""
    return settings.projects_path / project_id / "style-guide.md"


@router.get("/{project_id}", response_model=ApiResponse[StyleGuideContent])
async def get_style_guide(
    project_id: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[StyleGuideContent]:
    """获取文风指南内容

    Args:
        project_id: 项目ID

    Returns:
        文风指南内容和最后修改时间

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    file_path = _get_style_guide_path(project_id, settings)

    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    # 如果文件不存在，返回默认模板
    if not file_path.exists():
        logger.info("文风指南文件不存在，创建默认模板: %s", project_id)
        file_path.write_text(DEFAULT_STYLE_GUIDE, encoding="utf-8")
        return ApiResponse.ok(StyleGuideContent(
            content=DEFAULT_STYLE_GUIDE,
            last_modified=datetime.now().isoformat()
        ))

    # 读取文件
    content = file_path.read_text(encoding="utf-8")
    last_modified = datetime.fromtimestamp(
        file_path.stat().st_mtime
    ).isoformat()

    logger.debug("获取文风指南成功: %s", project_id)
    return ApiResponse.ok(StyleGuideContent(
        content=content,
        last_modified=last_modified
    ))


@router.post("/{project_id}", response_model=ApiResponse[None])
async def save_style_guide(
    project_id: str,
    req: SaveStyleGuideRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    """保存文风指南内容

    Args:
        project_id: 项目ID
        req: 保存请求，包含新的文风指南内容

    Returns:
        保存成功响应

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    file_path = _get_style_guide_path(project_id, settings)

    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    # 写入文件
    file_path.write_text(req.content, encoding="utf-8")

    logger.info("文风指南已保存: %s", project_id)
    return ApiResponse.ok(message="文风指南已保存")
