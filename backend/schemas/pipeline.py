"""墨韵 - 管线引擎数据模型"""

from pydantic import BaseModel, Field


class PipelineStepDef(BaseModel):
    """管线步骤定义（来自 YAML）"""
    id: str
    label: str
    prompt: str  # prompt 模板路径，如 pipeline/polish/depai
    fallback: str | None = None  # 失败时回退到哪步的输出变量名
    output: str | None = None  # 可选：步骤完成后将输出写入此文件（相对于 project_id）
    confirm: bool = True  # 是否需要用户确认后才继续下一步


class PipelineDef(BaseModel):
    """管线定义（来自 YAML）"""
    name: str
    label: str
    steps: list[PipelineStepDef]


class PipelineRunRequest(BaseModel):
    """运行管线请求"""
    pipeline: str
    project_id: str
    target_file: str | None = None
    user_input: str | None = None
    output_mode: str = "overwrite"  # legacy overwrite | write_scene | candidate | append | dimension_file
    extra_vars: dict = Field(default_factory=dict)


class StepStatus(BaseModel):
    """步骤执行状态"""
    step_id: str
    label: str
    status: str  # running | done | skipped | failed
    output_summary: str = ""


class PipelineStatus(BaseModel):
    """管线执行状态"""
    pipeline: str
    current_step: int = 0
    total_steps: int = 0
    steps: list[StepStatus] = Field(default_factory=list)


class PipelineInfo(BaseModel):
    """管线列表项"""
    name: str
    label: str
    steps: list[dict]  # [{id, label}, ...]
    source: str = "system"  # system | custom


class StepDetail(BaseModel):
    """步骤详情（含 prompt 内容）"""
    id: str
    label: str
    prompt_content: str
    fallback: str | None = None
    confirm: bool = True


class PipelineDetail(BaseModel):
    """管线详情"""
    name: str
    label: str
    source: str
    steps: list[StepDetail]


class PipelineSaveRequest(BaseModel):
    """保存管线"""
    name: str = ""
    label: str | None = None
    steps: list[dict] | None = None  # [{id, label, prompt_content, fallback}]


class CreatePipelineRequest(BaseModel):
    """创建自定义管线"""
    name: str
    label: str
    steps: list[dict]  # [{id, label, prompt_content}]


class PipelineListResponse(BaseModel):
    pipelines: list[PipelineInfo]
    total: int


class PipelineDetailResponse(BaseModel):
    pipeline: PipelineDetail
