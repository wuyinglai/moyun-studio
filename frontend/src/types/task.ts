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
