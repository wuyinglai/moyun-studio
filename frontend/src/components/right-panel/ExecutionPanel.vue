<template>
  <div
    class="execution-panel"
    data-testid="task-status-panel"
  >
    <!-- M0403-1 状态指示 -->
    <div class="panel-section">
      <div class="section-header">
        <span class="section-title">LLM 工作堆栈</span>
        <span
          class="exec-status"
          :class="{ running: hasRunningTasks }"
        >
          <span class="status-dot" />
          {{ hasRunningTasks ? '运行中' : '空闲' }}
        </span>
        <button
          class="btn-icon"
          title="清空"
          @click="clearAll"
        >
          <i class="fa-solid fa-trash-can" />
        </button>
        <!-- 开发模式测试入口 -->
        <button
          v-if="isDevMode"
          data-testid="dry-run-task-button"
          class="btn-dry-run"
          title="Dry Run 测试"
          @click="handleDryRunTask"
        >
          <i class="fa-solid fa-flask-vial" />
          Dry Run
        </button>
        <!-- Pipeline Dry Run 测试入口 -->
        <button
          v-if="isDevMode"
          data-testid="dry-run-pipeline-button"
          class="btn-dry-run btn-pipeline"
          title="Pipeline Dry Run 测试"
          @click="handleDryRunPipeline"
        >
          <i class="fa-solid fa-pipe-section" />
          Pipeline Dry Run
        </button>
        <!-- Batch Dry Run 测试入口 -->
        <button
          v-if="isDevMode"
          data-testid="dry-run-batch-button"
          class="btn-dry-run btn-batch"
          title="Batch Dry Run 测试"
          @click="handleDryRunBatch"
        >
          <i class="fa-solid fa-list-ul" />
          Batch Dry Run
        </button>
      </div>

      <div
        v-if="tasks.length === 0"
        class="section-empty"
      >
        <i class="fa-solid fa-inbox" />
        <span>暂无任务</span>
      </div>

      <div
        v-else
        class="task-list"
      >
        <div
          v-for="task in tasks"
          :key="task.id"
          class="task-card"
          :class="task.status"
        >
          <div class="task-header">
            <span class="task-name">{{ task.name }}</span>
            <span class="task-status-badge">{{ statusText[task.status] }}</span>
          </div>

          <div
            v-if="task.status === 'running'"
            class="task-progress"
          >
            <div
              class="progress-bar"
              :style="{ width: task.progress + '%' }"
            />
          </div>

          <div class="task-meta">
            <span class="task-time">{{ formatTime(task.createdAt) }}</span>
            <div class="task-actions">
              <button
                v-if="task.status === 'pending' || task.status === 'running'"
                class="btn-cancel"
                @click="handleCancelTask(task.id)"
              >
                <i class="fa-solid fa-stop" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 修改摘要 -->
    <div
      v-if="diffSummary.hasSummary.value"
      class="panel-section"
    >
      <div class="section-header">
        <span class="section-title">AI 修改摘要</span>
        <button
          class="btn-icon"
          title="关闭"
          @click="diffSummary.dismiss()"
        >
          <i class="fa-solid fa-xmark" />
        </button>
      </div>
      <div class="diff-summary-body">
        <pre class="diff-summary-text">{{ diffSummary.current.value?.summary }}</pre>
      </div>
    </div>

    <!-- 日志 -->
    <div class="panel-section panel-section--logs">
      <div class="section-header">
        <span class="section-title">执行日志</span>
        <button
          class="btn-icon"
          title="清空"
          @click="clearLogs"
        >
          <i class="fa-solid fa-trash-can" />
        </button>
      </div>

      <div
        ref="logContainer"
        class="log-list"
      >
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-item"
          :class="log.level"
        >
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>

        <div
          v-if="logs.length === 0"
          class="section-empty"
        >
          <i class="fa-solid fa-terminal" />
          <span>暂无日志</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { useNotificationStore } from '@/stores/notification'
import { useDiffSummary } from '@/composables/useDiffSummary'
import { cancelQueuedTask } from '@/composables/useTaskQueue'
import api from '@/services/api'
import { API_ROUTES } from '@/shared/api/routes'

const route = useRoute()
const isDevMode = import.meta.env.DEV

const diffSummary = useDiffSummary()

const taskStore = useTaskStore()
const notification = useNotificationStore()

const logContainer = ref<HTMLElement | null>(null)

onMounted(() => {
  taskStore.startPolling(5000)
})

onUnmounted(() => {
  taskStore.stopPolling()
})

