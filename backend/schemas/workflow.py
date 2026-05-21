"""墨韵 - 工作流数据模型"""

from pydantic import BaseModel, Field
from typing import Any


class WorkflowStepDef(BaseModel):
    """工作流步骤定义（来自 YAML）"""
    id: str
    label: str
    type: str = "pipeline"  # pipeline | loop | file | human_review | human_edit | human_choice | human_score | human_instruction
    pipeline: str | None = None
    input: str | None = None
    output: str | None = None
    output_mode: str = "overwrite"  # AI_GUARDRAIL_ALLOW: schema default
    action: str | None = None  # file step: mkdir | copy | delete
    path: str | None = None  # file step path
    count: str | None = None  # loop step: "{{ variables.xxx }}" or number
    var: str | None = None  # loop step: variable name (vol, ch, etc.)
    extra_vars: dict[str, str] = Field(default_factory=dict)
    steps: list["WorkflowStepDef"] = Field(default_factory=list)  # loop sub-steps
    output_key: str | None = None  # Human 节点: 输出变量名


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


class WorkflowResumeRequest(BaseModel):
    """恢复工作流请求"""
    action: str  # approve | edit_and_approve | regenerate | stop
    output: str = ""  # 用户编辑后的内容
    extra_vars: dict[str, str] = Field(default_factory=dict)  # 额外变量


class WorkflowRunState(BaseModel):
    """完整的工作流执行状态（用于持久化和恢复）"""
    run_id: str
    workflow: str
    project_id: str
    status: str = "running"  # running | waiting_for_user | done | failed | stopped
    current_node: str | None = None  # 当前等待的节点 ID
    current_step_path: str | None = None  # 当前步骤路径
    waiting_reason: str | None = None  # 等待原因
    available_actions: list[str] = Field(default_factory=list)  # 可用动作
    waiting_input: str | None = None  # 等待用户处理的输入内容
    variables: dict[str, str] = Field(default_factory=dict)
    loop_vars: dict[str, Any] = Field(default_factory=dict)
    step_outputs: dict[str, str] = Field(default_factory=dict)
    completed_paths: list[str] = Field(default_factory=list)
    # 用于恢复执行的状态
    remaining_steps: list[dict] = Field(default_factory=list)  # 剩余步骤（序列化后）
    updated_at: str = ""


class WorkflowRunStatus(BaseModel):
    """工作流执行状态（API 响应）"""
    run_id: str
    workflow: str
    project_id: str
    status: str = "running"  # running | waiting_for_user | done | failed | stopped
    current_node: str | None = None
    waiting_reason: str | None = None
    available_actions: list[str] = Field(default_factory=list)
    waiting_input: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)
    step_outputs: dict[str, str] = Field(default_factory=dict)
    updated_at: str = ""
