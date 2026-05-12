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


class ProjectInfo(BaseModel):
    project_id: str
    name: str
    genre: str = ""
    theme: str = ""
    tone: str = ""
    target_word_count: int = 0
    completion_rate: float = 0.0  # 0.0 ~ 1.0
    total_words: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectInfo]
    total: int


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
    """章节信息"""
    id: str
    name: str
    sections: int


class OutlineResponse(BaseModel):
    """大纲响应"""
    outline: str = Field(..., description="大纲内容（Markdown格式）")
    chapters: list[OutlineChapterInfo] = Field(default_factory=list, description="章节列表")


class ConfirmOutlineRequest(BaseModel):
    """确认大纲请求"""
    outline: str = Field(..., description="大纲内容（Markdown格式）")
