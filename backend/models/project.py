"""墨韵 - 项目模型"""

from datetime import datetime
from pydantic import BaseModel


class ProjectMeta(BaseModel):
    """项目元数据"""
    project_id: str
    name: str
    genre: str = ""
    theme: str = ""
    tone: str = ""
    target_word_count: int = 0
    pov: str = "第三人称"
    created_at: datetime
    updated_at: datetime


class ContextStats(BaseModel):
    """上下文统计"""
    total_words: int = 0
    total_chapters: int = 0
    total_sections: int = 0
    last_updated: datetime
