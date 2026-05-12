import axios from 'axios'
import { useNotificationStore } from '@/stores/notification'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器：统一处理 { success, data, message }
api.interceptors.response.use(
  (response) => {
    const { success, data, message } = response.data
    if (!success) {
      throw new Error(message || '请求失败')
    }
    return data
  },
  (error) => {
    const message = error.response?.data?.message || error.message
    try {
      const notificationStore = useNotificationStore()
      notificationStore.addNotification({
        type: 'error',
        message,
        autoClose: true,
      })
    } catch {
      // Pinia store 可能还未初始化，忽略
    }
    return Promise.reject(error)
  }
)

export default api
