"""墨韵 - 项目相关 Schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    genre: str = Field(default="", description="题材")
    theme: str = Field(default="", description="主题")
    tone: str = Field(default="", description="基调")
    background: str = Field(default="", description="故事背景")
    writing_style: str = Field(default="", description="写作风格")
    target_word_count: int = Field(default=100000, ge=10000, description="目标字数")
    author: str = Field(default="", description="作者名")
    # 场景级配置（sec = 单场景）
    scene_target_chars: int = Field(default=800, description="单场景目标字数")
    scenes_per_chapter: int = Field(default=5, description="每章节场景数")
    chapters_per_volume: int = Field(default=12, description="每卷章节数")


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="项目名称")
    genre: Optional[str] = Field(default=None, description="题材")
    theme: Optional[str] = Field(default=None, description="主题")
    tone: Optional[str] = Field(default=None, description="基调")
    background: Optional[str] = Field(default=None, description="故事背景")
    writing_style: Optional[str] = Field(default=None, description="写作风格")
    target_word_count: Optional[int] = Field(default=None, ge=10000, description="目标字数")
    author: Optional[str] = Field(default=None, description="作者名")
    # 场景级配置
    scene_target_chars: Optional[int] = Field(default=None, description="单场景目标字数")
    scenes_per_chapter: Optional[int] = Field(default=None, description="每章节场景数")
    chapters_per_volume: Optional[int] = Field(default=None, description="每卷章节数")


class ProjectInfo(BaseModel):
    project_id: str
    name: str
    author: str = ""
    genre: str = ""
    theme: str = ""
    tone: str = ""
    background: str = ""
    writing_style: str = ""
    target_word_count: int = 0
    completion_rate: float = 0.0  # 0.0 ~ 1.0
    total_words: int = 0
    created_at: datetime
    updated_at: datetime
    # 场景级配置（sec = 单场景）
    scene_target_chars: int = 800
    scenes_per_chapter: int = 5
    chapters_per_volume: int = 12
    unit_label: str = "scene"


class ProjectListResponse(BaseModel):
    projects: list[ProjectInfo]
    total: int


class ProjectStatsResponse(BaseModel):
    """项目统计信息"""
    total_sections: int = 0
    completed_sections: int = 0
    total_words: int = 0
    chapter_count: int = 0
    volume_count: int = 0
    completion_rate: float = 0.0


# ─── Wizard 流程 Schemas ──────────────────────────────────────────

class BookIdeaRequest(BaseModel):
    """生成书名和创意的请求"""
    genre: str = Field(..., description="题材")
    tone: str = Field(default="", description="基调")
    background: str = Field(default="", description="故事背景")
    theme: str = Field(default="", description="主题")
    writing_style: str = Field(default="", description="写作风格")
    author: str = Field(default="", description="作者名")
    target_word_count: int = Field(default=50000, description="目标字数")


class BookIdeaResponse(BaseModel):
    """书名和创意响应"""
    name: str = Field(..., description="生成的书名")
    description: str = Field(..., description="创意描述")


class GenerateOutlineRequest(BaseModel):
    """生成大纲的请求"""
    genre: str = Field(..., description="题材")
    tone: str = Field(default="", description="基调")
    background: str = Field(default="", description="故事背景")
    theme: str = Field(default="", description="主题")
    writing_style: str = Field(default="", description="写作风格")
    author: str = Field(default="", description="作者名")
    target_word_count: int = Field(default=50000, description="目标字数")
    book_name: str = Field(default="", description="书名")
    book_description: str = Field(default="", description="创意描述")


class OutlineChapterInfo(BaseModel):
    """章节信息（场景级：每个章节包含多个场景）"""
    id: str
    name: str
    sections: int = 5  # 默认每章节5个场景
    scenes: int = 5   # 场景数量，与 sections 含义相同


class OutlineResponse(BaseModel):
    """大纲响应"""
    outline: str = Field(..., description="大纲内容（Markdown格式）")
    chapters: list[OutlineChapterInfo] = Field(default_factory=list, description="章节列表")


class ConfirmOutlineRequest(BaseModel):
    """确认大纲请求"""
    outline: str = Field(..., description="大纲内容（Markdown格式）")