const tasks = computed(() => {
  const statusOrder: Record<string, number> = { running: 0, pending: 1, waiting: 2, done: 3, failed: 4, cancelled: 5 }
  return [...taskStore.tasks].sort((a, b) => {
    const oa = statusOrder[a.status] ?? 99
    const ob = statusOrder[b.status] ?? 99
    if (oa !== ob) return oa - ob
    return b.createdAt - a.createdAt  // 同状态按创建时间倒序
  })
})
const logs = computed(() => taskStore.logs)
const hasRunningTasks = computed(() => tasks.value.some(t => t.status === 'running'))

const statusText: Record<string, string> = {
  pending: '等待中',
  running: '进行中',
  done: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

// 自动滚动到最新日志
watch(logs, async () => {
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}, { deep: true })

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function handleCancelTask(taskId: string) {
  try {
    try {
      await api.post(API_ROUTES.taskCancel(taskId))
    } catch {
      // 本地临时任务可能尚未注册到后端，仍允许取消前端队列状态。
    }
    taskStore.cancelTask(taskId)
    cancelQueuedTask(taskId)
    notification.warning('任务已取消')
  } catch {
    notification.error('取消失败')
  }
}

function clearAll() {
  taskStore.clearTasks()
  notification.success('任务队列已清空')
}

function clearLogs() {
  taskStore.clearLogs()
  notification.success('日志已清空')
}

// ─── 开发模式 Dry Run 测试入口 ────────────────────
interface DryRunResult {
  success: boolean
  data?: {
    task_id: string
  }
}

async function handleDryRunTask() {
  try {
    const projectId = route.params.projectId as string
    if (!projectId) {
      notification.error('未找到项目 ID')
      return
    }

    const result = await api.post('/tasks', {
      template_category: 'generate',
      template_type: 'chapter',
      project_id: projectId,
      variables: {},
      dry_run: true,
    }) as DryRunResult

    if (result.success) {
      notification.info(`Dry Run 任务已提交: ${result.data?.task_id}`)
      taskStore.addLog('info', `[Dry Run] 任务提交成功: ${result.data?.task_id}`)
      // 立即轮询更新任务列表
      await taskStore.pollTasks()
    }
  } catch (error) {
    notification.error('Dry Run 任务提交失败')
    taskStore.addLog('error', '[Dry Run] 任务提交失败')
    console.error('Dry Run error:', error)
  }
}

// ─── Pipeline Dry Run 测试入口 ────────────────────

async function handleDryRunPipeline() {
  try {
    const projectId = route.params.projectId as string
    if (!projectId) {
      notification.error('未找到项目 ID')
      return
    }

    taskStore.addLog('info', '[Pipeline Dry Run] 开始执行...')

    // 使用当前打开的文件路径，如果没有则使用默认测试路径
    const targetFile = (route.query.file as string) || 'chapters/vol-01/ch-001/sec-001.md'

    // 监听 SSE 流
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'}/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pipeline: 'polish',
        project_id: projectId,
        target_file: targetFile,
        dry_run: true,
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      taskStore.addLog('error', `[Pipeline Dry Run] 请求失败: ${response.status} ${errorText}`)
      notification.error('Pipeline Dry Run 请求失败')
      return
    }

    // 读取 SSE 流
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let done = false
    let receivedDone = false
    let isDryRun = false

    while (!done) {
      const { value, done: streamDone } = await reader!.read()
      done = streamDone
      if (value) {
        buffer += decoder.decode(value, { stream: !done })
      }

      // 处理 SSE 数据
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            const event = data.event || data.type

            if (event === 'done') {
              receivedDone = true
              isDryRun = data.dry_run === true
              taskStore.addLog('success', `[Pipeline Dry Run] 完成! dry_run=${isDryRun}`)
            } else if (event === 'generation') {
              taskStore.addLog('info', `[Pipeline] generation: dry_run=${data.dry_run || false}`)
            } else if (event === 'error') {
              taskStore.addLog('error', `[Pipeline] 错误: ${data.message}`)
            } else {
              taskStore.addLog('info', `[Pipeline] ${event}`)
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }

    if (receivedDone) {
      notification.success(`Pipeline Dry Run 完成! dry_run=${isDryRun}`)
    } else {
      notification.warning('Pipeline Dry Run 未收到 done 事件')
      taskStore.addLog('warning', '[Pipeline Dry Run] 未收到 done 事件')
    }
  } catch (error) {
    notification.error('Pipeline Dry Run 执行失败')
    taskStore.addLog('error', `[Pipeline Dry Run] 执行失败: ${error}`)
    console.error('Pipeline Dry Run error:', error)
  }
}

// ─── Batch Dry Run 测试入口 ───────────────────────
async function handleDryRunBatch() {
  try {
    const projectId = route.params.projectId as string
    if (!projectId) {
      notification.error('未找到项目 ID')
      return
    }

    taskStore.addLog('info', '[Batch Dry Run] 开始执行...')

    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'}/generate/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        volume_number: 1,
        chapter_number: 1,
        section_numbers: [1, 2],
        prompt_type: 'generate/chapter',
        dry_run: true,
      }),
    })

    const data = await response.json()

    if (!response.ok || !data?.success) {
      taskStore.addLog('error', `[Batch Dry Run] 请求失败: ${data?.message || response.status}`)
      notification.error('Batch Dry Run 请求失败')
      return
    }

    const result = data.data
    const total = result.total
    const succeeded = result.succeeded

    // 检查是否所有项都是 dry_run
    const allDryRun = (result.tasks || []).every((t: any) => t.dry_run === true)
    if (allDryRun) {
      notification.success(`Batch Dry Run 完成! ${succeeded}/${total} 项`)
      taskStore.addLog('success', `[Batch Dry Run] 完成! dry_run=true, ${succeeded}/${total} 项`)
    } else {
      notification.warning(`Batch Dry Run 完成，但部分项未标记 dry_run`)
      taskStore.addLog('warning', `[Batch Dry Run] 部分项未标记 dry_run`)
    }
  } catch (error) {
    notification.error('Batch Dry Run 执行失败')
    taskStore.addLog('error', `[Batch Dry Run] 执行失败: ${error}`)
    console.error('Batch Dry Run error:', error)
  }
}
</script>

