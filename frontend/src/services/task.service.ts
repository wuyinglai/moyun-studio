/**
 * 任务服务 - 封装 /api/tasks 和 /api/stop 相关操作
 */
import api from './api'
import type { Task, ExecutionLog } from '@/types/task'

export const taskService = {
  /** 获取所有任务 */
  list(projectId: string) {
    return api.get<Task[]>('/tasks', {
      params: { project_id: projectId },
    })
  },

  /** 获取单个任务 */
  get(taskId: string) {
    return api.get<Task>(`/tasks/${taskId}`)
  },

  /** 获取执行日志 */
  getLogs(projectId: string, taskId: string) {
    return api.get<ExecutionLog[]>('/tasks/logs', {
      params: { project_id: projectId, task_id: taskId },
    })
  },

  /** 停止当前任务 */
  stop(projectId: string) {
    return api.post('/stop', { project_id: projectId })
  },
}
