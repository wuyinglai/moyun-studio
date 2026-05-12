import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  autoClose: boolean
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])

  let counter = 0

  function addNotification(payload: Omit<Notification, 'id'>) {
    const id = `notification-${++counter}`
    const notification: Notification = {
      id,
      ...payload,
    }
    notifications.value.push(notification)

    // 自动消失（5秒）
    if (notification.autoClose) {
      setTimeout(() => {
        removeNotification(id)
      }, 5000)
    }
  }

  function removeNotification(id: string) {
    const index = notifications.value.findIndex((n) => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  function success(message: string) {
    addNotification({ type: 'success', message, autoClose: true })
  }

  function error(message: string) {
    addNotification({ type: 'error', message, autoClose: true })
  }

  function warning(message: string) {
    addNotification({ type: 'warning', message, autoClose: true })
  }

  function info(message: string) {
    addNotification({ type: 'info', message, autoClose: true })
  }

  return {
    notifications,
    addNotification,
    removeNotification,
    success,
    error,
    warning,
    info,
  }
})
