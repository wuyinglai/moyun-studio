<template>
  <Teleport to="body">
    <div class="notification-container" v-if="store.notifications.length > 0">
      <TransitionGroup name="notification">
        <div
          v-for="n in store.notifications"
          :key="n.id"
          class="notification"
          :class="`notification--${n.type}`"
        >
          <i :class="iconClass(n.type)"></i>
          <span class="notification-message">{{ n.message }}</span>
          <button class="notification-close" @click="store.removeNotification(n.id)">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useNotificationStore } from '@/stores/notification'

const store = useNotificationStore()

function iconClass(type: string) {
  switch (type) {
    case 'success':
      return 'fa-solid fa-check-circle notification-icon'
    case 'error':
      return 'fa-solid fa-circle-exclamation notification-icon'
    case 'warning':
      return 'fa-solid fa-triangle-exclamation notification-icon'
    default:
      return 'fa-solid fa-info-circle notification-icon'
  }
}
</script>

<style scoped lang="scss">
.notification-container {
  position: fixed;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  pointer-events: none;
}

.notification {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  pointer-events: all;
  min-width: 280px;
  max-width: 480px;

  &--success {
    border-color: var(--accent-success);
    .notification-icon {
      color: var(--accent-success);
    }
  }

  &--error {
    border-color: var(--accent-danger);
    .notification-icon {
      color: var(--accent-danger);
    }
  }

  &--warning {
    border-color: var(--accent-warning);
    .notification-icon {
      color: var(--accent-warning);
    }
  }
}

.notification-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.notification-message {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
}

.notification-close {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  transition: color 0.2s;

  &:hover {
    color: var(--text-primary);
  }
}

// 过渡动画
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.notification-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
