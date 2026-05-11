"""墨韵 - 近期上下文 API

端点：
  GET  /api/recent-context/{project_id}      获取近期上下文（最近5章摘要）
  POST /api/recent-context/{project_id}/append  追加新章节摘要
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.core.exceptions import ProjectNotFoundError
from backend.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["近期上下文"], prefix="/recent-context")

# 常量
MAX_RECENT_CHAPTERS = 5  # 保留最近章节数


# ─── Schema ──────────────────────────────────────────────────────────

class ChapterSummary(BaseModel):
    """章节摘要"""
    path: str = Field(..., description="章节路径")
    title: str = Field(..., description="章节标题")
    summary: str = Field(default="", description="章节摘要")
    word_count: int = Field(default=0, ge=0, description="字数")
    created_at: str = Field(..., description="创建时间")


class RecentContextContent(BaseModel):
    """近期上下文内容"""
    chapters: list[ChapterSummary] = Field(
        default_factory=list,
        description="最近章节摘要列表"
    )
    total_words: int = Field(default=0, ge=0, description="总字数")
    chapter_range: dict[str, str] = Field(
        default_factory=dict,
        description="章节范围"
    )


class AppendChapterRequest(BaseModel):
    """追加章节摘要请求"""
    chapter_path: str = Field(..., description="章节路径")
    title: str = Field(..., description="章节标题")
    summary: str = Field(default="", description="章节摘要")
    word_count: int = Field(default=0, ge=0, description="字数")


# ─── 默认近期上下文模板 ───────────────────────────────────────────────

DEFAULT_RECENT_CONTEXT = """# 近期上下文摘要

## 章节范围
- 起始章节：
- 结束章节：

## 摘要列表

（暂无章节摘要）

## 快速索引

### 人物状态速查
| 人物 | 章节 | 当前状态 |
|------|------|---------|
| | | |

### 伏笔状态速查
| 伏笔 | 埋设章节 | 状态 |
|------|---------|------|
| | | |

### 势力关系速查
| 势力 | 章节 | 关系变化 |
|------|------|---------|
| | | |
"""


# ─── 工具函数 ────────────────────────────────────────────────────────

def _get_recent_context_path(project_id: str, settings: Settings) -> Path:
    """获取近期上下文文件路径"""
    return settings.projects_path / project_id / "recent-context.md"


def _get_chapters_meta_path(project_id: str, settings: Settings) -> Path:
    """获取章节元数据存储路径"""
    return settings.projects_path / project_id / ".chapters-meta.json"


def _load_chapters_meta(project_id: str, settings: Settings) -> dict[str, Any]:
    """加载章节元数据"""
    meta_path = _get_chapters_meta_path(project_id, settings)
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {"chapters": [], "total_words": 0}


def _save_chapters_meta(project_id: str, settings: Settings, data: dict[str, Any]) -> None:
    """保存章节元数据"""
    meta_path = _get_chapters_meta_path(project_id, settings)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_recent_context_file(
    project_id: str,
    settings: Settings,
    chapters: list[ChapterSummary]
) -> None:
    """更新近期上下文Markdown文件"""
    file_path = _get_recent_context_path(project_id, settings)

    # 构建Markdown内容
    if not chapters:
        content = DEFAULT_RECENT_CONTEXT
    else:
        start_ch = chapters[0] if chapters else None
        end_ch = chapters[-1] if chapters else None

        chapters_md = []
        for ch in chapters:
            chapters_md.append(f"""### {ch.title}
- **路径**: `{ch.path}`
- **字数**: {ch.word_count}
- **摘要**: {ch.summary}
- **创建时间**: {ch.created_at}
""")

        total_words = sum(ch.word_count for ch in chapters)

        content = f"""# 近期上下文摘要

## 章节范围
- 起始章节：{start_ch.title if start_ch else '无'}
- 结束章节：{end_ch.title if end_ch else '无'}

## 摘要列表
{''.join(chapters_md)}

