<template>
  <div></div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
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

// 监听新通知添加
watch(
  () => store.notifications.length,
  () => {
    const latestNotification = store.notifications[store.notifications.length - 1]
    if (latestNotification && !notificationKeys.has(latestNotification.id)) {
      showAntNotification(latestNotification)
    }
  }
)

// 清理已关闭的通知
setInterval(() => {
  const existingIds = store.notifications.map(n => n.id)
  notificationKeys.forEach((_, key) => {
    if (!existingIds.includes(key)) {
      notificationKeys.delete(key)
    }
  })
}, 1000)
</script>
