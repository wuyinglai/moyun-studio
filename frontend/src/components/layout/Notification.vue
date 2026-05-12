<template>
  <div class="notification-item" :class="`type-${notification.type}`">
    <div class="notification-icon">
      <i :class="iconClass"></i>
    </div>
    <div class="notification-content">
      <span class="notification-message">{{ notification.message }}</span>
    </div>
    <button class="notification-close" @click="$emit('close')">
      <i class="fa-solid fa-times"></i>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Notification } from '@/types'

const props = defineProps<{
  notification: Notification
}>()

defineEmits<{
  (e: 'close'): void
}>()

const iconClass = computed(() => {
  switch (props.notification.type) {
    case 'success': return 'fa-solid fa-check-circle'
    case 'error': return 'fa-solid fa-exclamation-circle'
    case 'warning': return 'fa-solid fa-exclamation-triangle'
    case 'info': return 'fa-solid fa-info-circle'
  }
})
</script>

<style scoped>
.notification-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  min-width: 280px;
  max-width: 400px;
  animation: slide-in 0.3s ease;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.notification-icon {
  flex-shrink: 0;
  font-size: 16px;
}

.type-success .notification-icon { color: var(--accent-success); }
.type-error .notification-icon { color: var(--accent-danger); }
.type-warning .notification-icon { color: var(--accent-warning); }
.type-info .notification-icon { color: var(--accent-primary); }

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-message {
  font-size: 14px;
  color: var(--text-primary);
  word-break: break-word;
}

.notification-close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: transparent;
  color: var(--text-muted);
  font-size: 10px;
  transition: all 0.2s;
}

.notification-close:hover {
  background: rgba(255,255,255,0.1);
  color: var(--text-primary);
}
</style>
