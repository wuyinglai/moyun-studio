import { ref } from 'vue'
import api from '@/services/api'

const BACKEND_STORAGE_KEY = 'moyun-api-baseurl'

/** 前端自检后端连通性 composable（全局单例） */
const backendReachable = ref(true)
const checking = ref(true)
const customUrl = ref(localStorage.getItem(BACKEND_STORAGE_KEY) || '')

let initialized = false

export function useBackendCheck() {
  /** 执行一次后端连通性检查 */
  async function checkBackend() {
    checking.value = true
    try {
      await api.get('/llm/config', { timeout: 5000 })
      backendReachable.value = true
    } catch {
      backendReachable.value = false
    } finally {
      checking.value = false
    }
  }

  /** 设置自定义后端地址 */
  function setCustomUrl(url: string) {
    const trimmed = url.trim()
    if (trimmed) {
      localStorage.setItem(BACKEND_STORAGE_KEY, trimmed)
    } else {
      localStorage.removeItem(BACKEND_STORAGE_KEY)
    }
    customUrl.value = trimmed
  }

  /** 清除自定义地址，恢复默认（Vite 代理） */
  function resetUrl() {
    localStorage.removeItem(BACKEND_STORAGE_KEY)
    customUrl.value = ''
  }

  // 全局只初始化一次
  if (!initialized) {
    initialized = true
    checkBackend()
  }

  return {
    backendReachable,
    checking,
    customUrl,
    checkBackend,
    setCustomUrl,
    resetUrl,
  }
}
