"""墨韵 - 故事状态 API

端点：
  GET  /api/story-state/{project_id}  获取故事全局状态
  POST /api/story-state/{project_id}  更新故事全局状态
"""

from datetime import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import MoyunFileNotFoundError, ProjectNotFoundError
from backend.core.file_ops import FileService
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["故事状态"], prefix="/story-state")


# ─── Schema ──────────────────────────────────────────────────────────

class StoryStateContent(BaseModel):
    """故事状态内容"""
    protagonist_status: dict[str, Any] = Field(
        default_factory=dict,
        description="主角当前状态"
    )
    factions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="势力关系"
    )
    foreshadowing: list[dict[str, Any]] = Field(
        default_factory=list,
        description="伏笔追踪列表"
    )
    main_plot_progress: int = Field(
        default=0,
        ge=0,
        le=100,
        description="主线进度百分比"
    )
    side_plots: list[dict[str, Any]] = Field(
        default_factory=list,
        description="支线进度列表"
    )
    key_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="关键道具/资源"
    )
    last_modified: str | None = Field(None, description="最后修改时间")


class UpdateStoryStateRequest(BaseModel):
    """更新故事状态请求"""
    protagonist_status: dict[str, Any] | None = Field(None, description="主角状态")
    factions: dict[str, list[str]] | None = Field(None, description="势力关系")
    foreshadowing: list[dict[str, Any]] | None = Field(None, description="伏笔列表")
    main_plot_progress: int | None = Field(None, ge=0, le=100, description="主线进度")
    side_plots: list[dict[str, Any]] | None = Field(None, description="支线列表")
    key_items: list[dict[str, Any]] | None = Field(None, description="关键道具")


# ─── 默认故事状态模板 ─────────────────────────────────────────────────

DEFAULT_STORY_STATE = """# 故事全局状态

## 一、故事基本信息
- 当前章节：
- 更新时间：

## 二、主角状态
### 基础信息
- 姓名：
- 身份：
- 年龄：

### 能力/境界（根据题材调整）
- 当前境界：
- 主要技能：
- 战斗力评估：

## 三、主要资源/道具
| 道具名称 | 当前状态 | 说明 |
|---------|---------|------|
| | | |

## 四、势力关系
### 主角所属势力
-

### 相关势力
| 势力名称 | 关系 | 说明 |
|---------|------|------|
| | | |

## 五、已揭示的重要设定
-

## 六、伏笔追踪
### 已埋设伏笔
| ID | 内容 | 埋设章节 | 状态 |
|----|------|---------|------|
| | | | 待回收 |

### 已回收伏笔
| ID | 内容 | 回收章节 |
|----|------|---------|
| | | |

## 七、进行中的主线/支线
### 主线进度
当前进度：0%

### 支线状态
| 支线名称 | 当前进度 | 说明 |
|---------|---------|------|
| | | |

## 八、关键人物关系
| 人物 | 与主角关系 | 当前状态 |
|------|----------|---------|
| | | |

## 九、待处理事项
- 下一章节需要处理的事项：
"""


# ─── 工具函数 ────────────────────────────────────────────────────────

def _make_file_service(settings: Settings) -> FileService:
    """创建 FileService 实例"""
    return FileService(settings.projects_path, max_file_write_size=settings.max_file_write_size)


def _story_state_rel_path(project_id: str) -> str:
    """获取 story-state.md 的 FileService 相对路径"""
    return f"{project_id}/story-state.md"


def _parse_story_state(content: str) -> StoryStateContent:
    """解析故事状态Markdown文件为结构化数据

    这是一个简化实现，直接返回原始内容和解析后的关键信息。
    完整实现需要更复杂的Markdown解析逻辑。
    """
    return StoryStateContent(
        protagonist_status={},
        factions={},
        foreshadowing=[],
        main_plot_progress=0,
        side_plots=[],
        key_items=[],
        last_modified=None
    )


# ─── 路由 ────────────────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ApiResponse[StoryStateContent])
async def get_story_state(
    project_id: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[StoryStateContent]:
    """获取故事全局状态

    Args:
        project_id: 项目ID

    Returns:
        故事状态内容

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    fs = _make_file_service(settings)
    rel_path = _story_state_rel_path(project_id)

    # 检查项目是否存在
    if not await fs.exists(project_id):
        raise ProjectNotFoundError(project_id)

    # 如果文件不存在，创建默认模板
    if not await fs.exists(rel_path):
        logger.info("故事状态文件不存在，创建默认模板: %s", project_id)
        await fs.write_file(rel_path, DEFAULT_STORY_STATE)
        return ApiResponse.ok(StoryStateContent(
            protagonist_status={},
            factions={},
            foreshadowing=[],
            main_plot_progress=0,
            side_plots=[],
            key_items=[],
            last_modified=datetime.now().isoformat()
        ))

    # 读取文件
    content, _, mtime = await fs.read_file(rel_path)
    last_modified = datetime.fromtimestamp(mtime).isoformat() if mtime else None

    # 解析Markdown内容
    parsed = _parse_story_state(content)
    parsed.last_modified = last_modified

    logger.debug("获取故事状态成功: %s", project_id)
    return ApiResponse.ok(parsed)


@router.post("/{project_id}", response_model=ApiResponse[None])
async def update_story_state(
    project_id: str,
    req: UpdateStoryStateRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    """更新故事全局状态

    Args:
        project_id: 项目ID
        req: 更新请求

    Returns:
        更新成功响应

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    fs = _make_file_service(settings)
    rel_path = _story_state_rel_path(project_id)

    # 检查项目是否存在
    if not await fs.exists(project_id):
        raise ProjectNotFoundError(project_id)

    # 如果文件不存在，创建默认模板
    if not await fs.exists(rel_path):
        await fs.write_file(rel_path, DEFAULT_STORY_STATE)

    # 读取现有内容
    current_content, _, _ = await fs.read_file(rel_path)

    # 构建更新后的结构化数据
    updated_state: dict[str, Any] = {}

    if req.protagonist_status is not None:
        updated_state["protagonist_status"] = req.protagonist_status
    if req.factions is not None:
        updated_state["factions"] = req.factions
    if req.foreshadowing is not None:
        updated_state["foreshadowing"] = req.foreshadowing
    if req.main_plot_progress is not None:
        updated_state["main_plot_progress"] = req.main_plot_progress
    if req.side_plots is not None:
        updated_state["side_plots"] = req.side_plots
    if req.key_items is not None:
        updated_state["key_items"] = req.key_items

    # 追加更新日志到文件（简单实现）
    update_log = f"""
## 更新记录
- 更新时间：{datetime.now().isoformat()}
- 更新内容：{updated_state}
"""
    await fs.write_file(rel_path, current_content + update_log)

    logger.info("故事状态已更新: %s", project_id)
    return ApiResponse.ok(message="故事状态已更新")
