<template>
  <div class="execution-panel">
    <!-- M0403-1 状态指示 -->
    <div class="panel-section">
      <div class="section-header">
        <span class="section-title">任务队列</span>
        <span class="exec-status" :class="{ running: hasRunningTasks }">
          <span class="status-dot"></span>
          {{ hasRunningTasks ? '运行中' : '空闲' }}
        </span>
        <button class="btn-icon" @click="clearAll" title="清空">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>

      <div v-if="tasks.length === 0" class="section-empty">
        <i class="fa-solid fa-inbox"></i>
        <span>暂无任务</span>
      </div>

      <div v-else class="task-list">
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

          <div v-if="task.status === 'running'" class="task-progress">
            <div class="progress-bar" :style="{ width: task.progress + '%' }"></div>
          </div>

          <div class="task-meta">
            <span class="task-time">{{ formatTime(task.createdAt) }}</span>
            <div class="task-actions">
              <button
                v-if="task.status === 'waiting'"
                class="btn-confirm"
                @click="confirmTask(task.id)"
              >
                <i class="fa-solid fa-play"></i> 继续
              </button>
              <button
                v-if="task.status === 'pending' || task.status === 'running'"
                class="btn-cancel"
                @click="cancelTask(task.id)"
              >
                <i class="fa-solid fa-stop"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日志 -->
    <div class="panel-section panel-section--logs">
      <div class="section-header">
        <span class="section-title">执行日志</span>
        <button class="btn-icon" @click="clearLogs" title="清空">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>

      <div class="log-list" ref="logContainer">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-item"
          :class="log.level"
        >
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>

        <div v-if="logs.length === 0" class="section-empty">
          <i class="fa-solid fa-terminal"></i>
          <span>暂无日志</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useTaskStore } from '@/stores/task'
import { useNotificationStore } from '@/stores/notification'

const taskStore = useTaskStore()
const notification = useNotificationStore()

const logContainer = ref<HTMLElement | null>(null)

const tasks = computed(() => taskStore.tasks)
const logs = computed(() => taskStore.logs)
const hasRunningTasks = computed(() => tasks.value.some(t => t.status === 'running'))

const statusText: Record<string, string> = {
  pending: '等待中',
  running: '进行中',
  done: '已完成',
  failed: '失败',
  cancelled: '已取消',
  waiting: '待确认',
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

function cancelTask(taskId: string) {
  taskStore.cancelTask(taskId)
  notification.warning('任务已取消')
}

function confirmTask(taskId: string) {
  taskStore.confirmTask(taskId)
  notification.success('已确认，继续执行')
}

function clearAll() {
  taskStore.clearTasks()
  notification.success('任务队列已清空')
}

function clearLogs() {
  taskStore.clearLogs()
  notification.success('日志已清空')
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
</style>
