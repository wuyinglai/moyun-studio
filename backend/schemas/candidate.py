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
from typing import Optional
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


class CandidateStatus(str, Enum):
    """候选稿状态"""
    PENDING = "pending"           # 待处理
    ADOPTED = "adopted"           # 已采用
    DISCARDED = "discarded"       # 已放弃


class CandidateInfo(BaseModel):
    """候选稿信息"""
    id: str = Field(..., description="候选稿唯一标识")
    source_path: str = Field(..., description="源文件路径")
    candidate_path: str = Field(..., description="候选稿文件路径")
    action: CandidateAction = Field(..., description="动作类型")
    status: CandidateStatus = Field(default=CandidateStatus.PENDING, description="状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    adopted_at: Optional[datetime] = Field(None, description="采用时间")
    word_count: int = Field(default=0, description="字数")
    summary: Optional[str] = Field(None, description="摘要")
    workflow_run_id: Optional[str] = Field(None, description="关联的工作流运行ID")
    
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
    workflow_run_id: Optional[str] = Field(None, description="关联的工作流运行ID")


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
    file_path: str = Field(..., description="被更新的文件路径")


class DeleteCandidateResponse(BaseModel):
    """删除候选稿响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
