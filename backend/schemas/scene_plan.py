"""墨韵 - Scene Plan 数据模型

Scene Plan 是场景规划的结构化中间表示，用于：
- 表达场景目标、人物、冲突、节拍等核心要素
- 与 Story State / Materials 建立关联
- 定义 candidate 策略和输出意图
- 作为 LLM 生成前的结构化输入
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OutputIntent(str, Enum):
    """输出意图类型"""
    DRAFT = "draft"           # 草稿
    POLISH = "polish"         # 润色
    REWRITE = "rewrite"       # 重写
    CONTINUE = "continue"     # 续写
    ANALYZE = "analyze"       # 分析


class CreatedBy(str, Enum):
    """创建者类型"""
    DRYRUN = "dryrun"         # 干运行测试
    MOCK = "mock"             # Mock 数据
    LLM = "llm"               # LLM 生成
    HUMAN = "human"           # 人工编辑


class ScenePlanReferences(BaseModel):
    """Scene Plan 引用信息"""
    story_state_keys: list[str] = Field(
        default_factory=list,
        description="关联的 Story State key 列表"
    )
    material_paths: list[str] = Field(
        default_factory=list,
        description="关联的 Material 路径列表（项目内相对路径）"
    )
    recent_context_paths: list[str] = Field(
        default_factory=list,
        description="关联的 Recent Context 路径列表"
    )


class ScenePlanCandidatePolicy(BaseModel):
    """Scene Plan candidate 策略"""
    require_candidate: bool = Field(
        default=True,
        description="是否要求生成 candidate（必须为 true）"
    )
    allow_direct_write: bool = Field(
        default=False,
        description="是否允许直接写入正式文件（必须为 false）"
    )


class ScenePlanMetadata(BaseModel):
    """Scene Plan 元数据"""
    created_by: CreatedBy = Field(
        default=CreatedBy.DRYRUN,
        description="创建者类型"
    )
    version: str = Field(
        default="1.0.0",
        description="Schema 版本"
    )


class ScenePlan(BaseModel):
    """Scene Plan 主结构"""
    project_id: str = Field(..., description="项目 ID")
    source_path: str = Field(..., description="源场景路径（项目内相对路径）")
    scene_id: Optional[str] = Field(None, description="场景 ID（可选）")
    title: str = Field(..., description="场景标题")
    goal: str = Field(..., description="场景目标")
    pov_character: Optional[str] = Field(None, description="视角人物")
    characters: list[str] = Field(
        default_factory=list,
        description="出场人物列表"
    )
    location: Optional[str] = Field(None, description="地点")
    time_hint: Optional[str] = Field(None, description="时间提示")
    conflict: str = Field(..., description="场景冲突")
    emotional_shift: Optional[str] = Field(None, description="情绪变化")
    required_beats: list[str] = Field(..., description="必须包含的情节节拍（至少 1 条）")
    constraints: list[str] = Field(
        default_factory=list,
        description="约束条件列表"
    )
    references: ScenePlanReferences = Field(
        default_factory=ScenePlanReferences,
        description="引用信息"
    )
    output_intent: OutputIntent = Field(..., description="输出意图")
    candidate_policy: ScenePlanCandidatePolicy = Field(
        default_factory=ScenePlanCandidatePolicy,
        description="Candidate 策略"
    )
    metadata: ScenePlanMetadata = Field(
        default_factory=ScenePlanMetadata,
        description="元数据"
    )
