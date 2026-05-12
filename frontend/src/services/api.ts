import axios from 'axios'
import { useNotificationStore } from '@/stores/notification'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器：兼容两种格式
// 格式1: { success: true, data: ..., message: '...' }  (标准封装)
// 格式2: 直接返回数据 (数组/对象/字符串等)
api.interceptors.response.use(
  (response) => {
    const body = response.data
    // 判断是否是标准封装格式（有 success 字段且为 boolean 类型）
    if (body && typeof body === 'object' && 'success' in body) {
      if (!body.success) {
        throw new Error(body.message || '请求失败')
      }
      return body.data
    }
    // 非标准格式，直接返回原始数据
    return body
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
