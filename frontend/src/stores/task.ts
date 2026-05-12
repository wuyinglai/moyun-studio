import { defineStore } from 'pinia'
import { ref } from 'vue'

export type TaskStatus = 'pending' | 'running' | 'done' | 'failed' | 'cancelled'

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

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const queue = ref<string[]>([])
  const logs = ref<Log[]>([])

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
    clearTasks,
    addLog,
    clearLogs,
    updateQueue,
  }
})