## 统计信息
- 总字数：{total_words}
- 章节数：{len(chapters)}
"""

    file_path.write_text(content, encoding="utf-8")


# ─── 路由 ────────────────────────────────────────────────────────────

@router.get("/{project_id}", response_model=ApiResponse[RecentContextContent])
async def get_recent_context(
    project_id: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[RecentContextContent]:
    """获取近期上下文（最近5章摘要）

    Args:
        project_id: 项目ID

    Returns:
        近期上下文内容

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    # 加载章节元数据
    meta = _load_chapters_meta(project_id, settings)
    chapters_data = meta.get("chapters", [])

    # 如果没有数据，返回默认结构
    if not chapters_data:
        return ApiResponse.ok(RecentContextContent(
            chapters=[],
            total_words=0,
            chapter_range={"start": "", "end": ""}
        ))

    # 转换为ChapterSummary列表
    chapters = [
        ChapterSummary(**ch) for ch in chapters_data
    ]

    # 计算总字数
    total_words = sum(ch.word_count for ch in chapters)

    # 章节范围
    chapter_range = {}
    if chapters:
        chapter_range = {
            "start": chapters[0].path,
            "end": chapters[-1].path
        }

    logger.debug("获取近期上下文成功: %s, 章节数: %d", project_id, len(chapters))
    return ApiResponse.ok(RecentContextContent(
        chapters=chapters,
        total_words=total_words,
        chapter_range=chapter_range
    ))


@router.post("/{project_id}/append", response_model=ApiResponse[None])
async def append_chapter_summary(
    project_id: str,
    req: AppendChapterRequest,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    """追加新章节摘要到近期上下文

    自动维护最近N章（默认5章）的摘要列表。

    Args:
        project_id: 项目ID
        req: 章节摘要信息

    Returns:
        追加成功响应

    Raises:
        ProjectNotFoundError: 项目不存在时抛出
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    # 加载现有章节元数据
    meta = _load_chapters_meta(project_id, settings)
    chapters_data = meta.get("chapters", [])

    # 创建新章节摘要
    new_chapter = ChapterSummary(
        path=req.chapter_path,
        title=req.title,
        summary=req.summary,
        word_count=req.word_count,
        created_at=datetime.now().isoformat()
    )

    # 添加到列表开头（最新章节在前）
    chapters_data.insert(0, new_chapter.model_dump())

    # 保持最大章节数
    if len(chapters_data) > MAX_RECENT_CHAPTERS:
        chapters_data = chapters_data[:MAX_RECENT_CHAPTERS]

    # 更新元数据
    meta["chapters"] = chapters_data
    meta["total_words"] = sum(ch.get("word_count", 0) for ch in chapters_data)
    meta["last_updated"] = datetime.now().isoformat()

    _save_chapters_meta(project_id, settings, meta)

    # 更新近期上下文Markdown文件
    chapters = [ChapterSummary(**ch) for ch in chapters_data]
    _update_recent_context_file(project_id, settings, chapters)

    logger.info(
        "章节摘要已追加: %s, 章节: %s, 当前摘要数: %d",
        project_id, req.chapter_path, len(chapters)
    )
    return ApiResponse.ok(message=f"章节摘要已追加，当前共 {len(chapters)} 章")


@router.delete("/{project_id}", response_model=ApiResponse[None])
async def clear_recent_context(
    project_id: str,
    settings: Settings = Depends(get_settings),
) -> ApiResponse[None]:
    """清空近期上下文

    Args:
        project_id: 项目ID

    Returns:
        清空成功响应
    """
    # 检查项目是否存在
    project_dir = settings.projects_path / project_id
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    # 清空章节元数据
    _save_chapters_meta(project_id, settings, {
        "chapters": [],
        "total_words": 0,
        "last_updated": datetime.now().isoformat()
    })

    # 更新Markdown文件
    _update_recent_context_file(project_id, settings, [])

    logger.info("近期上下文已清空: %s", project_id)
    return ApiResponse.ok(message="近期上下文已清空")
