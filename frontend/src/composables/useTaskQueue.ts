import { ref } from 'vue'
import { useTaskStore } from '@/stores/task'

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
        taskStore.addLog('info', `等待确认: ${task.name}`)
        await new Promise<void>((resolve) => {
          _confirmResolvers.set(task.id, resolve)
        })
        // 用户已确认，标记完成
        taskStore.completeTask(task.id)
      }

      _queue.value.shift()
    } catch (e: any) {
      taskStore.failTask(task.id)
      taskStore.addLog('error', `失败: ${task.name} — ${e.message || e}`)
      _queue.value.shift()
    }
  }

  _isProcessing.value = false
}

/* ─── 导出函数 ──────────────────────────────────────────── */

/**
 * 将任务加入执行队列（L1 逐确认 / L2 自动连续）
 */
export function enqueueTask(
  executor: () => Promise<void>,
  name: string,
): string {
  const id = `task-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
  const taskStore = useTaskStore()
  taskStore.addTask(id, name)
  _queue.value.push({ id, executor, name })

  if (!_isProcessing.value) {
    processQueue()
  }

  return id
}

/**
 * 外部确认当前暂停的任务（ExecutionPanel 的确认按钮调用）
 */
export function confirmTask(taskId: string) {
  const resolver = _confirmResolvers.get(taskId)
  if (resolver) {
    resolver()
    _confirmResolvers.delete(taskId)
  }
}

/**
 * 取消队列中的任务
 */
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
}

/* ─── Vue 响应式 composable ─────────────────────────────── */

export function useTaskQueue() {
  return {
    enqueue: enqueueTask,
    confirmTask: confirmTask,
    cancelTask: cancelQueuedTask,
    isProcessing: _isProcessing,
    queueLength: _queue.value.length,
  }
}
