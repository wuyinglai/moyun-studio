<template>
  <div class="task-card" :class="`status-${task.status}`">
    <div class="task-header">
      <div class="task-status-icon">
        <i :class="statusIcon"></i>
      </div>
      <div class="task-info">
        <span class="task-name">{{ task.name }}</span>
        <span class="task-meta">{{ task.operation || statusLabel }}</span>
      </div>
      <div class="task-actions" v-if="task.status === 'running'">
        <button class="btn-stop" @click="$emit('stop', task.id)" title="停止">
          <i class="fa-solid fa-stop"></i>
        </button>
      </div>
    </div>

    <!-- 进度条（running 时显示） -->
    <div v-if="task.status === 'running' && task.progress !== undefined" class="task-progress">
      <div class="progress-bar" :style="{ width: task.progress + '%' }"></div>
    </div>

    <!-- 错误信息 -->
    <div v-if="task.status === 'failed' && task.error" class="task-error">
      <i class="fa-solid fa-exclamation-circle"></i>
      {{ task.error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Task } from '@/types/task'

const props = defineProps<{
  task: Task
}>()

defineEmits<{
  (e: 'stop', taskId: string): void
}>()

const statusIcon = computed(() => {
  switch (props.task.status) {
    case 'waiting': return 'fa-regular fa-clock'
    case 'running': return 'fa-solid fa-spinner fa-spin'
    case 'completed': return 'fa-solid fa-check-circle'
    case 'failed': return 'fa-solid fa-times-circle'
  }
})

const statusLabel = computed(() => {
  switch (props.task.status) {
    case 'waiting': return '等待中'
    case 'running': return '执行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
  }
})
</script>

<style scoped>
.task-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.task-card:hover {
  background: rgba(255,255,255,0.05);
}

.status-waiting { border-left-color: var(--text-muted); }
.status-running { border-left-color: var(--accent-primary); }
.status-completed { border-left-color: var(--accent-success); }
.status-failed { border-left-color: var(--accent-danger); }

.task-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-status-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.status-waiting .task-status-icon { color: var(--text-muted); }
.status-running .task-status-icon { color: var(--accent-primary); }
.status-completed .task-status-icon { color: var(--accent-success); }
.status-failed .task-status-icon { color: var(--accent-danger); }

.task-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  font-size: 11px;
  color: var(--text-muted);
}

.task-actions {
  flex-shrink: 0;
}

.btn-stop {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--accent-danger);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.btn-stop:hover {
  opacity: 1;
}

.task-progress {
  margin-top: 8px;
  height: 3px;
  background: var(--bg-secondary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--accent-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.task-error {
  margin-top: 6px;
  font-size: 12px;
  color: var(--accent-danger);
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
