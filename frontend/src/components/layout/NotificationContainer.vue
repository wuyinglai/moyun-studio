<template>
  <div></div>
</template>

<script setup lang="ts">
import { watch, onUnmounted } from 'vue'
import { notification } from 'ant-design-vue'
import { useNotificationStore } from '@/stores/notification'

const store = useNotificationStore()

let notificationKeys = new Map()

function showAntNotification(notificationItem: any) {
  const key = notificationItem.id

  const config: any = {
    message: '',
    description: notificationItem.message,
    duration: 3,
    key,
  }

  switch (notificationItem.type) {
    case 'success':
      notification.success(config)
      break
    case 'error':
      notification.error(config)
      break
    case 'warning':
      notification.warning(config)
      break
    default:
      notification.info(config)
  }

  notificationKeys.set(key, true)
}

// 监听新通知添加，同时清理已关闭通知的 key
watch(
  () => store.notifications.length,
  () => {
    // 显示最新通知
    const latestNotification = store.notifications[store.notifications.length - 1]
    if (latestNotification && !notificationKeys.has(latestNotification.id)) {
      showAntNotification(latestNotification)
    }
    // 清理已关闭的通知 key
    if (notificationKeys.size > store.notifications.length) {
      const existingIds = new Set(store.notifications.map(n => n.id))
      notificationKeys.forEach((_, key) => {
        if (!existingIds.has(key)) notificationKeys.delete(key)
      })
    }
  }
)

onUnmounted(() => {
  notificationKeys = new Map()
})
</script>
