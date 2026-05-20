/** SSE 模块 - 事件过滤工具 */

import type { BaseEvent } from './types'

/**
 * 按 project_id 过滤事件
 * 只处理当前项目的事件，忽略其他项目的事件
 */
export function filterByProjectId<T extends BaseEvent>(
  event: T,
  currentProjectId: string | undefined,
): boolean {
  if (!event.project_id || !currentProjectId) return true
  return event.project_id === currentProjectId
}

/**
 * 按 task_id 过滤事件
 * 只处理指定任务的事件
 */
export function filterByTaskId<T extends BaseEvent>(
  event: T,
  currentTaskId: string | undefined,
): boolean {
  if (!currentTaskId) return true
  const taskId = event.task_id || event.taskId
  if (!taskId) return true
  return taskId === currentTaskId
}

/**
 * 组合过滤：同时按 project_id 和 task_id 过滤
 */
export function filterEvent<T extends BaseEvent>(
  event: T,
  options: { projectId?: string; taskId?: string },
): boolean {
  return filterByProjectId(event, options.projectId) && filterByTaskId(event, options.taskId)
}
