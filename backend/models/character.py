"""墨韵 - 角色模型"""

from datetime import datetime
from pydantic import BaseModel


class CharacterProfile(BaseModel):
    """角色档案"""
    character_id: str
    name: str
    role: str = "supporting"
    age: str | None = None
    appearance: str = ""
    personality: str = ""
    background: str = ""
    abilities: list[str] = []
    relationships: dict[str, str] = {}
    status: str = "active"
    created_at: datetime
    updated_at: datetime
