<template>
  <div
    v-if="visibleNotifications.length > 0"
    class="notification-ticker"
  >
    <div
      v-for="item in visibleNotifications"
      :key="item.id"
      class="ticker-item"
      :class="'ticker-' + item.type"
    >
      <span class="ticker-icon">{{ iconMap[item.type] }}</span>
      <span class="ticker-msg">{{ item.message }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { useNotificationStore } from '@/stores/notification'

const store = useNotificationStore()

const iconMap: Record<string, string> = {
  success: '✓',
  error: '✗',
  warning: '⚠',
  info: 'ℹ',
}

const visibleNotifications = ref<{ id: string; type: string; message: string }[]>([])
const timers = new Map<string, ReturnType<typeof setTimeout>>()
const MAX_VISIBLE = 3

watch(
  () => store.notifications.length,
  () => {
    const latest = store.notifications[store.notifications.length - 1]
    if (!latest) return

    // 添加到可见列表
    visibleNotifications.value.push({ ...latest })
    if (visibleNotifications.value.length > MAX_VISIBLE) {
      const removed = visibleNotifications.value.shift()
      if (removed && timers.has(removed.id)) {
        clearTimeout(timers.get(removed.id)!)
        timers.delete(removed.id)
      }
    }

    // 3秒后自动移除
    const timer = setTimeout(() => {
      const idx = visibleNotifications.value.findIndex(n => n.id === latest.id)
      if (idx !== -1) visibleNotifications.value.splice(idx, 1)
      timers.delete(latest.id)
    }, 3000)
    timers.set(latest.id, timer)
  }
)

onUnmounted(() => {
  timers.forEach(t => clearTimeout(t))
  timers.clear()
})
</script>

<style scoped>
.notification-ticker {
  position: fixed;
  top: 48px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 4px;
  pointer-events: none;
  max-width: 600px;
  width: 100%;
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  animation: ticker-in 0.2s ease-out;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.ticker-success {
  background: rgba(82, 196, 26, 0.15);
  color: #b7eb8f;
  border: 1px solid rgba(82, 196, 26, 0.3);
}

.ticker-error {
  background: rgba(255, 77, 79, 0.15);
  color: #ffa39e;
  border: 1px solid rgba(255, 77, 79, 0.3);
}

.ticker-warning {
  background: rgba(250, 173, 20, 0.15);
  color: #ffe58f;
  border: 1px solid rgba(250, 173, 20, 0.3);
}

.ticker-info {
  background: rgba(24, 144, 255, 0.15);
  color: #91d5ff;
  border: 1px solid rgba(24, 144, 255, 0.3);
}

.ticker-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.ticker-msg {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@keyframes ticker-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
