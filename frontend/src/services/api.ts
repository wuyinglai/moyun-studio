import axios, { type AxiosRequestConfig } from 'axios'
import { useNotificationStore } from '@/stores/notification'

const rawApi = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器：兼容两种格式
// 格式1：{ success: true, data: ..., message: '...' }（标准封装）
// 格式2：直接返回数据（数组/对象/字符串等）
rawApi.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'success' in body) {
      if (!body.success) {
        throw new Error(body.message || '请求失败')
      }
      return body.data
    }
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

/**
 * 根据实际拦截器行为重新类型化的 api 实例
 * 拦截器返回 T（已解包），而非 AxiosResponse<T>
 */
export interface TypedApi {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
}

// 默认导出：类型正确的实例（拦截器已解包响应，返回 T 而非 AxiosResponse<T>）
const api = rawApi as unknown as TypedApi
export default api

// 如需访问原始 AxiosResponse，可导入 rawApi
export { rawApi }
