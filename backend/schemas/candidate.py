"""墨韵 - 候选稿数据模型

候选稿是 AI 生成的内容，尚未覆盖正式文件。用户可以：
- 预览候选稿
- 采用候选稿（覆盖原文件）
- 放弃候选稿（删除）

候选稿存储在项目目录的 `.candidates/` 子目录下。
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any

from pydantic import BaseModel, Field


class CandidateAction(str, Enum):
    """候选稿动作类型"""
    REWRITE = "rewrite"           # 重写
    CONTINUE = "continue"         # 续写
    MODIFY = "modify"             # 修改
    CHAT = "chat"                 # 聊天改稿
    EXPAND = "expand"             # 扩写
    SHRINK = "shrink"             # 缩写
    POLISH = "polish"             # 润色
    FALLBACK_DRAFT = "fallback_draft"  # 应急草稿（LLM 失败后 fallback 生成）
    FEEDBACK_REVISION = "feedback_revision"  # 用户反馈再生成候选稿


class CandidateStatus(str, Enum):
    """候选稿状态"""
    PENDING = "pending"           # 待处理
    ADOPTED = "adopted"           # 已采用
    REJECTED = "rejected"         # 已拒绝（含冲突）
    DISCARDED = "discarded"       # 已放弃


class CandidateInfo(BaseModel):
    """候选稿信息"""
    id: str = Field(..., description="候选稿唯一标识")
    project_id: str = Field("", description="项目ID")
    source_path: str = Field(..., description="源文件路径（项目内相对路径，不带 project_id）")
    candidate_path: str = Field(..., description="候选稿文件路径")
    action: CandidateAction = Field(..., description="动作类型")
    base_hash: str = Field("", description="创建时源文件内容哈希")
    base_mtime: float | None = Field(None, description="创建时源文件修改时间")
    status: CandidateStatus = Field(default=CandidateStatus.PENDING, description="状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    adopted_at: datetime | None = Field(None, description="采用时间")
    word_count: int = Field(default=0, description="字数")
    summary: str | None = Field(None, description="摘要")
    workflow_run_id: str | None = Field(None, description="关联的工作流运行ID")
    model: str | None = Field(None, description="生成模型")
    pipeline_id: str | None = Field(None, description="管线ID")
    prompt_version: str | None = Field(None, description="Prompt 版本（可选）")
    source_mode: str | None = Field(None, description="来源模式: lite 或 professional")

    # 连续性检查信息 — 来自 pipeline continuity gate
    continuity: Dict[str, Any] = Field(default_factory=dict, description="连续性检查结果（has_warning/severity/message 等）")
    source_type: str | None = Field(None, description="来源类型: llm 或 dry-run")
    warning_message: str | None = Field(None, description="面向用户的简短警告摘要，例如'可能与前文设定不一致'")

    # Scene Plan provenance 字段
    generation_context: Dict[str, Any] = Field(default_factory=dict, description="生成上下文，包含 scene_plan_used 等信息")
    scene_plan_hash: str = Field("", description="生成时使用的 Scene Plan 哈希")
    scene_plan_path: str = Field("", description="生成时使用的 Scene Plan 文件路径（项目内相对路径）")
    beat_validation: Dict[str, Any] = Field(default_factory=dict, description="Required beat validation metadata")
    parent_candidate_id: str | None = Field(None, description="Parent candidate id for feedback revision candidates")
    revision_group_id: str | None = Field(None, description="Revision lineage group id")
    revision_index: int = Field(0, description="Revision index within a lineage group")

    @property
    def filename(self) -> str:
        """获取候选稿文件名"""
        return Path(self.candidate_path).name

    @property
    def source_filename(self) -> str:
        """获取源文件名"""
        return Path(self.source_path).name


class CreateCandidateRequest(BaseModel):
    """创建候选稿请求"""
    project_id: str = Field(..., description="项目ID")
    source_path: str = Field(..., description="源文件路径")
    action: CandidateAction = Field(..., description="动作类型")
    content: str = Field(..., description="候选稿内容")
    workflow_run_id: str | None = Field(None, description="关联的工作流运行ID")
    model: str | None = Field(None, description="生成模型")
    pipeline_id: str | None = Field(None, description="管线ID")
    prompt_version: str | None = Field(None, description="Prompt 版本")
    source_mode: str | None = Field(None, description="来源模式: lite 或 professional")

    # 连续性检查信息
    continuity: Dict[str, Any] = Field(default_factory=dict, description="连续性检查结果")
    source_type: str | None = Field(None, description="来源类型: llm 或 dry-run")
    warning_message: str | None = Field(None, description="面向用户的简短警告摘要")

    # Scene Plan provenance 字段
    generation_context: Dict[str, Any] = Field(default_factory=dict, description="生成上下文")
    scene_plan_hash: str = Field("", description="Scene Plan 哈希")
    scene_plan_path: str = Field("", description="Scene Plan 文件路径")
    beat_validation: Dict[str, Any] = Field(default_factory=dict, description="Required beat validation metadata")
    parent_candidate_id: str | None = Field(None, description="Parent candidate id")
    revision_group_id: str | None = Field(None, description="Revision lineage group id")
    revision_index: int = Field(0, description="Revision index")


class CandidateRevisionRequest(BaseModel):
    """Create a child revision candidate from user feedback."""
    feedback_text: str = Field("", description="User feedback for revision")
    quick_actions: list[str] = Field(default_factory=list, description="Quick feedback action labels")
    repair_scope: str = Field("full_candidate", description="full_candidate | keep_opening | ending_only")
    inherit_required_beats: bool = Field(True, description="Inherit required beats from parent candidate")
    inherit_forbidden_beats: bool = Field(True, description="Inherit forbidden beats from parent candidate")
    run_beat_validation: bool = Field(True, description="Run beat validator for child candidate when beats exist")


class AdoptCandidateRequest(BaseModel):
    """采用候选稿请求"""
    project_id: str = Field(..., description="项目ID")
    candidate_id: str = Field(..., description="候选稿ID")


class DeleteCandidateRequest(BaseModel):
    """删除候选稿请求"""
    project_id: str = Field(..., description="项目ID")
    candidate_id: str = Field(..., description="候选稿ID")


class CandidateListResponse(BaseModel):
    """候选稿列表响应"""
    candidates: list[CandidateInfo] = Field(..., description="候选稿列表")


class CandidateDetailResponse(BaseModel):
    """候选稿详情响应"""
    candidate: CandidateInfo = Field(..., description="候选稿信息")
    content: str = Field(..., description="候选稿内容")


class AdoptCandidateResponse(BaseModel):
    """采用候选稿响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    file_path: str = Field("", description="被更新的文件路径")
    conflict: bool = Field(False, description="是否因源文件已变化而冲突")


class DeleteCandidateResponse(BaseModel):
    """删除候选稿响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
