"""墨韵 - Pipeline YAML 配置校验模型

用于启动时校验 prompts/pipeline/*.yaml 的结构正确性，
在用户运行 pipeline 之前就发现配置错误。
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ─── 允许的 output_mode 值 ──────────────────────────────────────
ALLOWED_OUTPUT_MODES = {
    "write_scene",
    "candidate",
    "append",
    "overwrite",
    "rewrite",
    "dimension_file",
    "none",
}

# output_mode 中需要给出 warning 的旧值（兼容但不推荐）
# LEGACY_COMPAT: overwrite/rewrite are accepted for old callers but normalized to safe modes.
DEPRECATED_OUTPUT_MODES = {"overwrite", "rewrite"}

# 危险 output 目标路径模式（需要候选稿保护）
DANGEROUS_OUTPUT_PATTERNS = (
    "chapters/",
    "story-state.md",
    "recent-context.md",
    "style-guide.md",
    "outline.md",
    "meta.json",
    "ch-meta.json",
)


class PipelineStepConfig(BaseModel):
    """管线步骤配置（校验用）

    字段与现有 PipelineStepDef 对齐，额外支持可选的
    type / output_mode / depends_on 字段以便未来扩展。
    """

    id: str = Field(..., description="步骤唯一标识")
    label: str = Field(..., description="步骤显示名称")
    prompt: str = Field(..., description="Prompt 模板路径（不含 .md 后缀）")
    fallback: str | None = Field(None, description="失败时回退到的步骤 ID")
    output: str | None = Field(None, description="步骤输出写入的文件路径")
    confirm: bool = Field(True, description="是否需要用户确认")
    # 扩展字段（当前 YAML 未使用，但校验时需要识别）
    type: str | None = Field(None, description="步骤类型（预留）")
    output_mode: str | None = Field(None, description="输出模式（预留）")
    depends_on: list[str] | None = Field(None, description="依赖步骤 ID 列表（预留）")

    model_config = {"extra": "forbid"}


class PipelineConfig(BaseModel):
    """管线配置（校验用）"""

    name: str = Field(..., description="管线名称")
    label: str = Field(..., description="管线显示名称")
    steps: list[PipelineStepConfig] = Field(..., description="步骤列表")

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _check_steps_not_empty(self) -> "PipelineConfig":
        if not self.steps:
            raise ValueError("steps 不能为空列表")
        return self


class PipelineValidationError(BaseModel):
    """单条校验错误"""

    step_id: str | None = None
    field: str | None = None
    message: str


class PipelineValidationWarning(BaseModel):
    """单条校验警告"""

    step_id: str | None = None
    field: str | None = None
    message: str


class PipelineValidationResult(BaseModel):
    """管线校验结果"""

    file: str = Field(..., description="YAML 文件名")
    valid: bool = Field(True, description="是否通过校验")
    errors: list[PipelineValidationError] = Field(default_factory=list)
    warnings: list[PipelineValidationWarning] = Field(default_factory=list)
