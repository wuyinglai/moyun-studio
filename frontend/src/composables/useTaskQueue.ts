import { ref } from 'vue'
import { useTaskStore } from '@/stores/task'
import { useNotificationStore } from '@/stores/notification'

/* ─── 模块级队列状态（单例） ────────────────────────────── */

interface QueueItem {
  id: string
  executor: () => Promise<void>
  name: string
}

const _queue = ref<QueueItem[]>([])
const _isProcessing = ref(false)

/** L1 待确认任务的 resolve 回调 */
const _confirmResolvers = new Map<string, () => void>()

/* ─── 持久化 ─────────────────────────────────────────── */

const PREFIX = 'moyun:task-queue:'

function _saveQueueMeta() {
  const metas = _queue.value.map(t => ({ id: t.id, name: t.name }))
  localStorage.setItem(PREFIX + 'queue', JSON.stringify(metas))
}

function _loadQueueMeta(): { id: string; name: string }[] {
  try {
    const raw = localStorage.getItem(PREFIX + 'queue')
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function restoreInterruptedTasks() {
  const metas = _loadQueueMeta()
  if (metas.length === 0) return

  const taskStore = useTaskStore()
  for (const meta of metas) {
    taskStore.addTask(meta.id, `[中断] ${meta.name}`)
    taskStore.markInterrupted(meta.id)
  }
  localStorage.removeItem(PREFIX + 'queue')
}

/* ─── 内部处理逻辑 ──────────────────────────────────────── */

function getAutoMode(): string {
  return localStorage.getItem('moyun-auto-mode') || 'L1'
}

async function processQueue() {
  if (_isProcessing.value || _queue.value.length === 0) return
  _isProcessing.value = true

  const taskStore = useTaskStore()

  while (_queue.value.length > 0) {
    const task = _queue.value[0]
    taskStore.startTask(task.id)
    taskStore.addLog('info', `开始: ${task.name}`)

    try {
      await task.executor()
      taskStore.completeTask(task.id)
      taskStore.addLog('success', `完成: ${task.name}`)

      // L1：暂停等待用户确认
      if (getAutoMode() === 'L1') {
        taskStore.waitForConfirm(task.id)
        await new Promise<void>((resolve) => {
          _confirmResolvers.set(task.id, resolve)
        })
        taskStore.completeTask(task.id)
      }

      _queue.value.shift()
      _saveQueueMeta()
    } catch (e: any) {
      taskStore.failTask(task.id)
      taskStore.addLog('error', `失败: ${task.name} — ${e.message || e}`)
      _queue.value.shift()
      _saveQueueMeta()
    }
  }

  _isProcessing.value = false
}

/* ─── 导出函数 ──────────────────────────────────────────── */

export function enqueueTask(
  executor: () => Promise<void>,
  name: string,
): string {
  const id = `task-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
  const taskStore = useTaskStore()
  taskStore.addTask(id, name)
  _queue.value.push({ id, executor, name })
  _saveQueueMeta()

  if (_isProcessing.value) {
    useNotificationStore().info(`「${name}」已加入队列，等当前任务完成后执行`)
  } else {
    processQueue()
  }

  return id
}

/** 确认当前暂停的任务（由编辑器按钮触发） */
export function confirmTask(taskId: string) {
  const resolver = _confirmResolvers.get(taskId)
  if (resolver) {
    resolver()
    _confirmResolvers.delete(taskId)
  }
}

export function cancelQueuedTask(taskId: string) {
  const resolver = _confirmResolvers.get(taskId)
  if (resolver) {
    resolver()
    _confirmResolvers.delete(taskId)
  }
  const taskStore = useTaskStore()
  taskStore.cancelTask(taskId)
  const idx = _queue.value.findIndex(t => t.id === taskId)
  if (idx >= 0) _queue.value.splice(idx, 1)
  _saveQueueMeta()
}

/* ─── Vue 响应式 composable ─────────────────────────────── */

export function useTaskQueue() {
  return {
    enqueue: enqueueTask,
    cancelTask: cancelQueuedTask,
    restoreInterruptedTasks,
    isProcessing: _isProcessing,
    queueLength: _queue.value.length,
  }
}