<style scoped lang="scss">
.execution-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-section {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);

  &--logs {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-bottom: none;
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 8px;
}

.exec-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  margin-right: auto;

  &.running {
    color: var(--accent-primary);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);

    .running & {
      background: var(--accent-success);
      animation: pulse 2s infinite;
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@keyframes pulse-waiting {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.btn-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 12px;

  &:hover {
    background: var(--bg-card);
    color: var(--text-primary);
  }
}

.section-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;

  i {
    font-size: 24px;
    opacity: 0.5;
  }
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.task-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 12px;

  &.pending {
    border-left: 3px solid var(--text-muted);
  }

  &.running {
    border-left: 3px solid var(--accent-primary);
  }

  &.done {
    border-left: 3px solid var(--accent-success);
  }

  &.failed {
    border-left: 3px solid var(--accent-danger);
  }

  &.cancelled {
    border-left: 3px solid var(--text-muted);
    opacity: 0.6;
  }

  &.waiting {
    border-left: 3px solid var(--accent-warning);
    animation: pulse-waiting 1.5s infinite;
  }
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.task-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.task-status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--bg-primary);
  color: var(--text-secondary);

  .running & {
    background: var(--accent-primary);
    color: white;
  }

  .done & {
    background: var(--accent-success);
    color: white;
  }

  .waiting & {
    background: var(--accent-warning);
    color: white;
  }

  .failed & {
    background: var(--accent-danger);
    color: white;
  }
}

.task-progress {
  height: 4px;
  background: var(--bg-primary);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 8px;

  .progress-bar {
    height: 100%;
    background: var(--accent-primary);
    transition: width 0.3s;
  }
}

.task-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.task-actions {
  display: flex;
  gap: 4px;
}

.btn-confirm {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-confirm:hover {
  opacity: 0.85;
}

.task-time {
  font-size: 11px;
  color: var(--text-muted);
}

.btn-cancel {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);

  &:hover {
    background: var(--accent-danger);
    color: white;
  }
}

.btn-dry-run {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--accent-warning);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    opacity: 0.85;
  }

  i {
    font-size: 10px;
  }
}

.btn-pipeline {
  background: #8b5cf6; // purple
  margin-left: 4px;
}

.btn-batch {
  background: #10b981; // green
  margin-left: 4px;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  padding: 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 11px;
}

.log-item {
  display: flex;
  gap: 8px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  margin-bottom: 2px;

  &.info {
    color: var(--text-secondary);
  }

  &.success {
    color: var(--accent-success);
  }

  &.warning {
    color: var(--accent-warning);
  }

  &.error {
    color: var(--accent-danger);
  }
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}

.log-message {
  word-break: break-all;
}

.diff-summary-body {
  max-height: 300px;
  overflow-y: auto;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  padding: 12px;
}

.diff-summary-text {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  margin: 0;
}
</style>
