/**
 * SSE 事件类型定义
 */

export type TaskStatus = 'pending' | 'running' | 'done' | 'failed'

export interface BaseEvent {
  taskId?: string
}

export interface GenerationEvent extends BaseEvent {
  delta?: string
  content?: string
  _targetFilePath?: string
}

export interface FileCreatedEvent {
  path: string
  name?: string
}

export interface FileUpdatedEvent {
  path: string
  content?: string
}

export interface FileRenamedEvent {
  oldPath: string
  newPath: string
}

export interface DirectoryCreatedEvent {
  path: string
  name?: string
}

export interface TaskEvent extends BaseEvent {
  status: TaskStatus
  name?: string
  progress?: number
}

export interface QueueEvent {
  queue: unknown[]
}

export interface LLMStatusEvent {
  connected: boolean
  model?: string
}

export interface ThinkingEvent {
  thinking?: boolean
  content?: string
}

export interface ErrorEvent {
  message: string
  code?: string
  warning?: boolean
}

export interface DoneEvent extends BaseEvent {
  message?: string
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

export type SSEEventType =
  | 'generation'
  | 'file-created'
  | 'file-updated'
  | 'file-renamed'
  | 'directory-created'
  | 'task'
  | 'queue'
  | 'llm-status'
  | 'thinking'
  | 'error'
  | 'done'
  | 'step_done'
  | 'prompt'
  | 'connected'
  | 'file-deleted'

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
  | StepDoneEvent
  | PromptEvent
