"""墨韵 - 场景领域对象"""

from pydantic import BaseModel


class SceneInfo(BaseModel):
    """场景文件元信息"""

    project_id: str
    volume: int
    chapter: int
    scene: int
    path: str
    target_chars: int = 800
    status: str = "draft"
    mtime: float | None = None
    word_count: int = 0
