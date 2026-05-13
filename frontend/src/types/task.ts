// 任务相关类型

export type TaskStatus = 'waiting' | 'running' | 'completed' | 'failed'

export interface Task {
  id: string
  name: string
  status: TaskStatus
  progress: number
  created_at?: string
  completed_at?: string
  error?: string
  // LLM 任务特有
  operation?: string
  target_file?: string
}

export interface TaskQueue {
  queue: string[]
  running: string | null
  completed: string[]
}

export interface ExecutionLog {
  id: string
  task_id: string
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
  timestamp: string
}

// 任务队列 API 类型
export interface TaskQueueItem {
  task_id: string
  status: string
  template: string
  created_at?: string
  completed_at?: string
  error?: string
}

export interface TaskQueueListResponse {
  tasks: TaskQueueItem[]
  total: number
  running: number
}

export interface TaskSubmitRequest {
  template_category: string
  template_type: string
  project_id: string
  target_file?: string | null
  variables?: Record<string, unknown>
}
