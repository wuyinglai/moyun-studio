"""墨韵 - 管线执行上下文与节点结果"""

from pydantic import BaseModel, Field


class NodeResult(BaseModel):
    """节点执行结果"""

    output: str = Field(default="", description="节点输出文本")
    warnings: list[str] = Field(default_factory=list, description="警告列表")
    candidate_id: str | None = Field(None, description="候选稿ID（如有）")
    artifacts: list[dict] = Field(default_factory=list, description="附带产物")
    events: list[dict] = Field(default_factory=list, description="待发送的 SSE 事件")


class PipelineContext(BaseModel):
    """管线执行上下文（跨步骤共享）"""

    project_id: str = Field(..., description="项目ID")
    pipeline_name: str = Field(..., description="管线名称")
    target_file: str | None = Field(None, description="目标文件路径")
    task_id: str = Field("", description="任务ID")
    output_mode: str = Field("overwrite", description="输出模式：legacy overwrite/write_scene/candidate/append")  # AI_GUARDRAIL_ALLOW: default value, policy enforces safety
    user_input: str | None = Field(None, description="用户输入")
    step_outputs: dict[str, str] = Field(default_factory=dict, description="步骤输出映射")
    system_vars: dict = Field(default_factory=dict, description="系统变量")
    project_vars: dict = Field(default_factory=dict, description="项目变量")
    chapter_vars: dict = Field(default_factory=dict, description="章节变量")
    extra_vars: dict = Field(default_factory=dict, description="额外变量")

    model_config = {"arbitrary_types_allowed": True}
