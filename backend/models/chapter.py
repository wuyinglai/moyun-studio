"""墨韵 - 章节模型"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChapterMeta(BaseModel):
    """章节元数据"""
    chapter_id: str
    chapter_title: str = ""
    chapter_index: int = 0
    volume_name: str = ""
    goal: str = ""
    memory: str = ""
    pending_foreshadowing: list[str] = []
    active_quests: list[str] = []
    status: str = "draft"
    version: str = "1.0"
    word_count: int = 0
    created_at: datetime
    last_modified: datetime


class VolumeMeta(BaseModel):
    """卷元数据"""
    volume_id: str
    volume_name: str
    chapter_count: int = 0
    start_chapter: int = 0
    end_chapter: int = 0
