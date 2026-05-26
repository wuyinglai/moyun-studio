import axios, { type AxiosRequestConfig, type AxiosError } from 'axios'
import { useNotificationStore } from '@/stores/notification'

declare module 'axios' {
  interface AxiosRequestConfig {
    __retryCount?: number
  }
}

const MAX_RETRIES = 3
const RETRY_DELAY_MS = 1000

const rawApi = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：动态 baseURL + 注入重试计数
rawApi.interceptors.request.use((config) => {
  ;config.__retryCount = 0
  // 如果用户在设置中配置了自定义后端地址，覆盖 baseURL
  if (typeof window !== 'undefined') {
    try {
      const customUrl = localStorage.getItem('moyun-api-baseurl')
      if (customUrl) {
        // 用户填的是后端根地址（如 http://127.0.0.1:8001），需要加上 /api 前缀
        config.baseURL = customUrl.replace(/\/+$/, '') + '/api'
      }
    } catch {
      // localStorage 不可用时忽略
    }
  }
  return config
})

// 判断是否可重试
function isRetryable(error: AxiosError): boolean {
  if (!error.response) {
    // 网络错误、断连等
    return true
  }
  const status = error.response.status
  // 5xx 服务器错误、429 限流、408 超时
  return status >= 500 || status === 429 || status === 408
}

// 响应拦截器：自动重试
rawApi.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config
    if (!config || !isRetryable(error)) {
      return Promise.reject(error)
    }

    config.__retryCount = (config.__retryCount || 0) + 1
    if (config.__retryCount >= MAX_RETRIES) {
      return Promise.reject(error)
    }

    // 指数退避
    const delay = RETRY_DELAY_MS * Math.pow(2, config.__retryCount - 1)
    await new Promise((resolve) => setTimeout(resolve, delay))

    // 重试时带上已发送的数据
    return rawApi.request(config)
  }
)

// 记录异常错误的额外信息
function logErrorDetail(err: unknown) {
  if (err instanceof Error) {
    console.error(`[API Error] ${err.name}: ${err.message}\nStack: ${err.stack}`)
  }
}

// 响应拦截器：兼容两种格式 & 错误通知
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
    // 记录详细错误信息到控制台
    logErrorDetail(error)
    const status = error.response?.status
    // 只在 5xx 服务器错误或网络断连时弹出通知，4xx 由调用方自行处理
    const isServerError = !status || status >= 500 || status === 429
    if (isServerError) {
      let message: string
      try {
        message = error.response?.data?.message || error.message || '请求失败'
      } catch {
        message = '请求失败'
      }
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
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
}

// 默认导出：类型正确的实例（拦截器已解包响应，返回 T 而非 AxiosResponse<T>）
const api = rawApi as unknown as TypedApi
export default api

// 如需访问原始 AxiosResponse，可导入 rawApi
export { rawApi }
