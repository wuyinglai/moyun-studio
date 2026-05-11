"""墨韵 - 素材模型"""

from datetime import datetime
from pydantic import BaseModel


class PlotItem(BaseModel):
    """情节项"""
    plot_id: str
    title: str
    description: str
    chapter_range: tuple[int, int] | None = None
    characters: list[str] = []
    importance: str = "normal"
    status: str = "active"


class SceneItem(BaseModel):
    """场景项"""
    scene_id: str
    location: str
    time: str
    participants: list[str] = []
    atmosphere: str = ""
    key_events: list[str] = []


class ChapterSummary(BaseModel):
    """章节摘要"""
    summary_id: str
    chapter_id: str
    summary: str
    word_count: int = 0
    key_events: list[str] = []
    characters_appeared: list[str] = []
    foreshadowing: list[str] = []
    created_at: datetime
