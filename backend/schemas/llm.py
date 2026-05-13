"""墨韵 - LLM 相关 Schemas"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LLMConfigRequest(BaseModel):
    api_type: Literal["openai", "anthropic", "ollama", "deepseek", "custom"] = "openai"
    api_url: str = ""
    api_key: str = ""
    model: str = ""
    thinking: bool = False


class LLMConfigResponse(BaseModel):
    api_type: str
    api_url: str
    model: str
    thinking: bool
    # 不返回 api_key


class LLMStatusResponse(BaseModel):
    connected: bool
    model: str
    message: str


class ModelInfo(BaseModel):
    id: str
    name: str


class LLMModelsResponse(BaseModel):
    models: list[ModelInfo]


class GenerateRequest(BaseModel):
    project_id: str
    file_path: str
    prompt_type: str = Field(..., description="Prompt 类型，如 generate/chapter")
    extra_vars: dict = Field(default_factory=dict, description="额外模板变量")
    mode: Literal["rewrite", "append", "chat"] = "rewrite"
    stream: bool = True


class ChatRequest(BaseModel):
    project_id: str
    message: str
    context_file: str | None = None


class BatchGenerateItem(BaseModel):
    """批量生成中的单个任务"""
    target_file: str
    status: str = "pending"  # pending | success | error
    word_count: int = 0
    error: str | None = None
    prompt: str = ""  # 渲染后的 prompt 文本（用于前端右侧面板展示）


class BatchGenerateResponse(BaseModel):
    """批量生成响应"""
    tasks: list[BatchGenerateItem]
    total: int
    succeeded: int
    failed: int


class BatchGenerateRequest(BaseModel):
    """批量生成请求"""
    project_id: str
    volume_number: int | None = Field(default=None, description="卷号，不指定则全部卷")
    chapter_number: int | None = Field(default=None, description="章号，不指定则全部章")
    section_numbers: list[int] | None = Field(default=None, description="节号列表，不指定则全部节")
    prompt_type: str = Field(default="generate/chapter", description="Prompt 模板类型")
    temperature: float = Field(default=0.7, ge=0, le=2, description="生成温度")
