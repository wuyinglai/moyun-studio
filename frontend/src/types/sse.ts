/**
 * SSE 事件类型定义
 *
 * 所有事件都带 project_id，有任务上下文时带 task_id。
 * file.updated 不发送完整正文 content。
 * 前端收到 SSE 后按 project_id/task_id 过滤。
 */

export type TaskStatus = 'pending' | 'running' | 'done' | 'failed'

export interface BaseEvent {
  /** 事件唯一标识 */
  event_id?: string
  /** 事件类型 */
  type?: string
  /** 项目ID（所有事件都带） */
  project_id?: string
  /** 任务ID（有任务上下文时） */
  task_id?: string
  /** 运行ID */
  run_id?: string
  /** 事件来源模块 */
  source?: string
  /** 事件时间 */
  timestamp?: string
  /** 旧字段兼容 */
  taskId?: string
}

export interface GenerationEvent extends BaseEvent {
  delta?: string
  content?: string
  _targetFilePath?: string
}

export interface FileCreatedEvent extends BaseEvent {
  path: string
  name?: string
}

export interface FileUpdatedEvent extends BaseEvent {
  path: string
  content?: string
  size?: number
  mtime?: number
  /** 重命名时包含旧路径 */
  oldPath?: string
  newPath?: string
}

export interface FileRenamedEvent extends BaseEvent {
  oldPath: string
  newPath: string
}

export interface DirectoryCreatedEvent extends BaseEvent {
  path: string
  name?: string
}

export interface TaskEvent extends BaseEvent {
  status: TaskStatus
  name?: string
  progress?: number
}

export interface QueueEvent extends BaseEvent {
  queue: unknown[]
}

export interface LLMStatusEvent extends BaseEvent {
  connected: boolean
  model?: string
}

export interface ThinkingEvent extends BaseEvent {
  thinking?: boolean
  content?: string
}

export interface ErrorEvent extends BaseEvent {
  message: string
  code?: string
  warning?: boolean
}

export interface DoneEvent extends BaseEvent {
  message?: string
}

export interface DiffSummaryEvent extends BaseEvent {
  summary: string
  target_file: string
}

export interface StepDoneEvent extends BaseEvent {
  step_id: string
  label: string
  status: 'done' | 'fallback' | 'error'
}

export interface PromptEvent extends BaseEvent {
  prompt: string
  step_id?: string
}

/** 候选稿创建事件 */
export interface CandidateCreatedEvent extends BaseEvent {
  candidate_id: string
  source_path: string
  action: string
}

/** 候选稿采用事件 */
export interface CandidateAdoptedEvent extends BaseEvent {
  candidate_id: string
  source_path: string
}

/** 管线启动事件 */
export interface PipelineStartedEvent extends BaseEvent {
  pipeline: string
}

/** 管线步骤事件 */
export interface PipelineStepEvent extends BaseEvent {
  step_id: string
  label?: string
  error?: string
}

/** 记忆更新事件 */
export interface MemoryUpdatedEvent extends BaseEvent {}

export type SSEEventType =
  | 'generation'
  | 'file-created'
  | 'file-updated'
  | 'file-renamed'
  | 'file-deleted'
  | 'directory-created'
  | 'task'
  | 'queue'
  | 'llm-status'
  | 'thinking'
  | 'error'
  | 'done'
  | 'step_done'
  | 'prompt'
  | 'diff_summary'
  | 'connected'
  | 'candidate-created'
  | 'candidate-adopted'
  | 'pipeline-started'
  | 'pipeline-step-started'
  | 'pipeline-step-completed'
  | 'pipeline-step-failed'
  | 'task-waiting-for-user'
  | 'task-completed'
  | 'memory-updated'

export type SSEEventData =
  | GenerationEvent
  | FileCreatedEvent
  | FileUpdatedEvent
  | FileRenamedEvent
  | DirectoryCreatedEvent
  | TaskEvent
  | QueueEvent
  | LLMStatusEvent
  | ThinkingEvent
  | ErrorEvent
  | DoneEvent
  | DiffSummaryEvent
  | StepDoneEvent
  | PromptEvent
  | CandidateCreatedEvent
  | CandidateAdoptedEvent
  | PipelineStartedEvent
  | PipelineStepEvent
  | MemoryUpdatedEvent
