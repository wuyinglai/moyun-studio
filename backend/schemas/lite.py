"""墨韵 - 爽文模式 Schemas"""

from typing import Literal

from pydantic import BaseModel, Field

Genre = Literal["玄幻", "武侠", "言情", "都市", "仙侠"]


class LiteWritingPrefs(BaseModel):
    """爽文模式写作偏好"""

    style: str = Field(default="热血", description="文风")
    intensity: str = Field(default="标准", description="爽点强度")
    pace: str = Field(default="快节奏", description="节奏")
    protagonist: str = Field(default="张扬", description="主角性格")
    likes: str = Field(default="", description="喜欢的元素")
    dislikes: str = Field(default="", description="不要写的内容")
    genre_params: dict[str, str] = Field(default_factory=dict, description="题材专属参数")


class LiteIdeaCard(BaseModel):
    """开局方向卡"""

    id: str
    title: str
    genre: Genre
    one_liner: str
    protagonist_hook: str
    core_conflict: str
    selling_point: str


class LiteNextOptionCard(BaseModel):
    """下一章爽点卡"""

    id: str
    title: str
    beat: str
    scene: str
    protagonist_desire: str = ""
    obstacle: str = ""
    payoff: str
    hook: str
    advancement: str = ""


class LiteIdeasRequest(BaseModel):
    seed: str = Field(default="", description="换一批用的随机种子")


class LiteIdeasResponse(BaseModel):
    cards: list[LiteIdeaCard]


class LiteProjectCreateRequest(BaseModel):
    card: LiteIdeaCard
    prefs: LiteWritingPrefs = Field(default_factory=LiteWritingPrefs)


class LiteProjectCreateResponse(BaseModel):
    project_id: str
    first_file: str
    story_engine: str


class LiteNextOptionsRequest(BaseModel):
    project_id: str
    current_file: str | None = Field(default=None, description="当前章节文件")
    prefs: LiteWritingPrefs = Field(default_factory=LiteWritingPrefs)


class LiteNextOptionsResponse(BaseModel):
    cards: list[LiteNextOptionCard]
    current_file: str
    next_file: str


class LiteWriteNextRequest(BaseModel):
    project_id: str
    target_file: str | None = Field(default=None, description="目标章节文件")
    output_file: str | None = Field(default=None, description="可选输出文件，用于候选稿")
    selected_card: LiteNextOptionCard
    prefs: LiteWritingPrefs = Field(default_factory=LiteWritingPrefs)
    action: Literal["write", "rewrite", "more_exciting", "more_reasonable", "continue", "write_next_scene", "write_current_scene", "rewrite_current_scene", "polish_current_scene"] = "write"


class LiteWriteNextResponse(BaseModel):
    file_path: str
    content: str
    quality_summary: str
    story_engine_summary: dict[str, str]
    chapter_plan: str | None = Field(default=None, description="完成一章后生成的下一章规划，为空表示不到章末")
    candidate_id: str | None = Field(default=None, description="候选稿 ID，非候选稿时为 None")
    source_file: str | None = Field(default=None, description="候选稿对应的源文件路径，非候选稿时为 None")
    fallback_used: bool = Field(default=False, description="是否使用了 fallback 草稿")
    retry_used: bool = Field(default=False, description="是否触发了自动重试")
    retry_count: int = Field(default=0, description="实际重试次数")
    fallback_candidate_id: str | None = Field(default=None, description="fallback 候选稿 ID，未使用 fallback 时为 None")
    write_skipped: bool = Field(default=False, description="是否跳过了写正式文件，比如 fallback 只创建候选稿时")
    write_skip_reason: str | None = Field(default=None, description="跳过写正式文件的原因，比如 'fallback_candidate_requires_review' 或 'fallback_candidate_create_failed'")
    quality_flags: list[str] = Field(default_factory=list, description="低质量检测标记，如 ['too_short', 'template_leak']")
    quality_warning: str | None = Field(default=None, description="面向用户的质量警告")
    quality_score: int | None = Field(default=None, description="1-5 质量评分")
