import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export type TaskStatus = 'pending' | 'running' | 'done' | 'failed' | 'cancelled' | 'waiting'

export interface Task {
  id: string
  name: string
  status: TaskStatus
  progress: number
  createdAt: number
}

export interface Log {
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  timestamp: number
}

/** 后端任务队列项 (与 GET /api/tasks 响应对齐) */
interface BackendTaskItem {
  task_id: string
  status: string
  template: string
  created_at?: string
  completed_at?: string
  error?: string
}

const STATUS_MAP: Record<string, TaskStatus> = {
  waiting: 'pending',
  running: 'running',
  completed: 'done',
  failed: 'failed',
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const queue = ref<string[]>([])
  const logs = ref<Log[]>([])
  let pollTimer: ReturnType<typeof setInterval> | null = null

  function addTask(id: string, name: string) {
    tasks.value.push({ id, name, status: 'pending', progress: 0, createdAt: Date.now() })
    queue.value.push(id)
  }

  function startTask(id: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.status = 'running'
    }
  }

  function updateTaskProgress(id: string, progress: number) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.progress = progress
    }
  }

  function completeTask(id: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.status = 'done'
      task.progress = 100
    }
    queue.value = queue.value.filter((qid) => qid !== id)
  }

  // G0116: L1 模式下等待确认
  function waitForConfirm(id: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.status = 'waiting'
      task.progress = 100
    }
  }

  function confirmTask(id: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task && task.status === 'waiting') {
      task.status = 'done'
    }
  }

  function failTask(id: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.status = 'failed'
    }
    queue.value = queue.value.filter((qid) => qid !== id)
  }

  function cancelTask(id: string) {
    const task = tasks.value.find((t) => t.id === id)
    if (task) {
      task.status = 'cancelled'
    }
    queue.value = queue.value.filter((qid) => qid !== id)
  }

  function clearTasks() {
    tasks.value = []
    queue.value = []
  }

  function addLog(level: Log['level'], message: string) {
    logs.value.push({ level, message, timestamp: Date.now() })
    if (logs.value.length > 500) {
      logs.value.splice(0, logs.value.length - 500)
    }
  }

  function clearLogs() {
    logs.value = []
  }

  /**
   * SSE 事件更新任务
   */
  function updateTask(taskId: string, data: Partial<Task>) {
    const task = tasks.value.find((t) => t.id === taskId)
    if (task) {
      if (data.status) task.status = data.status
      if (typeof data.progress === 'number') task.progress = data.progress
      if (data.name) task.name = data.name
    } else if (data.name && data.status) {
      // 如果任务不存在但有数据，创建一个新任务
      addTask(taskId, data.name)
      startTask(taskId)
      if (data.status === 'done') completeTask(taskId)
      if (data.status === 'failed') failTask(taskId)
    }
  }

  /**
   * 更新队列
   */
  function updateQueue(newQueue: string[]) {
    queue.value = newQueue
  }

  // ─── 后端任务队列轮询 ──────────────────────────────────────

  function _toLocalTask(bt: BackendTaskItem): Task {
    const name = bt.template.split('/').pop() || bt.template
    return {
      id: bt.task_id,
      name,
      status: STATUS_MAP[bt.status] || 'pending',
      progress: bt.status === 'completed' ? 100 : bt.status === 'running' ? 50 : 0,
      createdAt: bt.created_at ? new Date(bt.created_at).getTime() : Date.now(),
    }
  }

  async function pollTasks() {
    try {
      const res = await api.get<{ tasks: BackendTaskItem[] }>('/tasks')
      const backendTasks = res.tasks || []

      // 合并后端任务到本地列表
      for (const bt of backendTasks) {
        const existing = tasks.value.find(t => t.id === bt.task_id)
        const local = _toLocalTask(bt)
        if (existing) {
          existing.status = local.status
          existing.progress = local.progress
          if (bt.error) addLog('error', `[${local.name}] ${bt.error}`)
        } else {
          tasks.value.push(local)
          if (local.status === 'running') addLog('info', `任务开始: ${local.name}`)
        }
      }

      // 更新队列顺序
      queue.value = backendTasks.filter(t => t.status !== 'completed' && t.status !== 'failed').map(t => t.task_id)
    } catch {
      // 静默失败（可能服务器未就绪）
    }
  }

  function startPolling(intervalMs = 3000) {
    stopPolling()
    pollTimer = setInterval(pollTasks, intervalMs)
    pollTasks() // 立即拉一次
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    tasks,
    queue,
    logs,
    addTask,
    startTask,
    updateTaskProgress,
    updateTask,
    completeTask,
    failTask,
    cancelTask,
    waitForConfirm,
    confirmTask,
    clearTasks,
    addLog,
    clearLogs,
    updateQueue,
    pollTasks,
    startPolling,
    stopPolling,
  }
})
