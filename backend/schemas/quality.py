"""墨韵 - 质量审查 Schema"""

from typing import Any

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    """审查问题"""
    severity: str = Field(..., description="严重程度: critical/major/minor")
    category: str = Field(..., description="问题类别")
    location: str = Field(default="", description="问题所在位置")
    description: str = Field(..., description="问题描述")


class QualityScores(BaseModel):
    """质量评分"""
    coherence: int = Field(default=0, ge=0, le=10, description="连贯性")
    character_consistency: int = Field(default=0, ge=0, le=10, description="角色一致性")
    setting_consistency: int = Field(default=0, ge=0, le=10, description="设定一致性")
    writing_quality: int = Field(default=0, ge=0, le=10, description="写作质量")
    logic: int = Field(default=0, ge=0, le=10, description="逻辑合理性")
    style_compliance: int = Field(default=0, ge=0, le=10, description="文风符合度")


class QualityReviewResult(BaseModel):
    """质量审查结果"""
    scores: QualityScores = Field(default_factory=QualityScores)
    summary: str = Field(default="", description="总体评价")
    strengths: list[str] = Field(default_factory=list, description="优点列表")
    issues: list[ReviewIssue] = Field(default_factory=list, description="问题列表")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class ReviewRequest(BaseModel):
    """审查请求"""
    project_id: str = Field(..., description="项目ID")
    target_file: str = Field(..., description="目标章节文件路径")
    chapter_title: str | None = Field(None, description="章节标题（可选）")


class BatchReviewRequest(BaseModel):
    """批量审查请求"""
    project_id: str = Field(..., description="项目ID")
    target_files: list[str] = Field(..., min_length=1, max_length=20, description="目标文件列表")


class ReviewItem(BaseModel):
    """单个审查结果项"""
    target_file: str = Field(..., description="文件路径")
    status: str = Field(default="success", description="状态: success/error")
    result: QualityReviewResult | None = Field(None, description="审查结果")
    error: str | None = Field(None, description="错误信息")


class BatchReviewResponse(BaseModel):
    """批量审查响应"""
    reviews: list[ReviewItem] = Field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    failed: int = 0
