"""墨韵 - LLM 相关 Schemas"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LLMConfigRequest(BaseModel):
    api_type: Literal["openai", "anthropic", "ollama", "custom"] = "openai"
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
