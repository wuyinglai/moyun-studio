"""墨韵 - 工作流数据模型"""

from pydantic import BaseModel, Field


class WorkflowStepDef(BaseModel):
    """工作流步骤定义（来自 YAML）"""
    id: str
    label: str
    type: str = "pipeline"  # pipeline | loop | file
    pipeline: str | None = None
    input: str | None = None
    output: str | None = None
    output_mode: str = "overwrite"
    action: str | None = None  # file step: mkdir | copy | delete
    path: str | None = None  # file step path
    count: str | None = None  # loop step: "{{ variables.xxx }}" or number
    var: str | None = None  # loop step: variable name (vol, ch, etc.)
    extra_vars: dict[str, str] = Field(default_factory=dict)
    steps: list["WorkflowStepDef"] = Field(default_factory=list)  # loop sub-steps


class WorkflowDef(BaseModel):
    """工作流定义（来自 YAML）"""
    name: str
    label: str
    description: str = ""
    variables: dict[str, str] = Field(default_factory=dict)
    steps: list[WorkflowStepDef] = []


class WorkflowRunRequest(BaseModel):
    """运行工作流请求"""
    workflow: str
    project_id: str
    variables: dict[str, str] = Field(default_factory=dict)


class WorkflowSaveRequest(BaseModel):
    """保存工作流请求"""
    name: str
    label: str
    description: str = ""
    variables: dict[str, str] = Field(default_factory=dict)
    steps: list[WorkflowStepDef] = []


class StepStatus(BaseModel):
    """步骤执行状态"""
    step_id: str
    label: str
    type: str
    status: str = "pending"  # pending | running | done | failed | skipped
    path: list[str] = Field(default_factory=list)
    current: int = 0
    total: int = 0


class WorkflowRunStatus(BaseModel):
    """工作流执行状态"""
    run_id: str
    workflow: str
    project_id: str
    status: str = "running"  # running | paused | done | failed | stopped
    steps: list[StepStatus] = Field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    started_at: str = ""
    updated_at: str = ""
