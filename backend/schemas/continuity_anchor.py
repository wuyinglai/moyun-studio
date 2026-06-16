"""Continuity anchor schemas."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ContinuityAnchorType(str, Enum):
    CHARACTER_STATE = "character_state"
    PLOT_CLUE = "plot_clue"
    OBJECT_LOCATION = "object_location"
    RELATIONSHIP = "relationship"
    WORLD_RULE = "world_rule"


class ContinuityAnchorScope(str, Enum):
    GLOBAL = "global"
    CHAPTER = "chapter"
    SCENE = "scene"
    CHARACTER = "character"


class ContinuityAnchorStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ContinuityAnchorPriority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class ContinuityAnchorSource(str, Enum):
    USER = "user"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContinuityAnchor(BaseModel):
    id: str = Field(..., min_length=1)
    type: ContinuityAnchorType = ContinuityAnchorType.CHARACTER_STATE
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    scope: ContinuityAnchorScope = ContinuityAnchorScope.GLOBAL
    status: ContinuityAnchorStatus = ContinuityAnchorStatus.ACTIVE
    priority: ContinuityAnchorPriority = ContinuityAnchorPriority.NORMAL
    source: ContinuityAnchorSource = ContinuityAnchorSource.USER
    updated_at: str = Field(default_factory=_now_utc)


class ContinuityAnchorsDocument(BaseModel):
    version: int = 1
    anchors: list[ContinuityAnchor] = Field(default_factory=list)


class ContinuityAnchorMetadata(BaseModel):
    enabled: bool = False
    used_count: int = 0
    anchor_ids: list[str] = Field(default_factory=list)
    types: dict[str, int] = Field(default_factory=dict)
