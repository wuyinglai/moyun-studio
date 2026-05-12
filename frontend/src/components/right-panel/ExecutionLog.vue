<template>
  <div class="execution-log" ref="containerRef">
    <div v-if="logs.length === 0" class="log-empty">
      <i class="fa-solid fa-terminal"></i>
      <span>暂无日志</span>
    </div>

    <TransitionGroup name="log" tag="div" class="log-list">
      <div
        v-for="log in logs"
        :key="log.id"
        class="log-entry"
        :class="`level-${log.level}`"
      >
        <span class="log-time">{{ formatTime(log.timestamp) }}</span>
        <span class="log-level-badge">{{ levelLabel(log.level) }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { ExecutionLog } from '@/types/task'

const props = defineProps<{
  logs: ExecutionLog[]
}>()

const containerRef = ref<HTMLElement | null>(null)

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function levelLabel(level: string): string {
  const map: Record<string, string> = {
    info: 'INFO',
    warning: 'WARN',
    error: 'ERROR',
    success: 'OK',
  }
  return map[level] || level.toUpperCase()
}

watch(
  () => props.logs.length,
  () => {
    nextTick(() => {
      if (containerRef.value) {
        containerRef.value.scrollTop = containerRef.value.scrollHeight
      }
    })
  }
)
</script>

<style scoped>
.execution-log {
  height: 100%;
  overflow-y: auto;
  font-family: var(--font-family-mono);
  font-size: 12px;
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
  color: var(--text-muted);
  opacity: 0.5;
}

.log-list {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.log-entry {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 3px;
  line-height: 1.4;
}

.log-entry:hover {
  background: rgba(255,255,255,0.03);
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
  font-size: 11px;
}

.log-level-badge {
  flex-shrink: 0;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
}

.level-info .log-level-badge { background: rgba(59,130,246,0.2); color: var(--accent-primary); }
.level-warning .log-level-badge { background: rgba(245,158,11,0.2); color: var(--accent-warning); }
.level-error .log-level-badge { background: rgba(239,68,68,0.2); color: var(--accent-danger); }
.level-success .log-level-badge { background: rgba(74,222,128,0.2); color: var(--accent-success); }

.log-message {
  color: var(--text-primary);
  word-break: break-word;
}

.level-warning .log-message { color: var(--accent-warning); }
.level-error .log-message { color: var(--accent-danger); }

/* 日志进入动画 */
.log-enter-active {
  transition: all 0.2s ease;
}
.log-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
