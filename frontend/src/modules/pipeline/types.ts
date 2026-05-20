/** 管线模块 - 类型定义 */

export interface PipelineStepDef {
  id: string
  label: string
  prompt: string
  fallback?: string
  output?: string
  confirm?: boolean
}

export interface PipelineDef {
  name: string
  label: string
  steps: PipelineStepDef[]
}

export interface PipelineRunRequest {
  project_id: string
  pipeline: string
  target_file?: string
  user_input?: string
  output_mode?: string
  extra_vars?: Record<string, string>
}

export interface StepDetail {
  id: string
  label: string
  prompt_content: string
  fallback?: string
  confirm?: boolean
}

export interface PipelineDetail {
  name: string
  label: string
  source: string
  steps: StepDetail[]
}
